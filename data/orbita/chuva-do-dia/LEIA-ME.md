<!-- Gerado com IA (Claude) -->
# A chuva do dia: a chuva do satélite até ontem, em mm, por cidade

**O que é.** Um programa que baixa a chuva do satélite GPM IMERG V07 (NASA/JAXA) e guarda, para cada cidade do motor
(Rio Verde, Jataí e Silvânia, nas mesmas coordenadas de `backend/orbita/motor.py`), um arquivo simples com a chuva de
cada dia em mm. Serve para o "como está hoje" ficar em dia: às 8h de Brasília o arquivo já tem o dia de ontem.
**O motor ainda não usa esta pasta**: a troca está descrita no fim e é decisão do time.

**De onde vem.** Não é um servidor da NASA. É a **cópia dos arquivos da NASA** (GES DISC e PPS) de meia em meia hora
que a **dynamical.org** mantém num balde aberto da Amazon (`s3://dynamical-nasa-imerg`, ficha
https://registry.opendata.aws/dynamical-nasa-imerg/), sem login. Licença **CC BY 4.0**; a citação pedida é
"NASA IMERG from dynamical.org". Duas versões: o **Early** (chega umas 5 horas depois) e o **Late** (umas 15 horas
depois, mais acertado). O endereço, a versão do dado e a hora de cada consulta ficam no `fonte.json` de cada cidade.

**Os arquivos.**
- `<cidade>/chuva-do-dia.csv`: `data`, `chuva_early_mm`, `chuva_late_mm`. Dia sem dado fica em branco, nunca zero. O
  dia de hoje não entra, por estar incompleto.
- `<cidade>/fonte.json`: de onde veio, a conta, a regra do dia e as consultas (endereço, hora UTC, snapshot).
- `baixar_chuva_do_dia.py` (precisa das 4 bibliotecas de `requisitos.txt`), `ler.py` (Python puro: o leitor),
  `test_ler.py` e `test_baixar.py` (sem internet).

**A regra do dia.** O arquivo traz a taxa de cada meia hora em kg m-2 s-1 (= mm por segundo); a chuva da meia hora é
a taxa x 1800. O rótulo da meia hora é o **início** dela, em UTC. O dia é o **de Brasília** (UTC-3): o dia D soma as
48 meias horas que começam de D 03:00 UTC a D+1 02:30 UTC. Dia com menos de 48 fica em branco.
**Conferida em 2026-11-15:** Rio Verde, de 01/09 a 30/10/2026 (60 dias, todos com dado), somou **353,0 mm no Early e
347,4 mm no Late**, os mesmos totais do teste da chuva recente; e os 90 dias do Early (89 do Late) saíram iguais, dia
por dia, aos daquele teste. A regra do rótulo foi deduzida naquele teste (a soma do dia UTC bate com a NASA POWER);
não está escrita na documentação da dynamical.

**Como rodar** (da raiz do repositório). O ambiente virtual fica fora do repositório:
```
python3 -m venv ~/.cache/orbita-rural/venv-chuva-do-dia
~/.cache/orbita-rural/venv-chuva-do-dia/bin/pip install -r data/orbita/chuva-do-dia/requisitos.txt
~/.cache/orbita-rural/venv-chuva-do-dia/bin/python -I data/orbita/chuva-do-dia/baixar_chuva_do_dia.py
```
Leva uns 15 segundos. Outras formas: `--cidade rio_verde` (só uma) e `--ponto LATITUDE LONGITUDE --pasta SAIDA` (um
ponto qualquer, numa pasta de fora). Ver na tela: `python3 -I data/orbita/chuva-do-dia/ler.py rio_verde --dias 10`.
Os testes: `python3 -I data/orbita/chuva-do-dia/test_ler.py` e `python3 -I data/orbita/chuva-do-dia/test_baixar.py`.

**De quanto em quanto tempo.** Uma vez por dia, depois das 6h de Brasília, já traz o dia de ontem no Early (ele
fecha por volta das 5h). O Late de ontem só fecha por volta das 15h: a rodada do dia seguinte o traz. A primeira
rodada baixa 90 dias; as seguintes só acrescentam os dias novos e baixam de novo os últimos 3 do arquivo (e o que
estiver em branco nos últimos 90). Se a rede falhar, o programa avisa e o arquivo de antes não muda. Nada aqui roda
sozinho: não há rotina agendada.

## A troca que o motor precisaria (não foi feita)
Hoje a chuva recente entra em `backend/orbita/hoje.py` (linhas do commit 061394b), lida da cor da imagem do NASA GIBS:
- **`ler_chuva_recente`, linhas 39 a 57**: abre `data/orbita/recente/<cidade>/chuva-recente.csv` (linha 42) e lê a
  coluna `chuva_mm` (linha 48). É a única leitura; `como_esta_hoje` chama na **linha 161** e passa a
  `esticar` na **linha 168**.

A troca, em poucas linhas, sem biblioteca nova (o motor lê o CSV com o `csv` que já usa):
1. Depois da linha 24, uma pasta nova: `PASTA_DA_CHUVA_DO_DIA = clima.PASTA_DOS_DADOS / "chuva-do-dia"`; na linha
   41, usar essa pasta no lugar de `PASTA_DA_CHUVA_RECENTE` (que continua valendo para o `chuva-5-dias.csv`).
2. Linha 42: `"chuva-do-dia.csv"`. Linha 48: pegar `chuva_late_mm` e, se estiver em branco, `chuva_early_mm`.
3. Linhas 53 e 54: as chaves do `fonte.json` novo (`o_que_e`, `de_onde_vem`, `licenca`, `citacao`,
   `versao_do_dado`, `conta`, `regra_do_dia`, `ponto`, `ultima_rodada_utc`, `ultimo_dia_com_dado`).
4. Os textos que falam da cor: o `AVISO` (linhas 25 a 29: sai "lida da cor da imagem" e "dia com menos de 2,4 mm sai
   como zero"; entra a cópia da dynamical.org), o aviso das linhas 164 e 165, a `origem` das linhas 215 e 216 e o
   começo do arquivo (linhas 4 a 15). A `conferencia_em_mm` (linhas 60 a 90, chamada na linha 218) compara "a chuva
   lida da cor": muda de nome ou sai.
5. O que acompanha: `backend/orbita/tests/test_hoje.py` (linhas 18 a 27 esperam o endereço do GIBS e as
   `ressalvas`), os números gravados (`respostas.js`, as conversas guardadas) e os documentos que dizem "lida da cor"
   (`LEIA-ME-motor.md`, `docs/orbita/DADOS-E-FONTES.md`, `docs/orbita/VALIDACAO.md`).

**O que saber antes de trocar.**
- O dia aqui é o de Brasília; a temperatura e a chuva guardada da NASA POWER são do dia UTC. Na emenda (a chuva
  guardada acaba em 14/09/2026), as 3 horas de 00h00 a 03h00 UTC do dia 15/09 não entram em nenhuma das duas.
- O dia do retrato continua preso à temperatura da NASA POWER guardada: a chuva chegar a ontem não basta.
- É uma estação só na conferência (Rio Verde): o satélite deu 26% a mais que a estação do INMET naqueles 60 dias.

## O que não foi feito ou conferido
- A troca no motor, e nenhuma rotina agendada.
- Jataí e Silvânia não têm estação para comparar: só foi conferido que o arquivo veio inteiro (90 dias, sem buraco).
- A estabilidade da cópia da dynamical.org por vários dias, e o Early e o Late contra o IMERG Final (ainda não saiu).
