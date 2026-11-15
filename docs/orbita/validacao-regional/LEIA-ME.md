<!-- Gerado com IA (Claude) -->
# Órbita Rural · os testes de Goiás: o que são e como refazer

Dois testes conferem a conta do Órbita Rural contra o que foi medido no chão, em Goiás. O resumo dos dois está em [../VALIDACAO.md](../VALIDACAO.md) (seções 1 e 2). Aqui ficam os programas, os resultados e o passo a passo para refazer.

| a pasta | a pergunta | o resultado |
|---|---|---|
| [colheita/](colheita/LEIA-ME.md) | onde a conta aponta mais falta de água para o milho safrinha, a colheita do IBGE foi menor? | sim, nos 20 municípios de Goiás que mais plantam milho safrinha (20 de 20) |
| [chuva/](chuva/LEIA-ME.md) | a chuva do satélite fica mais perto da chuva medida no chão do que a chuva de modelo? | sim, em 21 de 27 estações do INMET (16 de 22 em Goiás e 5 de 5 no Distrito Federal) |

## O que tem em cada pasta

- `colheita/`: o programa `regional.py`; o `LEIA-ME.md` com o método, as tabelas e as fontes; `dados/cidades.csv` (os 20 municípios, a área e o ponto de cada um); `dados/consultas.json` (o endereço e a hora de cada consulta); e `resultados/` (a falta de água e o rendimento de cada cidade em cada safra, as medidas por cidade e por safra, e o `resultado.json` com tudo).
- `chuva/`: o programa `chuva_regional.py`; o `LEIA-ME.md` com o método, as tabelas e as fontes; `estacoes.csv` (as 31 estações); `janelas.csv` (cada estação em cada janela); `diario-fev-jun.csv` (dia a dia, a chuva da estação, a do satélite e a de modelo); `lista-a-parte.csv`; `resultado.json`; e `fonte.json` (o endereço, a hora e a assinatura de cada arquivo baixado).

As respostas cruas das fontes não vêm no repositório (só os arquivos anuais do INMET somam perto de 1 GB): os programas baixam de novo. As tabelas dos dois `LEIA-ME.md` são escritas pelos próprios programas, entre as marcas `TABELA` e `FIM` (na colheita) e `tabelas` (na chuva).

## Como refazer

Precisa só do Python 3 (biblioteca padrão) e de internet. A partir da raiz do repositório:

    cd docs/orbita/validacao-regional/colheita
    python3 -I regional.py baixar      # o IBGE e a NASA POWER, uma consulta por vez (uns 3 minutos)
    python3 -I regional.py calcular    # a conta, as medidas, os arquivos de resultados/ e as tabelas do LEIA-ME

    cd ../chuva
    python3 -I chuva_regional.py testar     # as regras, com casos feitos à mão (sem internet)
    python3 -I chuva_regional.py baixar     # os 10 arquivos anuais do INMET e as 62 consultas à NASA POWER
    python3 -I chuva_regional.py calcular   # refaz os CSV, o resultado.json e as tabelas do LEIA-ME

O `regional.py` usa o motor deste repositório (`backend/orbita/`); para apontar outro, a variável `ORBITA_REPO`. O `chuva_regional.py` guarda o que baixa numa pasta de cache fora do repositório e confere a assinatura de cada arquivo antes de usar.

Conferido em 2026-11-15 nesta pasta: o `chuva_regional.py testar` passa e o `regional.py` encontra o motor do repositório. Os resultados guardados aqui são os que os mesmos programas escreveram na rodada de 2026-11-15, com os dados baixados naquele dia.
