/*
 * Contrato público do painel regional, do lado da interface.
 *
 * Os tipos descrevem exatamente o que o JSON publicado entrega — nada além. O
 * `null` é parte do contrato, não um acidente: ele marca o ano em que a região
 * não teve cobertura completa, e `municipiosComDado` diz quantos informaram.
 */

export interface RegionalMunicipality {
  readonly ibgeCode: string
  readonly nome: string
  readonly slug: string
}

export interface RegionalIdentity {
  readonly slug: string
  readonly nome: string
  readonly totalMunicipios: number
  readonly municipios: readonly RegionalMunicipality[]
}

export interface RegionalPageCopy {
  readonly eyebrow: string
  readonly titulo: string
  readonly descricao: string
}

export interface RegionalCoveragePoint {
  readonly ano: number
  readonly numerador: number | null
  readonly denominador: number | null
  readonly valor: number | null
  readonly municipiosComDado: number
}

export interface RegionalCoverageIndicator {
  readonly chave: string
  readonly titulo: string
  readonly faixaEtaria: string
  readonly unidade: 'percent'
  readonly baseTerritorial: { readonly numerador: string, readonly denominador: string }
  readonly campos: { readonly numerador: string, readonly denominador: string }
  readonly ultimoAno: number | null
  readonly valorUltimoAno: number | null
  readonly series: readonly RegionalCoveragePoint[]
}

export interface RegionalCoverageBlock {
  readonly label: string
  readonly descricao: string
  readonly indicadores: readonly RegionalCoverageIndicator[]
}

export interface RegionalCountPoint {
  readonly ano: number
  readonly valor: number | null
  readonly municipiosComDado: number
  readonly percentual?: number | null
}

export type RegionalBreakdown = Readonly<Record<string, readonly RegionalCountPoint[]>>

export interface RegionalEnrollmentSeries {
  readonly total: readonly RegionalCountPoint[]
  readonly integral: readonly RegionalCountPoint[]
  readonly por_etapa: RegionalBreakdown
  readonly por_dependencia: RegionalBreakdown
  readonly por_localizacao: RegionalBreakdown
}

export interface RegionalEnrollmentBlock {
  readonly label: string
  readonly descricao: string
  readonly ultimoAno: number | null
  readonly totalUltimoAno: number | null
  readonly series: RegionalEnrollmentSeries
}

export interface RegionalSource {
  readonly nome: string
  readonly uso: string
}

export interface RegionalDocument {
  readonly schemaVersion: string
  readonly generatorVersion: string
  readonly generatedAt: string
  readonly stateCode: string
  readonly contentVersion: string
  readonly regiao: RegionalIdentity
  readonly pagina: RegionalPageCopy
  readonly atendimento: RegionalCoverageBlock
  readonly matriculas: RegionalEnrollmentBlock
  readonly metodologia: readonly string[]
  readonly fontes: readonly RegionalSource[]
}

export interface RegionalManifestEntry {
  readonly slug: string
  readonly name: string
  readonly path: string
  readonly municipalityCount: number
  readonly contentHash: string
  readonly contentVersion: string
  readonly byteSize: number
}

export interface RegionalLoaderResult {
  readonly document: RegionalDocument
  readonly entry: RegionalManifestEntry
  readonly integrity: 'verified' | 'declared'
}
