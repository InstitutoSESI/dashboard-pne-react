import type { CellObject, Row, Sheet } from 'write-excel-file/browser'
import { PNE_2026_FEDERAL_GUIDANCE } from '../../data/pne2026FederalGuidance.js'
import { cadernoFrontKey } from '../../domain/cadernoFrontsStorage.js'
import { resolveFactorGuidance } from './cadernoFederalGuidance.js'
import { FACTOR_TITLE } from './cadernoPlainLanguage.js'
import { CADERNO_ALL_SECTION_KEYS, goalFullTitle } from './cadernoVocabulary.js'
import type { CadernoDocument } from './cadernoTypes'

/*
 * Planilha da oficina municipal.
 *
 * As colunas são exatamente as do `municipal-decision-template` da pesquisa:
 * a identificação vem preenchida do caderno e todo campo de ação nasce vazio
 * para ser escrito na oficina. A classe pública entra como estava na data da
 * ficha (`public_deliberation_class_at_decision`) e a exportação não altera,
 * agrega nem pontua nada.
 */

export const CADERNO_DECISION_COLUMNS = [
  'municipality_ibge7',
  'municipality_name',
  'uf',
  'decision_cycle',
  'goal_id',
  'indicator_id',
  'factor_id',
  'diagnostic_reference_date',
  'public_deliberation_class_at_decision',
  'municipal_weight_profile',
  'action_decision',
  'action_description',
  'responsible',
  'partners',
  'deadline',
  'budget_nominal',
  'budget_share_of_available',
  'process_indicator',
  'outcome_indicator',
  'baseline',
  'action_target',
  'decision_justification',
  'workshop_date',
  'participants',
  'review_date',
  'notes',
] as const

export type CadernoDecisionColumn = (typeof CADERNO_DECISION_COLUMNS)[number]

export type CadernoDecisionRow = Readonly<Record<CadernoDecisionColumn, string>>

export const CADERNO_FEDERAL_GUIDANCE_COLUMNS = [
  'goal_id',
  'objetivo',
  'factor_id',
  'causa',
  'orientacao_meta',
  'orientacao_causa',
  'referencias',
] as const

export type CadernoFederalGuidanceColumn =
  (typeof CADERNO_FEDERAL_GUIDANCE_COLUMNS)[number]

export type CadernoFederalGuidanceRow = Readonly<
  Record<CadernoFederalGuidanceColumn, string>
>

export interface CadernoDecisionWorkbook {
  fileName: string
  federalGuidanceRows: readonly CadernoFederalGuidanceRow[]
  rows: readonly CadernoDecisionRow[]
  sheets: Sheet<Blob>[]
}

const PREFILLED_COLUMNS = new Set<CadernoDecisionColumn>([
  'municipality_ibge7',
  'municipality_name',
  'uf',
  'goal_id',
  'indicator_id',
  'factor_id',
  'diagnostic_reference_date',
  'public_deliberation_class_at_decision',
])

const HEADER_BACKGROUND = '#14532D'
const HEADER_TEXT = '#FFFFFF'
const OPEN_FIELD_BACKGROUND = '#FEF3C7'
const BORDER = '#CBD5E1'
const TEXT = '#172033'

function emptyRow(): Record<CadernoDecisionColumn, string> {
  return Object.fromEntries(
    CADERNO_DECISION_COLUMNS.map((column) => [column, '']),
  ) as Record<CadernoDecisionColumn, string>
}

/**
 * Uma linha por hipótese selecionada e por relação meta×indicador que a
 * sustenta: é a relação que carrega a classe pública vigente.
 */
export function buildCadernoDecisionRows(
  caderno: CadernoDocument,
  selectedKeys: readonly string[],
): readonly CadernoDecisionRow[] {
  const selected = new Set(selectedKeys)
  const rows: CadernoDecisionRow[] = []

  for (const goal of caderno.goals) {
    for (const sectionKey of CADERNO_ALL_SECTION_KEYS) {
      for (const hypothesis of goal.hypotheses[sectionKey]) {
        if (!selected.has(cadernoFrontKey(goal.goalId, hypothesis.factorId))) continue
        for (const relation of hypothesis.relations) {
          rows.push(Object.freeze({
            ...emptyRow(),
            municipality_ibge7: caderno.municipality.ibge7,
            municipality_name: caderno.municipality.name,
            uf: caderno.municipality.uf,
            goal_id: relation.relationId,
            indicator_id: relation.indicatorId,
            factor_id: hypothesis.factorId,
            diagnostic_reference_date: caderno.referenceDate,
            public_deliberation_class_at_decision: relation.deliberationClass,
          }))
        }
      }
    }
  }

  return rows
}

interface GuidanceReference {
  readonly label: string
  readonly url: string
}

function formatGuidanceReferences(references: readonly GuidanceReference[]): string {
  const seenUrls = new Set<string>()
  const formatted: string[] = []

  for (const reference of references) {
    if (!reference.label || !reference.url || seenUrls.has(reference.url)) continue
    seenUrls.add(reference.url)
    formatted.push(`${reference.label} — ${reference.url}`)
  }

  return formatted.join('\n')
}

/** Uma linha informativa por frente municipal selecionada. */
export function buildCadernoFederalGuidanceRows(
  caderno: CadernoDocument,
  selectedKeys: readonly string[],
): readonly CadernoFederalGuidanceRow[] {
  const selected = new Set(selectedKeys)
  const emitted = new Set<string>()
  const rows: CadernoFederalGuidanceRow[] = []

  for (const goal of caderno.goals) {
    const goalGuidance = PNE_2026_FEDERAL_GUIDANCE[goal.goalId]
    for (const sectionKey of CADERNO_ALL_SECTION_KEYS) {
      for (const hypothesis of goal.hypotheses[sectionKey]) {
        const frontKey = cadernoFrontKey(goal.goalId, hypothesis.factorId)
        if (!selected.has(frontKey) || emitted.has(frontKey)) continue
        emitted.add(frontKey)

        const factorGuidance = resolveFactorGuidance(hypothesis.factorId)
        const references: GuidanceReference[] = [
          ...(goalGuidance?.sources ?? []).map((source) => ({
            label: source.name,
            url: source.url,
          })),
          ...(factorGuidance?.references ?? []),
        ]

        rows.push(Object.freeze({
          goal_id: goal.goalId,
          objetivo: goalFullTitle(goal),
          factor_id: hypothesis.factorId,
          causa: FACTOR_TITLE[hypothesis.factorId] ?? hypothesis.name ?? '',
          orientacao_meta: goalGuidance?.summary ?? '',
          orientacao_causa: factorGuidance?.text ?? '',
          referencias: formatGuidanceReferences(references),
        }))
      }
    }
  }

  return rows
}

function cell(value: string, prefilled: boolean): CellObject {
  return {
    value,
    type: String,
    format: '@',
    textColor: TEXT,
    alignVertical: 'top',
    wrap: true,
    borderColor: BORDER,
    borderStyle: 'thin',
    ...(prefilled ? {} : { backgroundColor: OPEN_FIELD_BACKGROUND }),
  }
}

function headerCell(value: string): CellObject {
  return {
    value,
    type: String,
    format: '@',
    backgroundColor: HEADER_BACKGROUND,
    textColor: HEADER_TEXT,
    fontWeight: 'bold',
    alignVertical: 'center',
    wrap: true,
    borderColor: BORDER,
    borderStyle: 'thin',
  }
}

export function buildCadernoDecisionFileName(caderno: CadernoDocument): string {
  const municipality = caderno.municipality.name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    || caderno.municipality.ibge7
  return `caderno-frentes-${municipality}-${caderno.referenceDate}.xlsx`
}

export function buildCadernoDecisionWorkbook(
  caderno: CadernoDocument,
  selectedKeys: readonly string[],
): CadernoDecisionWorkbook {
  const rows = buildCadernoDecisionRows(caderno, selectedKeys)
  const federalGuidanceRows = buildCadernoFederalGuidanceRows(caderno, selectedKeys)
  const data: Row[] = [
    CADERNO_DECISION_COLUMNS.map((column) => headerCell(column)),
    ...rows.map((row) => CADERNO_DECISION_COLUMNS.map(
      (column) => cell(row[column], PREFILLED_COLUMNS.has(column)),
    )),
  ]
  const federalGuidanceData: Row[] = [
    CADERNO_FEDERAL_GUIDANCE_COLUMNS.map((column) => headerCell(column)),
    ...federalGuidanceRows.map((row) => CADERNO_FEDERAL_GUIDANCE_COLUMNS.map(
      (column) => cell(row[column], true),
    )),
  ]

  return {
    fileName: buildCadernoDecisionFileName(caderno),
    federalGuidanceRows,
    rows,
    sheets: [
      {
        sheet: 'Frentes da oficina',
        data,
        columns: CADERNO_DECISION_COLUMNS.map((column) => ({
          width: PREFILLED_COLUMNS.has(column) ? 24 : 32,
        })),
        stickyRowsCount: 1,
        stickyColumnsCount: 3,
        orientation: 'landscape',
        showGridLines: false,
      },
      {
        sheet: 'Orientação federal',
        data: federalGuidanceData,
        columns: CADERNO_FEDERAL_GUIDANCE_COLUMNS.map((column) => ({
          width: column === 'goal_id' || column === 'factor_id' ? 16 : 48,
        })),
        stickyRowsCount: 1,
        stickyColumnsCount: 3,
        orientation: 'landscape',
        showGridLines: false,
      },
    ],
  }
}
