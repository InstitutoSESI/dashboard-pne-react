import {
  ArrowLeftRight,
  ArrowRight,
  BookOpenCheck,
  BriefcaseBusiness,
  Building2,
  CalendarRange,
  GraduationCap,
  MapPinned,
  Network,
  UsersRound,
} from 'lucide-react'
import { useMemo, type ComponentType, type MouseEvent, type SVGProps } from 'react'
import type {
  ManagerReviewCard,
  ManagerReviewEvidence,
  ManagerReviewEvidenceProfile,
  ManagerReviewPriority,
  ManagerReviewSupportingRelation,
} from '../vocacoesPneManagerReviewModel'
import { buildVocacoesPneManagerReviewModel } from '../vocacoesPneManagerReviewModel'
import type { VocacoesPneLoadedBundle } from '../vocacoesPneUiV2Types'

type Icon = ComponentType<SVGProps<SVGSVGElement>>

const CARD_ICONS: Record<string, Icon> = {
  'relacao-coortes-oferta': UsersRound,
  'relacao-trajetoria-mobilidade': GraduationCap,
  'relacao-trabalho-juvenil-ensino-medio': BriefcaseBusiness,
  'relacao-eja-escolaridade-adulta': BookOpenCheck,
  'agenda-coortes-capacidade': Building2,
  'agenda-trabalho-aprendizagem': Network,
  'agenda-ocupacoes-formacao': MapPinned,
  'conexao-contexto-socioeconomico-trajetoria': UsersRound,
  'conexao-ruralidade-oferta-transporte': MapPinned,
  'conexao-educacao-especial-aee': BookOpenCheck,
}

function scrollToId(event: MouseEvent<HTMLAnchorElement>, id: string) {
  event.preventDefault()
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function MiniSeries({ evidence }: { evidence: ManagerReviewEvidence }) {
  const points = (evidence.series?.points ?? []).filter((point) => (
    point.value !== null
    && (point.availabilityState === 'observed' || point.availabilityState === 'observed_zero')
  ))
  if (points.length < 4) return null

  const values = points.map((point) => point.value as number)
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  const range = maximum - minimum
  const width = 180
  const height = 46
  const padding = 4
  const coordinatePairs = points.map((point, index) => {
    const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2)
    const normalized = range === 0 ? 0.5 : ((point.value as number) - minimum) / range
    const y = height - padding - normalized * (height - padding * 2)
    return { x, y }
  })
  const coordinates = coordinatePairs.map(({ x, y }) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
  const lastPoint = points[points.length - 1]
  const firstCoordinate = coordinatePairs[0]
  const lastCoordinate = coordinatePairs[coordinatePairs.length - 1]

  return (
    <svg
      className="vpm-mini-series"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${evidence.label}: evolução de ${points[0].year} a ${lastPoint.year}`}
      preserveAspectRatio="none"
    >
      <title>{`${evidence.label}: evolução observada no período`}</title>
      <line x1={padding} x2={width - padding} y1={height - padding} y2={height - padding} />
      <polyline points={coordinates} />
      <circle cx={firstCoordinate.x} cy={firstCoordinate.y} r="2.6" />
      <circle cx={lastCoordinate.x} cy={lastCoordinate.y} r="3.2" />
    </svg>
  )
}

function EvidenceMetric({ evidence }: { evidence: ManagerReviewEvidence }) {
  return (
    <article className="vpm-evidence-metric" data-availability-state={evidence.availabilityState}>
      <div className="vpm-evidence-metric__heading">
        <span>{evidence.label}</span>
        <small>{evidence.period}</small>
      </div>
      <strong>{evidence.value}</strong>
      <p>{evidence.detail}</p>
      <MiniSeries evidence={evidence} />
      {evidence.comparison ? <p className="vpm-evidence-metric__comparison">{evidence.comparison}</p> : null}
      <footer>{evidence.lens}</footer>
    </article>
  )
}

function EvidenceSide({ label, evidence, side }: {
  label: string
  evidence: ManagerReviewEvidence[]
  side: 'education' | 'territory'
}) {
  return (
    <section className={`vpm-evidence-side vpm-evidence-side--${side}`}>
      <header>
        {side === 'education' ? <GraduationCap aria-hidden="true" /> : <MapPinned aria-hidden="true" />}
        <span>{label}</span>
      </header>
      <div className="vpm-evidence-side__grid">
        {evidence.map((item) => <EvidenceMetric key={item.id} evidence={item} />)}
      </div>
    </section>
  )
}

function RelationshipVisual({ card }: { card: ManagerReviewCard }) {
  const territoryFirst = card.directionId === 'territory-to-education'
  const first = territoryFirst
    ? <EvidenceSide label={card.territoryLabel} evidence={card.territoryEvidence} side="territory" />
    : <EvidenceSide label={card.educationLabel} evidence={card.educationEvidence} side="education" />
  const second = territoryFirst
    ? <EvidenceSide label={card.educationLabel} evidence={card.educationEvidence} side="education" />
    : <EvidenceSide label={card.territoryLabel} evidence={card.territoryEvidence} side="territory" />

  return (
    <div
      className="vpm-relation-visual"
      data-main-visual={card.id}
      aria-label={`Leitura integrada: ${card.educationLabel} e ${card.territoryLabel}`}
    >
      {first}
      <div className="vpm-relation-connector" aria-label={card.connector}>
        <ArrowLeftRight aria-hidden="true" />
        <span>{card.connector}</span>
      </div>
      {second}
    </div>
  )
}

function EvidenceProfile({ profile }: { profile: ManagerReviewEvidenceProfile }) {
  return (
    <section
      className="vpm-evidence-profile"
      data-evidence-class={profile.evidenceClass}
      aria-label={`Sustentação da leitura: ${profile.evidenceLabel}`}
    >
      <div className="vpm-evidence-profile__badge">
        <BookOpenCheck aria-hidden="true" />
        <span>{profile.evidenceLabel}</span>
      </div>
      <div>
        <h4>O que os dados sustentam</h4>
        <p>{profile.evidenceSummary}</p>
      </div>
      <div>
        <h4>Por que vale ler em conjunto</h4>
        <p>{profile.mechanism}</p>
      </div>
    </section>
  )
}

type SourcesAndMethodContent = Pick<
  ManagerReviewCard,
  'monitoringIndicators' | 'sourceRefs' | 'interpretationBoundary'
>

function SourcesAndMethod({ card, bundle }: {
  card: SourcesAndMethodContent
  bundle: VocacoesPneLoadedBundle
}) {
  const sourceRegistry = new Map([
    ...bundle.core.sourceRegistry.map((source) => [source.sourceRef, source] as const),
    ...bundle.insights.source_registry.map((source) => [source.sourceRef, source] as const),
  ])
  const sources = card.sourceRefs.map((sourceRef) => sourceRegistry.get(sourceRef)).filter((source) => source !== undefined)
  const renderContent = (className: string) => (
    <div className={className}>
      <section>
        <h4>Indicadores para acompanhar</h4>
        <ul>{card.monitoringIndicators.map((indicator) => <li key={indicator}>{indicator}</li>)}</ul>
      </section>
      <section>
        <h4>Fontes e períodos</h4>
        <ul>{sources.map((source) => <li key={source.sourceRef}><b>{source.label}</b><span>{source.period}</span></li>)}</ul>
      </section>
      <section>
        <h4>Como ler esta relação</h4>
        <p>{card.interpretationBoundary}</p>
      </section>
    </div>
  )

  return (
    <>
      <details className="vpm-details">
        <summary>Ver indicadores, fontes e como ler</summary>
        {renderContent('vpm-details__content')}
      </details>
      {renderContent('vpm-print-details')}
    </>
  )
}

function ReviewCard({ card, bundle }: {
  card: ManagerReviewCard
  bundle: VocacoesPneLoadedBundle
}) {
  const IconComponent = CARD_ICONS[card.id] ?? CalendarRange
  return (
    <article
      id={card.id}
      className="vpm-card"
      data-review-card={card.id}
      data-direction={card.directionId}
    >
      <header className="vpm-card__header">
        <div className="vpm-card__number"><IconComponent aria-hidden="true" /><span>{card.sequence}</span></div>
        <div>
          <p className="vpi-eyebrow">{card.eyebrow}</p>
          <h3>{card.title}</h3>
          <p className="vpm-card__answer">{card.answer}</p>
        </div>
      </header>

      <RelationshipVisual card={card} />

      <EvidenceProfile profile={card} />

      <aside className="vpm-planning">
        <div>
          <span>Questão para o planejamento</span>
          <p>{card.planningQuestion}</p>
        </div>
        <dl>
          <div><dt>Responsabilidade</dt><dd>{card.responsibility}</dd></div>
          <div><dt>Temas do PNE</dt><dd>{card.pneTopics.join(' · ')}</dd></div>
        </dl>
      </aside>

      <SourcesAndMethod card={card} bundle={bundle} />
    </article>
  )
}

function SupportingRelationCard({ relation, bundle }: {
  relation: ManagerReviewSupportingRelation
  bundle: VocacoesPneLoadedBundle
}) {
  const IconComponent = CARD_ICONS[relation.id] ?? CalendarRange
  return (
    <article className="vpm-supporting-card" data-supporting-relation={relation.id} id={relation.id}>
      <header>
        <span className="vpm-supporting-card__icon"><IconComponent aria-hidden="true" /></span>
        <div>
          <p className="vpi-eyebrow">{relation.eyebrow}</p>
          <h3>{relation.title}</h3>
          <p>{relation.answer}</p>
        </div>
      </header>
      <div className="vpm-supporting-card__evidence">
        {relation.evidence.map((item) => <EvidenceMetric key={item.id} evidence={item} />)}
      </div>
      <EvidenceProfile profile={relation} />
      <aside className="vpm-supporting-card__planning">
        <span>Questão para o planejamento</span>
        <p>{relation.planningQuestion}</p>
        <small>{relation.responsibility}</small>
      </aside>
      <SourcesAndMethod card={relation} bundle={bundle} />
    </article>
  )
}

function PriorityCard({ priority }: { priority: ManagerReviewPriority }) {
  const id = priority.href.slice(1)
  return (
    <article className="vpm-priority" data-priority-id={priority.id}>
      <p className="vpi-eyebrow">{priority.label}</p>
      <h3>{priority.title}</h3>
      <p>{priority.summary}</p>
      <dl>{priority.figures.map((figure) => (
        <div key={`${figure.label}-${figure.period}`}>
          <dt>{figure.label}</dt>
          <dd>{figure.value}</dd>
          <small>{figure.period}</small>
        </div>
      ))}</dl>
      <footer>
        <span>{priority.responsibility}</span>
        <a href={priority.href} onClick={(event) => scrollToId(event, id)}>Ver evidências <ArrowRight aria-hidden="true" /></a>
      </footer>
    </article>
  )
}

export function VocacoesPneManagerReview({
  bundle,
  municipalityEntityId,
  municipalityName,
  surface = 'review',
}: {
  bundle: VocacoesPneLoadedBundle
  municipalityEntityId: string | null
  municipalityName: string | null
  surface?: 'review' | 'official'
}) {
  const model = useMemo(
    () => buildVocacoesPneManagerReviewModel(bundle, municipalityEntityId, municipalityName),
    [bundle, municipalityEntityId, municipalityName],
  )

  return (
    <div className="vpm-review">
      <aside className="vpm-method-note">
        <BookOpenCheck aria-hidden="true" />
        <p>Esta página reúne mudanças da educação e do território ao longo do tempo. Os dados são apresentados em conjunto quando ajudam a interpretar uma mesma questão de planejamento. A leitura não atribui automaticamente uma mudança à outra.</p>
      </aside>

      <nav className="vpm-direction-nav" aria-label="Navegação pelas duas direções da análise">
        {model.directions.map((direction) => (
          <a
            key={direction.id}
            href={`#${direction.id}`}
            onClick={(event) => scrollToId(event, direction.id)}
          >
            <span>{direction.sequence}</span>
            <div><b>{direction.title}</b><small>{direction.question}</small></div>
            <ArrowRight aria-hidden="true" />
          </a>
        ))}
        {model.supportingRelations.length > 0 ? (
          <a href="#conexoes-complementares" onClick={(event) => scrollToId(event, 'conexoes-complementares')}>
            <span>+</span>
            <div><b>Conexões complementares</b><small>Outros sinais que qualificam o planejamento</small></div>
            <ArrowRight aria-hidden="true" />
          </a>
        ) : null}
      </nav>

      <section className="vpm-priorities" aria-labelledby="vpm-priorities-title">
        <header>
          <p className="vpi-eyebrow">Síntese municipal · sem ranking</p>
          <h2 id="vpm-priorities-title">O que os dados colocam na agenda de {model.entityName}</h2>
          <p>Três temas organizam a conversa inicial. Eles combinam diferença local, responsabilidade e possibilidade de acompanhamento — sem condensar os dados em uma nota.</p>
        </header>
        <div className="vpm-priorities__grid">
          {model.priorities.map((priority) => <PriorityCard key={priority.id} priority={priority} />)}
        </div>
      </section>

      {model.directions.map((direction) => (
        <section
          key={direction.id}
          id={direction.id}
          className="vpm-direction"
          data-direction-id={direction.id}
          aria-labelledby={`${direction.id}-title`}
        >
          <header className="vpm-direction__header">
            <span>Direção {direction.sequence}</span>
            <div>
              <h2 id={`${direction.id}-title`}>{direction.title}</h2>
              <p>{direction.question}</p>
              <small>{direction.summary}</small>
            </div>
          </header>
          <div className="vpm-direction__cards">
            {direction.cards.map((card) => <ReviewCard key={card.id} card={card} bundle={bundle} />)}
          </div>
        </section>
      ))}

      {model.supportingRelations.length > 0 ? (
        <section
          className="vpm-supporting"
          id="conexoes-complementares"
          aria-labelledby="vpm-supporting-title"
        >
          <header className="vpm-supporting__header">
            <p className="vpi-eyebrow">Leituras que ampliam o diagnóstico</p>
            <h2 id="vpm-supporting-title">Outras conexões que merecem entrar na conversa</h2>
            <p>Elas acrescentam contexto social, territorial e de organização da oferta. São mostradas com o alcance que os dados permitem, sem disputar espaço com as sete leituras centrais.</p>
          </header>
          <div className="vpm-supporting__grid">
            {model.supportingRelations.map((relation) => (
              <SupportingRelationCard key={relation.id} relation={relation} bundle={bundle} />
            ))}
          </div>
        </section>
      ) : null}

      {surface === 'review' ? (
        <aside className="vpm-review-status">
          <BookOpenCheck aria-hidden="true" />
          <p><b>Página pronta para validação de conteúdo.</b> A promoção pública continua separada desta etapa de revisão com a gestora.</p>
        </aside>
      ) : (
        <aside className="vpm-review-status vpm-review-status--official">
          <BookOpenCheck aria-hidden="true" />
          <p><b>Como esta leitura usa evidências.</b> Contrastes e movimentos simultâneos só entram quando há uma razão substantiva para lê-los juntos. Quando os testes não sustentam um padrão estável, isso reduz o alcance da interpretação e mantém o tema apenas como agenda de acompanhamento.</p>
        </aside>
      )}
    </div>
  )
}
