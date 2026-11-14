<!-- Gerado com IA (Claude) -->
# Os dados para cruzar (cópia)

Cópia, sem mudança, do que a frente dos dados baixou em 2026-11-14 para conferir o motor (ponto -17.79, -50.92, de
2014-07-01 a 2026-10-31). O endereço e a hora de cada consulta estão nos arquivos `fonte*.json` e no
`LEIA-ME-da-validacao-cruzada.md` (o LEIA-ME original, com os programas de baixar citados lá).

| arquivo aqui | o que é | colunas |
|---|---|---|
| `chuva/open-meteo.csv` | Open-Meteo (o arquivo histórico), com a ETo do FAO | `data,chuva_mm,tmax_c,tmin_c,eto_mm` |
| `chuva/era5.csv` | Open-Meteo com o modelo ERA5 (lá se chama `open-meteo-era5.csv`) | as mesmas |
| `chuva/imerg.csv` | a chuva de satélite GPM IMERG, da NASA | `data,chuva_mm` |
| `chuva/chirps.csv` | a chuva de satélite com estações CHIRPS | `data,chuva_mm` |
| `chuva/inmet.csv` | a chuva medida em terra, a estação do INMET de Rio Verde (lá fica em `inmet/inmet.csv`) | `data,chuva_mm` |
| `ibge/rendimento_rio_verde.csv` | IBGE, Produção Agrícola Municipal, Rio Verde | `ano,produto,rendimento_kg_ha,area_colhida_ha,producao_t` |

Dia sem dado fica em branco e nunca vira zero. O motor usa `imerg`, `chirps` e `era5` como fonte de chuva opcional
(`--chuva`); a temperatura é sempre a da NASA POWER. O `python3 -m orbita.validar` lê tudo daqui.
