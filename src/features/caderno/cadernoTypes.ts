/*
 * Contrato de leitura do caderno de hipóteses (`pne2026-caderno-v2`).
 *
 * Todo campo é texto: o artefato não carrega nenhum número capaz de ordenar
 * hipóteses, e a camada de apresentação não pode introduzir um.
 */

export type CadernoHypothesisSection =
  | 'adverse_signal'
  | 'no_public_data'
  | 'protective_present'

export interface CadernoMunicipality {
  readonly ibge7: string
  readonly name: string
  readonly uf: string
}

export interface CadernoSourceDiagnostic {
  readonly builderVersion: string
  readonly catalogSha256: string
  readonly diagnosticCsvSha256: string
}

export interface CadernoCuration {
  readonly sha256: string
  readonly version: string
}

export interface CadernoLegalGoal {
  readonly legalGoalId: string
  readonly title: string
}

export interface CadernoIndicator {
  readonly availability: string
  readonly caveat: string
  readonly collectionTrigger: string
  readonly gapRaw: string
  readonly indicatorId: string
  readonly indicatorTitle: string
  readonly legalGoalTitle: string
  readonly relationId: string
  readonly targetReference: string
  readonly trend: string
  readonly unit: string
  readonly valueRaw: string
  readonly year: string
}

export interface CadernoSignal {
  readonly caution: string
  /** Recorte da observação, verbatim de `subgroup_or_territory` da ficha. */
  readonly dimensions: string
  readonly direction: string
  readonly maxInference: string
  readonly measureId: string
  readonly observability: string
  readonly period: string
  readonly stance: string
  readonly unit: string
  readonly valueRaw: string
}

export interface CadernoEvidence {
  readonly designLevel: string
  readonly finding: string
  readonly id: string
  readonly levelForRelationship: string
}

export interface CadernoRelation {
  readonly classificationRationale: string
  readonly deliberationClass: string
  readonly indicatorId: string
  readonly relationId: string
}

export interface CadernoHypothesis {
  readonly classDate: string
  readonly diagnosticRole: string
  readonly evidence: readonly CadernoEvidence[]
  readonly expectedRelationship: string
  readonly factorId: string
  readonly governability: string
  readonly howToConfirmLocally: readonly string[]
  readonly mechanism: string
  readonly name: string
  readonly relations: readonly CadernoRelation[]
  readonly signals: readonly CadernoSignal[]
}

export interface CadernoReadingCaution {
  readonly factorId: string
  readonly name: string
  readonly note: string
}

export interface CadernoMonitoringSignal {
  readonly dimensions: string
  readonly direction: string
  readonly measureId: string
  readonly period: string
  readonly unit: string
  readonly valueRaw: string
}

export interface CadernoMonitoringContext {
  readonly factorId: string
  readonly name: string
  readonly relations: readonly CadernoRelation[]
  readonly signals: readonly CadernoMonitoringSignal[]
}

export interface CadernoGoal {
  readonly goalId: string
  readonly legalGoals: readonly CadernoLegalGoal[]
  readonly indicators: readonly CadernoIndicator[]
  readonly hypotheses: Readonly<Record<CadernoHypothesisSection, readonly CadernoHypothesis[]>>
  readonly readingCautions: readonly CadernoReadingCaution[]
  readonly monitoring_context: readonly CadernoMonitoringContext[]
}

export interface CadernoDocument {
  readonly schemaVersion: 'pne2026-caderno-v2'
  readonly workbookSchemaVersion: 'pne-priority-hypothesis-workbook-v2'
  readonly contractVersion: string
  readonly municipality: CadernoMunicipality
  readonly referenceDate: string
  readonly disclaimer: string
  readonly curation: CadernoCuration
  readonly sourceDiagnostic: CadernoSourceDiagnostic
  readonly goals: readonly CadernoGoal[]
}

export interface CadernoLoaderResult {
  readonly schemaVersion: 'pne2026-caderno-loader-result-v1'
  readonly municipalityId: string
  readonly municipalityName: string
  readonly referenceDate: string
  readonly outputSha256: string
  readonly caderno: CadernoDocument
}
