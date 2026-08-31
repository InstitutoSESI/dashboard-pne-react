import { ArrowRight, BookOpen, CircleAlert, MapPinned } from 'lucide-react'
import type { MouseEvent, ReactNode } from 'react'
import { REGION_ENTITY_ID } from '../vocacoesPneSelectors'
import { storyVariant } from '../vocacoesPneJob5kRuntime'
import type {
  Job5KConditionalContext,
  Job5KEjaStory,
  Job5KEndpoint,
  Job5KHighSchoolStory,
  Job5KLogisticsStory,
  Job5KStory,
  Job5KYouthStory,
  VocacoesPneJob5KBundle,
} from '../vocacoesPneJob5kTypes'
import { EvidenceDisclosure } from './VocacoesPneVisuals'

const integerFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const decimalFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 })
const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
})

const STORY_ANCHORS: Record<Job5KStory['story_id'], string> = {
  STORY_HIGH_SCHOOL_TRAJECTORY: 'leitura-ensino-medio',
  STORY_EJA_TERRITORY: 'leitura-eja',
  STORY_LOGISTICS_EPT: 'leitura-logistica-ept',
  STORY_YOUTH_WORK_APPRENTICESHIP: 'leitura-trabalho-aprendizagem',
}

function scrollToStory(event: MouseEvent<HTMLAnchorElement>, storyId: Job5KStory['story_id']) {
  event.preventDefault()
  document.getElementById(STORY_ANCHORS[storyId])?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

function formatInteger(value: number | null) {
  return value === null ? 'Indisponível' : integerFormatter.format(value)
}

function formatDecimal(value: number | null, suffix = '') {
  return value === null ? 'Indisponível' : `${decimalFormatter.format(value)}${suffix}`
}

function formatSigned(value: number | null, suffix = '') {
  if (value === null) return 'Indisponível'
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}${decimalFormatter.format(Math.abs(value))}${suffix}`
}

function endpointText(endpoint: Job5KEndpoint) {
  if (endpoint.initial_value === null || endpoint.final_value === null) return 'Indisponível'
  return `${formatInteger(endpoint.initial_value)} → ${formatInteger(endpoint.final_value)}`
}

function isObserved(endpoint: Job5KEndpoint) {
  return endpoint.availability_state === 'observed' || endpoint.availability_state === 'observed_zero'
}

function EvidenceMetric({ label, children, detail, state }: {
  label: string
  children: ReactNode
  detail?: string
  state?: string
}) {
  return (
    <article className="vpk-evidence-metric" data-availability-state={state}>
      <span>{label}</span>
      <strong>{children}</strong>
      {state === 'observed_zero' ? <small>Zero observado</small> : detail ? <small>{detail}</small> : null}
    </article>
  )
}

function HighSchoolVisual({ story, entityId }: { story: Job5KHighSchoolStory; entityId: string }) {
  const maximum = Math.max(...story.ten_municipality_distribution.map((item) => Math.abs(item.absolute_change)), 1)
  const selectedCode = entityId === REGION_ENTITY_ID ? null : entityId
  const region = story.primary_evidence.by_entity.find((item) => item.entity_id === REGION_ENTITY_ID)
  const active = story.primary_evidence.by_entity.find((item) => item.entity_id === entityId) ?? region

  return (
    <figure className="vpk-main-visual" data-main-visual="high-school-change">
      <header className="vpk-visual-header">
        <div>
          <p className="vpi-eyebrow">Mudança observada · 2014–2025</p>
          <h4>Movimentos municipais do ensino médio</h4>
        </div>
        <div className="vpk-visual-facts">
          {active ? <EvidenceMetric label={entityId === REGION_ENTITY_ID ? 'Vale do Sinos' : 'Município'} detail="matrículas localizadas">{endpointText(active.high_school)}</EvidenceMetric> : null}
          {active ? <EvidenceMetric label="Turmas" detail="mesmo período">{endpointText(active.classes)}</EvidenceMetric> : null}
        </div>
      </header>
      <div className="vpk-diverging-list" role="list" aria-label="Mudança de matrículas de ensino médio nos dez municípios">
        {story.ten_municipality_distribution.map((item) => {
          const width = Math.abs(item.absolute_change) / maximum * 100
          const selected = item.municipality_ibge_code === selectedCode
          return (
            <div
              key={item.municipality_ibge_code}
              className={`vpk-diverging-row${selected ? ' is-selected' : ''}`}
              role="listitem"
              aria-label={`${item.municipality_name}: ${formatSigned(item.absolute_change)} matrículas`}
            >
              <span>{item.municipality_name}</span>
              <div className="vpk-diverging-track" aria-hidden="true">
                <span className="vpk-diverging-half vpk-diverging-half--negative">
                  {item.absolute_change < 0 ? <i style={{ width: `${width}%` }} /> : null}
                </span>
                <span className="vpk-diverging-zero" />
                <span className="vpk-diverging-half vpk-diverging-half--positive">
                  {item.absolute_change >= 0 ? <i style={{ width: `${width}%` }} /> : null}
                </span>
              </div>
              <strong>{formatSigned(item.absolute_change)}</strong>
            </div>
          )
        })}
      </div>
      <figcaption>Ordem do cadastro municipal canônico; a posição não representa classificação. O Vale registrou {formatSigned(region?.high_school.absolute_change ?? null)} matrículas no período.</figcaption>
    </figure>
  )
}

function EjaVisual({ story, entityId }: { story: Job5KEjaStory; entityId: string }) {
  const selectedCode = entityId === REGION_ENTITY_ID ? null : entityId
  const allShares = story.ten_municipality_distribution.flatMap((item) => [
    item.fundamental.resident_public_share_percent,
    item.fundamental.located_eja_share_percent,
    item.high_school.resident_public_share_percent,
    item.high_school.located_eja_share_percent,
  ])
  const scaleMaximum = Math.max(...allShares, 1)
  const stages = [
    { key: 'fundamental' as const, label: 'Ensino fundamental' },
    { key: 'high_school' as const, label: 'Ensino médio' },
  ]

  return (
    <figure className="vpk-main-visual" data-main-visual="eja-territorial-distribution">
      <header className="vpk-visual-header">
        <div>
          <p className="vpi-eyebrow">Distribuições municipais · 2022</p>
          <h4>Público residente e EJA localizada, por etapa</h4>
        </div>
        <div className="vpk-visual-facts">
          <EvidenceMetric label="Distância territorial · fundamental">{formatDecimal(story.primary_evidence.regional_distance_percentage_points.fundamental, ' p.p.')}</EvidenceMetric>
          <EvidenceMetric label="Distância territorial · ensino médio">{formatDecimal(story.primary_evidence.regional_distance_percentage_points.high_school, ' p.p.')}</EvidenceMetric>
        </div>
      </header>
      <div className="vpk-eja-stages">
        {stages.map((stage) => (
          <section key={stage.key} aria-labelledby={`vpk-eja-${stage.key}`}>
            <h5 id={`vpk-eja-${stage.key}`}>{stage.label}</h5>
            <div className="vpk-paired-list" role="list">
              {story.ten_municipality_distribution.map((item) => {
                const values = item[stage.key]
                const residentPosition = values.resident_public_share_percent / scaleMaximum * 100
                const locatedPosition = values.located_eja_share_percent / scaleMaximum * 100
                const selected = item.municipality_ibge_code === selectedCode
                const left = Math.min(residentPosition, locatedPosition)
                const width = Math.abs(residentPosition - locatedPosition)
                return (
                  <div
                    key={item.municipality_ibge_code}
                    className={`vpk-paired-row${selected ? ' is-selected' : ''}`}
                    role="listitem"
                    aria-label={`${item.municipality_name}: público residente ${formatDecimal(values.resident_public_share_percent, '%')}; EJA localizada ${formatDecimal(values.located_eja_share_percent, '%')}; diferença ${formatSigned(values.difference_percentage_points, ' p.p.')}`}
                  >
                    <span>{item.municipality_name}</span>
                    <div className="vpk-paired-track" aria-hidden="true">
                      <i className="vpk-paired-connector" style={{ left: `${left}%`, width: `${width}%` }} />
                      <i className="vpk-paired-point vpk-paired-point--resident" style={{ left: `${residentPosition}%` }} />
                      <i className="vpk-paired-point vpk-paired-point--located" style={{ left: `${locatedPosition}%` }} />
                    </div>
                    <strong>{formatSigned(values.difference_percentage_points, ' p.p.')}</strong>
                  </div>
                )
              })}
            </div>
          </section>
        ))}
      </div>
      <figcaption><span><i className="vpk-legend-dot vpk-paired-point--resident" /> público residente</span><span><i className="vpk-legend-dot vpk-paired-point--located" /> EJA localizada</span> As etapas têm denominadores próprios e não são somadas.</figcaption>
    </figure>
  )
}

function LogisticsVisual({ story, entityId }: { story: Job5KLogisticsStory; entityId: string }) {
  const rows = story.ten_municipality_distribution.rows
  const selectedCode = entityId === REGION_ENTITY_ID ? null : entityId
  const maximum = Math.max(...rows.flatMap((item) => [
    item.share_of_positive_regional_change_percent,
    item.share_of_regional_ept_percent,
  ]), 1)
  const region = story.primary_evidence.by_entity.find((item) => item.entity_id === REGION_ENTITY_ID)
  const active = story.primary_evidence.by_entity.find((item) => item.entity_id === entityId) ?? region

  return (
    <figure className="vpk-main-visual" data-main-visual="logistics-ept-territory">
      <header className="vpk-visual-header">
        <div>
          <p className="vpi-eyebrow">Duas localizações territoriais</p>
          <h4>Mudança da ocupação logística e EPT localizada</h4>
        </div>
        <div className="vpk-visual-facts">
          {active ? <EvidenceMetric label="Auxiliar de logística" detail="vínculos no local de trabalho">{formatInteger(active.occupation.initial_value)} → {formatInteger(active.occupation.final_value)}</EvidenceMetric> : null}
          {active ? <EvidenceMetric label="EPT localizada · 2025" state={active.ept.availability_state}>{isObserved(active.ept) ? formatInteger(active.ept.final_value) : 'Indisponível'}</EvidenceMetric> : null}
        </div>
      </header>
      <div className="vpk-double-bar-list" role="list" aria-label="Participações municipais da mudança ocupacional e da EPT localizada">
        {rows.map((item) => {
          const selected = item.municipality_ibge_code === selectedCode
          return (
            <div key={item.municipality_ibge_code} className={`vpk-double-bar-row${selected ? ' is-selected' : ''}`} role="listitem">
              <span>{item.municipality_name}</span>
              <div className="vpk-double-bar-pair">
                <div aria-label={`${item.municipality_name}: ${formatDecimal(item.share_of_positive_regional_change_percent, '%')} da mudança positiva regional da ocupação`}>
                  <i className="vpk-bar vpk-bar--work" style={{ width: `${item.share_of_positive_regional_change_percent / maximum * 100}%` }} />
                  <small>ocupação {formatDecimal(item.share_of_positive_regional_change_percent, '%')}</small>
                </div>
                <div aria-label={`${item.municipality_name}: ${formatDecimal(item.share_of_regional_ept_percent, '%')} da EPT regional`}>
                  <i className="vpk-bar vpk-bar--education" style={{ width: `${item.share_of_regional_ept_percent / maximum * 100}%` }} />
                  <small>EPT {item.technical_enrollments_availability_state === 'observed_zero' ? 'zero observado' : formatDecimal(item.share_of_regional_ept_percent, '%')}</small>
                </div>
              </div>
              <strong>{formatSigned(item.share_difference_percentage_points, ' p.p.')}</strong>
            </div>
          )
        })}
      </div>
      <figcaption><span><i className="vpk-legend-line vpk-bar--work" /> mudança positiva da ocupação</span><span><i className="vpk-legend-line vpk-bar--education" /> EPT localizada</span> Local de trabalho e localização escolar não identificam as mesmas pessoas.</figcaption>
    </figure>
  )
}

function YouthVisual({ story, entityId }: { story: Job5KYouthStory; entityId: string }) {
  const selectedCode = entityId === REGION_ENTITY_ID ? null : entityId
  const maximumChange = Math.max(...story.ten_municipality_distribution.map((item) => item.rais_15_17_absolute_change), 1)
  const maximumShare = Math.max(...story.ten_municipality_distribution.map((item) => item.apprenticeship_share_percent_2025), 1)
  const region = story.primary_evidence.by_entity.find((item) => item.entity_id === REGION_ENTITY_ID)
  const active = story.primary_evidence.by_entity.find((item) => item.entity_id === entityId) ?? region

  return (
    <figure className="vpk-main-visual" data-main-visual="youth-work-apprenticeship">
      <header className="vpk-visual-header">
        <div>
          <p className="vpi-eyebrow">Registros paralelos</p>
          <h4>Trabalho formal de 15 a 17 anos e aprendizagem</h4>
        </div>
        <div className="vpk-visual-facts">
          {active ? <EvidenceMetric label="Vínculos formais · 2019–2025">{endpointText(active.rais_15_17)}</EvidenceMetric> : null}
          {active ? <EvidenceMetric label="Aprendizagem nas admissões · 2025">{formatInteger(active.apprenticeship_share_2025.numerator)} / {formatInteger(active.apprenticeship_share_2025.denominator)} = {formatDecimal(active.apprenticeship_share_2025.percent, '%')}</EvidenceMetric> : null}
        </div>
      </header>
      <div className="vpk-youth-list" role="list" aria-label="Fatos municipais de trabalho formal juvenil e aprendizagem">
        {story.ten_municipality_distribution.map((item) => {
          const selected = item.municipality_ibge_code === selectedCode
          return (
            <div key={item.municipality_ibge_code} className={`vpk-youth-row${selected ? ' is-selected' : ''}`} role="listitem">
              <span>{item.municipality_name}</span>
              <div>
                <small>Vínculos: {formatInteger(item.rais_15_17_initial_value)} → {formatInteger(item.rais_15_17_final_value)}</small>
                <i className="vpk-youth-stock" style={{ width: `${item.rais_15_17_absolute_change / maximumChange * 100}%` }} />
              </div>
              <div>
                <small>Aprendizagem: {formatInteger(item.apprenticeship_events_2025)} / {formatInteger(item.youth_admission_events_2025)}</small>
                <i className="vpk-youth-flow" style={{ width: `${item.apprenticeship_share_percent_2025 / maximumShare * 100}%` }} />
              </div>
              <strong>{formatDecimal(item.apprenticeship_share_percent_2025, '%')}</strong>
            </div>
          )
        })}
      </div>
      <figcaption>Os vínculos são estoques anuais; aprendizagem e admissões são eventos. Nenhuma linha identifica pessoas únicas entre as fontes.</figcaption>
    </figure>
  )
}

function StoryVisual({ story, entityId }: { story: Job5KStory; entityId: string }) {
  switch (story.story_id) {
    case 'STORY_HIGH_SCHOOL_TRAJECTORY': return <HighSchoolVisual story={story} entityId={entityId} />
    case 'STORY_EJA_TERRITORY': return <EjaVisual story={story} entityId={entityId} />
    case 'STORY_LOGISTICS_EPT': return <LogisticsVisual story={story} entityId={entityId} />
    case 'STORY_YOUTH_WORK_APPRENTICESHIP': return <YouthVisual story={story} entityId={entityId} />
  }
}

function SecondaryEvidence({ story, entityId }: { story: Job5KStory; entityId: string }) {
  if (story.story_id === 'STORY_HIGH_SCHOOL_TRAJECTORY') {
    const active = story.secondary_evidence.by_entity.find((item) => item.entity_id === entityId)
    if (!active) return null
    const trajectoryLabels: Record<string, string> = {
      approval_rate_percent: 'aprovação',
      dropout_rate_percent: 'abandono',
      failure_rate_percent: 'reprovação',
      age_grade_distortion_rate_percent: 'distorção idade-série',
    }
    return (
      <div className="vpk-secondary-grid">
        {Object.entries(active.trajectory_2025).map(([metric, value]) => (
          <EvidenceMetric key={metric} label={`Trajetória · ${trajectoryLabels[metric] ?? metric.replace(/_/gu, ' ')}`} detail="2025" state={value.availability_state}>{formatDecimal(value.value, '%')}</EvidenceMetric>
        ))}
        <EvidenceMetric label="Mobilidade de residentes" detail="fotografia de 2022" state={active.mobility_2022.availability_state}>{formatDecimal(active.mobility_2022.value, '%')}</EvidenceMetric>
        <EvidenceMetric label="Contexto socioeconômico" detail="2023">{formatDecimal(active.inse_2023)}</EvidenceMetric>
        <EvidenceMetric label="Cenário mecânico para 2030" detail="contexto não preditivo" state={active.mechanical_pressure_2030.availability_state}>{formatDecimal(active.mechanical_pressure_2030.value)}</EvidenceMetric>
      </div>
    )
  }

  if (story.story_id === 'STORY_EJA_TERRITORY') {
    const active = story.secondary_evidence.by_entity.find((item) => item.entity_id === entityId)
    const region = story.secondary_evidence.regional_history
    return (
      <div className="vpk-secondary-grid">
        {active ? <EvidenceMetric label="EJA no território selecionado" detail="matrículas localizadas · 2014–2025" state={active.eja_history.availability_state}>{endpointText(active.eja_history)}</EvidenceMetric> : null}
        {entityId !== REGION_ENTITY_ID ? <EvidenceMetric label="EJA no Vale" detail="matrículas localizadas · 2014–2025" state={region.availability_state}>{endpointText(region)}</EvidenceMetric> : null}
      </div>
    )
  }

  if (story.story_id === 'STORY_LOGISTICS_EPT') {
    const active = story.secondary_evidence.by_entity.find((item) => item.entity_id === entityId)
    if (!active) return null
    return (
      <div className="vpk-secondary-grid">
        <EvidenceMetric label="Vínculos formais de 18 a 24 anos" detail="local de trabalho · 2019–2025" state={active.youth_work_18_24.availability_state}>{endpointText(active.youth_work_18_24)}</EvidenceMetric>
        {active.youth_regional_change_contribution_percent !== null ? <EvidenceMetric label="Participação na mudança regional de 18 a 24 anos" detail="contraste descritivo">{formatDecimal(active.youth_regional_change_contribution_percent, '%')}</EvidenceMetric> : null}
        <p className="vpk-inline-boundary">A correspondência entre ocupações e cursos é normativa e muitos-para-muitos; ela não identifica as mesmas pessoas nem transforma toda EPT em formação logística.</p>
      </div>
    )
  }

  const active = story.secondary_evidence.by_entity.find((item) => item.entity_id === entityId)
  if (!active) return null
  return (
    <div className="vpk-secondary-grid">
      <EvidenceMetric label="Vínculos formais de 18 a 24 anos" detail="estoque · 2019–2025" state={active.rais_18_24.availability_state}>{endpointText(active.rais_18_24)}</EvidenceMetric>
      <EvidenceMetric label="Admissões de 15 a 17 anos" detail="eventos · 2020–2025" state={active.caged_admissions_15_17.availability_state}>{endpointText(active.caged_admissions_15_17)}</EvidenceMetric>
      <EvidenceMetric label="Admissões de 18 a 24 anos" detail="eventos · 2020–2025" state={active.caged_admissions_18_24.availability_state}>{endpointText(active.caged_admissions_18_24)}</EvidenceMetric>
      {active.school_trajectory ? <EvidenceMetric label="Abandono no ensino médio" detail="leitura escolar paralela · 2025">{formatDecimal(active.school_trajectory.dropout_percent_2025, '%')}</EvidenceMetric> : null}
    </div>
  )
}

function SourceList({ story, bundle }: { story: Job5KStory; bundle: VocacoesPneJob5KBundle }) {
  const sources = story.source_refs.map((sourceRef) => bundle.source_registry.find((item) => item.sourceRef === sourceRef)).filter((item) => item !== undefined)
  return (
    <div className="vpk-source-grid">
      <section>
        <h5>Fontes congeladas</h5>
        <ul>{sources.map((source) => <li key={source.sourceRef}><b>{source.label}</b><span>{source.period}</span></li>)}</ul>
      </section>
      <section>
        <h5>Acompanhar</h5>
        <ul>{story.monitoring_indicators.map((indicator) => <li key={indicator}>{indicator}</li>)}</ul>
      </section>
      <section>
        <h5>Coordenação</h5>
        <ul>{story.institutional_coordination.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </div>
  )
}

function StoryArticle({ story, bundle, entityId, entityName, storyNumber }: {
  story: Job5KStory
  bundle: VocacoesPneJob5KBundle
  entityId: string
  entityName: string
  storyNumber: number
}) {
  const variant = storyVariant(story, entityId)
  return (
    <article id={STORY_ANCHORS[story.story_id]} className="vpk-story" data-story-id={story.story_id}>
      <header className="vpk-story__header">
        <p className="vpi-eyebrow">Leitura {storyNumber} · {variant.territorial_function}</p>
        <h3>{variant.title_conclusion}</h3>
        <p>{variant.integrated_summary}</p>
        <div className="vpk-story__meta"><span>{story.periods.join(' · ')}</span><span>Rede total</span><span>Revisão da gestora pendente</span></div>
      </header>

      <StoryVisual story={story} entityId={entityId} />

      <div className="vpk-reading-grid">
        <section>
          <span>Leitura regional</span>
          <p>{story.regional_read}</p>
        </section>
        <section>
          <span>{entityId === REGION_ENTITY_ID ? 'Síntese do Vale' : `Leitura para ${entityName}`}</span>
          <p>{variant.selected_municipality_read}</p>
        </section>
      </div>

      <aside className="vpk-planning">
        <MapPinned aria-hidden="true" />
        <div><span>Implicação para o planejamento</span><p>{story.planning_implication}</p></div>
      </aside>

      <p className="vpk-boundary"><CircleAlert aria-hidden="true" /> <span><b>Limite de interpretação.</b> {story.interpretation_boundary}</span></p>

      <EvidenceDisclosure title="Ver evidências complementares, fontes e acompanhamento" testId={`evidence-${STORY_ANCHORS[story.story_id]}`}>
        <SecondaryEvidence story={story} entityId={entityId} />
        <SourceList story={story} bundle={bundle} />
      </EvidenceDisclosure>
    </article>
  )
}

function ContextEndpoint({ label, endpoint }: { label: string; endpoint: Job5KEndpoint }) {
  return <EvidenceMetric label={label} detail={`${endpoint.initial_year ?? '—'}–${endpoint.final_year ?? '—'}`} state={endpoint.availability_state}>{endpointText(endpoint)}</EvidenceMetric>
}

function ConditionalContextCard({ context, entityId }: { context: Job5KConditionalContext; entityId: string }) {
  if (context.context_id === 'CONTEXT_RURALITY_TRANSPORT') {
    const variant = context.variants.find((item) => item.entity_id === entityId)
    if (!variant) return null
    return (
      <article className="vpk-context-card">
        <p className="vpi-eyebrow">Contexto condicional</p>
        <h4>{variant.title}</h4>
        <p>{variant.summary}</p>
        <div className="vpk-secondary-grid">
          <ContextEndpoint label="Matrículas rurais" endpoint={variant.rural_enrollments} />
          <ContextEndpoint label="Escolas rurais" endpoint={variant.rural_schools} />
          <ContextEndpoint label="Ensino médio rural" endpoint={variant.rural_high_school_enrollments} />
          <EvidenceMetric label="Previsão administrativa 2026" detail="planejamento; não é execução" state={variant.pnate_2026.availability_state}>{variant.pnate_2026.value === null ? 'Indisponível' : currencyFormatter.format(variant.pnate_2026.value)}</EvidenceMetric>
        </div>
      </article>
    )
  }
  const variant = context.variants.find((item) => item.entity_id === entityId)
  if (!variant) return null
  return (
    <article className="vpk-context-card">
      <p className="vpi-eyebrow">Contexto descritivo</p>
      <h4>{variant.title}</h4>
      <p>{variant.summary}</p>
      <div className="vpk-secondary-grid">
        <ContextEndpoint label="Matrículas da educação especial" endpoint={variant.special_enrollments} />
        <ContextEndpoint label="Escolas que informam AEE" endpoint={variant.schools_reporting_aee} />
      </div>
      <p className="vpk-inline-boundary">{variant.interpretation_boundary}</p>
    </article>
  )
}

function MainReadings({ bundle, entityId, entityName }: {
  bundle: VocacoesPneJob5KBundle
  entityId: string
  entityName: string
}) {
  return (
    <section className="vpk-main-readings" aria-labelledby="vpk-main-readings-title">
      <header>
        <p className="vpi-eyebrow">Síntese gerada pelas mesmas regras para Vale e municípios</p>
        <h2 id="vpk-main-readings-title">Principais leituras para {entityName}</h2>
        <p>Quatro conclusões orientam a leitura; indicadores adicionais ficam disponíveis como evidência, sem competir com a narrativa principal.</p>
      </header>
      <div className="vpk-reading-cards">
        {bundle.stories.map((story, index) => {
          const variant = storyVariant(story, entityId)
          return (
            <article key={story.story_id} data-testid={`main-reading-${index + 1}`}>
              <span>Leitura {index + 1}</span>
              <h3>{variant.title_conclusion}</h3>
              <p>{variant.integrated_summary}</p>
              <dl>
                {variant.key_figures.map((figure) => (
                  <div key={`${figure.label}-${figure.period}`}><dt>{figure.label}</dt><dd>{figure.value}</dd><small>{figure.period}</small></div>
                ))}
              </dl>
              <footer><span>{variant.territorial_function}</span><a href={`#${STORY_ANCHORS[story.story_id]}`} onClick={(event) => scrollToStory(event, story.story_id)}>Abrir leitura <ArrowRight aria-hidden="true" /></a></footer>
            </article>
          )
        })}
      </div>
    </section>
  )
}

export function VocacoesPneInsights({ bundle, municipalityEntityId, municipalityName }: {
  bundle: VocacoesPneJob5KBundle
  municipalityEntityId: string | null
  municipalityName: string | null
}) {
  const entityId = municipalityEntityId ?? REGION_ENTITY_ID
  const entityName = municipalityName ?? bundle.region.name

  return (
    <div className="vpk-insights">
      <nav className="vpk-anchor-nav" aria-label="Navegação pelas quatro leituras principais">
        <ol>{bundle.stories.map((story, index) => (
          <li key={story.story_id}><a href={`#${STORY_ANCHORS[story.story_id]}`} onClick={(event) => scrollToStory(event, story.story_id)}><span>{index + 1}</span>{storyVariant(story, entityId).title_conclusion}<ArrowRight aria-hidden="true" /></a></li>
        ))}</ol>
      </nav>

      <MainReadings bundle={bundle} entityId={entityId} entityName={entityName} />

      {bundle.directions.map((direction) => {
        const directionStories = bundle.stories.filter((story) => story.direction_id === direction.direction_id)
        return (
          <section key={direction.direction_id} className="vpk-direction" aria-labelledby={`vpk-direction-${direction.sequence}`}>
            <header className="vpk-direction__header">
              <span>Direção {direction.sequence}</span>
              <div><h2 id={`vpk-direction-${direction.sequence}`}>{direction.title}</h2><p>{direction.manager_question}</p></div>
            </header>
            {directionStories.map((story) => (
              <StoryArticle
                key={story.story_id}
                story={story}
                bundle={bundle}
                entityId={entityId}
                entityName={entityName}
                storyNumber={bundle.stories.indexOf(story) + 1}
              />
            ))}
            {direction.sequence === 1 ? (
              <div className="vpk-conditional-contexts">
                <EvidenceDisclosure title={`Abrir contextos condicionais para ${entityName}`} testId="conditional-contexts">
                  <div className="vpk-context-grid">
                    {bundle.conditional_contexts.map((context) => <ConditionalContextCard key={context.context_id} context={context} entityId={entityId} />)}
                  </div>
                </EvidenceDisclosure>
              </div>
            ) : null}
          </section>
        )
      })}

      <aside className="vpk-review-state">
        <BookOpen aria-hidden="true" />
        <p><b>Uso interno.</b> As quatro leituras aguardam revisão da gestora e não estão autorizadas como narrativa pública.</p>
      </aside>
    </div>
  )
}

export const job5kStoryAnchors = STORY_ANCHORS
