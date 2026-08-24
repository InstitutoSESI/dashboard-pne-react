/**
 * Orientação federal do PNE 2026–2036 para o Caderno de Hipóteses.
 *
 * Esta é uma camada editorial da plataforma. Ela sintetiza referências da
 * Lei nº 15.388/2026 sem alterar metas, causas ou artefatos publicados.
 *
 * @typedef {{ref: string, text: string}} Pne2026FederalStrategy
 * @typedef {{name: string, url: string}} Pne2026FederalSource
 * @typedef {{
 *   summary: string,
 *   strategies: readonly Pne2026FederalStrategy[],
 *   sources: readonly Pne2026FederalSource[],
 * }} Pne2026FederalGuidanceEntry
 */

const LAW_SOURCE = Object.freeze({
  name: 'Lei nº 15.388/2026',
  url:
    'https://www2.camara.leg.br/legin/fed/lei/2026/lei-15388-14-abril-2026-798950-publicacaooriginal-178891-pl.html',
})

const LAW_SOURCES = Object.freeze([LAW_SOURCE])

/**
 * @param {{summary: string, strategies: Pne2026FederalStrategy[]}} entry
 * @returns {Pne2026FederalGuidanceEntry}
 */
function federalGuidance(entry) {
  return Object.freeze({
    summary: entry.summary,
    strategies: Object.freeze(entry.strategies.map((item) => Object.freeze(item))),
    sources: LAW_SOURCES,
  })
}

/** @type {Readonly<Record<string, Pne2026FederalGuidanceEntry>>} */
export const PNE_2026_FEDERAL_GUIDANCE = Object.freeze({
  '1': federalGuidance({
    summary:
      'O novo PNE pede ampliar as matrículas em creche de acordo com a demanda manifesta e universalizar a pré-escola. Também orienta que a expansão seja planejada com busca ativa, cooperação federativa e atenção aos territórios com menor atendimento.',
    strategies: [
      {
        ref: 'Meta 1.a',
        text:
          'Pede atender toda a demanda manifesta por creche e alcançar, no país, ao menos 60% das crianças de até 3 anos ao fim do decênio.',
      },
      {
        ref: 'Meta 1.c',
        text:
          'Estabelece a universalização da pré-escola para crianças de 4 e 5 anos até o segundo ano de vigência.',
      },
      {
        ref: 'Estratégia 1.3',
        text:
          'Orienta levantamento da demanda e busca ativa na educação infantil, articulados com assistência social, saúde e proteção à infância.',
      },
      {
        ref: 'Estratégia 1.12',
        text:
          'Prevê assistência técnica e financeira para ampliar creche e pré-escola onde o atendimento é menor.',
      },
    ],
  }),
  '3': federalGuidance({
    summary:
      'O novo PNE pede que todas as crianças estejam alfabetizadas e com aprendizagem adequada em matemática ao final do segundo ano. Para orientar a ação, estabelece acompanhamento contínuo, avaliações diagnósticas, apoio pedagógico às escolas e recomposição das aprendizagens.',
    strategies: [
      {
        ref: 'Meta 3.a',
        text:
          'Estabelece pelo menos 80% das crianças alfabetizadas ao fim do segundo ano até o quinto ano do plano e todas até o fim do decênio.',
      },
      {
        ref: 'Estratégia 3.10',
        text:
          'Orienta avaliações diagnósticas e formativas contínuas para acompanhar cada criança e apoiar intervenções pedagógicas mais imediatas.',
      },
      {
        ref: 'Estratégia 3.13',
        text:
          'Pede fortalecimento das secretarias para apoiar a gestão e o trabalho pedagógico das escolas.',
      },
      {
        ref: 'Estratégia 3.15',
        text:
          'Propõe recomposição das aprendizagens com acompanhamento contínuo e individualizado dos estudantes.',
      },
    ],
  }),
  '4': federalGuidance({
    summary:
      'O novo PNE pede acesso universal à escola e trajetórias que levem crianças e jovens a concluir cada etapa na idade regular. A orientação combina metas de acesso e conclusão com busca ativa intersetorial para alcançar quem está fora da escola.',
    strategies: [
      {
        ref: 'Meta 4.a',
        text:
          'Estabelece acesso universal à escola para a população de 6 a 17 anos até o terceiro ano do plano.',
      },
      {
        ref: 'Meta 4.b',
        text: 'Pede que todos os estudantes concluam o quinto ano na idade regular.',
      },
      {
        ref: 'Meta 4.c',
        text:
          'Pede que ao menos 95% concluam o nono ano na idade regular, com equidade e atenção à diversidade.',
      },
      {
        ref: 'Meta 4.d',
        text:
          'Pede que ao menos 90% concluam o ensino médio na idade regular, com equidade e atenção à diversidade.',
      },
      {
        ref: 'Estratégia 4.10',
        text:
          'Orienta busca ativa intersetorial e integração de informações educacionais e sociais sobre crianças e adolescentes fora da escola.',
      },
    ],
  }),
  '5': federalGuidance({
    summary:
      'O novo PNE estabelece referências de aprendizagem para os anos iniciais, os anos finais e o ensino médio, com redução das desigualdades. Também orienta avaliações que apoiem a recomposição e ações intersetoriais para ambientes escolares seguros e acolhedores.',
    strategies: [
      {
        ref: 'Meta 5.a',
        text:
          'Define referências de aprendizagem básica e adequada ao término dos anos iniciais do ensino fundamental.',
      },
      {
        ref: 'Meta 5.b',
        text:
          'Define referências de aprendizagem básica e adequada ao término dos anos finais do ensino fundamental.',
      },
      {
        ref: 'Meta 5.d',
        text:
          'Define referências de aprendizagem básica e adequada ao término do ensino médio.',
      },
      {
        ref: 'Estratégia 5.11',
        text:
          'Orienta avaliações diagnósticas e formativas para desenvolver e recompor aprendizagens e subsidiar políticas educacionais.',
      },
      {
        ref: 'Estratégia 5.24',
        text:
          'Propõe prevenção das violências e promoção da cultura de paz em ambientes escolares seguros, inclusivos e estimulantes.',
      },
    ],
  }),
  '6': federalGuidance({
    summary:
      'O novo PNE pede ampliar a educação integral em tempo integral com qualidade e intencionalidade pedagógica. A jornada ampliada deve reunir condições adequadas de oferta, acompanhamento e experiências educativas diversificadas.',
    strategies: [
      {
        ref: 'Meta 6.a',
        text:
          'Estabelece referências progressivas de escolas e estudantes atendidos em jornada mínima de 7 horas diárias ou 35 semanais.',
      },
      {
        ref: 'Estratégia 6.1',
        text:
          'Orienta política nacional que combine expansão com infraestrutura, profissionais, alimentação, transporte e recursos pedagógicos adequados.',
      },
      {
        ref: 'Estratégia 6.2',
        text:
          'Prevê diretrizes, monitoramento e avaliação para assegurar qualidade e intencionalidade pedagógica na jornada integral.',
      },
      {
        ref: 'Estratégia 6.3',
        text:
          'Orienta aproveitar o tempo ampliado com experiências acadêmicas, culturais, esportivas e de recomposição articuladas pedagogicamente.',
      },
    ],
  }),
  '7': federalGuidance({
    summary:
      'O novo PNE pede conectividade de alta velocidade adequada ao uso pedagógico e aprendizagem em educação digital. A orientação reúne infraestrutura, equipamentos, práticas pedagógicas e formação de professores para uso seguro, responsável e crítico das tecnologias.',
    strategies: [
      {
        ref: 'Meta 7.a',
        text:
          'Estabelece conectividade pedagógica de alta velocidade, inclusive redes internas wi-fi, em todas as escolas públicas até o fim do decênio.',
      },
      {
        ref: 'Estratégia 7.1',
        text:
          'Orienta combinar internet, redes internas, infraestrutura e equipamentos adequados em todas as escolas públicas.',
      },
      {
        ref: 'Estratégia 7.3',
        text:
          'Prevê parâmetros mínimos de quantidade e qualidade para equipamentos destinados à educação digital.',
      },
      {
        ref: 'Estratégia 7.8',
        text:
          'Pede estratégias pedagógicas de educação digital e midiática com uso seguro, responsável e equilibrado.',
      },
      {
        ref: 'Estratégia 7.10',
        text:
          'Orienta formação docente para integrar tecnologias digitais ao ensino de forma ética, crítica e criativa.',
      },
    ],
  }),
  '8': federalGuidance({
    summary:
      'O novo PNE pede que os estabelecimentos de ensino avancem em conforto térmico, educação ambiental e preparação para as mudanças do clima. A orientação inclui planos climáticos, referenciais de infraestrutura, protocolos de emergência e integração da educação ambiental ao currículo.',
    strategies: [
      {
        ref: 'Meta 8.b',
        text:
          'Estabelece que todos os estabelecimentos de ensino tenham estrutura e instalações com conforto térmico.',
      },
      {
        ref: 'Meta 8.c',
        text:
          'Estabelece educação ambiental em todas as instituições, alinhada à política nacional e às diretrizes curriculares.',
      },
      {
        ref: 'Estratégia 8.1',
        text:
          'Prevê apoio técnico e financeiro para planos educacionais de prevenção, mitigação e adaptação climática.',
      },
      {
        ref: 'Estratégia 8.13',
        text:
          'Orienta protocolos de segurança e planos escolares de resposta a emergências climáticas com a Defesa Civil.',
      },
      {
        ref: 'Estratégia 8.15',
        text:
          'Pede estratégias pedagógicas de educação ambiental transversais às áreas de conhecimento.',
      },
    ],
  }),
  '9': federalGuidance({
    summary:
      'O novo PNE pede atendimento escolar indígena com acesso, permanência, qualidade, multilinguismo e interculturalidade. A orientação valoriza currículos, materiais e formas de gestão construídos com respeito às culturas e às línguas das comunidades.',
    strategies: [
      {
        ref: 'Meta 9.d',
        text:
          'Estabelece atendimento universal da pré-escola ao ensino médio indígena, com multilinguismo, interculturalidade e diretrizes próprias.',
      },
      {
        ref: 'Estratégia 9.1',
        text:
          'Orienta matrizes curriculares e projetos pedagógicos que respeitem as culturas e a autonomia das escolas.',
      },
      {
        ref: 'Estratégia 9.3',
        text:
          'Prevê materiais didáticos específicos e acompanhamento que considerem língua materna e identidade cultural.',
      },
      {
        ref: 'Estratégia 9.12',
        text:
          'Propõe Territórios Etnoeducacionais como espaços de pactuação e gestão compartilhada da política escolar indígena.',
      },
    ],
  }),
  '10': federalGuidance({
    summary:
      'O novo PNE pede ampliar e universalizar o atendimento educacional especializado, com acesso, permanência e aprendizagem em sistema inclusivo. A orientação inclui acessibilidade, redes de suporte, profissionais especializados e salas de recursos multifuncionais.',
    strategies: [
      {
        ref: 'Meta 10.b',
        text:
          'Estabelece AEE para ao menos 80% do público até o quinto ano e universalização até o fim do decênio.',
      },
      {
        ref: 'Estratégia 10.2',
        text:
          'Orienta eliminar barreiras e monitorar a acessibilidade em todas as escolas.',
      },
      {
        ref: 'Estratégia 10.4',
        text:
          'Prevê redes de suporte com profissionais de apoio, intérpretes, especialistas e equipes multiprofissionais.',
      },
      {
        ref: 'Estratégia 10.20',
        text:
          'Orienta melhorar salas de recursos e diversificar as formas de AEE para apoiar permanência e aprendizagem.',
      },
    ],
  }),
  '11': federalGuidance({
    summary:
      'O novo PNE pede elevar a alfabetização e a conclusão da educação básica entre jovens, adultos e idosos, além de expandir a EJA. A orientação combina busca ativa regular com currículos e práticas adequados às necessidades e singularidades dos estudantes.',
    strategies: [
      {
        ref: 'Meta 11.a',
        text:
          'Estabelece alfabetização de 97% da população com 15 anos ou mais até o quinto ano e superação do analfabetismo no decênio.',
      },
      {
        ref: 'Meta 11.b',
        text:
          'Pede elevar a conclusão do ensino fundamental entre adultos e universalizá-la para a população de 15 a 29 anos.',
      },
      {
        ref: 'Meta 11.c',
        text:
          'Pede elevar a conclusão do ensino médio entre adultos e universalizá-la para a população de 18 a 29 anos.',
      },
      {
        ref: 'Meta 11.d',
        text:
          'Estabelece expansão progressiva das matrículas na EJA para quem não concluiu a educação básica.',
      },
      {
        ref: 'Estratégia 11.10',
        text:
          'Orienta busca ativa regular e intersetorial para identificar demanda e garantir acesso à EJA.',
      },
      {
        ref: 'Estratégia 11.13',
        text:
          'Pede currículos, projetos e práticas construídos com a comunidade e adequados às especificidades dos estudantes da EJA.',
      },
    ],
  }),
  '12': federalGuidance({
    summary:
      'O novo PNE pede expandir o acesso, a permanência e a conclusão na educação profissional e tecnológica, inclusive articulada ao ensino médio e à EJA. A orientação valoriza articulação territorial entre redes e assistência estudantil para quem dela necessita.',
    strategies: [
      {
        ref: 'Meta 12.a',
        text:
          'Estabelece expansão da educação técnica integrada ou concomitante ao ensino médio, com qualidade e permanência.',
      },
      {
        ref: 'Meta 12.b',
        text:
          'Pede ampliar em pelo menos 60% as matrículas em cursos técnicos subsequentes, com qualidade e permanência.',
      },
      {
        ref: 'Meta 12.c',
        text:
          'Estabelece expansão da EJA articulada à educação profissional durante o decênio.',
      },
      {
        ref: 'Estratégia 12.4',
        text:
          'Orienta articulação entre redes de educação profissional para diversificar a oferta nos territórios.',
      },
      {
        ref: 'Estratégia 12.7',
        text:
          'Prevê assistência estudantil para apoiar acesso e permanência, com atenção a públicos em maior vulnerabilidade.',
      },
    ],
  }),
  '14': federalGuidance({
    summary:
      'O novo PNE pede ampliar acesso, escolarização e conclusão na graduação, com qualidade e redução das desigualdades. A orientação combina expansão articulada e interiorizada da oferta com políticas afirmativas e assistência estudantil.',
    strategies: [
      {
        ref: 'Meta 14.a',
        text:
          'Estabelece acesso à graduação de qualidade para 40% da população de 18 a 24 anos, com redução das desigualdades.',
      },
      {
        ref: 'Meta 14.b',
        text:
          'Estabelece educação superior completa para 40% da população de 25 a 34 anos, com redução das desigualdades.',
      },
      {
        ref: 'Meta 14.c',
        text:
          'Pede aumento gradual das titulações anuais na graduação, inclusive no segmento público.',
      },
      {
        ref: 'Meta 14.d',
        text: 'Estabelece taxa bruta de escolarização de 60% na educação superior.',
      },
      {
        ref: 'Estratégia 14.4',
        text:
          'Orienta expansão articulada e interiorização das instituições públicas gratuitas para ampliar o atendimento territorial.',
      },
      {
        ref: 'Estratégia 14.7',
        text:
          'Prevê políticas afirmativas, assistência estudantil, seleção e infraestrutura adequadas para acesso, permanência e conclusão.',
      },
    ],
  }),
  '15': federalGuidance({
    summary:
      'O novo PNE pede padrões de qualidade para a graduação e amplia referências para dedicação e titulação do corpo docente. A orientação inclui indicadores objetivos, financiamento adequado e condições institucionais para professores e equipes.',
    strategies: [
      {
        ref: 'Meta 15.a',
        text:
          'Estabelece que toda a oferta de graduação atenda aos padrões nacionais de qualidade.',
      },
      {
        ref: 'Meta 15.b',
        text:
          'Define referências de ampliação da proporção de docentes em tempo integral por tipo de instituição.',
      },
      {
        ref: 'Meta 15.c',
        text:
          'Define referências de ampliação de mestres e doutores no corpo docente da educação superior.',
      },
      {
        ref: 'Estratégia 15.1',
        text:
          'Orienta padrões nacionais de qualidade com indicadores objetivos para instituições e cursos.',
      },
      {
        ref: 'Estratégia 15.13',
        text:
          'Prevê financiamento, infraestrutura e contratação e valorização de profissionais nas instituições públicas.',
      },
    ],
  }),
  '16': federalGuidance({
    summary:
      'O novo PNE pede ampliar a formação de mestres e doutores com equidade, inclusão e atenção às necessidades da sociedade. A orientação prevê expansão territorial da pós-graduação, bolsas e assistência estudantil, além de conexão com demandas sociais e do trabalho.',
    strategies: [
      {
        ref: 'Meta 16.a',
        text:
          'Estabelece referências anuais de titulação de mestres e doutores por 100 mil habitantes, com atenção às desigualdades.',
      },
      {
        ref: 'Estratégia 16.1',
        text:
          'Orienta ampliar a pós-graduação nas áreas e localidades pouco atendidas, inclusive por programas em rede.',
      },
      {
        ref: 'Estratégia 16.2',
        text:
          'Prevê fomento à pesquisa, bolsas e assistência estudantil para acesso, permanência e conclusão.',
      },
      {
        ref: 'Estratégia 16.8',
        text:
          'Pede alinhamento da formação pós-graduada às demandas sociais, das políticas públicas e do mundo do trabalho.',
      },
    ],
  }),
  '17': federalGuidance({
    summary:
      'O novo PNE pede formação específica, valorização e condições adequadas de trabalho para os profissionais da educação básica. As metas tratam de formação superior na área de atuação, carreira, vínculo efetivo, qualidade das licenciaturas e pós-graduação ligada ao trabalho docente.',
    strategies: [
      {
        ref: 'Meta 17.a',
        text:
          'Estabelece formação superior específica para todos os docentes da educação básica até o quinto ano.',
      },
      {
        ref: 'Meta 17.c',
        text:
          'Pede planos de carreira legais com referência no piso nacional e limite de tempo de interação com estudantes.',
      },
      {
        ref: 'Meta 17.d',
        text:
          'Estabelece redução dos profissionais do magistério sem cargo efetivo a no máximo 30% em cada rede.',
      },
      {
        ref: 'Meta 17.e',
        text:
          'Define referências de desempenho adequado no Enade para concluintes de pedagogia e licenciaturas.',
      },
      {
        ref: 'Meta 17.f',
        text:
          'Pede que 70% dos docentes concluam pós-graduação relacionada à sua área de atuação profissional.',
      },
    ],
  }),
  '18': federalGuidance({
    summary:
      'O novo PNE pede participação e controle social no planejamento, na gestão democrática e no acompanhamento das políticas educacionais. Para isso, estabelece conselhos escolares e fóruns de educação em funcionamento e orienta apoio às instâncias colegiadas.',
    strategies: [
      {
        ref: 'Meta 18.b',
        text:
          'Estabelece conselhos escolares instituídos e atuantes em todas as escolas públicas, com participação dos segmentos da comunidade.',
      },
      {
        ref: 'Meta 18.c',
        text:
          'Estabelece fóruns permanentes de educação, instituídos por lei e em funcionamento em todos os entes.',
      },
      {
        ref: 'Estratégia 18.4',
        text:
          'Orienta autonomia, qualificação e apoio às instâncias colegiadas para fortalecer gestão democrática e participação social.',
      },
      {
        ref: 'Estratégia 18.6',
        text:
          'Prevê condições de funcionamento dos fóruns e participação popular no acompanhamento dos planos decenais.',
      },
      {
        ref: 'Estratégia 18.10',
        text:
          'Pede apoio técnico às instâncias colegiadas para elaboração, acompanhamento e controle social das políticas.',
      },
    ],
  }),
  '19': federalGuidance({
    summary:
      'O novo PNE pede qualidade e equidade nas condições de oferta, incluindo a superação de situações críticas de infraestrutura escolar. A orientação combina padrões de infraestrutura com planejamento do investimento, monitoramento, transparência e controle social.',
    strategies: [
      {
        ref: 'Meta 19.c',
        text:
          'Estabelece condições mínimas de funcionamento e salubridade em todas as escolas até o terceiro ano do plano.',
      },
      {
        ref: 'Estratégia 19.4',
        text:
          'Orienta padrões mínimos, básicos e adequados de infraestrutura escolar, inclusive espaço mínimo por aluno.',
      },
      {
        ref: 'Estratégia 19.11',
        text:
          'Pede aperfeiçoamento do planejamento, da gestão, do monitoramento e da avaliação dos investimentos em infraestrutura.',
      },
      {
        ref: 'Estratégia 19.13',
        text:
          'Orienta aprimorar os controles interno, externo e social dos recursos públicos da educação.',
      },
      {
        ref: 'Estratégia 19.19',
        text:
          'Prevê transparência, controle social e divulgação anual dos dispêndios e custos por estudante.',
      },
    ],
  }),
})
