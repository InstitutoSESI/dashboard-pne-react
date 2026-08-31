import { useEffect, useMemo, useState, type ComponentType } from 'react'
import { AlertCircle, Beaker, MapPinned, Printer } from 'lucide-react'
import { ErrorState } from '../../components/ErrorState'
import { LoadingState } from '../../components/LoadingState'
import { MunicipalitySelector } from '../../components/MunicipalitySelector'
import { useMunicipality } from '../../context/MunicipalityContext'
import '../../styles/vocacoes-pne-internal.css'
import type {
  VocacoesPneLoadedBundle,
  VocacoesPneTechnicalBundle,
} from './vocacoesPneUiV2Types'
import {
  loadVocacoesPneTechnicalBundle,
  useVocacoesPneInternalBundle,
} from './useVocacoesPneInternalBundle'
import { VocacoesPneManagerReview } from './components/VocacoesPneManagerReview'
import { EvidenceDisclosure } from './components/VocacoesPneVisuals'
import type { MacroblockProps } from './components/VocacoesPneMacroblocks'
import {
  DemographyOfferBlock,
  EconomyEptCoordinationBlock,
  InclusionAdultsBlock,
  MobilityHighSchoolBlock,
  RuralityTransportBlock,
  TrajectoryConditionsBlock,
  YouthWorkTrainingBlock,
} from './components/VocacoesPneMacroblocks'

const MACROBLOCK_COMPONENTS: Record<string, ComponentType<MacroblockProps>> = {
  A_DEMOGRAPHY_AND_OFFER: DemographyOfferBlock,
  B_TRAJECTORY_AND_CONDITIONS: TrajectoryConditionsBlock,
  C_MOBILITY_AND_HIGH_SCHOOL: MobilityHighSchoolBlock,
  D_RURALITY_AND_TRANSPORT: RuralityTransportBlock,
  E_INCLUSION_AND_ADULTS: InclusionAdultsBlock,
  F_YOUTH_WORK_AND_TRAINING: YouthWorkTrainingBlock,
  G_ECONOMY_EPT_AND_COORDINATION: EconomyEptCoordinationBlock,
}

function TechnicalPanel({ technical }: { technical: VocacoesPneTechnicalBundle }) {
  const evidence = technical.technicalEvidence
  return (
    <aside className="vpi-technical" aria-labelledby="vpi-technical-title">
      <header>
        <Beaker aria-hidden="true" />
        <div>
          <p className="vpi-eyebrow">Camada interna separada</p>
          <h2 id="vpi-technical-title">Modo técnico</h2>
          <p>Esta camada não aparece por padrão e é retirada da impressão da gestora.</p>
        </div>
      </header>
      <div className="vpi-technical__grid">
        <section>
          <h3>Critérios metodológicos</h3>
          <p><b>{evidence.c1C12.length}</b> registros preservados no bundle técnico.</p>
          <p>O conteúdo bruto permanece separado da leitura editorial e não é exposto nesta tela.</p>
        </section>
        <section>
          <h3>Verificações transportadas</h3>
          <p><b>{evidence.qa.length}</b> registros de qualidade carregados.</p>
          <p>Visibilidade padrão e impressão para a gestora permanecem desativadas.</p>
        </section>
      </div>
      <p className="vpi-technical__hash">Registros complementares verificados: <b>{evidence.shiftShare.length}</b>.</p>
      <p className="vpi-technical__hash">Manifesto congelado: <code>{evidence.frozenJob5hManifestSha256}</code></p>
    </aside>
  )
}

function Job5IEvidenceLayer({ bundle, municipalityEntityId, municipalityName }: {
  bundle: VocacoesPneLoadedBundle
  municipalityEntityId: string | null
  municipalityName: string | null
}) {
  const municipalityNames = useMemo(
    () => new Map(bundle.core.municipalities.map((item) => [item.ibgeCode, item.name])),
    [bundle.core.municipalities],
  )
  const sourceRegistry = useMemo(
    () => new Map(bundle.core.sourceRegistry.map((item) => [item.sourceRef, item])),
    [bundle.core.sourceRegistry],
  )
  const visualContracts = useMemo(
    () => new Map(bundle.core.visualContracts.map((item) => [item.visualContractId, item])),
    [bundle.core.visualContracts],
  )

  return (
    <section className="vpk-evidence-layer" aria-label="Indicadores e séries de apoio">
      <EvidenceDisclosure title="Explorar indicadores e séries de apoio" testId="job5i-evidence-layer">
        <p className="vpk-evidence-intro">A camada abaixo preserva os sete conjuntos de evidências do trabalho anterior. Ela serve à conferência e não define a ordem da narrativa.</p>
        {bundle.core.directions.map((direction) => (
          <section key={direction.directionId} className="vpi-direction vpk-evidence-direction" aria-labelledby={`evidence-direction-${direction.sequence}`}>
            <header className="vpi-direction__header">
              <span>Conjunto {direction.sequence}</span>
              <h2 id={`evidence-direction-${direction.sequence}`}>{direction.title}</h2>
              <p>{direction.summary}</p>
            </header>
            {bundle.core.macroblocks
              .filter((macroblock) => macroblock.directionId === direction.directionId)
              .map((macroblock) => {
                const Component = MACROBLOCK_COMPONENTS[macroblock.macroblockId]
                const visualContract = visualContracts.get(macroblock.visualContractId)
                if (!Component || !visualContract) return null
                return (
                  <Component
                    key={macroblock.macroblockId}
                    core={bundle.core}
                    series={bundle.series}
                    municipalityEntityId={municipalityEntityId}
                    municipalityName={municipalityName}
                    municipalityNames={municipalityNames}
                    sourceRegistry={sourceRegistry}
                    macroblock={macroblock}
                    visualContract={visualContract}
                  />
                )
              })}
          </section>
        ))}
      </EvidenceDisclosure>
    </section>
  )
}

export function InternalPageContent({ bundle }: { bundle: VocacoesPneLoadedBundle }) {
  const { selectedMunicipalityId, setSelectedMunicipalityId } = useMunicipality()
  const validMunicipalityCodes = useMemo(
    () => new Set(bundle.core.municipalities.map((item) => item.ibgeCode)),
    [bundle.core.municipalities],
  )
  const initialMunicipalityId = selectedMunicipalityId && validMunicipalityCodes.has(selectedMunicipalityId)
    ? selectedMunicipalityId
    : bundle.insights.fallback_municipality_ibge_code
  const [viewMunicipalityId, setViewMunicipalityId] = useState<string | null>(initialMunicipalityId)
  const [technicalMode, setTechnicalMode] = useState(false)
  const [technicalState, setTechnicalState] = useState<{
    loading: boolean
    error: string | null
    data: VocacoesPneTechnicalBundle | null
  }>({ loading: false, error: null, data: null })

  useEffect(() => {
    if (selectedMunicipalityId && validMunicipalityCodes.has(selectedMunicipalityId)) {
      setViewMunicipalityId(selectedMunicipalityId)
    }
  }, [selectedMunicipalityId, validMunicipalityCodes])

  const selectedMunicipality = bundle.core.municipalities.find((item) => (
    item.ibgeCode === viewMunicipalityId
  )) ?? null
  const activeEntityName = selectedMunicipality?.name ?? bundle.core.region.name

  async function toggleTechnicalMode() {
    const next = !technicalMode
    setTechnicalMode(next)
    if (!next || technicalState.data || technicalState.loading) return
    setTechnicalState({ loading: true, error: null, data: null })
    try {
      const data = await loadVocacoesPneTechnicalBundle()
      setTechnicalState({ loading: false, error: null, data })
    } catch (error: unknown) {
      setTechnicalState({
        loading: false,
        error: error instanceof Error ? error.message : 'Falha ao validar a camada técnica.',
        data: null,
      })
    }
  }

  function changeMunicipality(value: string | null) {
    if (value !== null && !validMunicipalityCodes.has(value)) return
    setViewMunicipalityId(value)
    setSelectedMunicipalityId(value)
  }

  return (
    <main className="vocacoes-pne-internal-page" data-job="manager-review-v1" data-publication="closed">
      <div className="vpi-internal-banner" role="status">
        <AlertCircle aria-hidden="true" size={16} />
        Página piloto para validação com a gestora — ainda não publicada
      </div>

      <header className="vpi-hero">
        <div className="vpi-hero__copy">
          <p className="vpi-eyebrow">Vocações × PNE · piloto de revisão</p>
          <h1>{activeEntityName}: educação, território e próximos anos</h1>
          <p>A página cruza indicadores educacionais, demográficos, sociais e econômicos em dois sentidos: compreender o cenário atual e transformar mudanças do território em questões para o planejamento.</p>
          <div className="vpi-hero__facts" aria-label="Escopo da leitura integrada">
            <span><b>4</b> relações explicativas</span>
            <span><b>3</b> agendas de futuro</span>
            <span><b>2</b> direções de planejamento</span>
          </div>
        </div>
        <aside className="vpi-hero__region">
          <MapPinned aria-hidden="true" />
          <div><span>Contexto sempre visível</span><strong>Vale do Sinos</strong><small>Leitura regional + município selecionado</small></div>
        </aside>
      </header>

      <section className="vpi-controls" aria-label="Controles do protótipo">
        <div className="vpi-controls__view">
          <span>Visão ativa</span>
          <button
            type="button"
            className={viewMunicipalityId === null ? 'is-active' : ''}
            aria-pressed={viewMunicipalityId === null}
            onClick={() => changeMunicipality(null)}
          >Vale do Sinos</button>
        </div>
        <MunicipalitySelector
          className="vpi-municipality-selector"
          municipalities={bundle.core.municipalities}
          selectedMunicipalityId={viewMunicipalityId}
          onChange={changeMunicipality}
          placeholder="Escolher entre os dez municípios"
        />
        <button type="button" className="vpi-print-button" onClick={() => window.print()}>
          <Printer aria-hidden="true" size={17} /> Imprimir leitura
        </button>
      </section>

      <VocacoesPneManagerReview
        bundle={bundle}
        municipalityEntityId={viewMunicipalityId}
        municipalityName={selectedMunicipality?.name ?? null}
      />

      <Job5IEvidenceLayer
        bundle={bundle}
        municipalityEntityId={viewMunicipalityId}
        municipalityName={selectedMunicipality?.name ?? null}
      />

      <section className="vpi-review-tools" aria-labelledby="vpi-review-tools-title">
        <div>
          <p className="vpi-eyebrow">Ferramenta de conferência</p>
          <h2 id="vpi-review-tools-title">Validação técnica separada da leitura da gestora</h2>
          <p>Os registros metodológicos continuam disponíveis para a equipe e não aparecem na impressão.</p>
        </div>
        <button type="button" className="vpi-technical-toggle" aria-pressed={technicalMode} onClick={toggleTechnicalMode}>
          <Beaker aria-hidden="true" size={17} />
          {technicalMode ? 'Ocultar modo técnico' : 'Abrir modo técnico'}
        </button>
      </section>

      {technicalMode ? (
        technicalState.loading ? <LoadingState message="Validando a camada técnica..." />
          : technicalState.error ? <ErrorState title="Camada técnica indisponível" message={technicalState.error} />
            : technicalState.data ? <TechnicalPanel technical={technicalState.data} /> : null
      ) : null}

      <footer className="vpi-footer">
        <p><b>Página pronta para revisão com a gestora; sem autorização para publicação.</b> A promoção pública depende da validação de conteúdo.</p>
        <p>Fontes oficiais congeladas · comparação temporal incorporada · rede total · vínculos PNE canônicos preservados.</p>
      </footer>
    </main>
  )
}

export function VocacoesPneInternalPage() {
  const state = useVocacoesPneInternalBundle()
  if (state.status === 'loading') return <LoadingState message="Validando o contrato interno Job 5K..." />
  if (state.status === 'error') return <ErrorState title="Protótipo interno indisponível" message={state.error} />
  return <InternalPageContent bundle={state.data} />
}
