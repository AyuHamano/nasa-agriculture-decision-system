<!-- Gerado com IA (Claude) -->
# A série da NASA POWER de Rio Verde (GO)

- **O que é:** a chuva (`PRECTOTCORR`, mm/dia), a temperatura máxima (`T2M_MAX`, °C) e a mínima (`T2M_MIN`, °C) de cada
  dia, de 1981-01-01 a 2026-11-13, no ponto -17.79, -50.92 (Rio Verde, GO). O quadrado da NASA POWER tem uns 50 km.
- **A fonte:** NASA POWER (Prediction Of Worldwide Energy Resources), a API diária, comunidade AG, grátis e sem login.
- **O endereço da consulta:** está em `consulta.txt`.
- **A hora em que foi baixada:** está em `baixado-em.txt` (2026-11-14, 13h42, horário de Brasília).
- **De onde veio esta cópia:** dos arquivos `resposta.json`, `consulta.txt` e `baixado-em.txt` que a conversa do projeto
  baixou e conferiu antes (a pasta `verificacao/nasa-power/` do projeto do time no hackathon). Copiados sem mudar nada.
- **Dia sem dado:** vem como -999. Na série baixada, só os 2 últimos dias (2026-11-12 e 2026-11-13) estão assim; o motor
  para no último dia com os três valores.
- **Atenção:** a chuva de 2025 nesta série é suspeita de baixa (678 mm no ano). A safra 2025-26 é calculada à parte, com
  o aviso "a conferir".
- **Como baixar de novo:** abrir o endereço de `consulta.txt` (ou `curl -o resposta.json "<o endereço>"`).
