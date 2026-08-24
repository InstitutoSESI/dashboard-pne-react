import {
  BadgePlus,
  Banknote,
  BookOpen,
  BusFront,
  CalendarCheck2,
  ChartArea,
  ClipboardList,
  Coins,
  Compass,
  Waypoints,
  Flag,
  GitFork,
  Landmark,
  LayoutGrid,
  ListChecks,
  NotebookPen,
  Rows3,
  Scale,
  ScanSearch,
  type LucideIcon,
} from 'lucide-react'

/*
 * Glifos de orientacao (wayfinding) para os subitens de PNE e Financiamento.
 * Diferente do selo de dominio da Educacao (EducationDomainIcon), que carrega
 * identidade e reaparece no eyebrow do cabecalho, estes vivem so na barra
 * lateral: dao a cada aba uma silhueta reconhecivel a 16px. Cada glifo nasce do
 * vocabulario da propria aba -- balanca para metas legais, onibus para o PNATE.
 *
 * Convencao compartilhada com os selos: viewBox 24x24, traco 1,7, sem fill.
 * Nenhum repete o icone do grupo na mesma tela (PNE = alvo; Financiamento =
 * barras) nem os itens globais (casa, documento).
 */
export type NavGlyphName =
  | 'pne-overview'
  | 'pne-legal-goals'
  | 'pne2014'
  | 'pne2026'
  | 'diagnostico'
  | 'matriz-prioridades'
  | 'caderno'
  | 'cenarios-educacao'
  | 'financeiros'
  | 'financeiros-panorama'
  | 'financeiros-aplicacao-recursos'
  | 'financeiros-fundeb'
  | 'financeiros-vaar'
  | 'financeiros-pnate'
  | 'visao-geral'
  | 'panorama'
  | 'educacao-superior'
  | 'demanda'
  | 'metodologia'

type NavGlyphSize = 'sm' | 'md'

const GLYPH_ICONS: Record<NavGlyphName, LucideIcon> = {
  // Livro aberto -- a leitura introdutoria "o que e o PNE".
  'pne-overview': BookOpen,
  // Balanca -- as metas legais / referencia normativa.
  'pne-legal-goals': Scale,
  // Calendario com marca -- o ciclo 2014-2024 ja concluido.
  pne2014: CalendarCheck2,
  // Bandeira -- o ciclo 2026-2036, a meta adiante.
  pne2026: Flag,
  // Lupa sobre barras -- o diagnostico, a leitura analitica do municipio.
  diagnostico: ScanSearch,
  // Lista de verificacao -- a organizacao dos problemas que exigem prioridade.
  'matriz-prioridades': ListChecks,
  // Caderno com caneta -- as hipoteses anotadas meta a meta para a oficina.
  caderno: NotebookPen,
  // Caminhos que se abrem a partir de um mesmo no -- as quatro leituras possiveis.
  'cenarios-educacao': Waypoints,
  // Grade -- a visao geral, o quadro de todas as areas.
  financeiros: LayoutGrid,
  // Area sob a curva -- o panorama, a sintese ampla.
  'financeiros-panorama': ChartArea,
  // Cedula -- a aplicacao e execucao dos recursos.
  'financeiros-aplicacao-recursos': Banknote,
  // Pilha de moedas -- o fundo redistribuido (FUNDEB).
  'financeiros-fundeb': Coins,
  // Moeda com adicao -- a complementacao (VAAR).
  'financeiros-vaar': BadgePlus,
  // Onibus -- o transporte escolar rural (PNATE).
  'financeiros-pnate': BusFront,
  // Bussola -- a visao geral, o ponto de partida para orientar a leitura.
  'visao-geral': Compass,
  // Barra segmentada -- a composicao das matriculas (Panorama educacional).
  panorama: Rows3,
  // Instituicao com colunas -- a Educacao Superior.
  'educacao-superior': Landmark,
  // Setas divergentes -- os cenarios (trajetorias futuras) de atendimento.
  demanda: GitFork,
  // Prancheta -- a metodologia e as fontes documentadas.
  metodologia: ClipboardList,
}

export function NavGlyphIcon({
  name,
  size = 'sm',
}: {
  name: NavGlyphName
  size?: NavGlyphSize
}) {
  const Icon = GLYPH_ICONS[name]

  return (
    <Icon
      aria-hidden="true"
      className={`nav-glyph nav-glyph--${size}`}
      strokeWidth={1.7}
    />
  )
}

export function isNavGlyphName(value: unknown): value is NavGlyphName {
  return typeof value === 'string' && value in GLYPH_ICONS
}
