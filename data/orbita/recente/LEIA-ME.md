<!-- Gerado com IA (Claude) -->
# A chuva recente do satélite (para o "como está hoje")

- **O que é:** a chuva de cada dia, de 2026-09-01 a 2026-11-13, no ponto de cada cidade do motor (`rio_verde/`,
  `jatai/` e `silvania/`), no arquivo `chuva-recente.csv` (colunas `data,chuva_mm`). Quem lê é `backend/orbita/hoje.py`.
- **Por que existe:** a chuva do satélite GPM IMERG que o motor usa vem pela NASA POWER e chega com cerca de 2 meses
  de atraso (último dia com dado: 2026-09-14). Para dizer como está a lavoura hoje é preciso um caminho mais rápido.
- **A fonte:** NASA GIBS (o serviço de imagens da NASA, o mesmo do Worldview), camada diária
  `IMERG_Precipitation_Rate`, sem login. Exemplo de endereço:
  `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/IMERG_Precipitation_Rate/default/2026-11-13/2km/5/11/14.png`.
  O GIBS só entrega imagem: o programa lê a cor do ponto e traduz pela tabela de cores oficial
  (`https://gibs.earthdata.nasa.gov/colormaps/v1.3/GPM_Precipitation_Rate.xml`). A chuva do dia é o meio da faixa de
  mm/hora vezes 24.
- **O endereço e a hora de cada consulta:** em `fonte.json`, na pasta de cada cidade (um registro por dia; hora em UTC).
  Baixado em 2026-11-15, por volta de 01h09 (horário de Brasília).
- **Como baixar de novo**, de dentro desta pasta:
  `python3 -I baixar_chuva_recente.py --inicio 2026-09-01 --fim 2026-11-15 -- -17.79 -50.92 rio_verde`
  (as opções vêm antes do `--`, porque a latitude e a longitude são números negativos).

## As ressalvas (ler antes de usar)
- **É valor lido de cor, em faixas:** cada faixa tem uns 6% de largura.
- **Chuva fraca some:** dia com menos de 2,4 mm (0,1 mm por hora de média) é transparente na camada e sai como 0.
- **É a versão rápida do IMERG (Early) nos dias recentes**, que a NASA corrige depois. A diferença entre a versão rápida
  e a final não foi medida aqui.
- **O que foi medido no teste** (Rio Verde, contra a chuva guardada do IMERG pela NASA POWER): em 30 dias de março de
  2026, a soma bateu (250,7 contra 250,4 mm); em 213 dias (de 2026-02-12 a 2026-09-14), ficou 7,1% abaixo (470,8
  contra 506,6 mm); dia a dia, a correlação foi de 0,92.
- **Nos dias recentes os dois caminhos discordam bastante:** em Rio Verde, de 2026-09-15 a 2026-11-11, esta chuva soma
  411,0 mm e a chuva de modelo da NASA POWER (PRECTOTCORR), 146,5 mm. Por isso o `como_esta_hoje` devolve a conta com
  as duas e a faixa entre elas. A chuva de modelo ficou bem abaixo da estação em terra de Rio Verde de 2021 para cá.
- **O dia é o dia UTC.** Dia sem imagem (ainda não publicada) fica em branco e nunca vira zero.

## O caminho para o dado exato de cada dia (próximo passo)
Uma conta Earthdata (grátis), para ler o IMERG diário em mm no GES DISC (o catálogo aberto mostra o dia 2026-11-13 já
publicado nas versões Early e Late). O que foi tentado e o que cada serviço respondeu está em `tentativas.md`.

## A mesma chuva em mm, de 5 em 5 dias (teste de 2026-11-15, 02h06 a 02h09)
Achado um caminho sem login com o valor em mm, sem ler cor: o GPM IMERG **Late** V07 somado de 5 em 5 dias (pêntada),
no servidor de dados do Climate Hazards Center da Universidade da Califórnia em Santa Barbara (o grupo do CHIRPS):
`https://data.chc.ucsb.edu/products/EWX2/IMERGlatev7/imerglatev7_global_pentad_data/data_AAAAMMDD_AAAAMMDD.tif`.
**Não é um servidor da NASA: é um espelho do produto da NASA.** O programa é `baixar_imerg_5_dias.py` (usa Pillow e
numpy para abrir a imagem; é o único daqui com biblioteca de fora, e o motor não depende dele). Ele grava
`chuva-5-dias.csv` (`inicio,fim,chuva_mm`) e `fonte-5-dias.json` (o endereço e a hora de cada consulta) em cada cidade.

- **O atraso:** em 2026-11-15 a última pêntada publicada era a de 06 a 10 de novembro (5 dias de atraso; no pior dia
  do ciclo chega a 9). A leitura da cor tem 2 dias. Falta o arquivo de 11 a 15 de outubro de 2026 (HTTP 404).
- **A unidade foi conferida, não suposta:** em Rio Verde, em 42 pêntadas de 2026-02-11 a 2026-09-10, a soma deu
  526,1 mm contra 528,2 mm do IMERG guardado da NASA POWER (0,4% de diferença; 0,1 mm de erro médio por pêntada).
  É a mesma chuva, em mm por pêntada.
- **A leitura da cor está certa:** de 2026-09-01 a 2026-11-10 (13 pêntadas), a cor somou 397,8 mm e o mm, 437,2 mm
  em Rio Verde (9,0% a menos); em Jataí, 416,8 contra 397,0 (5,0% a mais); em Silvânia, 398,0 contra 353,4 (12,6% a
  mais). Ou seja: a chuva rápida dar o dobro da chuva de modelo **não é erro da leitura da cor**.
- **Contra a estação em terra** (INMET de Rio Verde, A025; 10 pêntadas de 2026-09-01 a 2026-10-25, as em que os
  quatro têm dado):

  | fonte | soma | contra a estação | erro médio por pêntada |
  |---|---|---|---|
  | a estação do INMET | 202,0 mm | | |
  | o satélite em mm (IMERG Late) | 278,7 mm | 38,0% a mais | 14,8 mm |
  | o satélite lido da cor (NASA GIBS) | 266,2 mm | 31,8% a mais | 16,7 mm |
  | a chuva de modelo (NASA POWER, PRECTOTCORR) | 111,6 mm | 44,8% a menos | 16,4 mm |

  A estação fica no meio: o satélite deu mais chuva do que ela e o modelo, menos. É um período curto (50 dias), uma
  estação só, e a estação mede um ponto enquanto o satélite mede um quadrado de uns 10 km.
- **A decisão:** a fonte do `como_esta_hoje` **não foi trocada**. O caminho novo não é claramente melhor: vem de 5
  em 5 dias (a conta precisa da chuva de cada dia), chega mais tarde e discorda da cor em menos de 13%. O que
  entrou foi a conferência: `chuva_recente.conferencia_em_mm`, na resposta do `como_esta_hoje`, mostra as duas somas
  lado a lado. A faixa larga continua, e agora se sabe por quê: ela é a distância entre o satélite e o modelo, e a
  estação caiu entre os dois.
- **Como baixar de novo:** `python3 -I baixar_imerg_5_dias.py --inicio 2026-02-11 --fim 2026-11-15`.
