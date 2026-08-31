/*
 * Contrato público do Panorama da Região, do lado da interface.
 *
 * O `null` permanece semântico: dado ausente não vira zero. Taxas regionais
 * existem apenas onde o artefato publica numerador e denominador agregáveis;
 * nos demais indicadores, o contrato identifica a mediana municipal.
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

export type RegionalEducationCountGroup =
  | 'rede'
  | 'oferta'
  | 'educacao_indigena'
  | 'sistema_s'

export interface RegionalEducationCountIndicator {
  readonly chave: string
  readonly titulo: string
  readonly grupo: RegionalEducationCountGroup
  readonly ano: number | null
  readonly valor: number | null
  readonly municipiosComDado: number
}

export type RegionalDistributionUnit = 'percent' | 'index' | 'score' | 'decimal'

export interface RegionalDistributionIndicator {
  readonly chave: string
  readonly titulo: string
  readonly unidade: RegionalDistributionUnit
  readonly ano: number | null
  readonly valor: number | null
  readonly valorEstado: number | null
  readonly minimoMunicipal: number | null
  readonly maximoMunicipal: number | null
  readonly municipiosComDado: number
  readonly municipiosEstadoComDado: number
}

export interface RegionalEducationQualityCategory {
  readonly chave: string
  readonly label: string
  readonly indicadores: readonly RegionalDistributionIndicator[]
}

export interface RegionalVaarIndicator {
  readonly chave: string
  readonly titulo: string
  readonly valor: number | null
  readonly valorEstado: number | null
  readonly municipiosComDado: number
  readonly municipiosEstadoComDado: number
}

export interface RegionalVaarBlock {
  readonly label: string
  readonly descricao: string
  readonly ano: number | null
  readonly indicadores: readonly RegionalVaarIndicator[]
}

export interface RegionalEducationBlock {
  readonly label: string
  readonly descricao: string
  readonly contagens: readonly RegionalEducationCountIndicator[]
  readonly qualidade: readonly RegionalEducationQualityCategory[]
  readonly vaar: RegionalVaarBlock
}

export type RegionalPneReferenceType = 'legal' | 'monitoring' | 'published'
export type RegionalPneDirection = 'at_least' | 'at_most'
export type RegionalPneMethod = 'regional_ratio' | 'municipal_median'

export interface RegionalPneReference {
  readonly tipo: RegionalPneReferenceType
  readonly label: string
  readonly valor: number
  readonly ano: number | null
  readonly direcao: RegionalPneDirection
}

export interface RegionalPneResult {
  readonly metodo: RegionalPneMethod
  readonly ano: number | null
  readonly valor: number | null
  readonly valorEstado: number | null
  readonly municipiosComDado: number
  readonly municipiosEstadoComDado: number
  readonly minimoMunicipal: number | null
  readonly maximoMunicipal: number | null
  readonly municipiosNaReferencia: number | null
  readonly distanciaReferencia: number | null
}

export interface RegionalPneIndicator {
  readonly chave: string
  readonly titulo: string
  readonly descricao: string
  readonly unidade: 'percent'
  readonly acompanhaReferencia: boolean
  readonly referencia: RegionalPneReference | null
  readonly resultado: RegionalPneResult
}

export interface RegionalPneCategory {
  readonly chave: string
  readonly label: string
  readonly indicadores: readonly RegionalPneIndicator[]
}

export interface RegionalPneBlock {
  readonly cicloId: 'pne_2026_2036'
  readonly label: string
  readonly descricao: string
  readonly totalIndicadores: number
  readonly totalReferencias: number
  readonly referenciasAvaliadas: number
  readonly referenciasAtingidas: number
  readonly indicadoresSemResultado: number
  readonly categorias: readonly RegionalPneCategory[]
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
  readonly educacao: RegionalEducationBlock
  readonly pne2026: RegionalPneBlock
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
