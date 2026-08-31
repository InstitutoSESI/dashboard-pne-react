import {
  ArrowDownRight,
  BookOpenCheck,
  CalendarClock,
  CircleAlert,
  MapPinned,
  Printer,
  Search,
  Target,
} from 'lucide-react'
import type { MouseEvent } from 'react'
import { PnePageHeader } from '../../components/PnePageHeader'
import type {
  VocacoesPneAdvancedAgenda,
  VocacoesPneAdvancedBundle,
  VocacoesPneAdvancedEvidence,
  VocacoesPneAdvancedReading,
  VocacoesPneAdvancedScopeVariant,
  VocacoesPneAdvancedTransversal,
  VocacoesPneAnalysisCheckStatus,
} from './vocacoesPneAdvancedContract'
import { resolveVocacoesPneAdvancedScope } from './vocacoesPneAdvancedContract'
import '../../styles/vocacoes-pne-advanced.css'

const MAIN_READING_IDS = [
  'demografia-matriculas-rede',
  'transformacao-economica-ept',
  'escolaridade-adulta-eja',
] as const

const MAIN_AGENDA_IDS = [
  'coordenar-demografia-rede',
  'mapear-acesso-ept',
  'revisar-eja-por-etapa',
] as const

const RELATION_GROUPS = [
  {
    id: 'populacao-acesso-rede',
    title: 'População, acesso e organização da rede',
    description: 'Como moradores, matrículas, oferta e deslocamentos ajudam a investigar o atendimento.',
    relationIds: ['demografia-matriculas-rede', 'ruralidade-organizacao-rede'],
  },
  {
    id: 'trajetoria-condicoes-vida',
    title: 'Trajetória escolar e condições de vida',
    description: 'Relações que ajudam a formular perguntas sobre permanência, desigualdade e busca ativa.',
    relationIds: ['trajetoria-contexto', 'contexto-social-registrado'],
  },
  {
    id: 'trabalho-formacao-eja',
    title: 'Trabalho, formação técnica e EJA',
    description: 'O que emprego, escolaridade adulta e oferta formativa colocam na agenda educacional.',
    relationIds: [
      'transformacao-economica-ept',
      'escolaridade-adulta-eja',
      'trabalho-juvenil-permanencia',
    ],
  },
  {
    id: 'inclusao-atendimento',
    title: 'Inclusão e organização territorial',
    description: 'Mudanças na oferta que precisam ser lidas junto de capacidade, qualidade e trajetória.',
    relationIds: ['inclusao-aee'],
  },
] as const

interface LibraryRelation {
  readonly id: string
  readonly title: string
  readonly question: string
  readonly summary: string
  readonly result: string
  readonly planning: string
  readonly limit: string
  readonly evidence: readonly VocacoesPneAdvancedEvidence[]
  readonly sources: readonly string[]
  readonly analysisStatus?: VocacoesPneAnalysisCheckStatus
  readonly featured: boolean
}

function scrollToSection(event: MouseEvent<HTMLAnchorElement>, id: string) {
  event.preventDefault()
  const target = document.getElementById(id)
  if (!(target instanceof HTMLElement)) return
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' })
  if (target.tabIndex < 0) target.tabIndex = -1
  target.focus({ preventScroll: true })
}

function formatNumber(value: number, format: VocacoesPneAdvancedEvidence['format'], showSign = false) {
  const options = showSign && value !== 0 ? { signDisplay: 'always' as const } : undefined
  if (format === 'integer') {
    return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0, ...options }).format(value)
  }
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    ...options,
  }).format(value)
}

function evidenceValueLabel(evidence: VocacoesPneAdvancedEvidence) {
  if (
    evidence.availability === 'calculated'
    && evidence.unit === 'matrículas'
    && evidence.label === 'Parte ligada à mudança no número de jovens'
  ) {
    const direction = evidence.value < 0 ? 'a menos' : evidence.value > 0 ? 'a mais' : ''
    const magnitude = formatNumber(Math.abs(evidence.value), 'integer')
    return `cerca de ${magnitude}${direction === '' ? '' : ` ${direction}`}`
  }
  const suffix = evidence.format === 'percent1'
    ? '%'
    : evidence.format === 'percentage_points1'
      ? ' p.p.'
      : ''
  if (evidence.valueKind === 'interval' && evidence.valueTo !== undefined) {
    return `${formatNumber(evidence.value, evidence.format)} a ${formatNumber(evidence.valueTo, evidence.format)}${suffix}`
  }
  return `${formatNumber(evidence.value, evidence.format, evidence.valueKind === 'change')}${suffix}`
}

function endpointLabel(evidence: VocacoesPneAdvancedEvidence) {
  if (evidence.startValue === undefined || evidence.endValue === undefined) return null
  return `${formatNumber(evidence.startValue, evidence.format)} → ${formatNumber(evidence.endValue, evidence.format)}`
}

function EvidenceMeasure({
  evidence,
  compact = false,
}: {
  evidence: VocacoesPneAdvancedEvidence
  compact?: boolean
}) {
  const endpoints = endpointLabel(evidence)
  return (
    <div
      className={`vpr-measure${compact ? ' vpr-measure--compact' : ''}`}
      data-evidence-item="true"
    >
      <span className="vpr-measure__context">{evidence.contextLabel}</span>
      <strong className="vpr-measure__value">{evidenceValueLabel(evidence)}</strong>
      <span className="vpr-measure__label">{evidence.label}</span>
      {endpoints === null ? null : <span className="vpr-measure__endpoints">{endpoints}</span>}
      <span className="vpr-measure__meta">{evidence.period} · {evidence.unit}</span>
      {evidence.availability === 'observed_zero' ? (
        <span className="vpr-measure__zero">zero observado</span>
      ) : null}
    </div>
  )
}

function mainStorySummary(reading: VocacoesPneAdvancedReading) {
  switch (reading.id) {
    case 'demografia-matriculas-rede':
      return 'População jovem e matrículas mudaram em ritmos diferentes. Isso ajuda a formular a pergunta, mas não encerra o diagnóstico: moradia, deslocamento, vagas e rede precisam ser vistos juntos.'
    case 'transformacao-economica-ept':
      return 'Empregos e oferta técnica mudam no território. Pede mapear cursos e acesso no Vale, sem presumir procura ou garantia de trabalho.'
    case 'escolaridade-adulta-eja':
      return 'EJA fundamental e médio mudaram em direções diferentes. Isso pede olhar etapa, turno e oferta, sem supor qual veio primeiro ou ligação estável com trabalho e escolaridade.'
    default:
      return reading.territorialReading
  }
}

export function vocacoesPnePublicStatusSentence(status: VocacoesPneAnalysisCheckStatus) {
  switch (status) {
    case 'consistent':
      return 'Esse padrão se repetiu nos recortes analisados, sem mostrar o que veio primeiro.'
    case 'watch':
      return 'Ainda faltam anos ou informações para saber se o movimento se mantém.'
    case 'not_confirmed':
      return 'A ligação não apareceu de forma estável nos recortes analisados.'
    case 'not_comparable':
      return 'Os dados medem períodos ou grupos diferentes e ainda não permitem uma comparação segura.'
  }
}

function readingResult(reading: VocacoesPneAdvancedReading) {
  switch (reading.id) {
    case 'demografia-matriculas-rede':
      return 'A conta organiza a mudança; a explicação segue em aberto.'
    case 'trajetoria-contexto':
      return 'A ligação não apareceu de forma estável quando outros contextos entraram na comparação.'
    case 'transformacao-economica-ept':
      return 'Faltam anos e dados de acesso para saber se o movimento permanece.'
    case 'escolaridade-adulta-eja':
      return 'As mudanças são observadas, mas não sabemos qual veio primeiro nem se a relação se mantém.'
    case 'trabalho-juvenil-permanencia':
      return 'A ligação entre emprego juvenil e permanência não apareceu de forma estável.'
    default:
      return vocacoesPnePublicStatusSentence(reading.analysisCheck.status)
  }
}

function librarySummary(reading: VocacoesPneAdvancedReading) {
  switch (reading.id) {
    case 'demografia-matriculas-rede':
      return 'Compara a mudança nas matrículas com a parte esperada pela mudança no número de jovens.'
    case 'trajetoria-contexto':
      return 'Compara abandono, condições socioeconômicas escolares e características da rede sem escolher uma causa antes da análise.'
    case 'transformacao-economica-ept':
      return 'Coloca lado a lado mudanças nos empregos, matrículas técnicas e cursos que podem ser acessados no município e na região.'
    case 'escolaridade-adulta-eja':
      return 'Observa como escolaridade adulta, perfil dos trabalhadores jovens e matrículas de EJA aparecem no mesmo território.'
    case 'trabalho-juvenil-permanencia':
      return 'Acompanha emprego formal de jovens e abandono escolar no mesmo período, preservando a possibilidade de outras explicações.'
    default:
      return reading.territorialReading
  }
}

function transversalResult(item: VocacoesPneAdvancedTransversal) {
  switch (item.id) {
    case 'ruralidade-organizacao-rede':
      return 'Esse padrão se repetiu nos recortes analisados. Oferta e matrículas rurais mudaram juntas, sem mostrar o que veio primeiro.'
    case 'inclusao-aee':
      return 'Este é um retrato do atendimento, não uma explicação do resultado educacional.'
    case 'contexto-social-registrado':
      return 'Este é um retrato das pessoas registradas, não uma medida de toda a população nem uma explicação da trajetória escolar.'
    default:
      return item.analysisCheck === undefined
        ? item.interpretation
        : vocacoesPnePublicStatusSentence(item.analysisCheck.status)
  }
}

function selectReadings(scope: VocacoesPneAdvancedScopeVariant) {
  const byId = new Map(scope.readings.map((reading) => [reading.id, reading]))
  return MAIN_READING_IDS
    .map((id) => byId.get(id))
    .filter((reading): reading is VocacoesPneAdvancedReading => reading !== undefined)
}

function selectAgendas(scope: VocacoesPneAdvancedScopeVariant) {
  const byId = new Map(scope.agendas.map((agenda) => [agenda.id, agenda]))
  return MAIN_AGENDA_IDS
    .map((id) => byId.get(id))
    .filter((agenda): agenda is VocacoesPneAdvancedAgenda => agenda !== undefined)
}

function buildLibraryRelations(scope: VocacoesPneAdvancedScopeVariant): readonly LibraryRelation[] {
  const readings: LibraryRelation[] = scope.readings.map((reading) => ({
    id: reading.id,
    title: reading.title,
    question: reading.question,
    summary: librarySummary(reading),
    result: readingResult(reading),
    planning: reading.planning.implication,
    limit: reading.limit,
    evidence: reading.evidence,
    sources: reading.sources,
    analysisStatus: reading.analysisCheck.status,
    featured: MAIN_READING_IDS.some((id) => id === reading.id),
  }))
  const transversal: LibraryRelation[] = scope.transversal.map((item) => ({
    id: item.id,
    title: item.title,
    question: item.planningQuestion,
    summary: item.interpretation,
    result: transversalResult(item),
    planning: item.planningQuestion,
    limit: item.limit,
    evidence: item.evidence,
    sources: item.sources,
    analysisStatus: item.analysisCheck?.status,
    featured: false,
  }))
  return [...readings, ...transversal]
}

function MainReadingCard({
  reading,
  index,
}: {
  reading: VocacoesPneAdvancedReading
  index: number
}) {
  const titleId = `vpr-reading-title-${reading.id}`
  const resultId = `vpr-reading-result-${reading.id}`
  return (
    <article
      className="vpr-reading"
      data-reading-card={reading.id}
      data-evidence-class={reading.evidenceClass.kind}
      data-analysis-status={reading.analysisCheck.status}
      id={`vpa-reading-${reading.id}`}
      aria-labelledby={titleId}
    >
      <header className="vpr-reading__header">
        <span className="vpr-reading__number">{String(index + 1).padStart(2, '0')}</span>
        <div>
          <p>{reading.theme}</p>
          <h3 id={titleId}>{reading.title}</h3>
        </div>
      </header>

      <p className="vpr-reading__question">{reading.question}</p>
      <p className="vpr-reading__answer">{mainStorySummary(reading)}</p>

      <div className="vpr-measure-grid" aria-label={`Até duas medidas centrais de ${reading.title}`}>
        {reading.evidence.slice(0, 2).map((evidence) => (
          <EvidenceMeasure evidence={evidence} key={evidence.label} />
        ))}
      </div>

      <section
        className="vpr-result"
        data-analysis-check={reading.id}
        data-analysis-status={reading.analysisCheck.status}
        aria-labelledby={resultId}
      >
        <BookOpenCheck aria-hidden="true" />
        <div>
          <span id={resultId}>O que a análise permite dizer</span>
          <p>{readingResult(reading)}</p>
        </div>
      </section>

      <div className="vpr-action">
        <Target aria-hidden="true" />
        <div>
          <span>O que isso pede da gestão</span>
          <p>{reading.planning.implication}</p>
        </div>
      </div>

      <p className="vpr-boundary" data-reading-boundary="visible">
        <CircleAlert aria-hidden="true" />
        <span><b>O que ainda não sabemos.</b> {reading.limit}</span>
      </p>

      <details className="vpr-details">
        <summary>Ver dados, fontes e outras explicações</summary>
        <div className="vpr-details__body">
          <section>
            <h4>Leitura completa dos dados</h4>
            <p>{reading.conclusion}</p>
            {reading.evidence.length <= 2 ? null : (
              <div className="vpr-details__extra-measures">
                {reading.evidence.slice(2).map((evidence) => (
                  <EvidenceMeasure compact evidence={evidence} key={evidence.label} />
                ))}
              </div>
            )}
          </section>
          <section>
            <h4>Como fizemos a comparação</h4>
            <p>{reading.comparisonNote}</p>
            <p>{reading.analysisCheck.summary}</p>
            <ul>{reading.analysisCheck.details.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
          <section>
            <h4>Como a relação pode acontecer</h4>
            <p>{reading.mechanism.summary}</p>
            <p><b>O que esperaríamos observar:</b> {reading.mechanism.expectedPattern}</p>
            <h4>Outras explicações possíveis</h4>
            <ul>{reading.mechanism.alternatives.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
          <section>
            <h4>O que acompanhar</h4>
            <div className="vpr-tags">
              {reading.planning.indicators.map((item) => <span key={item}>{item}</span>)}
            </div>
            <h4>Fontes e o que cada dado mede</h4>
            <ul>{reading.sources.map((item) => <li key={item}>{item}</li>)}</ul>
            <p><b>A leitura deve ser revista se:</b> {reading.mechanism.boundary}</p>
          </section>
        </div>
      </details>
    </article>
  )
}

function AgendaCard({ agenda, index }: { agenda: VocacoesPneAdvancedAgenda; index: number }) {
  return (
    <article className="vpr-agenda" data-agenda-card={agenda.id}>
      <header>
        <span>{String(index + 1).padStart(2, '0')}</span>
        <h3>{agenda.title}</h3>
      </header>
      <p className="vpr-agenda__status">Agenda para avaliar; não é prioridade automática.</p>
      <p><b>Por que olhar agora.</b> {agenda.whyNow}</p>
      <div className="vpr-agenda__action">
        <ArrowDownRight aria-hidden="true" />
        <p><span>Próximo passo possível</span>{agenda.action}</p>
      </div>
      <dl>
        <div><dt>Responsável principal</dt><dd>{agenda.responsibility.lead}</dd></div>
        <div><dt>Quando acompanhar</dt><dd>{agenda.cadence}</dd></div>
      </dl>
    </article>
  )
}

function AgendaDetails({ agendas }: { agendas: readonly VocacoesPneAdvancedAgenda[] }) {
  return (
    <details className="vpr-agenda-collective">
      <summary>Ver participantes, indicadores e critérios de revisão das agendas</summary>
      <div>
        {agendas.map((agenda) => (
          <section key={agenda.id}>
            <h3>{agenda.title}</h3>
            <p><b>Etapa e público:</b> {agenda.educationStage} · {agenda.exposedPopulation}</p>
            <p><b>Contribuem:</b> {agenda.responsibility.contributors.join(' · ')}</p>
            <p><b>Indicadores:</b> {agenda.indicators.join(' · ')}</p>
            <p><b>Rever a decisão quando:</b> {agenda.trigger}</p>
            <p><b>A leitura ganha força se:</b> {agenda.strengthenIf}</p>
            <p><b>A leitura perde força se:</b> {agenda.weakenIf}</p>
          </section>
        ))}
      </div>
    </details>
  )
}

function RelationLibrary({ scope }: { scope: VocacoesPneAdvancedScopeVariant }) {
  const relations = buildLibraryRelations(scope)
  const ruralRelation = relations.find((relation) => relation.id === 'ruralidade-organizacao-rede')

  return (
    <>
      {ruralRelation === undefined ? null : (
        <aside className="vpr-strongest-pattern" data-strongest-pattern={ruralRelation.id}>
          <BookOpenCheck aria-hidden="true" />
          <p>
            <strong>O padrão que mais se repetiu nos dados:</strong>{' '}
            oferta e matrículas rurais mudaram juntas. Isso não mostra o que veio primeiro
            nem se a oferta foi suficiente.
          </p>
        </aside>
      )}

      <div className="vpr-library" data-relation-library={relations.length}>
        {RELATION_GROUPS.map((group) => {
          const groupRelations = group.relationIds
            .map((id) => relations.find((relation) => relation.id === id))
            .filter((relation): relation is LibraryRelation => relation !== undefined)
          return (
            <details className="vpr-library__group" data-relation-group={group.id} key={group.id}>
              <summary>
                <span><b>{group.title}</b><small>{group.description}</small></span>
                <strong>{groupRelations.length} {groupRelations.length === 1 ? 'relação' : 'relações'}</strong>
              </summary>
              <div className="vpr-library__rows">
                {groupRelations.map((relation) => (
                  <article
                    className="vpr-relation"
                    data-relation-item={relation.id}
                    data-analysis-status={relation.analysisStatus}
                    key={relation.id}
                  >
                    <header>
                      <div>
                        <h3>{relation.title}</h3>
                        {relation.featured ? <span>Também aparece em destaque</span> : null}
                      </div>
                      <p>{relation.summary}</p>
                    </header>
                    <div className="vpr-relation__measures">
                      {relation.evidence.slice(0, 2).map((evidence) => (
                        <EvidenceMeasure compact evidence={evidence} key={evidence.label} />
                      ))}
                    </div>
                    {relation.analysisStatus === 'not_confirmed' ? (
                      <p><b>Pergunta que testamos.</b> {relation.question}</p>
                    ) : null}
                    <p className="vpr-relation__result"><b>O que encontramos.</b> {relation.result}</p>
                    <p>
                      <b>{relation.analysisStatus === 'not_confirmed' ? 'Por que isso importa para a gestão.' : 'Questão para a gestão.'}</b>{' '}
                      {relation.planning}
                    </p>
                    <p className="vpr-relation__limit"><b>Limite.</b> {relation.limit}</p>
                    <p className="vpr-relation__sources"><b>Fontes:</b> {relation.sources.join(' · ')}</p>
                  </article>
                ))}
              </div>
            </details>
          )
        })}
      </div>
    </>
  )
}

export function VocacoesPneAdvancedReport({
  bundle,
  municipalityId,
}: {
  bundle: VocacoesPneAdvancedBundle
  municipalityId: string | null
}) {
  const scope = resolveVocacoesPneAdvancedScope(bundle, municipalityId)
  const mainReadings = selectReadings(scope)
  const mainAgendas = selectAgendas(scope)
  const secondaryAgenda = scope.agendas.find((agenda) => !MAIN_AGENDA_IDS.some((id) => id === agenda.id))
  const relationCount = scope.readings.length + scope.transversal.length
  const entityContext = municipalityId === null
    ? `${bundle.region.municipalityCount} municípios · ${bundle.region.stateCode}`
    : `${bundle.region.name} · município incluído na região`

  return (
    <div
      className="page-stack vocacoes-pne-advanced-page vpr-page"
      data-content-version={bundle.contentVersion}
      data-publication="official-advanced"
      data-region={bundle.region.slug}
      data-scope={scope.entityType}
    >
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={entityContext}
        description="Uma leitura integrada para compreender o cenário educacional e preparar decisões sobre rede, formação, permanência e inclusão."
        eyebrow="Vocações da Região · educação e território"
        title={`${scope.entityName}: educação e território`}
        variant="editorial"
      />

      <main className="vpr-main">
        <section className="vpr-hero" aria-labelledby="vpr-hero-title">
          <div className="vpr-hero__copy">
            <p className="vpr-eyebrow">Leitura para decisão</p>
            <h2 id="vpr-hero-title">{scope.headline}</h2>
            <p>{scope.standfirst}</p>
            <div className="vpr-hero__counts" aria-label="Escopo da leitura">
              <span><b>{mainReadings.length}</b> histórias centrais</span>
              <span><b>{mainAgendas.length}</b> frentes para planejar</span>
              <span><b>{relationCount}</b> relações para explorar</span>
            </div>
          </div>
          <aside className="vpr-hero__scope">
            <MapPinned aria-hidden="true" />
            <div>
              <span>Área analisada</span>
              <strong>{scope.entityName}</strong>
              <small>{bundle.region.name} aparece como referência</small>
            </div>
            <button type="button" onClick={() => window.print()}>
              <Printer aria-hidden="true" /> Imprimir leitura
            </button>
          </aside>
        </section>

        <nav className="vpr-nav vpa-nav" aria-label="Seções da leitura integrada">
          <a href="#vpr-summary" onClick={(event) => scrollToSection(event, 'vpr-summary')}>Resumo</a>
          <a href="#vpr-understand" onClick={(event) => scrollToSection(event, 'vpr-understand')}>Entender o cenário</a>
          <a href="#vpr-plan" onClick={(event) => scrollToSection(event, 'vpr-plan')}>Planejar os próximos anos</a>
          <a href="#vpr-library" onClick={(event) => scrollToSection(event, 'vpr-library')}>Explorar relações</a>
        </nav>

        <section className="vpr-summary" id="vpr-summary" tabIndex={-1} aria-labelledby="vpr-summary-title">
          <div className="vpr-section-heading">
            <p className="vpr-eyebrow">Resumo para decidir</p>
            <h2 id="vpr-summary-title">Três mensagens para orientar a primeira leitura</h2>
          </div>
          <div className="vpr-signal-grid">
            {scope.decisionSignals.map((signal, index) => (
              <article key={signal.title}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <h3>{signal.title}</h3>
                <p>{signal.text}</p>
              </article>
            ))}
          </div>
          <p className="vpr-caution">
            <CircleAlert aria-hidden="true" />
            Quando dois dados mudam juntos, isso abre uma pergunta. Não prova, sozinho, que um causou o outro.
          </p>
          <p className="vpr-containment"><MapPinned aria-hidden="true" /> {scope.containmentDisclosure}</p>

          <div className="vpr-directions">
            <article>
              <span>PNE → Vocações</span>
              <h3>Entender o cenário</h3>
              <p>Partimos de um resultado educacional e observamos o que população, trabalho e condições de vida ajudam a investigar.</p>
            </article>
            <article>
              <span>Vocações → PNE</span>
              <h3>Planejar os próximos anos</h3>
              <p>Partimos das mudanças do território e perguntamos o que precisa entrar na agenda da educação e do PME.</p>
            </article>
          </div>
        </section>

        <section className="vpr-readings" id="vpr-understand" tabIndex={-1} aria-labelledby="vpr-understand-title">
          <div className="vpr-section-heading vpr-section-heading--split">
            <div>
              <p className="vpr-eyebrow">PNE → Vocações</p>
              <h2 id="vpr-understand-title">O que o território ajuda a entender sobre a educação?</h2>
            </div>
            <p>
              Estas três histórias aparecem primeiro porque ajudam decisões imediatas.
              A ordem segue utilidade para o planejamento, não o grau de certeza.
            </p>
          </div>
          <div className="vpr-reading-stack">
            {mainReadings.map((reading, index) => (
              <MainReadingCard index={index} key={reading.id} reading={reading} />
            ))}
          </div>
        </section>

        <section className="vpr-agendas-section" id="vpr-plan" tabIndex={-1} aria-labelledby="vpr-plan-title">
          <div className="vpr-section-heading vpr-section-heading--split">
            <div>
              <p className="vpr-eyebrow">Vocações → PNE</p>
              <h2 id="vpr-plan-title">O que precisamos preparar na educação para os próximos anos?</h2>
            </div>
            <p>
              As frentes abaixo transformam as leituras em perguntas de gestão.
              Elas precisam de avaliação local antes de virar prioridade, meta ou expansão de oferta.
            </p>
          </div>
          <div className="vpr-agenda-grid">
            {mainAgendas.map((agenda, index) => <AgendaCard agenda={agenda} index={index} key={agenda.id} />)}
          </div>
          {secondaryAgenda === undefined ? null : (
            <aside className="vpr-secondary-agenda" data-agenda-secondary={secondaryAgenda.id}>
              <Search aria-hidden="true" />
              <p>
                <b>Uma ação transversal:</b> {secondaryAgenda.action}{' '}
                Ela complementa as três frentes e mantém o abandono na rotina de acompanhamento.
              </p>
            </aside>
          )}
          <AgendaDetails agendas={scope.agendas} />
        </section>

        <section className="vpr-library-section" id="vpr-library" tabIndex={-1} aria-labelledby="vpr-library-title">
          <div className="vpr-section-heading vpr-section-heading--split">
            <div>
              <p className="vpr-eyebrow">Outras relações que analisamos</p>
              <h2 id="vpr-library-title">Explore as conexões por tema</h2>
            </div>
            <p>
              A biblioteca reúne todas as {relationCount} relações públicas desta leitura.
              Abra somente o tema que ajuda a decisão em discussão.
            </p>
          </div>
          <RelationLibrary scope={scope} />
        </section>

        <section className="vpr-method" aria-labelledby="vpr-method-title">
          <BookOpenCheck aria-hidden="true" />
          <div>
            <p className="vpr-eyebrow">Transparência</p>
            <h2 id="vpr-method-title">Como chegamos a estas leituras</h2>
            <p>A página mostra relações úteis e também resultados inconclusivos, sempre com o limite específico de cada comparação.</p>
            <details className="vpr-method__details">
              <summary>Ver método, balanço completo e fontes</summary>
              <div>
                <p><b>Regra principal.</b> {bundle.methodology.causalityStatement}</p>
                <p>{bundle.methodology.evidenceStatement}</p>
                <p>{bundle.methodology.availabilityStatement}</p>
                <p>{bundle.methodology.municipalIdentity}</p>

                <section className="vpr-method__atlas" data-relationship-atlas="98">
                  <h3>Mapa completo das relações avaliadas</h3>
                  <div>
                    <span><b>{bundle.methodology.relationshipAtlas.testedRelationships}</b> relações avaliadas</span>
                    <span><b>{bundle.methodology.relationshipAtlas.robustRows}</b> comparações repetidas</span>
                    <span><b>{bundle.methodology.relationshipAtlas.notRobustRows}</b> ligações não confirmadas</span>
                    <span><b>{bundle.methodology.relationshipAtlas.insufficientRows}</b> com informação insuficiente</span>
                    <span><b>{bundle.methodology.relationshipAtlas.descriptiveRows}</b> apenas descritivas</span>
                    <span><b>{bundle.methodology.relationshipAtlas.blockedRows}</b> sem comparação segura</span>
                  </div>
                  <p>{bundle.methodology.relationshipAtlas.statement}</p>
                  <p>{bundle.methodology.relationshipAtlas.familyThresholdStatement}</p>
                </section>

                <section>
                  <h3>Fontes e populações observadas</h3>
                  <ul>{bundle.methodology.sources.map((source) => <li key={source}>{source}</li>)}</ul>
                  <p>
                    Os dados educacionais incluem escolas municipais, estaduais, federais e privadas.
                    Matrículas, moradores, empregos formais e cadastros sociais não acompanham necessariamente as mesmas pessoas.
                  </p>
                </section>
              </div>
            </details>
          </div>
          <CalendarClock aria-hidden="true" className="vpr-method__clock" />
        </section>
      </main>
    </div>
  )
}
