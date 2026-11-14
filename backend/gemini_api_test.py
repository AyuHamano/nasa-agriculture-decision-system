
import argparse
import json
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv
import requests

DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_MAX_OUTPUT_TOKENS = 200
DEFAULT_CIDADE = "Rio Verde, GO"
DEFAULT_CULTURAS = "soja -> milho safrinha -> pousio"
DEFAULT_PRIORIDADES = "renda extra, solo/nitrogênio, erosão"
DEFAULT_LATITUDE = -17.7923
DEFAULT_LONGITUDE = -50.9190
DEFAULT_ANO_INICIO = 2020
DEFAULT_ANO_FIM = 2025
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMS = ["T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "EVLAND"]

SYSTEM_INSTRUCTION = """
Você é um assistente agronômico de apoio à decisão para produtores brasileiros.
Sua prioridade obrigatória e permanente é ECONOMIZAR ÁGUA. Essa prioridade nunca
pode ser removida, substituída ou colocada abaixo das preferências opcionais do
usuário. Dê recomendações práticas, objetivas e adequadas à localização e à
sequência de culturas informadas. Não invente medições climáticas, produtividade,
preços ou garantias de resultado. Quando faltarem dados, declare as suposições e
indique quais dados devem ser consultados. Responda em português do Brasil.
""".strip()

# Carrega a chave do arquivo .env na raiz do projeto. O arquivo e ignorado pelo Git.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
load_dotenv(PROJECT_ROOT / ".env")

def _nome_cache(latitude: float, longitude: float, ano_inicio: int, ano_fim: int) -> Path:
    """Gera um nome de cache específico para o ponto e período."""
    ponto = f"{latitude:.4f}_{longitude:.4f}".replace("-", "m").replace(".", "p")
    return CACHE_DIR / f"power_{ponto}_{ano_inicio}_{ano_fim}.json"


def _valores_validos(valores: dict[str, float]) -> list[float]:
    return [float(valor) for valor in valores.values() if float(valor) > -900]


def obter_resumo_nasa_power(
    latitude: float, longitude: float, ano_inicio: int, ano_fim: int
) -> str:
    """Busca dados diários da NASA POWER, usa cache e resume indicadores úteis."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    arquivo_cache = _nome_cache(latitude, longitude, ano_inicio, ano_fim)

    if arquivo_cache.exists():
        dados = json.loads(arquivo_cache.read_text(encoding="utf-8"))
        origem = "cache local"
    else:
        resposta = requests.get(
            NASA_POWER_URL,
            params={
                "parameters": ",".join(NASA_PARAMS),
                "community": "AG",
                "latitude": latitude,
                "longitude": longitude,
                "start": f"{ano_inicio}0101",
                "end": f"{ano_fim}1231",
                "format": "JSON",
                "time-standard": "LST",
            },
            timeout=60,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        arquivo_cache.write_text(json.dumps(dados), encoding="utf-8")
        origem = "NASA POWER"

    try:
        parametros = dados["properties"]["parameter"]
        chuva = _valores_validos(parametros["PRECTOTCORR"])
        evap = _valores_validos(parametros["EVLAND"])
        temp = _valores_validos(parametros["T2M"])
        minimas = _valores_validos(parametros["T2M_MIN"])
        maximas = _valores_validos(parametros["T2M_MAX"])
    except (KeyError, TypeError, ValueError) as erro:
        raise RuntimeError("Resposta da NASA POWER não contém os indicadores esperados.") from erro

    if not all([chuva, evap, temp, minimas, maximas]):
        raise RuntimeError("A NASA POWER retornou dados insuficientes para este ponto e período.")

    anos = ano_fim - ano_inicio + 1
    chuva_anual = sum(chuva) / anos
    evap_anual = sum(evap) / anos
    geadas_ano = sum(valor <= 2 for valor in minimas) / anos
    calor_ano = sum(valor >= 35 for valor in maximas) / anos

    return (
        f"Fonte: {origem}; NASA POWER, ponto {latitude:.4f}, {longitude:.4f}, "
        f"período histórico {ano_inicio}-{ano_fim}. "
        f"Temperatura média: {sum(temp) / len(temp):.1f} °C. "
        f"Chuva média anual: {chuva_anual:.0f} mm. "
        f"Evaporação terrestre média anual: {evap_anual:.0f} mm. "
        f"Saldo hídrico simplificado (chuva - evaporação): {chuva_anual - evap_anual:.0f} mm/ano. "
        f"Dias médios por ano com mínima <= 2 °C: {geadas_ano:.1f}; "
        f"com máxima >= 35 °C: {calor_ano:.1f}."
    )


def montar_prompt(cidade: str, culturas: str, prioridades: str, dados_nasa: str) -> str:
    """Monta a solicitação sem permitir a remoção da economia de água."""
    prioridades_opcionais = prioridades.strip() or "nenhuma informada"
    return f"""
Analise o cenário agrícola a seguir:

- Localização: {cidade}
- Sequência atual de culturas: {culturas}
- Prioridade fixa do sistema: economizar água
- Prioridades adicionais do usuário: {prioridades_opcionais}
- Indicadores climáticos históricos calculados: {dados_nasa}

Entregue a resposta neste formato:
1. Diagnóstico resumido do cenário.
2. Plano para economizar água em cada etapa da sequência de culturas.
3. Recomendações que conciliem economia de água com as prioridades adicionais.
4. Principais riscos e cuidados, incluindo solo, nitrogênio e erosão quando relevantes.
5. Próxima ação recomendada ao produtor.

Use linguagem simples e ações concretas. Diferencie recomendações gerais de
conclusões que exigiriam dados locais ou climáticos ainda não fornecidos.
Use os números da NASA POWER como base climática histórica, sem tratá-los como
previsão meteorológica atual.
""".strip()


def gerar_resposta(prompt: str, model: str, max_output_tokens: int) -> str:
    """Envia um prompt ao Gemini e retorna somente o texto gerado."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY nao foi definida. No PowerShell, execute: "
            '$env:GEMINI_API_KEY = "sua_chave"'
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            max_output_tokens=max_output_tokens,
        ),
    )

    if not response.text:
        raise RuntimeError("O Gemini retornou uma resposta sem texto.")
    return response.text


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera recomendações agrícolas com o Gemini.")
    parser.add_argument("--cidade", default=DEFAULT_CIDADE, help="Cidade ou região da propriedade")
    parser.add_argument("--lat", type=float, default=DEFAULT_LATITUDE, help="Latitude do ponto no mapa")
    parser.add_argument("--lon", type=float, default=DEFAULT_LONGITUDE, help="Longitude do ponto no mapa")
    parser.add_argument("--culturas", default=DEFAULT_CULTURAS, help="Sequência atual de culturas")
    parser.add_argument(
        "--prioridades",
        default=DEFAULT_PRIORIDADES,
        help="Prioridades adicionais; economizar água já é sempre obrigatório",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Gemini a usar")
    parser.add_argument("--ano-inicio", type=int, default=DEFAULT_ANO_INICIO, help="Início da série NASA POWER")
    parser.add_argument("--ano-fim", type=int, default=DEFAULT_ANO_FIM, help="Fim da série NASA POWER")
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help="Limite de tokens da resposta (padrão: 200)",
    )
    args = parser.parse_args()
    if args.ano_inicio > args.ano_fim:
        parser.error("--ano-inicio não pode ser maior que --ano-fim")

    try:
        dados_nasa = obter_resumo_nasa_power(args.lat, args.lon, args.ano_inicio, args.ano_fim)
        prompt = montar_prompt(args.cidade, args.culturas, args.prioridades, dados_nasa)
        resposta = gerar_resposta(prompt, args.model, args.max_output_tokens)
    except Exception as error:
        print(f"Erro ao chamar o Gemini: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Modelo: {args.model} | Limite de saída: {args.max_output_tokens} tokens")
    print("Prioridade fixa: economizar água\n")
    print(f"Dados climáticos: {dados_nasa}\n")
    print(resposta)


if __name__ == "__main__":
    main()
