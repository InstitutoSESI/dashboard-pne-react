/** Navigation belongs to this experience. Nothing here reads browser storage. */
export const PME_PAGES = {
  apresentacao: 'Início',
  inicio: 'Panorama municipal',
  objetivos: 'Objetivos do PNE',
  agenda: 'Agenda de Análise',
  evidencias: 'Evidências',
  financiamento: 'Financiamento',
  relatorios: 'Relatórios',
  objetivo: 'Ficha do objetivo',
  'relatorio-tecnico': 'Relatório Técnico Municipal',
  transparencia: 'Fontes e critérios',
} as const

export type PmePage = keyof typeof PME_PAGES
export type PmeReportKind = 'sintese' | 'caderno' | 'agenda'
export type PmeEvidenceFilter = 'todas' | 'observadas' | 'lacunas'

export interface PmeRoute {
  page: PmePage
  municipalityId: string | null
  objectiveId: string | null
  themeId: string | null
  relationId: string | null
  evidenceFilter: PmeEvidenceFilter
  reportKind: PmeReportKind
  error: string | null
}

const objectivePattern = /^(?:[1-9]|1[0-9])$/
const parameters = ['municipio', 'objetivo', 'tema', 'relacao', 'situacao', 'relatorio']
const isPmePage = (value: string): value is PmePage => Object.prototype.hasOwnProperty.call(PME_PAGES, value)

export function parsePmeHash(hash: string): PmeRoute {
  const [rawPage = '', query = ''] = hash.replace(/^#/, '').split('?')
  const params = new URLSearchParams(query)
  const page = rawPage || 'apresentacao'
  const municipalityId = params.get('municipio') || null
  const objectiveId = params.get('objetivo') || null
  const themeId = params.get('tema') || null
  const relationId = params.get('relacao') || null
  const evidenceFilter = params.get('situacao') || 'todas'
  const reportKind = params.get('relatorio') || 'sintese'
  let error: string | null = null
  if (!isPmePage(page)) error = 'Este endereço não pertence ao percurso PME.'
  else if (parameters.some((key) => params.getAll(key).length > 1)) error = 'O endereço repete um parâmetro de seleção.'
  else if (municipalityId && !/^43\d{5}$/.test(municipalityId)) error = 'O endereço deve conter o código IBGE textual de sete dígitos de um município do RS.'
  else if (objectiveId && !objectivePattern.test(objectiveId)) error = 'O objetivo deve estar entre 1 e 19.'
  else if (page === 'objetivo' && !objectiveId) error = 'Selecione um dos 19 objetivos para abrir sua ficha.'
  else if (themeId && !/^[a-z0-9_-]+$/.test(themeId)) error = 'O tema indicado no endereço é inválido.'
  else if (relationId && !/^[a-zA-Z0-9._-]+$/.test(relationId)) error = 'A relação indicada no endereço é inválida.'
  else if (!['todas', 'observadas', 'lacunas'].includes(evidenceFilter)) error = 'O filtro de disponibilidade indicado no endereço é inválido.'
  else if (!['sintese', 'caderno', 'agenda'].includes(reportKind)) error = 'O tipo de relatório indicado no endereço é inválido.'
  return {
    page: isPmePage(page) ? page : 'apresentacao',
    municipalityId, objectiveId, themeId, relationId,
    evidenceFilter: evidenceFilter as PmeEvidenceFilter,
    reportKind: reportKind as PmeReportKind,
    error,
  }
}

/** Public filters are shareable; a municipality is never coerced to a number. */
export function buildPmeHash(
  page: PmePage,
  context: Partial<Omit<PmeRoute, 'page' | 'error'>> = {},
): string {
  const params = new URLSearchParams()
  if (context.municipalityId) params.set('municipio', context.municipalityId)
  if (context.objectiveId) params.set('objetivo', context.objectiveId)
  if (context.themeId) params.set('tema', context.themeId)
  if (context.relationId) params.set('relacao', context.relationId)
  if (context.evidenceFilter && context.evidenceFilter !== 'todas') params.set('situacao', context.evidenceFilter)
  if (context.reportKind && context.reportKind !== 'sintese') params.set('relatorio', context.reportKind)
  return `#${page}${params.size ? `?${params}` : ''}`
}

export function pmeLink(route: PmeRoute, page: PmePage, changes: Partial<PmeRoute> = {}): string {
  return buildPmeHash(page, { ...route, relationId: null, evidenceFilter: page === 'evidencias' ? route.evidenceFilter : 'todas', reportKind: page === 'relatorios' ? route.reportKind : 'sintese', ...changes })
}
