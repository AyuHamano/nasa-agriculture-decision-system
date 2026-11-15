/* Gerado com IA (Claude). */
/* As constantes do produto e todos os textos da tela do produtor, num objeto só (TEXTOS.pt).
   Os textos da leitura do agrônomo ficam em js/textos-agronomo.js. Nenhum número de dado mora aqui. */

var NOME_DO_PRODUTO = "Órbita Rural";
var API_BASE = "";   // o endereço da API (ex.: "http://127.0.0.1:8000"); vazio = usa as conversas guardadas.
                     // Para ligar sem editar: abra a tela com ?api=http://127.0.0.1:8000

var TEXTOS = {
  pt: {
    abertura: {
      titulo: "A lavoura o ano inteiro, com o que o satélite viu",
      texto: "Conte o que você planta e onde. O Órbita Rural faz a conta com o que os satélites da NASA viram na sua região e põe a sua rotação ao lado de outras."
    },
    leituras: { produtor: "Produtor", agronomo: "Agrônomo", rotulo: "Quem está lendo" },
    momentos: {
      rotulo: "Os três momentos da lavoura",
      antes: { quando: "Antes de plantar", pergunta: "O que eu planto agora?", comeco: "Planto soja e depois milho safrinha em Rio Verde. Vale trocar a minha rotação?" },
      durante: { quando: "Durante a safra", pergunta: "Como está a minha lavoura?", comeco: "Como está a água da minha lavoura hoje?" },
      depois: { quando: "Depois de colher", pergunta: "O que a terra mostrou?", comeco: "Colhi o milho. O que a terra mostrou nesta safra?" },
      prova: "Ver a prova: a safra {safra}, dia a dia",
      proximo: "Próximo passo do projeto",
      proximoTexto: "Este momento ainda não tem conversa pronta. Ele entra no próximo passo do projeto."
    },
    modo: {
      guardadas: "Conversas guardadas",
      aoVivo: "Agente ao vivo",
      explicaGuardadas: "Você está vendo conversas guardadas: foram gravadas com o agente e os números são os da conta.",
      explicaAoVivo: "O agente está ligado: escreva a sua pergunta.",
      caiu: "Não consegui falar com o agente agora ({motivo}). Mostrando as conversas guardadas.",
      semChave: "o servidor está sem a chave da IA",
      semResposta: "ele não respondeu",
      erro: "ele respondeu com erro",
      semConversas: "As conversas guardadas ainda não foram gravadas nesta pasta. Veja no LEIA-ME.md como gravar, ou abra a tela com o agente ligado."
    },
    conversa: {
      titulo: "A conversa",
      escolha: "Outras conversas deste momento",
      produtor: "Você",
      agente: "Órbita Rural",
      dizer: "Dizer isto",
      proxima: "A sua próxima fala",
      fim: "Fim desta conversa.",
      recomecar: "Ver de novo",
      escrevendo: "Fazendo a conta",
      campo: "Escreva aqui",
      rotuloDoCampo: "A sua fala",
      enviar: "Enviar",
      apoio: {
        conta: "Resposta tirada da conta",
        dados_do_lugar: "Resposta tirada dos dados da NASA do seu lugar",
        conhecimento_geral: "Conhecimento geral: a nossa conta não mede isto"
      },
      conferido: "Números conferidos com a conta",
      naoConferido: "Texto trocado pelas frases da conta",
      textoDe: { ia: "Texto escrito por IA; cada número foi conferido com a conta.", frases_prontas: "Texto de frases prontas, preenchidas com os números da conta." },
      verComparacao: "Ver a comparação",
      verFicha: "Ver a ficha",
      verReplay: "Ver a safra dia a dia",
      lerTudo: "Ler a resposta inteira"
    },
    ficha: {
      titulo: "A sua ficha",
      sub: "É com ela que a conta é feita. Confira antes.",
      vaziaTitulo: "A ficha aparece aqui",
      vaziaTexto: "Três coisas bastam para a conta: o município, o tipo de solo e a rotação de hoje. O agente pergunta o que faltar.",
      campos: { cidade_id: "Município", terra: "Tipo de solo", rotacao_atual: "O que você planta hoje", plantio_da_soja: "Plantio da soja", preocupacao: "O que mais preocupa" },
      falta: "falta dizer",
      semData: "pelo calendário da região",
      cidades: { rio_verde: "Rio Verde (GO)", jatai: "Jataí (GO)", silvania: "Silvânia (GO)" },
      terras: { pouca: "Arenoso (segura pouca água)", media: "Textura média", muita: "Argiloso (segura muita água)" },
      culturas: { soja: "soja", milho: "milho safrinha", pousio: "pousio (terra parada)", braquiaria: "braquiária (capim)", sorgo: "sorgo" },
      preocupacoes: { agua: "A água", calor: "O calor", terra: "A terra descoberta" },
      confirmar: "Está certo, pode calcular",
      confirmarFala: "Está certo, pode calcular.",
      corrigir: "Corrigir",
      confirmada: "Ficha conferida por você",
      corrigirTitulo: "O que está errado?",
      corrigirGuardada: "Nesta demonstração a ficha é a da conversa guardada. Com o agente ligado, ele refaz a conta com a sua correção.",
      corrigirEnviar: "Mandar a correção",
      cancelar: "Cancelar",
      correcaoFala: "Corrigindo a ficha: {itens}."
    },
    comparacao: {
      titulo: "As rotações lado a lado",
      sub: "A sua rotação de hoje e outras opções, com a mesma conta e o mesmo clima.",
      deHoje: "A sua rotação de hoje",
      outra: "Outra opção",
      preocupaLinha: "Você disse que o que mais preocupa é {o_que}: por isso vem primeiro.",
      grupos: { agua: "Água", calor: "Calor", terra: "Terra coberta" },
      medidas: {
        falta_no_pior_ano_mm: "Água que faltou no pior ano",
        falta_no_ano_normal_mm: "Água que falta num ano normal",
        dias_de_sede_no_pior_ano: "Dias de sede no pior ano",
        dias_de_calor_forte_no_pior_ano: "Dias de calor forte no pior ano",
        dias_sem_planta_viva: "Dias do ano sem planta viva"
      },
      curtas: { falta_no_pior_ano_mm: "Falta de água no pior ano", dias_de_calor_forte_no_pior_ano: "Calor forte", dias_sem_planta_viva: "Sem planta viva" },
      unidades: { mm: "mm", dias: "dias" },
      faixa: "de {de} a {ate}",
      faixaCurta: "{de} a {ate}",
      semMedida: "sem medida",
      limite: "acima de {c} °C",
      limiteDaCultura: "{cultura}: acima de {c} °C na fase mais sensível",
      limiteHipotese: "(limite por hipótese)",
      satelite: "O satélite viu {n} dias sem planta verde",
      frases: { evidencia: "A prova", beneficio: "O que ganha", risco: "O risco", falta_saber: "O que falta saber" },
      resumo: "Resumo",
      rotacao: "Rotação",
      comoLer: "Como ler estes números",
      glossario: [
        ["mm", "milímetros de água. 1 mm é 1 litro de água em cada metro quadrado de terra."],
        ["Água que faltou", "o quanto a planta pediu e a terra não tinha para dar."],
        ["Dia de sede", "dia em que a planta já sentia a falta de água."],
        ["Calor forte", "dia mais quente do que a cultura aguenta na fase em que ela é mais sensível."],
        ["Sem planta viva", "dia do ano em que a terra fica sem planta crescendo. O satélite confere isso pelo verde das folhas (o índice NDVI)."],
        ["Pior ano", "a safra de pior colheita da região nos registros do IBGE. O ano normal é a safra do meio."],
        ["De ... a ...", "quando a conta depende de algo que ainda não foi medido, ela mostra a faixa em vez de um número só."]
      ],
      agronomo: "Converse com o agrônomo antes de decidir",
      agronomoTexto: "Esta ferramenta apoia a decisão: ela não substitui quem conhece a sua terra. A leitura do agrônomo mostra como a conta foi feita, com que valores e de onde eles vêm.",
      agronomoBotao: "Abrir a leitura do agrônomo"
    },
    replay: {
      sobre: "A prova",
      titulo: "A safra {safra}, dia a dia",
      texto: "A safra refeita dia a dia, com a chuva que o satélite da NASA mediu em {cidade}.",
      textoSemLugar: "A safra refeita dia a dia, com a chuva que o satélite da NASA mediu.",
      rotacao: "Na terra: {nome}.",
      pulso: ["Neste dia a água acabou.", "O produtor não sabia.", "O satélite sabia."],
      culturas: { soja: "soja", milho: "milho safrinha", sorgo: "sorgo", braquiaria: "braquiária (capim)", milho_com_capim: "milho com capim", sem_planta: "sem planta" },
      semPlanta: "Terra sem planta viva",
      tocar: "Tocar", pausar: "Pausar", voltar: "Voltar ao começo", cheia: "Tela cheia", sair: "Sair da tela cheia",
      velocidade: "Velocidade", linha: "O dia da safra",
      dia: "Dia {n} de {total}",
      naTerra: "na terra",
      agua: "Água na terra", chuva: "Chuva do dia", falta: "Água que faltou no dia", tmax: "Temperatura máxima",
      comSede: "Lavoura com sede", calorForte: "Calor forte",
      legenda: { chuva: "Chuva de cada dia", agua: "Água guardada na terra", sede: "Dias de sede", calor: "Dias de calor forte" },
      marcos: { plantio: "Plantio", agua_acabou: "A água acabou", sede: "Começa a sede", calor_forte: "Calor forte", colheita: "Colheita" },
      comeco: "Toque para ver os dias passando.",
      sem: "O replay da safra aparece aqui quando a conversa guardada da safra 2015-16 for gravada."
    },
    agronomo: {
      titulo: "A leitura do agrônomo",
      texto: "Como a conta foi feita, com que valores e de onde eles vêm. As hipóteses e os limites da conta ficam aqui.",
      terra: "A conta para o solo",
      nota: "Esta leitura mostra a conta guardada de Rio Verde (GO), com a rotação de hoje e a rotação com capim.",
      sem: "A resposta do motor não foi gravada nesta pasta (dados/respostas.js).",
      voltar: "Voltar para a conversa"
    },
    cooperativa: {
      titulo: "Para a cooperativa e a assistência técnica",
      texto: "O produtor fica no centro. O técnico da cooperativa confere a mesma conta na leitura do agrônomo, lavoura por lavoura. Um painel para acompanhar vários produtores de uma vez é o próximo passo."
    },
    rodape: {
      lema: "Inteligência do espaço. Decisões para a terra.",
      fontes: "De onde vêm os dados: a chuva é do satélite GPM IMERG, da NASA; a temperatura é da NASA POWER; o verde da lavoura é do satélite MODIS, da NASA. A conta da água segue o manual FAO-56. A colheita é do IBGE e a chuva medida em terra é da estação do INMET.",
      ia: "Uso de IA: esta tela foi programada com apoio de IA (Claude). Na conversa, o texto do agente é escrito por IA ou montado com frases prontas, e todo número é conferido com a conta antes de aparecer.",
      time: "Feito pela Equipe Agronautas no NASA Space Apps Challenge 2026. Ferramenta de apoio: converse com o agrônomo antes de decidir."
    }
  }
};

function t(chave, valores) {
  var no = TEXTOS.pt, partes = chave.split(".");
  for (var i = 0; i < partes.length; i++) { no = no == null ? undefined : no[partes[i]]; }
  if (typeof no !== "string") return no === undefined ? chave : no;
  return no.replace(/\{(\w+)\}/g, function (tudo, nome) { return valores && valores[nome] !== undefined && valores[nome] !== null ? valores[nome] : "—"; });
}
