export type MunicipalReportCoverage = 'complete' | 'partial' | 'future_integration'

export interface MunicipalReportCoverageEntry {
  section: number
  components: string[]
  dataFiles: string[]
  sources: string[]
  years: string[]
  charts: string[]
  tables: string[]
  narratives: string[]
  coverage: MunicipalReportCoverage
}

// Inventário interno de arquitetura. Não deve ser renderizado na página pública.
export const MUNICIPAL_REPORT_COVERAGE_INVENTORY: MunicipalReportCoverageEntry[] = [
  { section: 1, components: ['MunicipalTechnicalReport'], dataFiles: ['municipal overview'], sources: ['Identificação municipal'], years: ['referência vigente'], charts: [], tables: [], narratives: ['identificação'], coverage: 'partial' },
  { section: 2, components: ['SnapshotSummary', 'StageOfferTable'], dataFiles: ['municipal overview'], sources: ['INEP — Censo Escolar'], years: ['2025'], charts: [], tables: ['matrículas por rede'], narratives: ['nota de cobertura'], coverage: 'complete' },
  { section: 3, components: ['SnapshotSummary', 'StageOfferTable'], dataFiles: ['municipal overview'], sources: ['INEP — Censo Escolar'], years: ['2025'], charts: [], tables: ['matrículas por rede'], narratives: [], coverage: 'complete' },
  { section: 4, components: ['SnapshotSummary', 'StageOfferTable'], dataFiles: ['municipal overview'], sources: ['INEP — Censo Escolar', 'INEP — Taxas de Rendimento Escolar'], years: ['2025'], charts: [], tables: ['matrículas por rede', 'rendimento escolar'], narratives: [], coverage: 'complete' },
  { section: 5, components: ['IndicatorTable'], dataFiles: ['education municipality document'], sources: ['INEP — Censo Escolar'], years: ['último ano publicado'], charts: [], tables: ['oferta em tempo integral'], narratives: [], coverage: 'partial' },
  { section: 6, components: ['MissingInformation'], dataFiles: [], sources: [], years: [], charts: [], tables: [], narratives: ['limitação metodológica'], coverage: 'future_integration' },
  { section: 7, components: ['IndicatorTable'], dataFiles: ['education municipality document'], sources: ['INEP', 'IBGE'], years: ['último ano publicado'], charts: [], tables: ['recortes indígenas e rurais'], narratives: ['limites territoriais'], coverage: 'partial' },
  { section: 8, components: ['SnapshotSummary', 'IndicatorTable'], dataFiles: ['municipal overview', 'education municipality document'], sources: ['INEP — Censo Escolar'], years: ['2025', 'último ano publicado'], charts: [], tables: ['matrículas da EJA'], narratives: [], coverage: 'complete' },
  { section: 9, components: ['SnapshotSummary'], dataFiles: ['municipal overview', 'special-education-v1'], sources: ['INEP — Censo Escolar'], years: ['2025'], charts: [], tables: [], narratives: ['consulta específica de AEE e Educação Bilíngue de Surdos em Modalidades'], coverage: 'partial' },
  { section: 10, components: ['HigherEducationReportContent'], dataFiles: ['higher education municipality document'], sources: ['INEP — Sinopse Estatística da Educação Superior'], years: ['último ano municipal utilizável'], charts: [], tables: ['indicadores de graduação'], narratives: ['limite sobre pós-graduação'], coverage: 'partial' },
  { section: 11, components: ['SnapshotSummary', 'IndicatorTable'], dataFiles: ['municipal overview', 'education municipality document'], sources: ['INEP'], years: ['2025', 'último ano publicado'], charts: [], tables: ['ofertas profissionais'], narratives: [], coverage: 'partial' },
  { section: 12, components: ['IndicatorTable'], dataFiles: ['education municipality document'], sources: ['INEP — Censo Escolar'], years: ['último ano publicado'], charts: [], tables: ['docentes por etapa'], narratives: [], coverage: 'partial' },
  { section: 13, components: ['MissingInformation'], dataFiles: [], sources: [], years: [], charts: [], tables: [], narratives: ['limitação metodológica'], coverage: 'future_integration' },
  { section: 14, components: ['SchoolInfrastructureReportTable', 'IndicatorTable'], dataFiles: ['education municipality document'], sources: ['Censo Escolar/INEP'], years: ['2025', 'último ano publicado'], charts: [], tables: ['infraestrutura por total e rede municipal', 'conectividade e equipamentos'], narratives: ['metodologia do contrato canônico', 'limite sobre acessibilidade'], coverage: 'partial' },
  { section: 15, components: ['links para módulos financeiros'], dataFiles: ['módulos financeiros'], sources: ['fontes próprias dos módulos'], years: ['conforme o módulo'], charts: [], tables: [], narratives: ['referência aos contratos homologados'], coverage: 'partial' },
  { section: 16, components: ['link para cenários de atendimento'], dataFiles: ['projeções e cenários'], sources: ['INEP', 'IBGE'], years: ['histórico e horizonte vigente'], charts: [], tables: [], narratives: ['distinção entre observado e projetado'], coverage: 'partial' },
  { section: 17, components: ['PmeReferenceIndicatorsTable'], dataFiles: ['diagnóstico público PNE 2026–2036'], sources: ['fontes declaradas pelo diagnóstico'], years: ['último ano por indicador'], charts: [], tables: ['situação atual em relação à referência'], narratives: ['nota de interpretação'], coverage: 'partial' },
  { section: 18, components: ['MunicipalTechnicalReport'], dataFiles: ['metadados do municipal overview'], sources: ['fontes declaradas'], years: ['referência vigente'], charts: [], tables: [], narratives: ['metodologia e limitações'], coverage: 'complete' },
  { section: 19, components: ['ReportTableRegion'], dataFiles: ['contratos consumidos pelo relatório'], sources: ['INEP', 'IBGE', 'base municipal do PME'], years: ['por base'], charts: [], tables: ['rastreabilidade pública'], narratives: [], coverage: 'complete' },
]
