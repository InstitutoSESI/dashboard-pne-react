import { useMemo } from 'react'
import { loadEducationMunicipio } from '../../data/educationData.js'
import { loadIndicadores, loadMunicipioData } from '../../data/staticData'
import { useMunicipioDiagnostic } from '../../hooks/useMunicipioDiagnostic'
import type { IndicadoresPayload, MunicipioData } from '../../types/data'
import { useAsyncData } from '../../utils/useAsyncData'
import { MunicipalTechnicalReport } from '../../features/education/components/MunicipalTechnicalReport'
import { useHigherEducation } from '../../features/education/hooks/useHigherEducation'
import { useMunicipalEducationOverview } from '../../features/education/hooks/useMunicipalEducationOverview'
import { useSpecialEducation } from '../../features/education/hooks/useSpecialEducation'
import type { EducationMunicipioData } from '../../features/education/educationTypes'
import type { Pne2026DiagnosticLoaderResult } from '../../features/diagnostic/diagnosticTypes'
import { PmeState } from './PmePrimitives'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeMunicipalityIdentity } from './pmeTypes'
import {
  buildPmeTechnicalReportData,
  resolvePmeTechnicalReportDiagnostic,
  validatePmeTechnicalReportIdentity,
} from './pmeTechnicalReportData'

interface PmeMunicipioData extends MunicipioData {
  pne_2026_2036?: {
    cenarios_planejamento?: Record<string, unknown>
    indicadores?: Record<string, unknown>
    projecoes?: Record<string, unknown>
  }
}

interface TechnicalReportLoadResult {
  education: EducationMunicipioData
  indicadores: IndicadoresPayload
  municipioData: PmeMunicipioData
}

const emissionDateFormatter = new Intl.DateTimeFormat('pt-BR')
const reportWording = {
  introduction: 'Uma visão integrada da educação municipal, com resultados, fontes e períodos de referência para consulta e discussão do PME.',
  financeSource: 'Fontes financeiras oficiais · Confira o exercício de cada valor',
  financeDescription: 'Consulte as despesas realizadas, as previsões de recursos e os indicadores de aplicação no painel de Financiamento.',
  financeNote: 'Cada valor financeiro mantém sua fonte, exercício e etapa: previsão, empenho, liquidação ou pagamento.',
  attendanceSource: 'INEP — Censo Escolar e IBGE — estimativas populacionais · Confira o ano de cada indicador',
}

/**
 * PME owns routing and identity. The report remains the same audited educational
 * composition used by the platform and its loaders are cached by municipality.
 */
export function PmeTechnicalReport({
  diagnostic,
  municipality,
  route,
}: {
  diagnostic?: Pne2026DiagnosticLoaderResult | null
  municipality: PmeMunicipalityIdentity
  route: PmeRoute
}) {
  const idMunicipality = municipality.ibgeCode
  const reportState = useAsyncData<TechnicalReportLoadResult>(async () => {
    const [education, municipioData, indicadores] = await Promise.all([
      loadEducationMunicipio(idMunicipality) as Promise<EducationMunicipioData>,
      loadMunicipioData(idMunicipality) as Promise<PmeMunicipioData>,
      loadIndicadores(),
    ])
    return { education, municipioData, indicadores }
  }, [idMunicipality])
  const overviewState = useMunicipalEducationOverview(idMunicipality, true)
  const higherEducationState = useHigherEducation(idMunicipality, true)
  const specialEducationState = useSpecialEducation(idMunicipality, true)
  // A supplied null deliberately means that the caller has no diagnostic module.
  const loadedDiagnosticState = useMunicipioDiagnostic(diagnostic === undefined ? idMunicipality : null)

  const linkOverrides = useMemo(() => ({
    educationHref: (section: string) => pmeLink(route, section === 'metodologia' ? 'transparencia' : 'evidencias'),
    financialHref: () => pmeLink(route, 'financiamento'),
  }), [route])

  if (reportState.loading) {
    return <PmeState kind="loading" title="Carregando as bases do relatório técnico"><p>As evidências educacionais do município estão sendo verificadas.</p></PmeState>
  }

  if (reportState.error) {
    return <PmeState kind="error" title="Não foi possível carregar o relatório técnico"><p>Reabra esta consulta para tentar carregar os dados municipais novamente.</p></PmeState>
  }

  if (!reportState.data) {
    return <PmeState kind="unavailable" title="Relatório técnico indisponível"><p>As bases necessárias para esta leitura não estão disponíveis para o município selecionado.</p></PmeState>
  }

  const { education, municipioData, indicadores } = reportState.data
  const resolvedDiagnostic = resolvePmeTechnicalReportDiagnostic(diagnostic, loadedDiagnosticState.data)
  const identityError = validatePmeTechnicalReportIdentity({
    diagnostic: resolvedDiagnostic,
    education,
    higherEducation: higherEducationState.data?.document,
    municipioData,
    municipality,
    overview: overviewState.data,
    specialEducation: specialEducationState.data?.document,
  })
  if (identityError) {
    return <PmeState kind="error" title="Não foi possível confirmar os dados do município"><p>Os dados encontrados não correspondem à seleção. Selecione o município novamente para refazer a consulta.</p></PmeState>
  }

  if (overviewState.status === 'idle' || overviewState.status === 'loading') {
    return <PmeState kind="loading" title="Carregando o panorama educacional"><p>O relatório ficará disponível quando a base municipal necessária para as tabelas for confirmada.</p></PmeState>
  }

  const reportData = buildPmeTechnicalReportData({
    education,
    indicadores,
    municipioData,
    specialEducationItems: specialEducationState.data?.viewModel.items ?? [],
  })
  const overview = overviewState.status === 'ready' ? overviewState.data : null

  return <>
    {overviewState.status === 'error' ? <PmeState kind="error" title="Panorama educacional não carregado"><p>O relatório preserva as demais evidências publicadas; as tabelas dependentes do panorama indicam a ausência da base.</p></PmeState> : null}
    {overviewState.status === 'absent' ? <PmeState kind="unavailable" title="Panorama educacional não publicado"><p>O relatório preserva os demais indicadores e sinaliza as tabelas que dependem desta base.</p></PmeState> : null}
    <MunicipalTechnicalReport
      educationItems={reportData.educationItems}
      emissionDate={emissionDateFormatter.format(new Date())}
      higherEducation={higherEducationState.data?.viewModel ?? null}
      higherEducationError={higherEducationState.error}
      higherEducationLoading={higherEducationState.loading}
      linkOverrides={linkOverrides}
      wording={reportWording}
      municipalityId={idMunicipality}
      municipalityName={municipality.name}
      municipalityPopulation={reportData.municipalityPopulation}
      municipalitySlug={municipality.slug}
      overview={overview}
      pmeDiagnostic={resolvedDiagnostic?.pne2026PublicDiagnostic ?? null}
      pmeDiagnosticError={diagnostic === undefined ? loadedDiagnosticState.error : null}
      pmeDiagnosticLoading={diagnostic === undefined ? loadedDiagnosticState.loading : false}
      pmeReferenceData={reportData.pmeReferenceData}
      schoolInfrastructure={reportData.schoolInfrastructure}
      specialEducation={specialEducationState.data?.document ?? null}
      specialEducationError={specialEducationState.error}
      specialEducationLoading={specialEducationState.loading}
    />
  </>
}
