# Questionário para produtores · Órbita Rural

> Cópia do questionário escrito em 2026-11-15 para a validação pelo uso (Equipe Agronautas, NASA Space Apps 2026).
> Texto escrito com IA (Claude) e conferido pela coordenação do projeto. **Ainda não foi enviado a produtores e não há
> respostas.** O que ele serve para provar está no fim; a leitura das respostas vai para o `VALIDACAO.md`.
> A área está em hectares, com a ajuda do alqueire goiano; o questionário é anônimo e só para maiores de 18 anos.

## O nosso questionário

**Como ler:** é só para o produtor rural. São 12 perguntas, em 3 seções: a pergunta 1 confirma que quem responde é produtor (quem não é, encerra ali); as perguntas 2 a 6 são sobre a lavoura; as perguntas 7 a 12, sobre o Órbita Rural.

### Como montar no Google Forms

(Escrito de memória, sem criar formulário: conferir os nomes dos botões na hora de montar.)

- Em Configurações, Respostas: "Coletar endereços de e-mail" em **Não coletar**; "Limitar a 1 resposta" **desligado**
  (ligado, ele obriga a entrar com conta do Google, e o formulário deixa de ser anônimo).
- Criar 3 seções. Na pergunta 1, abrir os três pontinhos e ligar "Ir para a seção com base na resposta": "Sim" segue para a
  seção 2; "Não" envia o formulário.
- Onde a lista tem "Outro.", usar o botão "Adicionar Outro" do Forms: ele abre um campo para a pessoa escrever.
- Onde diz "marque até 2" ou "marque até 3": três pontinhos, "Validação de resposta", "Selecionar no máximo".
- Cabeçalho sem logo da NASA. O logo do time está em `frontend/orbita/marca/`.

### Título

Formulário - Produtor Rural

### Texto de abertura

> Somos a Equipe Agronautas e participamos do NASA Space Apps Challenge 2026, o hackathon internacional da NASA.
>
> Estamos desenvolvendo uma ferramenta para apoiar a decisão do que plantar e o acompanhamento da lavoura ao longo do
> ano. Queremos entender como essa decisão é tomada hoje, o que mais tem prejudicado as safras e se uma ferramenta assim
> ajudaria no campo.
>
> Leva uns 3 minutos. O questionário é anônimo: não pedimos nome, CPF, telefone nem e-mail. As respostas serão usadas
> somente neste projeto, sempre somadas, sem identificar ninguém.
>
> Só para maiores de 18 anos. Ao responder, você confirma que tem 18 anos ou mais.
>
> Não existe resposta certa ou errada: vale o que acontece na lavoura.

### Seção 1 · Quem responde

**1. Você é produtor(a) rural?**
Tipo: múltipla escolha · Obrigatória: sim
- Sim. (segue para a seção 2)
- Não. (envia o formulário)

### Seção 2 · A sua lavoura

**2. Em qual estado e município fica a sua lavoura?**
Tipo: texto curto · Obrigatória: sim
Texto de ajuda: Escreva o município e a sigla do estado.

**3. O que você planta?**
Tipo: caixas de seleção · Obrigatória: sim
Texto de ajuda: Marque tudo o que você planta.
- Soja.
- Milho.
- Sorgo.
- Feijão.
- Algodão.
- Cana-de-açúcar.
- Café.
- Hortaliças ou frutas.
- Pasto para o gado.
- Outro.

**4. Qual é o tamanho da área que você planta?**
Tipo: múltipla escolha · Obrigatória: sim
Texto de ajuda: 1 alqueire goiano tem 4,84 hectares. 50 hectares são cerca de 10 alqueires.
- Até 50 hectares.
- De 51 a 200 hectares.
- De 201 a 500 hectares.
- De 501 a 1.000 hectares.
- Mais de 1.000 hectares.
- Prefiro não dizer.

**5. Hoje, como você decide o que plantar depois da safra principal (a segunda safra ou safrinha)?**
Tipo: caixas de seleção · Obrigatória: sim
Texto de ajuda: Marque tudo o que pesa na sua decisão.
- Pela minha experiência, pelo que já deu certo aqui.
- Pela data em que plantei ou colhi a safra principal.
- Pela previsão do tempo.
- Pelo preço de venda e pelo custo de plantar.
- Pela orientação do agrônomo ou técnico.
- Pela orientação da cooperativa.
- Pelo que os vizinhos estão plantando.
- Por aplicativo ou programa de computador.
- Em conversa com a família ou com o sócio.
- Não planto depois da safra principal.
- Outro.

**6. O que mais prejudicou as suas últimas safras?**
Tipo: caixas de seleção · Obrigatória: sim
Texto de ajuda: Marque até 3.
- Faltou chuva na hora em que a planta mais precisava.
- Choveu demais ou fora de hora.
- Calor forte demais.
- Praga ou doença.
- Terra descoberta ou enxurrada levando a terra (erosão).
- Preço de venda baixo.
- Custo alto de adubo, semente e defensivo.
- Nada prejudicou.
- Outro.

### Seção 3 · Sobre o Órbita Rural

Descrição da seção (colar no campo de descrição, antes das perguntas):

> O Órbita Rural é uma ferramenta em desenvolvimento. Ela usa dados públicos da NASA para olhar três coisas na lavoura ao
> longo do ano: a chuva medida por satélite, o calor e o quanto a terra está coberta de planta, vista do espaço.
>
> A pessoa escreve a pergunta do jeito dela. Por exemplo: "plantei a soja tarde, ainda vale o milho ou vou de sorgo?".
> A ferramenta responde com uma indicação e mostra os dados em que se apoiou.
>
> São três momentos: antes de plantar (comparar opções do que plantar e quando), durante a safra (acompanhar a chuva, o
> calor e a cobertura da terra) e depois de colher (guardar o registro de como foi a safra).
>
> Ela não substitui o agrônomo e não promete lucro. O projeto usa dados públicos da NASA, mas não é um produto da NASA.

**7. De 1 a 5, o quanto uma ferramenta assim ajudaria nas decisões da lavoura?**
Tipo: escala de 1 a 5 · Obrigatória: sim
Rótulo do 1: Não ajudaria em nada. · Rótulo do 5: Ajudaria muito.

**8. Em qual destes momentos ela ajudaria mais?**
Tipo: múltipla escolha · Obrigatória: sim
- Antes de plantar.
- Durante a safra.
- Depois de colher.
- Em nenhum deles.

**9. Se você pudesse fazer uma pergunta sobre a lavoura a essa ferramenta, qual seria?**
Tipo: texto curto · Obrigatória: não

**10. Por onde você preferiria receber esse tipo de informação?**
Tipo: múltipla escolha · Obrigatória: sim
- Pelo WhatsApp.
- Por um aplicativo no celular.
- Por um painel no computador.
- Pelo agrônomo ou técnico que acompanha a lavoura.
- Não usaria.
- Outro.

**11. O que faria você confiar no que a ferramenta diz?**
Tipo: caixas de seleção · Obrigatória: sim
Texto de ajuda: Marque até 2.
- Saber que os dados vêm da NASA.
- Ver a chuva do satélite comparada com a chuva medida na estação da região.
- O agrônomo ou técnico conferir a indicação.
- Ver funcionando na minha terra durante uma safra.
- A indicação de outro produtor que já usou.
- Nada disso me faria confiar.
- Outro.

**12. Você toparia testar essa ferramenta durante uma safra?**
Tipo: múltipla escolha · Obrigatória: sim
- Sim.
- Talvez.
- Não.

### Mensagem depois do envio

> Obrigado. A sua resposta foi registrada e vai ajudar a Equipe Agronautas a fazer uma ferramenta mais útil para o campo.


## O que cada pergunta prova

Cada resposta pode sustentar a afirmação ou derrubar: o número só entra no slide depois que as respostas chegarem. Com
poucas respostas, mostrar a contagem ("7 de 10"), não a porcentagem.

| pergunta | a afirmação do pitch que ela sustenta |
|---|---|
| 1 (filtro) | "Ouvimos produtores": tira quem não é do campo |
| 2 (onde fica a lavoura) | De onde vêm as respostas: se são de Goiás, como o caso de Rio Verde e o documento do IFAG |
| 3 (o que planta) | Quem respondeu planta soja, milho ou sorgo, que é o caso que calculamos |
| 4 (a área) | A ferramenta não é só para o pequeno produtor: mostra o tamanho de quem se interessou |
| 5 (como decide) | A decisão da segunda safra hoje sai da experiência e da previsão, sem ensaio com os dados do lugar; e o agrônomo e a cooperativa pesam nela (a porta de chegada) |
| 6 (o que prejudicou) | A dor é real, e é a das três pernas do projeto: a água, o calor e a terra coberta |
| 7 (escala de 1 a 5) | A validação pelo uso: quem está no campo diz que ajudaria |
| 8 (o momento) | A história do ano inteiro (antes, durante, depois) e qual momento vale mais; o "antes" é o que já funciona |
| 9 (a pergunta dele) | "O produtor pergunta do jeito dele": perguntas de verdade, que também servem para a demonstração |
| 10 (por onde receber) | O formato da ferramenta: uma conversa, um painel ou pela mão do técnico |
| 11 (o que faz confiar) | "Cada número tem prova": se a comparação com a estação e a conferência do agrônomo pesam mais do que só o nome da NASA |
| 12 (testar numa safra) | A continuidade: há quem tope o teste numa safra de verdade |
