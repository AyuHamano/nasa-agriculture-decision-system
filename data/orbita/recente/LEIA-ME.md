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

## O caminho para o dado exato (próximo passo)
Uma conta Earthdata (grátis), para ler o IMERG diário em mm no GES DISC (o catálogo aberto mostra o dia 2026-11-13 já
publicado nas versões Early e Late). O que foi tentado e o que cada serviço respondeu está em `tentativas.md`.
