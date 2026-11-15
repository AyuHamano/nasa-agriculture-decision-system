# O verde visto pelo satélite (NDVI) em 6 pontos perto de Rio Verde (GO)

> Gerado com IA (Claude). Os 6 CSV são cópia fiel do que foi baixado; quem lê é `backend/orbita/ndvi.py`.

O NDVI é um índice de 0 a 1 que o satélite mede: perto de 1, muita planta verde; perto de 0,2, quase nenhuma.
Aqui ele serve de prova só da rotação de hoje: por quantos dias seguidos, de junho em diante, cada ponto fica
"sem planta verde".

## A fonte
- **O produto:** MOD13Q1 v061 (MODIS/Terra Vegetation Indices 16-Day L3 Global 250m), da NASA (LP DAAC):
  https://doi.org/10.5067/MODIS/MOD13Q1.061 · uma medida a cada 16 dias, pixel de 250 m.
- **O espelho por onde vieram:** Microsoft Planetary Computer, coleção `modis-13Q1-061`
  (https://planetarycomputer.microsoft.com/dataset/modis-13Q1-061), sem login.
- **As consultas** (feitas em 2026-11-14, por volta das 18h04):
  - a lista das imagens: `POST https://planetarycomputer.microsoft.com/api/stac/v1/search`, com a coleção
    `modis-13Q1-061`, o ponto, a plataforma `terra` e o período de 2018-07-01 a 2026-10-31;
  - o valor no ponto: `GET https://planetarycomputer.microsoft.com/api/data/v1/item/point/{lon},{lat}`, com as
    camadas `250m_16_days_NDVI` e `250m_16_days_pixel_reliability` de cada imagem.

## Os pontos (aviso)
Os 6 pontos foram **escolhidos no mapa**, a 15 ou 20 km de Rio Verde: não se sabe de quem são nem o que foi
plantado em cada um. Não são lavouras conhecidas do time.

| arquivo | latitude, longitude |
|---|---|
| `sul.csv` | -17.95, -50.95 |
| `norte.csv` | -17.65, -50.90 |
| `oeste.csv` | -17.80, -51.10 |
| `leste.csv` | -17.85, -50.72 |
| `sudoeste.csv` | -17.93, -51.12 |
| `noroeste.csv` | -17.62, -51.05 |

## As colunas
- `Date`: o primeiro dia dos 16 dias da medida.
- `ndvi_bruto`: o NDVI multiplicado por 10.000 (dividir por 10.000); -3000 quer dizer "sem dado".
- `pixel_reliability`: a qualidade da medida. 0 é boa e 1 é aceitável (só essas valem); 2 é neve e 3 é nuvem.
- `item`: o nome da imagem de onde o valor saiu. `lat`, `lon`: o ponto.

## Os buracos
- Cada arquivo tem 154 medidas, de 2018-06-26 a 2026-10-16.
- O espelho não tem imagem **de 2024-02-18 a 2025-06-10** nem **de 2025-06-26 a 2025-11-17** (as datas são a
  última medida antes e a primeira depois de cada buraco). Por isso 2024 e 2025 não entram na conta dos dias.
- Falta também a medida de 2023-02-18 (fora da época que a conta olha).
- Medidas com nuvem (`pixel_reliability` 3), que a conta não usa: de 2 a 10 por ponto. Nenhuma linha destes
  arquivos tem -3000.
- 2026 vai só até 2026-10-16: é "ano em andamento", mostrado à parte e fora da mediana.

## Como ler
"Sem planta verde" **não é** "terra descoberta": o satélite mede o verde das folhas e não vê a palha.

## Jataí e Silvânia (entraram em 2026-11-15)
O mesmo produto e o mesmo espelho, agora em 6 pontos perto de cada uma das duas cidades. Os arquivos ficam em
`data/orbita/cidades/jatai/ndvi/` e `data/orbita/cidades/silvania/ndvi/` (o motor lê de lá sozinho).

- **O programa:** `baixar_ndvi.py`, nesta pasta (só a biblioteca padrão do Python). Como rodar de novo:
  `python3 -I baixar_ndvi.py --cidade jatai --lat=-17.88 --lon=-51.71 --saida ../cidades/jatai/ndvi` e
  `python3 -I baixar_ndvi.py --cidade silvania --lat=-16.66 --lon=-48.61 --saida ../cidades/silvania/ndvi --distancias 15,20,25`.
- **Quando:** Jataí, das 02h05 às 02h06; Silvânia, das 02h09 às 02h10 (horário de Brasília, 2026-11-15).
- **O endereço e a hora de cada consulta:** no `fonte.json` de cada pasta (a busca no catálogo e a conferência no
  mapa, uma a uma) e na coluna `consultado_em_utc` de cada CSV (a hora de cada medida; o endereço é o modelo que
  está no `fonte.json`, com o nome da imagem que está na coluna `item`).

### Como os pontos foram escolhidos (aviso)
Os pontos foram **escolhidos no mapa**, por uma regra escrita antes de ver o NDVI de qualquer um deles. **Não se
sabe de quem são nem o que foi plantado em cada um, e ninguém conferiu em campo.**
1. Os candidatos: a 15 e a 20 km do ponto da cidade, em 8 direções, na ordem norte, leste, sul, oeste, nordeste,
   sudeste, sudoeste, noroeste (primeiro os de 15 km).
2. O mapa: o mapa anual de uso da terra de 10 m (`io-lulc-annual-v02`, da Impact Observatory, Esri e Microsoft, no
   mesmo espelho). Passa o candidato em que o centro e 4 lugares a uns 110 m dele são "lavoura" (classe 5, Crops)
   nos mapas de 2018 e de 2023. O mapa diz "lavoura", não diz qual; e mapa erra.
3. Ficam os 6 primeiros que passam. Em Jataí passaram 7 dos 16. Em Silvânia só 4 dos 16: entrou mais uma volta de
   candidatos, a 25 km, e os 2 primeiros que passaram completaram os 6 (em volta de Silvânia há mais pasto e mata).

| cidade | arquivo | latitude, longitude |
|---|---|---|
| Jataí | `sul-15km.csv` | -18.015, -51.710 |
| Jataí | `nordeste-15km.csv` | -17.785, -51.610 |
| Jataí | `norte-20km.csv` | -17.700, -51.710 |
| Jataí | `leste-20km.csv` | -17.880, -51.521 |
| Jataí | `oeste-20km.csv` | -17.880, -51.899 |
| Jataí | `nordeste-20km.csv` | -17.753, -51.577 |
| Silvânia | `oeste-15km.csv` | -16.660, -48.751 |
| Silvânia | `sudoeste-15km.csv` | -16.755, -48.709 |
| Silvânia | `norte-20km.csv` | -16.480, -48.610 |
| Silvânia | `sudeste-20km.csv` | -16.787, -48.477 |
| Silvânia | `nordeste-25km.csv` | -16.501, -48.444 |
| Silvânia | `sudeste-25km.csv` | -16.819, -48.444 |

### O que veio e os buracos
- Cada arquivo tem 154 medidas, de 2018-06-26 a 2026-10-16, com os mesmos buracos do espelho que Rio Verde tem
  (de 2024-02-18 a 2025-06-10 e de 2025-06-26 a 2025-11-17): 2024 e 2025 não entram na conta.
- Medidas com nuvem, que a conta não usa: de 6 a 14 por ponto em Jataí e de 5 a 9 em Silvânia. Por causa delas, em
  Jataí 2 pontos ficam de fora em 2019, em 2021 e em 2022, e em Silvânia 1 ponto fica de fora em 2018.
- O que a conta do motor dá (a mesma regra de Rio Verde, o limite de 20% da amplitude de cada ponto, que é
  hipótese): em Jataí, a mediana é de 80 dias seguidos sem planta verde (30 medidas, de 0 a 128 dias); em Silvânia,
  96 dias (35 medidas, de 16 a 192 dias). Em Rio Verde continua 96 (36 medidas, de 16 a 160). O calendário diz 122.
- O outro caminho oficial, o serviço de recortes do MODIS do ORNL DAAC (`modis.ornl.gov/rst/api/v1/`), respondeu
  503 (fora do ar) em 2026-11-15 às 02h03, como em 2026-11-14: não deu para tapar os buracos por ele.
