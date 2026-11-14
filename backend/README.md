# API do backend

API MVP para receber a localização e a rotação de uma propriedade, consultar o
histórico climático da NASA POWER e enviar esse contexto ao Gemini.

## Requisitos

- Python 3.10 ou superior
- Uma chave da API Gemini

## Instalação

Execute os comandos na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Crie o arquivo `.env` na raiz do repositório, usando `.env.example` como modelo,
e configure a chave:

```env
GEMINI_API_KEY=sua_chave
```

Não versione nem compartilhe o `.env`.

## Executar

Ainda na raiz do repositório:

```bash
uvicorn backend.api:app --reload
```

- Verificação: <http://127.0.0.1:8000/health>
- Documentação interativa: <http://127.0.0.1:8000/docs>

## Consultar recomendações

Envie `POST /api/recommendations` com um ponto representativo da propriedade:
`latitude` e `longitude` em graus decimais. Se o mapa tiver vários polígonos, o
frontend deve calcular um ponto central e enviar somente esse par de coordenadas.

```bash
curl -X POST http://127.0.0.1:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "location_name": "Fazenda Teste",
    "latitude": -28.7,
    "longitude": -52.8,
    "rotation": ["milho", "feijão", "milho safrinha"],
    "priorities": ["economia de água", "renda extra"],
    "start_year": 2015,
    "end_year": 2025
  }'
```

`start_year` e `end_year` são opcionais (padrões: 2015 e 2025) e devem ser
iguais ou posteriores a 1981. A API consulta NASA POWER no ponto enviado e inclui
o resumo no contexto enviado ao Gemini. A resposta contém `context` (localização,
rotação, prioridades e evidências) e `recommendation`. Os dados da NASA POWER
são armazenados em `data/cache/` por ponto e período.

## Fontes incluídas nesta versão

- **NASA POWER:** consultada para as coordenadas e o período informados.
- **MODIS e SMAP:** pausadas nesta versão; a API as indica como não consultadas.

NASA POWER fornece contexto climático histórico em grade, não medições diretas
do talhão nem previsão meteorológica. As recomendações do Gemini são apoio à
decisão e devem ser validadas com conhecimento agronômico local.
