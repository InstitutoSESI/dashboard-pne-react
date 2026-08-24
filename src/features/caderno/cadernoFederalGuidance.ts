/*
 * Orientação federal em linguagem de planejamento por fator.
 *
 * A camada sintetiza passagens localizadas da Lei nº 15.388/2026 e, quando a
 * orientação é de processo, do Caderno MEC/SASE. Ela não classifica, ordena ou
 * altera as causas do artefato municipal.
 */

interface CadernoFactorReference {
  readonly label: string
  readonly url: string
}

export interface CadernoFactorGuidance {
  readonly text: string
  readonly references: readonly CadernoFactorReference[]
}

const LAW_REFERENCE = Object.freeze({
  label: 'Lei nº 15.388/2026',
  url:
    'https://www2.camara.leg.br/legin/fed/lei/2026/lei-15388-14-abril-2026-798950-publicacaooriginal-178891-pl.html',
})

const MEC_REFERENCE = Object.freeze({
  label: 'MEC/SASE — Caderno de Orientações (2014)',
  url: 'https://pne.mec.gov.br/images/pdf/pne_pme_caderno_de_orientacoes.pdf',
})

const LAW_ONLY = Object.freeze([LAW_REFERENCE])
const LAW_AND_MEC = Object.freeze([LAW_REFERENCE, MEC_REFERENCE])

function guidance(
  text: string,
  references: readonly CadernoFactorReference[] = LAW_ONLY,
): CadernoFactorGuidance {
  return Object.freeze({ references, text })
}

export const FACTOR_GUIDANCE: Readonly<Record<string, CadernoFactorGuidance>> = Object.freeze({
  F_DISTANCE: guidance(
    'A Estratégia 10.10 orienta transporte municipal e intermunicipal gratuito e acessível para o público da educação especial, com atenção ao tempo de deslocamento. A referência ajuda a examinar rotas e barreiras de acesso sem atribuir o problema ao município antes da verificação local.',
  ),
  F_POV_CCT: guidance(
    'A Estratégia 2.24 orienta integrar dados oficiais, especialmente os de beneficiários de programas de transferência de renda, para monitorar o direito à educação e articular a proteção à infância. A Estratégia 1.6 orienta acompanhar acesso e permanência de crianças em vulnerabilidade socioeconômica em colaboração com famílias, assistência social, saúde e proteção à infância.',
  ),
  F_DEMAND_DISCOVERY: guidance(
    'A Estratégia 1.3 orienta combinar levantamento da demanda por creche e busca ativa, sob coordenação da educação e em parceria com assistência social, saúde e proteção à infância.',
  ),
  F_EC_QUALITY: guidance(
    'A Estratégia 2.2 orienta implementar e monitorar as diretrizes nacionais de qualidade e equidade da educação infantil, com ações, responsáveis e prazos definidos.',
  ),
  F_ATTEND: guidance(
    'A Estratégia 4.10 orienta busca ativa intersetorial de crianças e adolescentes fora da escola, com integração entre informações educacionais e sociais.',
  ),
  F_MGMT: guidance(
    'A Estratégia 5.18 orienta fortalecer investigação, planejamento e gestão pedagógica por meio de apoio técnico e financeiro à gestão escolar.',
  ),
  F_FOUNDATION: guidance(
    'A Estratégia 3.15 orienta recomposição das aprendizagens com acompanhamento contínuo e individualizado dos estudantes.',
  ),
  F_TIME_QUALITY: guidance(
    'Na jornada ampliada, a Estratégia 6.3 orienta aproveitar efetivamente o tempo de permanência com experiências diversificadas e intencionalidade pedagógica.',
  ),
  F_HOME_LEARNING: guidance(
    'A Estratégia 4.14 orienta ações que aproximem escolas e famílias e favoreçam a participação de pais ou responsáveis na vida escolar e no desenvolvimento integral dos estudantes.',
  ),
  F_TEACH_COACH: guidance(
    'As Estratégias 17.13 e 17.14 orientam supervisão e acompanhamento por profissionais experientes, além de troca de práticas e reflexão conjunta sobre o trabalho pedagógico.',
  ),
  F_TEACH_MATCH: guidance(
    'A Meta 17.a pede formação superior específica na etapa, área ou componente em que o docente atua. A Estratégia 17.11 orienta formação específica para quem atua fora da área de licenciatura.',
  ),
  F_STRUCT_PED: guidance(
    'A Estratégia 5.11 orienta avaliações diagnósticas e formativas para definir ações de desenvolvimento e recomposição. A Estratégia 5.22 pede materiais didáticos de qualidade e com conteúdo referenciado cientificamente.',
  ),
  F_FOOD: guidance(
    'A Estratégia 11.7 inclui alimentação entre os apoios suplementares à permanência na EJA. A Estratégia 19.15 orienta fortalecer os parâmetros do Pnae voltados à segurança alimentar e nutricional.',
  ),
  F_INTERGOV: guidance(
    'O Caderno MEC/SASE orienta que o PME explicite o que o município fará com apoio do Estado e da União e, nas ofertas que não são de responsabilidade municipal direta, quais iniciativas de articulação serão desenvolvidas. A lei trata as estratégias como ações propostas às diferentes esferas de governo.',
    LAW_AND_MEC,
  ),
  F_DISASTER: guidance(
    'A Estratégia 8.13 orienta construir protocolos de segurança e planos escolares de prevenção e resposta a emergências climáticas em articulação com a Defesa Civil e outros órgãos públicos.',
  ),
  F_REPETITION: guidance(
    'A Estratégia 4.6 orienta acompanhamento individual e monitoramento da trajetória, sobretudo nas transições entre etapas. A Estratégia 5.12 prevê práticas de recomposição para estudantes com rendimento defasado.',
  ),
  F_HEALTH: guidance(
    'A Estratégia 5.26 orienta atenção psicossocial nas comunidades escolares com articulação entre educação, saúde e assistência social. Na EJA, a Estratégia 11.7 também prevê apoio suplementar de saúde para favorecer a permanência.',
  ),
  F_WORK: guidance(
    'A Estratégia 11.5 orienta integrar empregadores e sistemas de ensino para compatibilizar a jornada de trabalho dos estudantes trabalhadores com a oferta da EJA.',
  ),
  F_PREG_CARE: guidance(
    'As Estratégias 12.10 e 14.14 orientam políticas de auxílio a estudantes com filhos para apoiar inclusão e permanência na educação profissional e na educação superior.',
  ),
  F_BULLY: guidance(
    'A Estratégia 5.25 orienta qualificar as equipes escolares para identificar, intervir e prevenir bullying e cyberbullying, com protocolos de acolhimento, proteção e responsabilização.',
  ),
  F_HEAT: guidance(
    'A Meta 8.b estabelece conforto térmico para estruturas e instalações de todos os estabelecimentos de ensino. A Estratégia 8.5 orienta referenciais de infraestrutura adaptados às mudanças do clima.',
  ),
  F_BASIC_INFRA: guidance(
    'A Meta 19.c estabelece condições mínimas de funcionamento e salubridade em todas as escolas até o terceiro ano do plano. A Estratégia 19.11 orienta planejar, monitorar e avaliar os investimentos em infraestrutura.',
  ),
  F_FULLTIME_DESIGN: guidance(
    'A Estratégia 6.2 orienta qualidade, monitoramento e intencionalidade pedagógica na jornada integral. A Estratégia 6.3 pede integração de atividades acadêmicas, culturais, esportivas e de recomposição no tempo ampliado.',
  ),
  F_DIG_PHYS: guidance(
    'A Meta 7.a pede conectividade de alta velocidade para uso pedagógico, inclusive com redes internas wi-fi. A Estratégia 7.3 orienta parâmetros mínimos de quantidade e qualidade dos equipamentos.',
  ),
  F_DIG_PED: guidance(
    'A Estratégia 7.8 orienta práticas pedagógicas de educação digital e midiática com uso seguro e equilibrado. A Estratégia 7.10 orienta formação docente para integrar as tecnologias ao ensino de forma ética, crítica e criativa.',
  ),
  F_ENV_CURR: guidance(
    'A Meta 8.c pede educação ambiental em todas as instituições de ensino. A Estratégia 8.15 orienta integrar saberes e tratar o tema transversalmente entre áreas de conhecimento.',
  ),
  F_INDIG_RELEV: guidance(
    'A Meta 9.d estabelece atendimento escolar indígena alinhado às diretrizes da modalidade, ao multilinguismo e à interculturalidade. A Estratégia 9.1 orienta currículos e projetos pedagógicos que respeitem culturas e autonomia escolar.',
  ),
  F_INCLUSION_SUPPORT: guidance(
    'A Meta 10.b pede ampliar e universalizar a oferta de AEE. A Estratégia 10.20 orienta melhorar salas de recursos e diversificar as formas de atendimento para apoiar permanência e aprendizagem.',
  ),
  F_EJA_FIT: guidance(
    'A Estratégia 11.2 orienta oferta gratuita da EJA em todos os turnos. A Estratégia 11.13 pede currículos e práticas construídos com participação da comunidade e adequados às especificidades dos estudantes.',
  ),
  F_CASH_AID_HE: guidance(
    'As Estratégias 12.7 e 14.7 orientam ampliar ou fortalecer a assistência estudantil para apoiar o acesso e a permanência na educação profissional e na graduação. Na graduação, a Estratégia 14.7 também abrange participação e conclusão.',
  ),
  F_EPT_BUNDLE: guidance(
    'A Meta 12.a combina expansão da educação técnica articulada ao ensino médio com qualidade e permanência. A Estratégia 12.4 orienta articular redes para diversificar a oferta nos territórios.',
  ),
  F_HE_FACULTY: guidance(
    'As Metas 15.b e 15.c estabelecem referências para ampliar docentes em tempo integral e a proporção de mestres e doutores no corpo docente da educação superior.',
  ),
  F_HE_OFFER: guidance(
    'A Estratégia 14.1 orienta expansão planejada a partir da demanda e das necessidades locais e regionais. A Estratégia 14.4 orienta expansão articulada e interiorização das instituições públicas gratuitas.',
  ),
  F_CAREER_PAY: guidance(
    'A Meta 17.b orienta equiparar o rendimento médio do magistério ao de ocupações com escolaridade equivalente. A Meta 17.c pede planos de carreira legais referenciados no piso salarial nacional.',
  ),
  F_POSTGRAD_CAP: guidance(
    'A Meta 16.a estabelece referências de formação anual de mestres e doutores. A Estratégia 16.1 orienta ampliar a pós-graduação nas áreas e localidades pouco atendidas, inclusive por programas em rede.',
  ),
  F_GOV_AUDIT: guidance(
    'A Estratégia 19.13 orienta aprimorar controles interno, externo e social dos recursos da educação. A Estratégia 19.19 pede transparência e divulgação anual dos dispêndios e custos por estudante.',
  ),
  F_PARTICIPATION: guidance(
    'As Metas 18.b e 18.c pedem conselhos escolares atuantes e fóruns permanentes de educação em funcionamento. A Estratégia 18.10 orienta apoio técnico às instâncias colegiadas para acompanhamento e controle social.',
  ),
})

export function resolveFactorGuidance(factorId: string): CadernoFactorGuidance | null {
  return FACTOR_GUIDANCE[factorId] ?? null
}
