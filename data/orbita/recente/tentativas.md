# Chuva de satélite recente (GPM IMERG) sem login novo: as tentativas

Teste de 30 minutos, começado em 2026-11-15 00:37 (Brasília) = 03:37 UTC. Ponto: Rio Verde (GO), latitude -17.79, longitude -50.92.
As respostas brutas de cada consulta ficaram em `bruto/`, nesta pasta.

**Resultado: deu certo, com ressalvas, pelo NASA GIBS (ideia 4).** O programa `baixar_chuva_recente.py` lê a cor do ponto na camada
diária do IMERG e traduz pela tabela de cores oficial. Último dia com dado: **2026-11-13** (2 dias de atraso). Nos 30 dias de março de 2026
a soma deu 250,7 mm contra 250,4 mm do `imerg.csv` (diferença de 0,1%); dia a dia o erro médio foi de 2,9 mm.
Ressalvas: é valor lido de cor (em faixas), dia com menos de 2,4 mm sai como 0, e os dias recentes são do IMERG **Early** (a comparação
de março provavelmente mediu Final contra Final; ver a ideia 4). O caminho com o dado exato continua sendo a conta Earthdata (ver o fim).
As ideias 1, 2, 3, 5 e 6 não deram.

## 1. NASA POWER (00:37)

- Consulta: `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=IMERG_PRECTOT,PRECTOTCORR&community=AG&longitude=-50.92&latitude=-17.79&start=20260718&end=20261115&format=JSON&time-standard=UTC`
- Resposta: HTTP 200 em 0,9 s. Fontes no cabeçalho: MERRA2, GEOSIT, IMERG.
- `IMERG_PRECTOT`: último dia com dado **2026-09-14** (59 dias com dado em 121). Igual ao arquivo guardado: atraso de 62 dias.
- `PRECTOTCORR` (chuva de modelo, não de satélite): último dia com dado **2026-11-13**, atraso de 2 dias. Só referência.
- Lista de parâmetros (`https://power.larc.nasa.gov/api/system/manager/parameters?community=AG&temporal=daily`, HTTP 200):
  de chuva só há `IMERG_PRECTOT`, `IMERG_PRECTOT_COUNT`, `IMERG_PRECLIQUID_PROB` (os três do mesmo IMERG atrasado),
  `PRECTOT`/`PRECTOTCORR` (modelo) e neve. Não existe parâmetro de IMERG Early ou Late.
- Conclusão: pela POWER não há chuva de satélite com atraso curto.

## 2. APIs públicas do GPM (00:37 a 00:40)

- `https://pmmpublisher.pps.eosdis.nasa.gov/opensearch?q=precip_1d&lat=-17.79&lon=-50.92&limit=7&startTime=2026-11-01&endTime=2026-11-14`:
  HTTP 200, mas devolve a página HTML do visualizador ("GPM Precipitation and Applications Viewer - Global"), não dados. A API de busca saiu do ar.
- O endereço antigo dos arquivos (`https://pmmpublisher.pps.eosdis.nasa.gov/products/gpm_1d/export/Global/2026/317/gpm_1d.20261113.tif`):
  HTTP 200 com a mesma página HTML (não é o arquivo).
- O programa do visualizador (`/js/precip_apps_viewer2.min.js`) aponta os downloads para
  `https://jsimpsonhttps.pps.eosdis.nasa.gov/imerg/gis/AAAA/MM/3B-HHR-L.MS.MRG.3IMERG.AAAAMMDD-...V07C.1day.tif` (IMERG Late, soma de 1 dia).
  Teste de `https://jsimpsonhttps.pps.eosdis.nasa.gov/imerg/gis/early/`: **HTTP 401**. Pede o cadastro do PPS (e-mail registrado em registration.pps.eosdis.nasa.gov).
- Pasta pública `https://gpmweb2https.pps.eosdis.nasa.gov/pub/`: HTTP 200, só vídeos, imagens e apresentações; nenhum dado por ponto.
- Conclusão: não há mais caminho sem cadastro no PPS.

## 3. Serviços de imagem ArcGIS da NASA (00:37 a 00:50) · o que chegou mais perto

- `https://gis.earthdata.nasa.gov/image/rest/services?f=json`: HTTP 404. `https://arcgis.gesdisc.eosdis.nasa.gov/authoritative/rest/services?f=json`: sem resposta (estourou 40 s, três vezes).
- Busca no portal do EGIS (`https://gis.earthdata.nasa.gov/portal/sharing/rest/search?q=IMERG&f=json&num=50`): HTTP 200, 24 itens públicos. Dois servem:
  `https://gis.earthdata.nasa.gov/portal/rest/services/GESDISC/GPM_3IMERGHHE/ImageServer` (IMERG **Early**, meia em meia hora, V07) e `.../GESDISC/GPM_3IMERGHH/ImageServer` (Final).
- Descrição do serviço Early (`?f=json` e `/multiDimensionalInfo?f=json`): HTTP 200, grade de 0,1 grau, variável `precipitation`,
  505.488 meias horas de 1998-01-01 até **2026-11-14 23:30 UTC** (atraso de horas). Há um buraco anunciado de 2026-10-04 a 2026-10-10.
- Leitura no ponto, uma meia hora por consulta (pedir várias de uma vez devolve só a primeira):
  `.../ImageServer/getSamples?geometry={"x":-50.92,"y":-17.79,"spatialReference":{"wkid":4326}}&geometryType=esriGeometryPoint&mosaicRule={"multidimensionalDefinition":[{"variableName":"precipitation","dimensionName":"StdTime","values":[1773100800000],"isSlice":true}]}&f=json`
  - 2026-03-10 00:00 UTC: 2,11 mm/h; 00:30: 2,26 mm/h; 2026-09-10 00:00: 0; 2026-11-13 00:00: 0. Resposta em 1 a 2 s. **Funciona.**
  - Qualquer meia hora da 01:00 em diante (testadas 01:00, 06:00, 12:00, 18:00, 23:30 em março, setembro e novembro; em Rio Verde e em outro ponto):
    `{"error":{"code":400,"message":"Invalid or missing input parameters.","details":["No resource could be found at that address. (status code 404)."]}}`.
  - Confirmado por outras duas operações: `identify` devolve `"NoData"` nessas meias horas (o item do catálogo é `2026-069-z48.mrf_2`: um arquivo por dia com 48 fatias),
    e `exportImage` (TIFF de 1 quadradinho) devolve 2,11 e 2,26 nas duas primeiras fatias e um TIFF vazio nas outras.
- Conclusão: o serviço é oficial, sem login e está em dia, mas **só as fatias 00:00 e 00:30 de cada dia têm dado**; não dá para somar o dia. Defeito do lado deles.

## 4. NASA GIBS (00:39 a 00:53)

- `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml`: HTTP 200. Camadas: `IMERG_Precipitation_Rate` (diária, até 2026-11-13)
  e `IMERG_Precipitation_Rate_30min` (até 2026-11-14 21:30 UTC). Só PNG.
- A escala de cores (`https://gibs.earthdata.nasa.gov/colormaps/v1.3/GPM_Precipitation_Rate.xml`) é em mm/hora, com faixas; abaixo de 0,1 mm/h é "Insignificant" (transparente).
- A ficha da camada (`https://gibs.earthdata.nasa.gov/layer-metadata/v1.0/IMERG_Precipitation_Rate.json`): diária; a fonte é o IMERG de meia hora,
  **Early** (GPM_3IMERGHHE) enquanto o dado é recente e **Final** (GPM_3IMERGHH) depois que ele sai.
- Teste (00:51): ladrilho `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/IMERG_Precipitation_Rate/default/2026-03-10/2km/5/11/14.png`, HTTP 200,
  PNG de paleta 512x512; o ponto cai no pixel (175, 500). A cor do ponto existe na tabela em todos os dias testados. Chuva do dia = meio da faixa (mm/h) x 24.
- Comparação com o `imerg.csv` guardado (o da POWER), rodada às 00:53 com o programa (`comparacao/`):

  | período | dias | soma GIBS | soma imerg.csv | diferença | erro médio por dia | correlação |
  |---|---|---|---|---|---|---|
  | 2026-03-01 a 03-30 | 30 | 250,7 mm | 250,4 mm | +0,3 mm (+0,1%) | 2,90 mm | 0,83 |
  | 2026-02-12 a 04-30 | 78 | 417,3 mm | 428,8 mm | -11,5 mm (-2,7%) | 1,87 mm | 0,90 |
  | 2026-02-12 a 09-14 | 213 | 470,8 mm | 506,6 mm | -35,8 mm (-7,1%) | 0,86 mm | 0,92 |

  Deslocando o dia em +1 ou -1 a correlação cai para 0,30 e 0,50: o dia do GIBS é o mesmo dia UTC do `imerg.csv`.
- Resultado para Rio Verde (`rio_verde/`, 2026-10-02 a 2026-11-15): 43 dias com dado de 45, último dia **2026-11-13**, soma 311,9 mm.
  Últimos dias: 11-08 = 11,0 mm; 11-09 = 18,5; 11-11 = 6,2; 11-12 = 3,9; 11-13 = 0; 11-14 e 11-15 ainda sem ladrilho (HTTP 404).
- Ressalvas, medidas ou lidas:
  1. Dia com menos de 0,1 mm/h de média (2,4 mm) é transparente e sai como 0. Por isso a soma fica abaixo na época seca (-7,1% no período todo).
  2. O valor vem em faixas de uns 6% de largura (222 faixas de 0,1 a 53 mm/h).
  3. Março já deve estar com o IMERG Final no GIBS, igual à POWER; então a tabela acima prova a leitura da cor, **não** a diferença entre o Early
     (o que vem nos dias recentes) e o Final. Essa diferença não foi medida aqui: não há dia recente no `imerg.csv` para comparar.
  4. Faltam no GIBS 2026-05-25 e 05-26 (sem ladrilho).
- Conclusão: **serve como caminho sem login para "como está a lavoura hoje"**, sabendo que é leitura de cor do IMERG Early.

## O que faltaria para ter o dado exato (5 linhas)

1. Uma conta Earthdata (grátis, `https://urs.earthdata.nasa.gov/users/new`), criada pelo Juca, com o aplicativo "NASA GESDISC DATA ARCHIVE" autorizado.
2. O usuário e a senha (ou o token) no `.env` da V4 ou num `~/.netrc` (`machine urs.earthdata.nasa.gov`).
3. O endereço: OPeNDAP do IMERG Late diário, `https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDL.07/AAAA/MM/3B-DAY-L.MS.MRG.3IMERG.AAAAMMDD-S000000-E235959.V07C.nc4.ascii?precipitation[0:0][LON:LON][LAT:LAT]` (Early: `GPM_3IMERGDE.07` e `3B-DAY-E`).
4. O catálogo aberto do CMR já mostra o dia 2026-11-13 publicado nos dois (atraso de 2 dias), em mm/dia e sem faixa de cor.
5. Alternativa sem conta Earthdata: o cadastro de e-mail do PPS (`registration.pps.eosdis.nasa.gov`) abre `jsimpsonhttps.pps.eosdis.nasa.gov/imerg/gis/` (GeoTIFF de 1 dia do Late).

## 5. GES DISC (00:50)

- `grep` dos nomes no `.env` da V4 por earthdata|nasa|gesdisc|urs: nada. `~/.netrc`: não existe. **Não há credencial Earthdata na máquina.**
- OPeNDAP (`https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDL.07/2026/11/3B-DAY-L.MS.MRG.3IMERG.20261113-S000000-E235959.V07C.nc4.ascii?...`):
  HTTP 302 para `urs.earthdata.nasa.gov/oauth/authorize`. **Pede conta Earthdata.**
- O catálogo CMR, que é aberto (`https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGDL&sort_key=-start_date&page_size=2` e `GPM_3IMERGDE`):
  HTTP 200; o IMERG diário Early e o Late já têm o dia **2026-11-13** publicado (atraso de 2 dias). O dado existe; só o download pede login.
- Data Rods (`hydro1.gesdisc.eosdis.nasa.gov/daac-bin/access/timeseries.cgi`): HTTP 301 para o aviso de que o serviço foi desligado.

## 6. Outros caminhos oficiais (00:40 a 00:42)

- ClimateSERV, do SERVIR/NASA (`https://climateserv.servirglobal.net/api/submitDataRequest/?datatype=26...`, 26 = IMERG Early de 1 dia): HTTP 200, sem login, e
  devolve a série por ponto para janeiro de 2024 (20 dias, ex.: 2024-01-20 = 33,5 mm). Para outubro e novembro de 2026 devolve lista vazia, e o conjunto de controle
  (CHIRPS, datatype 0) também. O serviço responde, mas parou de receber dado novo. Não serve.
