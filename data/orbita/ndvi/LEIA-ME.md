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
