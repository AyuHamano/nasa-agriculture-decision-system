/* Base: o painel do ramo nat do time (nathancabrall). Ligação com o motor e telas de resultado geradas com IA (Claude) */
/* adaptar(resposta, extras): o ÚNICO lugar do site que lê a resposta do motor (POST /recomendacao ou dados/respostas.js)
   e os complementos do gerador (dados/complementos.js). Se o motor mudar o nome de um campo, o ajuste é aqui e em mais lugar nenhum.
   Campo novo não quebra; opcional que falta vira null. Nada é calculado aqui: só se escolhe o que mostrar.
   Reaproveitado do site anterior (js/adaptar.js) e ampliado para a faixa da alternativa, a sede forte e a palha. */
(function () {
  "use strict";

  function primeiro() { for (var i = 0; i < arguments.length; i++) if (arguments[i] !== undefined && arguments[i] !== null) return arguments[i]; return null; }
  function obj(x) { return x && typeof x === "object" && !Array.isArray(x) ? x : {}; }
  function lista(x) { return Array.isArray(x) ? x : []; }
  function ehLink(v) { return typeof v === "string" && /^https?:\/\//.test(v); }
  function faixa(x) { x = obj(x); return x.menor === undefined || x.maior === undefined ? null : { menor: x.menor, maior: x.maior }; }

  // O veredito de cada prioridade, numa palavra só: "atual", "alternativa", "empate", "depende" ou "nm" (não medido).
  // Na água vale o veredito pela faixa (as duas pontas da disputa do capim com o milho); o campo antigo "melhor" só olha o meio.
  var PELA_FAIXA = { alternativa_melhor: "alternativa", alternativa_pior: "atual", empate: "empate", depende_da_hipotese: "depende" };
  function veredito(melhor, pelaFaixa) {
    if (pelaFaixa && PELA_FAIXA[pelaFaixa]) return PELA_FAIXA[pelaFaixa];
    if (melhor === "atual" || melhor === "alternativa" || melhor === "empate") return melhor;
    return "nm";
  }

  function cultura(c, recebeu, recebeuFaixa) {
    c = obj(c);
    return { pedido: primeiro(c.pedido_mm), bebido: primeiro(c.bebido_mm), falta: primeiro(c.falta_mm), faltaPct: primeiro(c.falta_relativa_pct),
             dias: primeiro(c.dias), diasDeSede: primeiro(c.dias_de_sede),
             recebeuPct: primeiro(c.agua_recebida_pct, recebeu),                 // o motor ainda não traz: vem do complemento
             recebeuFaixa: faixa(primeiro(c.agua_recebida_faixa_pct, recebeuFaixa)) };
  }
  function lado(s, recebeu, fx) {
    s = obj(s); recebeu = obj(recebeu); fx = obj(fx);
    return { soja: cultura(s.soja, recebeu.soja), milho: cultura(s.milho, recebeu.milho, recebeu.milho_faixa), total: cultura(s.total),
             aguaNoPlantio: primeiro(s.agua_na_terra_no_plantio_da_soja_mm), capimBebeu: primeiro(obj(s.braquiaria).bebido_mm),
             capimJunto: primeiro(obj(s.braquiaria).bebido_junto_com_o_milho_mm), chuvaJanela: primeiro(s.chuva_da_janela_mm),
             faixa: Object.keys(fx).length ? { milhoPct: faixa(fx.falta_do_milho_pct), milhoMm: faixa(fx.falta_do_milho_mm), totalMm: faixa(fx.falta_total_mm), sede: faixa(fx.dias_de_sede) } : null };
  }
  function cenarios(x) {
    var saida = []; x = obj(x);
    Object.keys(x).forEach(function (id) { var c = obj(x[id]); saida.push({ id: id, falta: primeiro(c.falta_mm), diferenca: primeiro(c.diferenca_mm), classe: c.classe || "" }); });
    return saida;
  }

  window.ORBITA_ADAPTAR = function adaptar(r, extras) {
    r = obj(r); extras = obj(extras);
    var rot = obj(r.rotacoes), atual = obj(rot.atual), alternativa = obj(rot.alternativa);
    var comp = obj(r.comparacao), regra = obj(r.regra_dos_anos), agua = obj(comp.agua), solo = obj(comp.solo_e_erosao);
    var cal = obj(r.calendario), clima = obj(r.clima), terra = obj(r.terra), ndvi = obj(r.ndvi), ver = obj(r.veredito), forte = obj(r.sede_forte);
    var opcao = terra.opcao || obj(r.entrada).terra || "";

    // Os complementos (dados/complementos.js): o desenho do ano e a chuva por mês valem para qualquer resposta; os números por tipo
    // de terra (a % de água recebida, a mensagem) só valem se a resposta tem a MESMA conta da guardada (compara, não calcula).
    var c = obj(extras.complementos), guardada = obj(extras.guardada);
    var mesmaConta = r === extras.guardada || (guardada.rotacoes !== undefined && JSON.stringify(r.rotacoes) === JSON.stringify(guardada.rotacoes));
    var daTerra = mesmaConta ? obj(obj(c.por_terra)[opcao]) : {};
    var recebida = obj(daTerra.agua_recebida_pct);
    var anoDaTerra = c.o_ano_da_terra, chuvaMes = c.chuva_por_mes;

    var safras = Object.keys(obj(atual.safras));
    var rendimentos = obj(regra.rendimento_por_safra_kg_ha), chuvas = obj(regra.chuva_por_safra_mm), faixas = obj(alternativa.faixa);
    var porSafra = {};
    safras.forEach(function (s) {
      var a = lado(obj(atual.safras)[s], obj(recebida.atual)[s]), b = lado(obj(alternativa.safras)[s], obj(recebida.alternativa)[s], faixas[s]);
      porSafra[s] = { safra: s, chuvaJanela: primeiro(a.chuvaJanela, chuvas[s]), rendimento: primeiro(rendimentos[s]), atual: a, alternativa: b };
    });

    var parte = obj(r.safra_2025_26), aParte = null;
    if (parte.safra) {
      aParte = { safra: parte.safra, aviso: parte.aviso || "", chuvaJanela: primeiro(parte.chuva_da_janela_mm),
                 atual: lado(parte.atual, obj(recebida.atual)[parte.safra]), alternativa: lado(parte.alternativa, obj(recebida.alternativa)[parte.safra], parte.faixa_da_alternativa) };
    }

    function semPlanta(x) { var s = obj(obj(x).sem_planta_viva); return { dias: primeiro(s.dias_sem_planta_viva), meses: primeiro(s.meses_sem_planta_viva), de: s.de || "", ate: s.ate || "" }; }
    function soma(x) { var s = obj(obj(x).soma_das_10_safras); return { soja: primeiro(s.falta_da_soja_mm), milho: primeiro(s.falta_do_milho_mm), diasDeSede: primeiro(s.dias_de_sede) }; }
    function plantio(p) { p = obj(p); return { plantio: p.plantio || "", sai: p.sai_da_terra || "", ciclo: primeiro(p.ciclo_dias) }; }
    function sedeForte(x) {
      var s = obj(obj(x).safras_com_sede_forte);
      return s.quantas === undefined ? null : { nivel: primeiro(s.nivel_pct), quantas: s.quantas, quais: lista(s.quais), alarmes: lista(s.alarmes_falsos), quebrasAbaixo: lista(s.quebras_abaixo_do_nivel), faixa: faixa(s.faixa) };
    }
    function palha(x) {
      var p = obj(obj(x).palha);
      return p.cobertura_pct === undefined ? null : { deQue: p.de_que || "", cobertura: p.cobertura_pct, evaporacaoAMenos: primeiro(p.evaporacao_a_menos_pct), ondeVale: p.onde_vale || "", regra: p.regra || "", etiqueta: p.etiqueta_da_cobertura || "" };
    }

    var pf = obj(agua.pela_faixa), an = obj(agua.no_ano_normal), disputa = obj(alternativa.disputa_com_o_milho);
    var pelaFaixa = pf.codigo ? { codigo: pf.codigo, frase: pf.frase || "", diferenca: faixa(pf.diferenca_mm), faltaHoje: primeiro(pf.falta_na_rotacao_de_hoje_mm),
                                  empate: primeiro(pf.empate_abaixo_de_mm, agua.empate_abaixo_de_mm), safra: pf.safra || "", cenarios: cenarios(pf.por_cenario),
                                  normal: an.codigo ? { safra: an.safra || "", codigo: an.codigo, diferenca: faixa(an.diferenca_mm), cenarios: cenarios(an.por_cenario) } : null } : null;

    var fonteNdvi = obj(ndvi.fonte), compNdvi = obj(ndvi.comparacao);
    var parametros = lista(r.parametros).map(function (p) {
      p = obj(p);
      return { parametro: String(primeiro(p.parametro, "")), valor: p.valor, etiqueta: String(primeiro(p.etiqueta, "")), fonte: ehLink(p.fonte) ? p.fonte : "", trecho: String(primeiro(p.trecho, "")) };
    });
    function valorDe(nome) { for (var i = 0; i < parametros.length; i++) if (parametros[i].parametro === nome) return parametros[i].valor; return null; }

    return {
      bruto: r,
      aviso: r.aviso || "", pergunta: r.pergunta || "",
      cidade: obj(r.local).nome || "",
      notasDaResposta: obj(obj(r.entrada).prioridades),
      terra: { opcao: opcao, classe: terra.classe || "", porMetro: primeiro(terra.agua_por_metro_mm),
               soja: primeiro(obj(terra.agua_que_segura_mm).soja), milho: primeiro(obj(terra.agua_que_segura_mm).milho),
               raizSoja: primeiro(obj(terra.raizes_m).soja), raizMilho: primeiro(obj(terra.raizes_m).milho) },
      nomes: { atual: atual.nome || "", alternativa: alternativa.nome || "" },
      veredito: { codigo: ver.codigo || "", frase: ver.frase || "" },
      prioridades: lista(r.prioridades).map(function (p) {
        p = obj(p);
        var faixaDaAgua = p.id === "agua" ? primeiro(p.veredito_pela_faixa, pf.codigo) : p.veredito_pela_faixa;
        return { id: p.id, nome: p.nome || p.id, nota: primeiro(p.nota), veredito: veredito(p.melhor, faixaDaAgua), medida: p.medida || "" };
      }),
      anos: { normal: primeiro(comp.ano_normal, regra.ano_normal), pior: primeiro(comp.pior_ano, regra.pior_ano) },
      safras: safras, porSafra: porSafra, aParte: aParte,
      semPlanta: { atual: semPlanta(atual), alternativa: semPlanta(alternativa) },
      soma: { atual: soma(atual), alternativa: soma(alternativa),
              faixaDaAlternativa: { milho: faixa(obj(alternativa.faixa_da_soma_das_10_safras).falta_do_milho_mm), diasDeSede: faixa(obj(alternativa.faixa_da_soma_das_10_safras).dias_de_sede) } },
      sedeForte: forte.nivel_pct === undefined ? null : {
        nivel: forte.nivel_pct, recebeuNivel: primeiro(daTerra.sede_forte_recebido_pct), oQueE: forte.o_que_e || "", quebra: forte.safra_de_quebra || "",
        safrasDeQuebra: lista(forte.safras_de_quebra), rendimentoDasQuebras: obj(forte.rendimento_das_safras_de_quebra_kg_ha), aviso: forte.aviso || "",
        limiteKgHa: primeiro(forte.limite_kg_ha), atual: sedeForte(atual), alternativa: sedeForte(alternativa) },
      palha: { atual: palha(atual), alternativa: palha(alternativa) },
      disputa: disputa.cenarios ? { oQueE: disputa.o_que_e || "", etiqueta: disputa.etiqueta || "", nosCamposAntigos: disputa.nos_campos_antigos || "",
                                    cenarios: Object.keys(obj(disputa.cenarios)).map(function (id) { var x = obj(disputa.cenarios[id]); return { id: id, fator: primeiro(x.fator), pedidoAMais: primeiro(x.pedido_a_mais_pct) }; }) } : null,
      agua: { pelaFaixa: pelaFaixa, diferencaDoMeio: primeiro(agua.diferenca_mm), empate: primeiro(agua.empate_abaixo_de_mm), nota: agua.nota || "" },
      soloMelhor: primeiro(solo.melhor),
      regra: { id: regra.regra || "", criterio: regra.criterio || "", fonteDoRendimento: regra.fonte_do_rendimento || "", mediana: primeiro(regra.mediana_kg_ha),
               desempate: regra.desempate || "", pelaChuva: { pior: obj(regra.pela_chuva_seria).pior_ano || "", normal: obj(regra.pela_chuva_seria).ano_normal || "" } },
      calendario: { soja: plantio(cal.soja), milho: plantio(cal.milho), capim: { secaEm: obj(cal.braquiaria).seca_em || "", diasAntes: primeiro(obj(cal.braquiaria).dias_antes_da_soja) },
                    entre: primeiro(cal.entre_a_soja_e_o_milho_dias) },
      clima: { chuvaId: obj(clima.chuva).id || "", chuvaFonte: obj(clima.chuva).fonte || "", chuvaOrigem: obj(clima.chuva).origem || "",
               temperaturaFonte: obj(clima.temperatura).fonte || "", temperaturaLink: ehLink(obj(clima.temperatura).consulta) ? obj(clima.temperatura).consulta : "",
               primeiroDia: clima.primeiro_dia || "", ultimoDia: clima.ultimo_dia || "", avisos: lista(clima.avisos), conta: clima.conta || "" },
      ndvi: { disponivel: ndvi.disponivel === true, frases: lista(ndvi.frases).length ? lista(ndvi.frases) : (compNdvi.frase ? [compNdvi.frase] : []),
              fonteNome: fonteNdvi.produto || "", fonteLink: ehLink(fonteNdvi.link) ? fonteNdvi.link : "" },
      parametros: parametros, valorDe: valorDe,
      hipoteses: primeiro(r.hipoteses, parametros.filter(function (p) { return p.etiqueta !== "publicado"; }).length),
      limites: lista(r.limites),
      anoDaTerra: anoDaTerra ? { meses: lista(anoDaTerra.meses), diasPorMes: lista(anoDaTerra.dias_por_mes), atual: lista(anoDaTerra.atual), alternativa: lista(anoDaTerra.alternativa) } : null,
      chuvaPorMes: chuvaMes ? { fonte: chuvaMes.fonte || "", maior: primeiro(chuvaMes.maior_mes_mm), safras: obj(chuvaMes.safras) } : null,
      mensagemDoMotor: typeof daTerra.mensagem === "string" ? { texto: daTerra.mensagem, notas: obj(daTerra.notas_da_mensagem) } : null,
      geradoEm: primeiro(c.gerado_em),
      temRecebida: Object.keys(recebida).length > 0
    };
  };
})();
