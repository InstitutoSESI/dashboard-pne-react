import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys.js'
import type { AppPageKey } from '../types/app'
import { normalizeRouteValue } from './appHash.js'

/*
 * Registro unico de navegacao.
 *
 * Antes deste modulo, registrar ou mover uma pagina exigia editar sete arquivos
 * coordenados (tipo, mapa de hash, produto, roteador, cabecalho, glifo,
 * migalha). Aqui vivem, num lugar so, a identidade de cada pagina (rota
 * canonica, aliases, rotulo, glifo, migalha) e a composicao dos grupos da barra
 * lateral.
 *
 * Duas fronteiras ficam deliberadamente de fora:
 *
 * 1. O produto analitico de cada pagina continua em `config/analyticsProducts`,
 *    contrato congelado por teste. O registro nao o duplica: quem precisa de
 *    visibilidade chama `resolvePageProduct(page)`.
 * 2. Os itens dos grupos "Indicadores educacionais" e "Financiamento" continuam
 *    nascendo dos catalogos canonicos de cada dominio (secoes de educacao e
 *    modulos financeiros). O registro apenas declara de qual catalogo o grupo
 *    se alimenta (`dynamicItems`), para nao duplicar rotulos que ja tem dono.
 *
 * Invariante: este modulo e puro. Ele e compilado isoladamente pelos testes de
 * rota, entao nao pode importar React, icones ou CSS. Icones e glifos aparecem
 * aqui como nomes, resolvidos para componentes no `Header`.
 */

export type NavGroupId = 'pne' | 'educacao' | 'financeiros' | 'relatorios' | 'analise-regional'

export type NavGroupIconName = 'Target' | 'GraduationCap' | 'Landmark' | 'FileText' | 'Compass'

export type NavDynamicItemSource = 'education-sections' | 'financial-modules'

export type NavItemCondition = 'foresight'

export interface NavPage {
  /** Chave canonica da pagina, a mesma do roteador. */
  readonly key: AppPageKey
  /** Rotulo curto, usado na barra lateral. */
  readonly label: string
  /** Rota canonica (sem `#`), a que a navegacao escreve na URL. */
  readonly route: string
  /** Rotas aceitas alem da canonica; nenhuma morre sem decisao registrada. */
  readonly aliases: readonly string[]
  /** Nome do glifo de wayfinding, ou `null` quando o item nao usa glifo. */
  readonly glyph: string | null
  /** Migalha da barra de contexto, ou `null` quando outro modulo a resolve. */
  readonly crumb: string | null
}

export interface NavItem {
  /** Identidade do item para o estado ativo do acordeao. */
  readonly key: string
  readonly label: string
  /** Alvo de navegacao; pode carregar query, como as secoes de educacao. */
  readonly target: string
  /** Pagina que o alvo resolve — decide a visibilidade por produto. */
  readonly page: AppPageKey
  readonly glyph: string | null
  readonly condition: NavItemCondition | null
}

export interface NavGroup {
  readonly id: NavGroupId
  readonly label: string
  readonly icon: NavGroupIconName
  readonly items: readonly NavItem[]
  readonly dynamicItems: NavDynamicItemSource | null
  /** Paginas cujo acordeao abre neste grupo. */
  readonly ownedPages: readonly AppPageKey[]
}

const page = (entry: NavPage): NavPage => Object.freeze(entry)

export const NAV_PAGES: readonly NavPage[] = Object.freeze([
  page({
    key: 'home',
    label: 'Home',
    route: 'home',
    aliases: [],
    glyph: null,
    crumb: 'Home',
  }),
  page({
    key: 'pne-overview',
    label: 'O que é o PNE',
    route: 'pne-overview',
    aliases: [],
    glyph: 'pne-overview',
    crumb: 'Metas do PNE / O que é o PNE',
  }),
  page({
    key: 'pne-legal-goals',
    label: 'Metas legais',
    route: 'pne-legal-goals',
    aliases: ['metas-legais'],
    glyph: 'pne-legal-goals',
    crumb: 'Metas legais do PNE 2026-2036 / Ciclo vigente',
  }),
  page({
    key: 'pne2014',
    label: 'PNE 2014–2024',
    route: 'pne2014',
    aliases: ['pne2024'],
    glyph: 'pne2014',
    crumb: 'Metas do PNE / Ciclo encerrado / Resultado consolidado',
  }),
  page({
    key: 'pne2026',
    label: 'PNE 2026–2036',
    route: 'pne2026',
    aliases: [],
    glyph: 'pne2026',
    crumb: 'Metas do PNE / Ciclo vigente / Acompanhamento atual',
  }),
  page({
    key: 'diagnostico',
    label: 'Diagnóstico municipal',
    route: 'diagnostico',
    aliases: [],
    glyph: 'diagnostico',
    crumb: 'Relatórios / Diagnóstico Municipal',
  }),
  page({
    key: 'matriz-prioridades',
    label: 'Matriz de Prioridades',
    route: 'matriz-prioridades',
    aliases: [],
    glyph: 'matriz-prioridades',
    crumb: 'Relatórios / Matriz de Prioridades',
  }),
  page({
    key: 'cenarios-educacao',
    label: 'Cenários da educação',
    route: 'cenarios-da-educacao',
    aliases: ['cenarios-da-educacao-municipal', 'cenarios-educacao'],
    glyph: 'cenarios-educacao',
    crumb: 'Metas do PNE / Planejamento municipal / Cenários da educação',
  }),
  page({
    key: 'educacao',
    label: 'Indicadores educacionais',
    route: 'educacao',
    aliases: ['sistemas', 'escolas-sistemas'],
    glyph: null,
    crumb: 'Indicadores de Educação',
  }),
  page({
    key: 'relatorio-tecnico-municipal',
    label: 'Relatório Técnico Municipal',
    route: 'relatorio-tecnico-municipal',
    aliases: [],
    glyph: 'relatorio-tecnico-municipal',
    crumb: 'Relatórios / Relatório Técnico Municipal',
  }),
  page({
    key: FINANCIAL_PAGE_KEYS.overview,
    label: 'Visão geral',
    route: 'financeiros',
    aliases: [],
    glyph: 'financeiros',
    crumb: null,
  }),
  page({
    key: FINANCIAL_PAGE_KEYS.panorama,
    label: 'Panorama financeiro',
    route: 'financeiros-panorama',
    aliases: ['panorama-financeiro'],
    glyph: 'financeiros-panorama',
    crumb: null,
  }),
  page({
    key: FINANCIAL_PAGE_KEYS.application,
    label: 'Aplicação e execução',
    route: 'financeiros-aplicacao-recursos',
    aliases: ['siope'],
    glyph: 'financeiros-aplicacao-recursos',
    crumb: null,
  }),
  page({
    key: FINANCIAL_PAGE_KEYS.fundeb,
    label: 'FUNDEB',
    route: 'financeiros-fundeb',
    aliases: ['fundeb'],
    glyph: 'financeiros-fundeb',
    crumb: null,
  }),
  page({
    key: FINANCIAL_PAGE_KEYS.vaar,
    label: 'Complementação VAAR',
    route: 'financeiros-vaar',
    aliases: ['vaar'],
    glyph: 'financeiros-vaar',
    crumb: null,
  }),
  page({
    key: FINANCIAL_PAGE_KEYS.pnate,
    label: 'PNATE',
    route: 'financeiros-pnate',
    aliases: ['pnate'],
    glyph: 'financeiros-pnate',
    crumb: null,
  }),
])

const NAV_PAGES_BY_KEY: ReadonlyMap<AppPageKey, NavPage> = new Map(
  NAV_PAGES.map((entry) => [entry.key, entry]),
)

export function getNavPage(key: AppPageKey): NavPage | null {
  return NAV_PAGES_BY_KEY.get(key) ?? null
}

/**
 * Mapa de rota normalizada para pagina. Toda rota vigente — canonica ou alias —
 * nasce daqui; o teste de rotas congela o conjunto resultante.
 */
export function buildHashPageMap(): Readonly<Record<string, AppPageKey>> {
  const map: Record<string, AppPageKey> = {}

  for (const entry of NAV_PAGES) {
    for (const route of [entry.route, ...entry.aliases]) {
      const normalized = normalizeRouteValue(route)
      if (normalized in map) {
        throw new Error(`Rota duplicada no registro de navegação: ${route}`)
      }
      map[normalized] = entry.key
    }
  }

  return Object.freeze(map)
}

/** Migalhas derivadas do registro, na forma que a barra de contexto consome. */
export function buildPageCrumbs(): Readonly<Record<string, string>> {
  const crumbs: Record<string, string> = {}

  for (const entry of NAV_PAGES) {
    if (entry.crumb !== null) crumbs[entry.key] = entry.crumb
  }

  return Object.freeze(crumbs)
}

const itemFromPage = (
  key: AppPageKey,
  overrides: Partial<Pick<NavItem, 'label' | 'condition'>> = {},
): NavItem => {
  const entry = NAV_PAGES_BY_KEY.get(key)
  if (!entry) throw new Error(`Página fora do registro de navegação: ${key}`)

  return Object.freeze({
    key,
    label: overrides.label ?? entry.label,
    target: entry.route,
    page: key,
    glyph: entry.glyph,
    condition: overrides.condition ?? null,
  })
}

/*
 * Um item que aponta para uma seção de outra página. O grupo dono do acordeão
 * continua sendo o da página alvo (regra de fallback), mas o atalho vive onde
 * o leitor o procura.
 */
const sectionItem = (item: NavItem): NavItem => Object.freeze(item)

export const NAV_GROUPS: readonly NavGroup[] = Object.freeze([
  /*
   * Relatórios reúne as leituras fechadas sobre o município — o que se lê de
   * ponta a ponta, não o que se consulta indicador a indicador. Por isso mistura
   * páginas de produtos diferentes (PNE e educação): o grupo é uma decisão
   * editorial, e a visibilidade continua sendo decidida item a item.
   */
  Object.freeze({
    id: 'relatorios',
    label: 'Relatórios',
    icon: 'FileText',
    items: Object.freeze([
      itemFromPage('diagnostico', { label: 'Diagnóstico Municipal' }),
      itemFromPage('matriz-prioridades'),
      sectionItem({
        key: 'panorama-educacional',
        label: 'Panorama Educacional',
        target: 'educacao?secao=panorama',
        page: 'educacao',
        glyph: 'panorama',
        condition: null,
      }),
      itemFromPage('relatorio-tecnico-municipal'),
    ]),
    dynamicItems: null,
    ownedPages: Object.freeze([
      'diagnostico',
      'matriz-prioridades',
      'relatorio-tecnico-municipal',
    ]),
  } satisfies NavGroup),
  Object.freeze({
    id: 'pne',
    label: 'PNE',
    icon: 'Target',
    items: Object.freeze([
      itemFromPage('pne-overview'),
      itemFromPage('pne-legal-goals'),
      itemFromPage('pne2014'),
      itemFromPage('pne2026'),
      itemFromPage('cenarios-educacao', { condition: 'foresight' }),
    ]),
    dynamicItems: null,
    ownedPages: Object.freeze([
      'pne-overview',
      'pne-legal-goals',
      'pne2014',
      'pne2026',
      'cenarios-educacao',
    ]),
  } satisfies NavGroup),
  Object.freeze({
    id: 'educacao',
    label: 'Indicadores educacionais',
    icon: 'GraduationCap',
    items: Object.freeze([]),
    dynamicItems: 'education-sections',
    ownedPages: Object.freeze(['educacao']),
  } satisfies NavGroup),
  Object.freeze({
    id: 'financeiros',
    label: 'Financiamento',
    icon: 'Landmark',
    items: Object.freeze([]),
    dynamicItems: 'financial-modules',
    ownedPages: Object.freeze([
      FINANCIAL_PAGE_KEYS.overview,
      FINANCIAL_PAGE_KEYS.panorama,
      FINANCIAL_PAGE_KEYS.application,
      FINANCIAL_PAGE_KEYS.fundeb,
      FINANCIAL_PAGE_KEYS.vaar,
      FINANCIAL_PAGE_KEYS.pnate,
    ]),
  } satisfies NavGroup),
])

/*
 * Itens raiz da barra lateral: fora de qualquer grupo, logo abaixo da Home. O
 * Relatório Técnico Municipal vivia aqui até a Fase 4 da reorganização, quando
 * entrou no grupo Relatórios.
 */
export const NAV_ROOT_ITEMS: readonly NavItem[] = Object.freeze([])

export function getOwnerGroupId(activePage: AppPageKey): NavGroupId | null {
  for (const group of NAV_GROUPS) {
    if (group.ownedPages.includes(activePage)) return group.id
  }
  return null
}
