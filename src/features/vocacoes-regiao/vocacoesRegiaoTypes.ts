/*
 * A forma do pacote público `vocacoes-regiao-2.6.0`, do lado de quem renderiza.
 *
 * Estes tipos descrevem o que o validador já garantiu. Eles não repetem a
 * validação — repetir daria a ilusão de duas camadas onde há uma: em runtime só
 * o validador existe, e o TypeScript some na compilação. O que os tipos fazem é
 * impedir que a página leia um campo que o contrato não tem.
 */

export type VocacoesEvidenceClass =
  | 'observed'
  | 'preliminary'
  | 'calculated'
  | 'estimated_indirect'

export type VocacoesPeriodGranularity = 'annual' | 'monthly'

export interface VocacoesPoint {
  readonly period: number
  readonly value: number
  readonly evidenceClass: VocacoesEvidenceClass
}

export interface VocacoesSeries {
  readonly seriesId: string
  readonly label: string
  readonly unitLabel: string
  readonly sourceLabel: string
  readonly evidenceClass: VocacoesEvidenceClass
  readonly evidenceLabel: string
  readonly universeLabel: string | null
  readonly aggregationLabel: string
  readonly ratioOf: { readonly numeratorLabel: string; readonly denominatorLabel: string } | null
  readonly periodGranularity: VocacoesPeriodGranularity
  readonly periodStart: number
  readonly periodEnd: number
  readonly periodLabel: string
  readonly preliminaryPeriods: readonly number[]
  readonly limitations: readonly string[]
  readonly points: readonly VocacoesPoint[]
}

export interface VocacoesSeriesReference {
  readonly seriesId: string
  readonly label: string
}

export interface VocacoesWindow {
  readonly start: number
  readonly end: number
}

export type VocacoesAssociativeReasonCode =
  | 'sem_intervalos_comparaveis'
  | 'janela_curta'
  | 'variancia_nula'
  | 'variacao_nula'
  | 'contraste_sem_regioes_comparaveis'
  | 'defasagem_sem_janela_suficiente'
  | 'serie_ausente'

export interface VocacoesAssociativeAbsence {
  readonly reasonCode: VocacoesAssociativeReasonCode
}

export interface VocacoesDirectionConcordance {
  readonly windowStart: number
  readonly windowEnd: number
  readonly intervals: number
  readonly concordant: number
  readonly opposite: number
  readonly ties: number
  readonly statement: string
}

export interface VocacoesComovementSeries {
  readonly seriesId: string
  readonly effStart: number
  readonly effEnd: number
  readonly valueStart: number
  readonly valueEnd: number
  readonly delta: number
  readonly deltaKind: 'nivel' | 'pontos'
}

export interface VocacoesAssociationComovement {
  readonly outcome: VocacoesComovementSeries
  readonly factor: VocacoesComovementSeries
  readonly statement: string
}

export interface VocacoesPairComovement {
  readonly a: VocacoesComovementSeries
  readonly b: VocacoesComovementSeries
  readonly statement: string
}

export interface VocacoesCorrelation {
  readonly intervals: number
  readonly pearsonDelta: number
  readonly spearmanDelta: number
  readonly strength: 'fraca' | 'moderada' | 'forte'
  readonly direction: 'positiva' | 'negativa' | 'nula'
  readonly statement: string
}

export interface VocacoesLaggedCorrelation {
  readonly intervals: number
  readonly pearsonDelta: number
  readonly spearmanDelta: number
  readonly strength: 'fraca' | 'moderada' | 'forte'
  readonly direction: 'positiva' | 'negativa' | 'nula'
}

export interface VocacoesStateContrast {
  readonly seriesId: string
  readonly statistic: 'variacao_percentual' | 'variacao_em_pontos'
  readonly value: number
  readonly rank: number
  readonly totalComparable: number
  readonly sameDirectionCount: number
  readonly direction: 'alta' | 'queda'
  readonly statement: string
}

export interface VocacoesFactorReading {
  readonly outcomeSeriesId: string
  readonly factorSeriesId: string
  readonly directionConcordance: VocacoesDirectionConcordance | VocacoesAssociativeAbsence
  readonly comovement: VocacoesAssociationComovement | VocacoesAssociativeAbsence
  readonly correlation: VocacoesCorrelation | VocacoesAssociativeAbsence
}

export interface VocacoesAssociationReading {
  readonly grammarVersion: string
  readonly methodNote: string
  readonly factorReadings: readonly VocacoesFactorReading[]
  readonly stateContrast: VocacoesStateContrast | VocacoesAssociativeAbsence
}

export interface VocacoesTemporalReading {
  readonly grammarVersion: string
  readonly methodNote: string
  readonly directionConcordance: VocacoesDirectionConcordance | VocacoesAssociativeAbsence
  readonly comovement: VocacoesPairComovement | VocacoesAssociativeAbsence
  readonly correlation: VocacoesCorrelation | VocacoesAssociativeAbsence
  readonly stateContrast: VocacoesStateContrast | VocacoesAssociativeAbsence
}

export interface VocacoesLaggedReading {
  readonly aSeriesId: string
  readonly bSeriesId: string
  readonly lagYears: number
  readonly rationale: string
  readonly windowA: VocacoesWindow
  readonly windowB: VocacoesWindow
  readonly intervals: number
  readonly concordant: number
  readonly opposite: number
  readonly ties: number
  readonly correlation: VocacoesLaggedCorrelation | VocacoesAssociativeAbsence
  readonly statement: string
}

export interface VocacoesLaggedAbsence {
  readonly aSeriesId: string
  readonly bSeriesId: string
  readonly lagYears: number
  readonly reasonCode: 'defasagem_sem_janela_suficiente' | 'serie_ausente'
  readonly statement: string
}

export interface VocacoesScreenedRelation {
  readonly relationId: string
  readonly seriesAId: string
  readonly seriesBId: string
  readonly window: VocacoesWindow
  readonly directionConcordance: VocacoesDirectionConcordance | VocacoesAssociativeAbsence
  readonly comovement: VocacoesPairComovement | VocacoesAssociativeAbsence
  readonly correlation: VocacoesCorrelation | VocacoesAssociativeAbsence
  readonly originStatement: string
}

export interface VocacoesScreenedRelations {
  readonly label: string
  readonly description: string
  readonly methodNote: string
  readonly criteria: {
    readonly minIntervals: number
    readonly minAbsPearson: number
    readonly maxItems: number
  }
  readonly items: readonly VocacoesScreenedRelation[]
}

export interface VocacoesAssociation {
  readonly associationId: string
  readonly label: string
  readonly window: VocacoesWindow
  readonly periodLabel: string
  readonly educationOutcome: VocacoesSeriesReference
  readonly territorialFactors: readonly VocacoesSeriesReference[]
  readonly observedStatement: string
  readonly allowedInterpretation: string
  readonly prohibitedClaim: string
  readonly hypotheses: readonly string[]
  readonly associativeReading: VocacoesAssociationReading
}

export interface VocacoesTemporalPair {
  readonly pairId: string
  readonly label: string
  readonly window: VocacoesWindow
  readonly periodLabel: string
  readonly seriesA: VocacoesSeriesReference
  readonly seriesB: VocacoesSeriesReference
  readonly observedStatement: string
  readonly prohibitedClaim: string
  readonly associativeReading: VocacoesTemporalReading
}

export type VocacoesScenarioStatute = 'exploratory' | 'normative'

export interface VocacoesScenarioAnchor {
  readonly seriesId: string
  readonly label: string
  readonly window: VocacoesWindow
  readonly periodLabel: string
  readonly startValue: number
  readonly endValue: number
  readonly directionLabel: string
}

export interface VocacoesScenarioImplication {
  readonly stageLabel: string
  readonly statement: string
}

/*
 * Tema de agenda do PNE — a ponte Vocações → PNE. `theme` é o enum fechado,
 * `themeLabel` a frase pública dele, e `statement` é byte-idêntico a uma das
 * implicações educacionais do mesmo cenário: o tema aponta para a implicação que
 * o sustenta, não escreve prosa nova.
 */
export interface VocacoesAgendaTheme {
  readonly theme: string
  readonly themeLabel: string
  readonly statement: string
}

export interface VocacoesNormativeCriterion {
  readonly order: number
  readonly publicName: string
  readonly definition: string
  readonly requiredState: string
  readonly tradeOff: string
  readonly failureMode: string
  readonly whatToFollow: string
}

export interface VocacoesScenario {
  readonly scenarioId: string
  readonly order: number
  readonly profileLabel: string
  readonly title: string
  readonly statute: VocacoesScenarioStatute
  readonly statuteLabel: string
  readonly centralMechanism: string
  readonly startingPointStatement: string
  readonly trajectoryStatement: string
  readonly stateAtHorizonStatement: string
  readonly anchors: readonly VocacoesScenarioAnchor[]
  readonly educationImplications: readonly VocacoesScenarioImplication[]
  readonly agendaThemes: readonly VocacoesAgendaTheme[]
  readonly contraryEvidence: readonly string[]
  readonly limits: readonly string[]
  readonly prohibitedClaim: string
}

/*
 * Camada municipal (Rodada 5 do V2, sucessora da D11) — vive dentro do bloco de
 * cenários, e por isso só existe onde há cenário.
 */
export interface VocacoesMunicipalDimension {
  readonly label: string
  readonly sourceLabel: string
  readonly unitLabel: string
  readonly periodLabel: string
  readonly kindLabel: string
  readonly universeLabel: string | null
}

export interface VocacoesMunicipalUndecomposable {
  readonly label: string
  readonly consultedSource: string
  readonly reason: string
}

export interface VocacoesMunicipalCompositionLine {
  readonly dimensionLabel: string
  readonly statement: string
}

export interface VocacoesMunicipalExposure {
  readonly order: number
  readonly exposureStatement: string
  readonly allowedInterpretation: string
  readonly prohibitedClaim: string
}

export interface VocacoesMunicipality {
  readonly municipalityId: string
  readonly name: string
  readonly composition: readonly VocacoesMunicipalCompositionLine[]
  readonly scenarioExposure: readonly VocacoesMunicipalExposure[]
}

export interface VocacoesMunicipalLayer {
  readonly label: string
  readonly description: string
  readonly methodNote: string
  readonly dimensions: readonly VocacoesMunicipalDimension[]
  readonly undecomposableDomains: readonly VocacoesMunicipalUndecomposable[]
  readonly municipalities: readonly VocacoesMunicipality[]
}

export interface VocacoesScenarioBlock {
  readonly methodologyLabel: string
  readonly focalQuestion: string
  readonly maturityNote: string
  readonly statuteNote: string
  readonly baseYear: number
  readonly targetYear: number
  readonly longScanTargetYear: number
  readonly baseYearStatement: string
  readonly horizonStatement: string
  readonly longScanStatement: string
  readonly compatibilityCeilingStatement: string
  readonly items: readonly VocacoesScenario[]
  readonly normativeCriteria: readonly VocacoesNormativeCriterion[]
  readonly realizationConditions: readonly string[]
  readonly robustImplications: readonly string[]
  readonly conditionalImplication: string
  readonly prohibitedClaim: string
  readonly municipalLayer: VocacoesMunicipalLayer
}

/*
 * O Bloco 4 existe nas dez regiões, e diz em qual dos dois estados está. O tipo
 * não é uma união discriminada porque o contrato já garante a correspondência
 * em runtime, e a página confere `status` uma vez antes de ler o bloco.
 */
export interface VocacoesScenarios {
  readonly label: string
  readonly description: string
  readonly statuteReadingNote: string | null
  readonly status: 'published' | 'absent'
  readonly absenceStatement: string | null
  readonly block: VocacoesScenarioBlock | null
}

export interface VocacoesSynthesisItem {
  readonly kindLabel: string
  readonly statement: string
  readonly basisLabel?: string
}

export interface VocacoesSynthesisAbsence {
  readonly kindLabel: string
  readonly statement: string
}

export interface VocacoesSynthesis {
  readonly label: string
  readonly description: string
  readonly methodNote: string
  readonly items: readonly VocacoesSynthesisItem[]
  readonly absentKinds: readonly VocacoesSynthesisAbsence[]
}

interface TextBlock<Item> {
  readonly label: string
  readonly description: string
  readonly items: readonly Item[]
}

export interface VocacoesDocument {
  readonly schemaVersion: string
  readonly contentVersion: string
  readonly generatedAt: string
  readonly generatorVersion: string
  readonly sourceVersion: string
  readonly sourceMethodologyStatus: string
  readonly publicationScope: string
  readonly region: {
    readonly slug: string
    readonly name: string
    readonly uf: string
    readonly municipalityCount: number
  }
  readonly page: {
    readonly eyebrow: string
    readonly title: string
    readonly description: string
    readonly neutralityNote: string
  }
  readonly howToRead: TextBlock<string>
  readonly synthesis: VocacoesSynthesis
  readonly territoryPortrait: {
    readonly label: string
    readonly description: string
    readonly series: readonly VocacoesSeries[]
  }
  readonly associations: TextBlock<VocacoesAssociation>
  readonly temporalPairs: TextBlock<VocacoesTemporalPair> & {
    readonly laggedItems: readonly (VocacoesLaggedReading | VocacoesLaggedAbsence)[]
  }
  readonly screenedRelations: VocacoesScreenedRelations
  readonly scenarios: VocacoesScenarios
  readonly sources: TextBlock<{ readonly label: string; readonly periodLabel: string }>
  readonly limitations: TextBlock<string>
  readonly provenance: {
    readonly sourcePackageSha256: string
    readonly sourceContractVersion: string
    readonly sourceBuilderVersion: string
    readonly sourceGeneratedAt: string
    readonly registrySha256: string
    readonly scenarioPackageSha256: string | null
    readonly scenarioSourceSha256: string | null
    readonly municipalPackageSha256: string | null
    readonly synthesisPackageSha256: string
  }
}
