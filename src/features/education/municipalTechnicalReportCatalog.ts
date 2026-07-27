import type {
  ReportChapterDefinition,
  ReportSectionDefinition,
} from './components/MunicipalTechnicalReportLayout'

export interface MunicipalReportPublicLabel {
  publicTitle: string
  publicShortTitle: string
  publicDescription: string
  unitLabel: string
  sourceLabel: string
  interpretationNote: string
}

export const MUNICIPAL_REPORT_SECTIONS: ReportSectionDefinition[] = [
  { id: 'caracterizacao', shortTitle: 'Caracterização do município', officialTitle: 'Caracterização do município' },
  { id: 'educacao-infantil', shortTitle: 'Educação Infantil', officialTitle: 'Diagnóstico do atendimento na Educação Infantil' },
  { id: 'ensino-fundamental', shortTitle: 'Ensino Fundamental', officialTitle: 'Diagnóstico do atendimento no Ensino Fundamental' },
  { id: 'ensino-medio', shortTitle: 'Ensino Médio', officialTitle: 'Diagnóstico do atendimento no Ensino Médio' },
  { id: 'tempo-integral', shortTitle: 'Educação em tempo integral', officialTitle: 'Diagnóstico da oferta da Educação Integral em tempo integral' },
  { id: 'socioambiental', shortTitle: 'Sustentabilidade socioambiental', officialTitle: 'Diagnóstico da sustentabilidade socioambiental na educação' },
  { id: 'territorios', shortTitle: 'Populações indígenas, quilombolas e do campo', officialTitle: 'Diagnóstico do atendimento às populações indígenas, quilombolas e do campo' },
  { id: 'eja', shortTitle: 'Educação de Jovens e Adultos', officialTitle: 'Diagnóstico do atendimento na Educação de Jovens e Adultos' },
  { id: 'educacao-especial', shortTitle: 'Educação Especial e Educação Bilíngue de Surdos', officialTitle: 'Diagnóstico do atendimento na Educação Especial e Educação Bilíngue de Surdos' },
  { id: 'educacao-superior', shortTitle: 'Educação Superior e Pós-graduação', officialTitle: 'Diagnóstico do atendimento na Educação Superior e Pós-graduação' },
  { id: 'educacao-profissional', shortTitle: 'Educação Profissional e Tecnológica', officialTitle: 'Diagnóstico do atendimento na Educação Profissional e Tecnológica' },
  { id: 'pessoal', shortTitle: 'Profissionais e docentes', officialTitle: 'Diagnóstico do pessoal da educação, com destaque para o quadro dos docentes' },
  { id: 'gestao-democratica', shortTitle: 'Participação social e gestão democrática', officialTitle: 'Diagnóstico da participação social e gestão democrática na educação' },
  { id: 'infraestrutura', shortTitle: 'Infraestrutura escolar e conectividade', officialTitle: 'Diagnóstico da infraestrutura e da conectividade da rede de ensino' },
  { id: 'orcamento', shortTitle: 'Orçamento da educação', officialTitle: 'Diagnóstico do orçamento disponível para educação' },
  { id: 'projecoes', shortTitle: 'Projeções de demanda', officialTitle: 'Projeções de demanda' },
  { id: 'pme', shortTitle: 'Indicadores do PME', officialTitle: 'Indicadores do PME' },
  { id: 'metodologia', shortTitle: 'Metodologia', officialTitle: 'Metodologia' },
  { id: 'bases-anexas', shortTitle: 'Bases de dados anexas', officialTitle: 'Bases de dados anexas' },
]

export const MUNICIPAL_REPORT_CHAPTERS: ReportChapterDefinition[] = [
  {
    id: 'capitulo-1',
    number: 1,
    title: 'Caracterização e atendimento',
    description: 'Características do município e condições de atendimento nas principais etapas da Educação Básica.',
    startIndex: 0,
    endIndex: 4,
  },
  {
    id: 'capitulo-2',
    number: 2,
    title: 'Modalidades, inclusão e territórios',
    description: 'Modalidades educacionais e recortes de inclusão, diversidade e território.',
    startIndex: 5,
    endIndex: 8,
  },
  {
    id: 'capitulo-3',
    number: 3,
    title: 'Educação profissional, superior e profissionais',
    description: 'Oferta profissional e superior e informações sobre os profissionais da educação.',
    startIndex: 9,
    endIndex: 11,
  },
  {
    id: 'capitulo-4',
    number: 4,
    title: 'Gestão, infraestrutura e financiamento',
    description: 'Participação social, condições físicas das redes e referências de financiamento.',
    startIndex: 12,
    endIndex: 14,
  },
  {
    id: 'capitulo-5',
    number: 5,
    title: 'Planejamento municipal',
    description: 'Projeções de demanda e referências para o acompanhamento do Plano Municipal de Educação.',
    startIndex: 15,
    endIndex: 16,
  },
  {
    id: 'capitulo-6',
    number: 6,
    title: 'Referências técnicas',
    description: 'Metodologia, fontes e rastreabilidade das informações reunidas no relatório.',
    startIndex: 17,
    endIndex: 18,
  },
]

export const MUNICIPAL_REPORT_METHODOLOGY_NOTES = [
  'A síntese educacional utiliza o ano de referência publicado para esta edição; anos diferentes são informados na própria seção.',
  'O total da Educação Básica corresponde ao total oficial publicado pelo Censo Escolar e não é recalculado pela soma das etapas.',
  'A referência territorial é o município onde a escola está localizada; as categorias urbana e rural descrevem a localização da unidade escolar.',
  'Os subtotais da rede pública são apresentados somente quando os registros municipal, estadual e federal permitem uma composição segura.',
  'Ausência de registro não é interpretada automaticamente como valor zero.',
  'Valores iguais a zero são apresentados somente quando a completude da base permite confirmar essa medida.',
  'A composição da Educação Básica evita somar novamente detalhamentos já incluídos nos totais.',
  'A Educação Especial é um recorte transversal e suas matrículas já estão incluídas nas etapas e modalidades da Educação Básica.',
  'As taxas de rendimento utilizam os registros municipais do INEP para o conjunto das redes, sem produzir média entre escolas.',
]

const INEP_CENSO = 'INEP — Censo Escolar'

export const MUNICIPAL_REPORT_PUBLIC_LABELS: Record<string, MunicipalReportPublicLabel> = {
  'mat-integral': {
    publicTitle: 'Matrículas em tempo integral',
    publicShortTitle: 'Tempo integral',
    publicDescription: 'Participação das matrículas em jornada de tempo integral.',
    unitLabel: 'percentual',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve a oferta registrada no município.',
  },
  'indigena-cobertura-estimada-4-17': {
    publicTitle: 'Cobertura educacional estimada da população indígena de 4 a 17 anos',
    publicShortTitle: 'Cobertura educacional indígena estimada',
    publicDescription: 'Estimativa de atendimento da população indígena em idade escolar.',
    unitLabel: 'percentual estimado',
    sourceLabel: 'INEP e IBGE',
    interpretationNote: 'A estimativa combina bases com universos territoriais distintos.',
  },
  'indigena-matriculas': {
    publicTitle: 'Matrículas na educação escolar indígena',
    publicShortTitle: 'Matrículas na educação escolar indígena',
    publicDescription: 'Matrículas registradas em educação escolar indígena.',
    unitLabel: 'matrículas',
    sourceLabel: 'INEP — Sinopse Estatística da Educação Básica',
    interpretationNote: 'A medida descreve registros escolares no município.',
  },
  'indigena-estabelecimentos': {
    publicTitle: 'Estabelecimentos com educação escolar indígena',
    publicShortTitle: 'Estabelecimentos de educação escolar indígena',
    publicDescription: 'Estabelecimentos que registram oferta de educação escolar indígena.',
    unitLabel: 'estabelecimentos',
    sourceLabel: 'INEP — Sinopse Estatística da Educação Básica',
    interpretationNote: 'A medida descreve a oferta registrada.',
  },
  'indigena-docentes': {
    publicTitle: 'Docentes na educação escolar indígena',
    publicShortTitle: 'Docentes na educação escolar indígena',
    publicDescription: 'Docentes vinculados à educação escolar indígena.',
    unitLabel: 'docentes',
    sourceLabel: 'INEP — Sinopse Estatística da Educação Básica',
    interpretationNote: 'A medida descreve vínculos docentes registrados.',
  },
  'indigena-turmas': {
    publicTitle: 'Turmas na educação escolar indígena',
    publicShortTitle: 'Turmas na educação escolar indígena',
    publicDescription: 'Turmas registradas na educação escolar indígena.',
    unitLabel: 'turmas',
    sourceLabel: 'INEP — Sinopse Estatística da Educação Básica',
    interpretationNote: 'A medida descreve a oferta registrada.',
  },
  'mat-rural': {
    publicTitle: 'Matrículas em escolas de localização rural',
    publicShortTitle: 'Matrículas em escolas rurais',
    publicDescription: 'Matrículas em unidades escolares classificadas em localização rural.',
    unitLabel: 'matrículas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'Localização rural não identifica, por si só, uma população específica.',
  },
  'mat-eja': {
    publicTitle: 'Matrículas na Educação de Jovens e Adultos',
    publicShortTitle: 'Matrículas na EJA',
    publicDescription: 'Matrículas registradas na Educação de Jovens e Adultos.',
    unitLabel: 'matrículas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida reúne as etapas disponíveis da modalidade.',
  },
  'mat-profissional': {
    publicTitle: 'Matrículas na Educação Profissional e Tecnológica',
    publicShortTitle: 'Matrículas na educação profissional',
    publicDescription: 'Matrículas registradas em ofertas de Educação Profissional e Tecnológica.',
    unitLabel: 'matrículas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A composição depende das ofertas publicadas para o município.',
  },
  'oferta-total': {
    publicTitle: 'Matrículas em cursos técnicos',
    publicShortTitle: 'Matrículas em cursos técnicos',
    publicDescription: 'Total de matrículas nas ofertas técnicas publicadas.',
    unitLabel: 'matrículas',
    sourceLabel: 'INEP — Sinopse Estatística da Educação Básica',
    interpretationNote: 'A medida descreve a oferta registrada.',
  },
  'docentes-total': {
    publicTitle: 'Total de docentes',
    publicShortTitle: 'Docentes',
    publicDescription: 'Total de docentes registrados no município.',
    unitLabel: 'docentes',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida considera os registros do Censo Escolar.',
  },
  'docentes-infantil': {
    publicTitle: 'Docentes da Educação Infantil',
    publicShortTitle: 'Docentes da Educação Infantil',
    publicDescription: 'Docentes registrados na Educação Infantil.',
    unitLabel: 'docentes',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve vínculos docentes registrados.',
  },
  'docentes-fundamental': {
    publicTitle: 'Docentes do Ensino Fundamental',
    publicShortTitle: 'Docentes do Ensino Fundamental',
    publicDescription: 'Docentes registrados no Ensino Fundamental.',
    unitLabel: 'docentes',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve vínculos docentes registrados.',
  },
  'docentes-medio': {
    publicTitle: 'Docentes do Ensino Médio',
    publicShortTitle: 'Docentes do Ensino Médio',
    publicDescription: 'Docentes registrados no Ensino Médio.',
    unitLabel: 'docentes',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve vínculos docentes registrados.',
  },
  'docentes-eja': {
    publicTitle: 'Docentes da Educação de Jovens e Adultos',
    publicShortTitle: 'Docentes da EJA',
    publicDescription: 'Docentes registrados na Educação de Jovens e Adultos.',
    unitLabel: 'docentes',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve vínculos docentes registrados.',
  },
  'docentes-profissional': {
    publicTitle: 'Docentes da Educação Profissional e Tecnológica',
    publicShortTitle: 'Docentes da educação profissional',
    publicDescription: 'Docentes registrados na Educação Profissional e Tecnológica.',
    unitLabel: 'docentes',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve vínculos docentes registrados.',
  },
  internet: {
    publicTitle: 'Escolas com acesso à internet',
    publicShortTitle: 'Acesso à internet',
    publicDescription: 'Participação das escolas com acesso à internet.',
    unitLabel: 'percentual de escolas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida informa presença de acesso, não qualidade da conexão.',
  },
  internet_alunos: {
    publicTitle: 'Escolas com internet disponível para estudantes',
    publicShortTitle: 'Internet para estudantes',
    publicDescription: 'Participação das escolas com internet disponível para uso dos estudantes.',
    unitLabel: 'percentual de escolas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida informa disponibilidade declarada.',
  },
  internet_aprendizagem: {
    publicTitle: 'Escolas com internet para atividades de aprendizagem',
    publicShortTitle: 'Internet para aprendizagem',
    publicDescription: 'Participação das escolas que declaram uso de internet em atividades de aprendizagem.',
    unitLabel: 'percentual de escolas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida informa uso declarado.',
  },
  banda_larga: {
    publicTitle: 'Escolas com conexão de banda larga',
    publicShortTitle: 'Banda larga',
    publicDescription: 'Participação das escolas com conexão de banda larga.',
    unitLabel: 'percentual de escolas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida não informa velocidade contratada ou efetiva.',
  },
  rede_local: {
    publicTitle: 'Escolas com rede local',
    publicShortTitle: 'Rede local',
    publicDescription: 'Participação das escolas com rede local instalada.',
    unitLabel: 'percentual de escolas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida informa infraestrutura declarada.',
  },
  rede_wireless: {
    publicTitle: 'Escolas com rede sem fio',
    publicShortTitle: 'Rede sem fio',
    publicDescription: 'Participação das escolas com rede local sem fio.',
    unitLabel: 'percentual de escolas',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida informa infraestrutura declarada.',
  },
  desktop_aluno: {
    publicTitle: 'Computadores de mesa para uso dos estudantes',
    publicShortTitle: 'Computadores de mesa',
    publicDescription: 'Equipamentos de mesa disponíveis para uso dos estudantes.',
    unitLabel: 'equipamentos',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve equipamentos registrados.',
  },
  comp_portatil_aluno: {
    publicTitle: 'Computadores portáteis para uso dos estudantes',
    publicShortTitle: 'Computadores portáteis',
    publicDescription: 'Equipamentos portáteis disponíveis para uso dos estudantes.',
    unitLabel: 'equipamentos',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve equipamentos registrados.',
  },
  tablet_aluno: {
    publicTitle: 'Tablets para uso dos estudantes',
    publicShortTitle: 'Tablets',
    publicDescription: 'Tablets disponíveis para uso dos estudantes.',
    unitLabel: 'equipamentos',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida descreve equipamentos registrados.',
  },
  subsequente_expansao: {
    publicTitle: 'Expansão das matrículas em cursos técnicos subsequentes',
    publicShortTitle: 'Expansão das matrículas em cursos técnicos subsequentes',
    publicDescription: 'Variação acumulada das matrículas em cursos técnicos subsequentes em relação ao ano-base.',
    unitLabel: 'percentual de expansão',
    sourceLabel: INEP_CENSO,
    interpretationNote: 'A medida acompanha expansão acumulada e não mede qualidade ou permanência.',
  },
}

export function getMunicipalReportIndicatorLabel(
  key: string,
  suppliedLabel?: string,
) {
  const catalogLabel = MUNICIPAL_REPORT_PUBLIC_LABELS[key]?.publicTitle
  if (catalogLabel) return catalogLabel

  const cleanLabel = suppliedLabel?.trim()
  if (cleanLabel && cleanLabel !== key && !cleanLabel.includes('_')) return cleanLabel
  return 'Indicador educacional'
}

export function getPmePublicIndicatorLabel(indicatorId: string, publicName: string) {
  return MUNICIPAL_REPORT_PUBLIC_LABELS[indicatorId]?.publicShortTitle
    ?? publicName.trim()
    ?? 'Indicador educacional'
}
