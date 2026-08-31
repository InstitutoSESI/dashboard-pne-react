import { useMemo, useState } from 'react'
import {
  ArrowLeft,
  BookOpenCheck,
  BriefcaseBusiness,
  Building2,
  CalendarRange,
  CircleAlert,
  Compass,
  GraduationCap,
  MapPinned,
  Network,
  Printer,
  Route,
  ShieldCheck,
  TriangleAlert,
  UsersRound,
  WalletCards,
} from 'lucide-react'
import { ErrorState } from '../../components/ErrorState'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { ACTIVE_STATE_CONFIG } from '../../config/stateConfig'
import type {
  CenariosEducacaoAction,
  CenariosEducacaoAvailability,
  CenariosEducacaoBundle,
  CenariosEducacaoCrossCuttingDriver,
  CenariosEducacaoPneStatus,
  CenariosEducacaoScenario,
} from './cenariosEducacaoContract'
import {
  ACRONYM_DEFINITIONS,
  ACTION_TYPE_PLAIN_LANGUAGE,
  AUTHORITY_PLAIN_LABELS,
  CADENCE_PLAIN_LABELS,
  DOMAIN_PLAIN_LABELS,
  DOMAIN_PLAIN_SUMMARIES,
  DRIVER_PLAIN_LANGUAGE,
  FACTOR_PLAIN_LANGUAGE,
  MUNICIPAL_PLAIN_LANGUAGE,
  SCENARIO_PLAIN_LANGUAGE,
  SIMPLE_DECISION_PRIORITIES,
  SIMPLE_PUBLIC_DATA_GAP,
  SIMPLE_PUBLIC_SIGNALS,
  SENTINEL_PLAIN_LANGUAGE,
} from './cenariosEducacaoPlainLanguage'
import { useCenariosEducacaoBundle } from './useCenariosEducacaoBundle'
import '../../styles/cenarios-educacao.css'

const integerFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 0,
})
const decimalFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})

const AVAILABILITY_LABELS: Readonly<Record<CenariosEducacaoAvailability, string>> = Object.freeze({
  observed: 'Dado observado',
  observed_zero: 'Zero registrado',
  calculated: 'Valor calculado',
  estimated_range: 'Estimativa',
  null: 'Sem resultado',
  unavailable: 'Ainda sem dado',
  suppressed: 'Dado protegido',
  not_applicable: 'Não se aplica',
})

const PNE_STATUS_LABELS: Readonly<Record<CenariosEducacaoPneStatus, string>> = Object.freeze({
  SUPPORTED: 'Pode ajudar',
  PRESSURED: 'Pode dificultar',
  AMBIGUOUS: 'Pode ajudar ou dificultar',
  INSUFFICIENT_EVIDENCE: 'Faltam dados',
})

const EXPOSURE_LABELS = Object.freeze({
  demographic: 'Número de estudantes',
  educational: 'Trajetória escolar',
  economic: 'Formação e trabalho',
  social: 'Condições sociais',
  territorial: 'Deslocamento e território',
})

const DRIVER_ICONS = Object.freeze({
  X_CLIMATE: MapPinned,
  X_TECHNOLOGY: GraduationCap,
  X_FISCAL: WalletCards,
  X_REGULATION: Network,
})

const ACTION_TYPES = ['NO_REGRET', 'CONTINGENT', 'REVERSIBLE_EXPERIMENT'] as const

const MONITORING_GROUPS: readonly {
  readonly id: string
  readonly title: string
  readonly description: string
  readonly cadences: readonly string[]
}[] = [
  {
    id: 'regular',
    title: 'Acompanhar durante o ano',
    description: 'Sinais que podem mudar em poucos meses e ajudam a perceber problemas cedo.',
    cadences: ['MONTHLY', 'QUARTERLY', 'SEMESTER'],
  },
  {
    id: 'annual',
    title: 'Revisar todos os anos',
    description: 'Informações que mostram mudanças mais lentas na procura, no acesso e nas trajetórias.',
    cadences: ['ANNUAL'],
  },
  {
    id: 'events',
    title: 'Registrar sempre que houver interrupção',
    description: 'Informações que só aparecem quando um evento afeta o atendimento educacional.',
    cadences: ['EVENT_BASED'],
  },
]

function SectionHeading({
  description,
  eyebrow,
  id,
  title,
}: {
  description: string
  eyebrow: string
  id: string
  title: string
}) {
  return (
    <div className="ce-section-heading">
      <span className="ce-eyebrow">{eyebrow}</span>
      <h2 id={id}>{title}</h2>
      <p>{description}</p>
    </div>
  )
}

function PneStatusBadge({ status }: { status: CenariosEducacaoPneStatus }) {
  return (
    <span className={'ce-pne-status ce-pne-status--' + status.toLowerCase()}>
      {PNE_STATUS_LABELS[status]}
    </span>
  )
}

function formatPercentage(value: number | null): string {
  return value === null ? 'não disponível' : decimalFormatter.format(value) + '%'
}

function formatGoalValue(value: string | null, unit: string | null): string {
  if (value === null) return 'não disponível'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return value
  if (unit === 'percent' || unit === '%') return decimalFormatter.format(numeric) + '%'
  return decimalFormatter.format(numeric)
}

function calculationNumber(driver: CenariosEducacaoCrossCuttingDriver, key: string): number | null {
  const value = driver.calculation?.[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function formatSchoolRatio(numerator: number, denominator: number, value: number | null): string {
  if (value === null) return 'Não disponível'
  return integerFormatter.format(numerator) + ' de ' + integerFormatter.format(denominator)
    + ' escolas (' + formatPercentage(value) + ')'
}

function formatMargin(value: number | null): string {
  return value === null ? 'não disponível' : decimalFormatter.format(value) + ' ponto percentual'
}

function AcronymGuide() {
  return (
    <aside className="ce-acronym-guide" aria-label="Siglas usadas na página">
      <strong>Siglas usadas</strong>
      <dl>
        {ACRONYM_DEFINITIONS.map(([short, long]) => (
          <div key={short}><dt>{short}</dt><dd>{long}</dd></div>
        ))}
      </dl>
    </aside>
  )
}

function DriverEvidence({ driver }: { driver: CenariosEducacaoCrossCuttingDriver }) {
  if (driver.driverId === 'X_CLIMATE') {
    return (
      <dl className="ce-driver-metrics">
        <div>
          <dt>Registros oficiais de eventos na região</dt>
          <dd>{integerFormatter.format(calculationNumber(driver, 'uniqueRegisteredOrRecognizedEventProtocols') ?? 0)}</dd>
        </div>
        <div>
          <dt>Municípios com pelo menos um registro</dt>
          <dd>{integerFormatter.format(calculationNumber(driver, 'municipalitiesWithEvent') ?? 0)} de 10</dd>
        </div>
        <div>
          <dt>Registros de Nova Santa Rita</dt>
          <dd>{integerFormatter.format(calculationNumber(driver, 'novaSantaRitaUniqueEventProtocols') ?? 0)}</dd>
        </div>
      </dl>
    )
  }

  if (driver.driverId === 'X_TECHNOLOGY') {
    return (
      <div className="ce-driver-technology">
        {driver.metrics?.map((metric) => (
          <article key={metric.metricId}>
            <strong>{metric.label}</strong>
            <dl>
              <div>
                <dt>Vale do Sinos</dt>
                <dd>{formatSchoolRatio(metric.region.numerator, metric.region.denominator, metric.region.valueRaw)}</dd>
              </div>
              <div>
                <dt>Nova Santa Rita</dt>
                <dd>{formatSchoolRatio(metric.novaSantaRita.numerator, metric.novaSantaRita.denominator, metric.novaSantaRita.valueRaw)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    )
  }

  if (driver.driverId === 'X_FISCAL') {
    return (
      <dl className="ce-driver-metrics">
        <div>
          <dt>Menor margem entre os municípios</dt>
          <dd>{formatMargin(calculationNumber(driver, 'minimumMarginPercentagePoints'))}</dd>
        </div>
        <div>
          <dt>Valor central entre os municípios</dt>
          <dd>{formatMargin(calculationNumber(driver, 'medianMarginPercentagePoints'))}</dd>
        </div>
        <div>
          <dt>Maior margem entre os municípios</dt>
          <dd>{formatMargin(calculationNumber(driver, 'maximumMarginPercentagePoints'))}</dd>
        </div>
        <div>
          <dt>Nova Santa Rita</dt>
          <dd>{formatMargin(calculationNumber(driver, 'novaSantaRitaMarginPercentagePoints'))}</dd>
        </div>
      </dl>
    )
  }

  return (
    <div className="ce-driver-gap" role="note">
      <CircleAlert aria-hidden="true" />
      <div>
        <strong>Ainda não há um dado público adequado</strong>
        <p>A informação disponível sobre transporte não mostra se existe cooperação educacional entre os municípios.</p>
      </div>
    </div>
  )
}

function DriverCard({ driver }: { driver: CenariosEducacaoCrossCuttingDriver }) {
  const Icon = DRIVER_ICONS[driver.driverId]
  const copy = DRIVER_PLAIN_LANGUAGE[driver.driverId]
  return (
    <article
      className={'ce-driver-card ce-driver-card--' + driver.maturity.toLowerCase()}
      data-driver-maturity={driver.maturity}
    >
      <div className="ce-driver-card__heading">
        <Icon aria-hidden="true" />
        <div>
          <span>{copy?.dataStatus ?? 'Situação dos dados'} · {driver.period}</span>
          <h3>{copy?.title ?? driver.label}</h3>
          <p>{copy?.introduction}</p>
        </div>
      </div>
      <DriverEvidence driver={driver} />
      <details className="ce-driver-details">
        <summary>Entenda o que o dado mostra e o que ainda falta</summary>
        <dl className="ce-driver-boundaries">
          <div><dt>O que mostra</dt><dd>{copy?.shows}</dd></div>
          <div><dt>O que não prova</dt><dd>{copy?.doesNotShow}</dd></div>
          <div><dt>Informação que ainda falta</dt><dd>{copy?.missing}</dd></div>
        </dl>
        <details className="ce-technical-note">
          <summary>Ver o texto técnico de referência</summary>
          <p><strong>Uso na análise:</strong> {driver.scenarioUse}</p>
          <p><strong>Limite:</strong> {driver.claimCeiling}</p>
          <p><strong>Lacuna:</strong> {driver.unresolvedGap}</p>
        </details>
      </details>
    </article>
  )
}

function ScenarioCard({
  active,
  onSelect,
  scenario,
}: {
  active: boolean
  onSelect: () => void
  scenario: CenariosEducacaoScenario
}) {
  const copy = SCENARIO_PLAIN_LANGUAGE[scenario.scenarioId]
  return (
    <article className={'ce-scenario-card ce-scenario-card--' + scenario.order + (active ? ' is-active' : '')}>
      <button
        aria-pressed={active}
        className="ce-scenario-card__button"
        onClick={onSelect}
        type="button"
      >
        <span className="ce-scenario-card__number">0{scenario.order}</span>
        <span className="ce-scenario-card__label">Possibilidade para 2036</span>
        <strong>{scenario.title}</strong>
        <p>{copy?.summary ?? scenario.summary}</p>
        <span>Ver o que pode acontecer</span>
      </button>
    </article>
  )
}

function SourceDescriptors({ bundle }: { bundle: CenariosEducacaoBundle }) {
  const descriptors = [
    ['Regras desta análise', bundle.sourceSnapshot.authoringContract],
    ['Diagnóstico de Vocações', bundle.sourceSnapshot.advancedBundle],
    ['Registro do diagnóstico', bundle.sourceSnapshot.advancedRegistry],
    ['Configuração regional', bundle.sourceSnapshot.regionConfig],
    ['Cadastro de municípios', bundle.sourceSnapshot.municipalityRegistry],
    ['Matriz do PNE de Nova Santa Rita', bundle.sourceSnapshot.focalPneMunicipalMatrix],
  ] as const
  return (
    <>
      <ul className="ce-source-list">
        {descriptors.map(([label, descriptor]) => (
          <li key={label}>
            <strong>{label}</strong>
            <code>{descriptor.path}</code>
            <span>Código de integridade {descriptor.sha256.slice(0, 16)}… · {integerFormatter.format(descriptor.byteSize)} bytes</span>
          </li>
        ))}
      </ul>
      <div className="ce-source-aggregate">
        <strong>Arquivos públicos dos dez municípios</strong>
        <span>30 arquivos: 10 educacionais, 10 financeiros e 10 matrizes do PNE</span>
        <code>SHA-256 {bundle.sourceSnapshot.regionalPublicInputs.sha256}</code>
      </div>
    </>
  )
}

const SIMPLE_DECISION_ICONS = [Building2, GraduationCap, UsersRound] as const

function SimpleSectionHeading({ id, number, title }: { id: string; number: string; title: string }) {
  return (
    <div className="ce-simple-section-heading">
      <span>{number}</span>
      <h2 id={id}>{title}</h2>
    </div>
  )
}

export function CenariosEducacaoSummaryReport({
  bundle,
  municipalityId,
}: {
  bundle: CenariosEducacaoBundle
  municipalityId: string | null
}) {
  const [selectedScenarioId, setSelectedScenarioId] = useState(bundle.scenarios[0].scenarioId)
  const selectedScenario = bundle.scenarios.find((scenario) => scenario.scenarioId === selectedScenarioId)
    ?? bundle.scenarios[0]
  const selectedScenarioCopy = SCENARIO_PLAIN_LANGUAGE[selectedScenario.scenarioId]
  const domainById = useMemo(
    () => new Map(bundle.domainRegistry.map((domain) => [domain.domainId, domain])),
    [bundle.domainRegistry],
  )
  const plainDomainSummaries = DOMAIN_PLAIN_SUMMARIES[selectedScenario.scenarioId] ?? {}
  const focalMunicipality = bundle.municipalities[0]
  const publicSignals = SIMPLE_PUBLIC_SIGNALS.map((copy) => ({
    copy,
    indicator: bundle.sentinelIndicators.find((indicator) => indicator.indicatorId === copy.indicatorId),
  })).filter((entry) => entry.indicator !== undefined)

  return (
    <div
      className="page-stack cenarios-educacao-page ce-simple-page"
      data-page-kind="summary"
      data-publication-status={bundle.publicationStatus}
      data-selected-municipality={municipalityId ?? 'none'}
    >
      <PnePageHeader
        actions={(
          <button className="ce-print-button" onClick={() => window.print()} type="button">
            <Printer aria-hidden="true" />
            Imprimir resumo
          </button>
        )}
        asideContent={null}
        asideLabel="Resumo da página"
        context={bundle.region.name}
        description="Estes quatro cenários não são previsões. Eles servem para conferir se o planejamento municipal continua funcionando quando o contexto muda."
        eyebrow="Cenários da Educação"
        title={'Como ' + focalMunicipality.municipalityName + ' pode se preparar para mudanças na educação'}
        variant="editorial"
      />

      <p className="ce-simple-lead">
        Antes de mudar vagas, cursos ou serviços, confirme quem será atendido, se as pessoas conseguem chegar e como manter o atendimento durante interrupções.
      </p>

      <main className="ce-simple-main">
        <section aria-labelledby="ce-simple-decisions" className="ce-simple-section">
          <SimpleSectionHeading id="ce-simple-decisions" number="01" title="Três decisões para tomar com mais segurança" />
          <div className="ce-simple-decision-grid">
            {SIMPLE_DECISION_PRIORITIES.map((decision, index) => {
              const Icon = SIMPLE_DECISION_ICONS[index]
              return (
                <article data-decision-priority={decision.id} key={decision.id}>
                  <Icon aria-hidden="true" />
                  <h3>{decision.title}</h3>
                  <p>{decision.explanation}</p>
                </article>
              )
            })}
          </div>
        </section>

        <section aria-labelledby="ce-simple-scenarios" className="ce-simple-section">
          <SimpleSectionHeading id="ce-simple-scenarios" number="02" title="Escolha um cenário para entender melhor" />
          <p className="ce-simple-section-intro">
            Cada cenário mostra uma mudança possível e ajuda a testar decisões antes que o contexto mude.
          </p>
          <div className="ce-scenario-grid">
            {bundle.scenarios.map((scenario) => (
              <ScenarioCard
                active={scenario.scenarioId === selectedScenario.scenarioId}
                key={scenario.scenarioId}
                onSelect={() => setSelectedScenarioId(scenario.scenarioId)}
                scenario={scenario}
              />
            ))}
          </div>

          <section
            aria-labelledby="ce-simple-selected-scenario"
            className={'ce-scenario-detail ce-scenario-detail--' + selectedScenario.order}
          >
            <div className="ce-scenario-detail__hero">
              <div>
                <span className="ce-eyebrow">Cenário 0{selectedScenario.order}</span>
                <h3 id="ce-simple-selected-scenario">{selectedScenario.title}</h3>
                <p>{selectedScenarioCopy?.summary ?? selectedScenario.summary}</p>
              </div>
              <span className="ce-scenario-detail__status">Não é previsão</span>
            </div>

            <div className="ce-subsection-heading ce-subsection-heading--compact">
              <h3>Como este cenário pode se desenvolver</h3>
            </div>
            <ol className="ce-causal-chain">
              {(selectedScenarioCopy?.steps ?? selectedScenario.causalChain).map((step) => <li key={step}>{step}</li>)}
            </ol>

            <div className="ce-balance-grid">
              <article>
                <Compass aria-hidden="true" />
                <h4>O que pode ajudar</h4>
                <ul>{(selectedScenarioCopy?.opportunities ?? selectedScenario.opportunities).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article>
                <TriangleAlert aria-hidden="true" />
                <h4>O que pode dificultar</h4>
                <ul>{(selectedScenarioCopy?.risks ?? selectedScenario.risks).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article>
                <Route aria-hidden="true" />
                <h4>Escolhas difíceis</h4>
                <ul>{(selectedScenarioCopy?.difficultChoices ?? selectedScenario.tradeOffs).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
            </div>

            <div className="ce-subsection-heading ce-subsection-heading--compact">
              <h3>O que muda em seis áreas da educação</h3>
            </div>
            <div className="ce-domain-grid">
              {selectedScenario.domains.map((domain) => (
                <article className="ce-domain-card" data-scenario-domain={domain.domainId} key={domain.domainId}>
                  <div className="ce-domain-card__heading">
                    <span>{DOMAIN_PLAIN_LABELS[domain.domainId] ?? domainById.get(domain.domainId)?.label}</span>
                  </div>
                  <p>{plainDomainSummaries[domain.domainId] ?? domain.state}</p>
                </article>
              ))}
            </div>
          </section>
        </section>

        <section aria-labelledby="ce-simple-signals" className="ce-simple-section">
          <SimpleSectionHeading id="ce-simple-signals" number="03" title="Três informações públicas para revisar todo ano" />
          <div className="ce-simple-signal-grid">
            {publicSignals.map(({ copy, indicator }) => (
              <article
                data-availability={indicator?.availability}
                data-public-signal={copy.indicatorId}
                key={copy.indicatorId}
              >
                <CalendarRange aria-hidden="true" />
                <h3>{copy.title}</h3>
                <p>{copy.decisionUse}</p>
              </article>
            ))}
          </div>
          <aside className="ce-simple-data-gap" role="note">
            <CircleAlert aria-hidden="true" />
            <div>
              <h3>O que os dados públicos ainda não mostram</h3>
              <p>{SIMPLE_PUBLIC_DATA_GAP}</p>
            </div>
          </aside>
        </section>
      </main>

      <nav aria-label="Continuar a análise" className="ce-simple-links">
        <a href={bundle.diagnosticBridge.route}>
          <strong>Vocações da Região</strong>
          <span>Ver os números atuais</span>
        </a>
        <a href="#pne2026">
          <strong>Plano Nacional de Educação</strong>
          <span>Acompanhar as metas</span>
        </a>
        <a href="#cenarios-da-educacao-dados">
          <strong>Dados e critérios da análise</strong>
          <span>Conferir fontes e construção dos futuros</span>
        </a>
      </nav>
    </div>
  )
}

export function CenariosEducacaoReport({
  bundle,
  municipalityId,
}: {
  bundle: CenariosEducacaoBundle
  municipalityId: string | null
}) {
  const [selectedScenarioId, setSelectedScenarioId] = useState(bundle.scenarios[0].scenarioId)
  const selectedScenario = bundle.scenarios.find((scenario) => scenario.scenarioId === selectedScenarioId)
    ?? bundle.scenarios[0]
  const selectedScenarioCopy = SCENARIO_PLAIN_LANGUAGE[selectedScenario.scenarioId]
  const selectedMunicipality = bundle.municipalities[0]
  const municipalExposure = selectedMunicipality.scenarioExposures.find(
    (exposure) => exposure.scenarioId === selectedScenario.scenarioId,
  ) ?? selectedMunicipality.scenarioExposures[0]
  const municipalCopy = MUNICIPAL_PLAIN_LANGUAGE[selectedScenario.scenarioId]
  const pneAssessment = bundle.pneStressTest.scenarioAssessments.find(
    (assessment) => assessment.scenarioId === selectedScenario.scenarioId,
  ) ?? bundle.pneStressTest.scenarioAssessments[0]
  const factorById = useMemo(
    () => new Map(bundle.factorRegistry.map((factor) => [factor.factorId, factor])),
    [bundle.factorRegistry],
  )
  const domainById = useMemo(
    () => new Map(bundle.domainRegistry.map((domain) => [domain.domainId, domain])),
    [bundle.domainRegistry],
  )
  const clusterById = useMemo(
    () => new Map(bundle.pneStressTest.clusters.map((cluster) => [cluster.clusterId, cluster])),
    [bundle.pneStressTest.clusters],
  )
  const actionsById = useMemo(
    () => new Map(bundle.actions.map((action) => [action.actionId, action])),
    [bundle.actions],
  )
  const municipalLevers = municipalExposure.leverIds
    .map((actionId) => actionsById.get(actionId))
    .filter((action): action is CenariosEducacaoAction => action !== undefined)
  const plainDomainSummaries = DOMAIN_PLAIN_SUMMARIES[selectedScenario.scenarioId] ?? {}

  return (
    <div
      className="page-stack cenarios-educacao-page ce-technical-page"
      data-page-kind="technical"
      data-publication-status={bundle.publicationStatus}
      data-selected-municipality={municipalityId ?? 'none'}
    >
      <PnePageHeader
        actions={(
          <div className="ce-header-actions">
            <a className="ce-technical-return" href="#cenarios-da-educacao">
              <ArrowLeft aria-hidden="true" />
              Voltar ao resumo
            </a>
            <button className="ce-print-button" onClick={() => window.print()} type="button">
              <Printer aria-hidden="true" />
              Imprimir análise
            </button>
          </div>
        )}
        asideContent={(
          <>
            <span className="pne-page-header__aside-title">Consulta completa</span>
            <strong className="pne-page-header__aside-highlight">Fontes e critérios</strong>
            <dl className="pne-page-header__facts">
              <div><dt>Até</dt><dd>{bundle.horizons.scenarioHorizon}</dd></div>
              <div><dt>Próxima revisão</dt><dd>{bundle.horizons.checkpoint}</dd></div>
              <div><dt>Foco municipal</dt><dd>Nova Santa Rita</dd></div>
            </dl>
          </>
        )}
        asideLabel="Resumo da página"
        context={bundle.region.name + ' · ' + bundle.region.municipalityCount + ' municípios'}
        description="Análise completa para conferir fontes, construção dos quatro futuros, relação com o Plano Nacional de Educação, ações e sinais de acompanhamento."
        eyebrow="Cenários da Educação · consulta detalhada"
        title="Dados e critérios da análise"
        variant="editorial"
      />

      <div className="ce-pilot-banner ce-pilot-banner--validated" role="note">
        <ShieldCheck aria-hidden="true" />
        <div>
          <strong>Estas são possibilidades para apoiar o planejamento</strong>
          <p>Nenhuma delas é previsão ou é considerada mais provável. A página ajuda a pensar o que preparar, o que acompanhar e quando rever decisões.</p>
        </div>
      </div>

      <nav aria-label="Seções da página" className="ce-page-nav">
        <a href="#ce-como-ler">Como ler</a>
        <a href="#ce-mudancas">O que pode mudar</a>
        <a href="#ce-cenarios">4 futuros</a>
        <a href="#ce-municipio">Nova Santa Rita</a>
        <a href="#ce-pne">PNE e ações</a>
        <a href="#ce-sinais">O que acompanhar</a>
      </nav>

      <main className="ce-main">
        <section aria-labelledby="ce-como-ler" className="ce-section ce-bridge-section">
          <SectionHeading
            description="Os dados sobre a situação atual continuam em Vocações da Região. Aqui, eles servem apenas como ponto de partida para pensar diferentes futuros."
            eyebrow="01 · Comece por aqui"
            id="ce-como-ler"
            title="Como ler esta página"
          />
          <div className="ce-reading-guide">
            <article>
              <span>1</span>
              <h3>Conheça as quatro possibilidades</h3>
              <p>Elas mostram combinações diferentes de mudanças que podem afetar a educação até 2036.</p>
            </article>
            <article>
              <span>2</span>
              <h3>Escolha uma para explorar</h3>
              <p>Veja efeitos possíveis na região, em Nova Santa Rita e na execução do PNE.</p>
            </article>
            <article>
              <span>3</span>
              <h3>Use para preparar decisões</h3>
              <p>As ações e os sinais ajudam a decidir sem precisar adivinhar qual futuro acontecerá.</p>
            </article>
          </div>
          <div className="ce-bridge-card">
            <BookOpenCheck aria-hidden="true" />
            <div>
              <span>Onde está o retrato atual</span>
              <h3>{bundle.diagnosticBridge.canonicalSection}</h3>
              <p>Consulte ali as séries, os fatos e as relações já observadas. Esta página evita repetir esse conteúdo.</p>
              <a href={bundle.diagnosticBridge.route}>Abrir Vocações da Região</a>
            </div>
            <dl>
              <div><dt>Referências conferidas</dt><dd>{bundle.diagnosticBridge.resolvedEvidenceRefCount}</dd></div>
              <div><dt>Trechos do diagnóstico copiados</dt><dd>{bundle.diagnosticBridge.copiedDiagnosticAssertions}</dd></div>
              <div><dt>Repetições longas encontradas</dt><dd>{bundle.diagnosticBridge.deDuplicationAudit.duplicateCount}</dd></div>
            </dl>
          </div>
          <AcronymGuide />
        </section>

        <section aria-labelledby="ce-mudancas" className="ce-section">
          <SectionHeading
            description="A análise parte de cinco perguntas simples. Cada futuro combina respostas diferentes para elas."
            eyebrow="02 · O que pode mudar"
            id="ce-mudancas"
            title="Cinco perguntas sobre o que pode mudar a educação na região"
          />
          <div className="ce-factor-grid">
            {bundle.factorRegistry.map((factor) => {
              const copy = FACTOR_PLAIN_LANGUAGE[factor.factorId]
              return (
                <article key={factor.factorId}>
                  <span>Pergunta para o planejamento</span>
                  <h3>{copy?.title ?? factor.label}</h3>
                  <p>{copy?.question ?? factor.uncertainty}</p>
                </article>
              )
            })}
          </div>
          <div className="ce-subsection-heading">
            <span className="ce-eyebrow">Informações que ajudam a acompanhar essas mudanças</span>
            <h3>Quatro temas presentes em todos os futuros</h3>
            <p>Os cartões mostram quanto dado público confiável existe hoje, o que ele ajuda a entender e o que ainda não pode ser respondido.</p>
          </div>
          <div className="ce-driver-grid">
            {bundle.crossCuttingDrivers.map((driver) => <DriverCard driver={driver} key={driver.driverId} />)}
          </div>
        </section>

        <section aria-labelledby="ce-cenarios" className="ce-section">
          <SectionHeading
            description="São histórias possíveis, não previsões. Nenhuma tem mais peso que as outras."
            eyebrow="03 · Quatro possibilidades"
            id="ce-cenarios"
            title="Escolha um futuro para entender melhor"
          />
          <div className="ce-scenario-grid">
            {bundle.scenarios.map((scenario) => (
              <ScenarioCard
                active={scenario.scenarioId === selectedScenario.scenarioId}
                key={scenario.scenarioId}
                onSelect={() => setSelectedScenarioId(scenario.scenarioId)}
                scenario={scenario}
              />
            ))}
          </div>

          <section
            aria-labelledby="ce-selected-scenario"
            className={'ce-scenario-detail ce-scenario-detail--' + selectedScenario.order}
          >
            <div className="ce-scenario-detail__hero">
              <div>
                <span className="ce-eyebrow">Possibilidade 0{selectedScenario.order}</span>
                <h3 id="ce-selected-scenario">{selectedScenario.title}</h3>
                <p>{selectedScenarioCopy?.summary ?? selectedScenario.summary}</p>
              </div>
              <span className="ce-scenario-detail__status">Não é previsão</span>
            </div>

            <div className="ce-subsection-heading ce-subsection-heading--compact">
              <h3>Como essa possibilidade pode se desenvolver</h3>
            </div>
            <ol className="ce-causal-chain">
              {(selectedScenarioCopy?.steps ?? selectedScenario.causalChain).map((step) => <li key={step}>{step}</li>)}
            </ol>

            <div className="ce-balance-grid">
              <article>
                <Compass aria-hidden="true" />
                <h4>O que pode ajudar</h4>
                <ul>{(selectedScenarioCopy?.opportunities ?? selectedScenario.opportunities).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article>
                <TriangleAlert aria-hidden="true" />
                <h4>O que pode dificultar</h4>
                <ul>{(selectedScenarioCopy?.risks ?? selectedScenario.risks).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article>
                <Route aria-hidden="true" />
                <h4>Escolhas difíceis</h4>
                <ul>{(selectedScenarioCopy?.difficultChoices ?? selectedScenario.tradeOffs).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
            </div>

            <div className="ce-subsection-heading ce-subsection-heading--compact">
              <h3>O que muda em seis áreas da educação</h3>
            </div>
            <div className="ce-domain-grid">
              {selectedScenario.domains.map((domain) => (
                <article className="ce-domain-card" data-scenario-domain={domain.domainId} key={domain.domainId}>
                  <div className="ce-domain-card__heading">
                    <span>{DOMAIN_PLAIN_LABELS[domain.domainId] ?? domainById.get(domain.domainId)?.label}</span>
                  </div>
                  <p>{plainDomainSummaries[domain.domainId] ?? domain.state}</p>
                </article>
              ))}
            </div>

            <details className="ce-scenario-technical-details">
              <summary>Ver como esta possibilidade foi montada</summary>
              <p>Cada futuro combina uma situação diferente para as cinco perguntas apresentadas no início da página.</p>
              <div className="ce-table-scroll" tabIndex={0} aria-label="Combinação de fatores no futuro selecionado">
                <table className="ce-state-matrix">
                  <caption>Combinação usada nesta possibilidade</caption>
                  <thead><tr><th scope="col">Pergunta</th><th scope="col">Situação</th><th scope="col">Descrição técnica</th></tr></thead>
                  <tbody>
                    {Object.entries(selectedScenario.configurationStates).map(([factorId, stateId]) => {
                      const factor = factorById.get(factorId)
                      const state = factor?.states.find((candidate) => candidate.stateId === stateId)
                      return (
                        <tr key={factorId}>
                          <th scope="row">{FACTOR_PLAIN_LANGUAGE[factorId]?.title ?? factor?.label}</th>
                          <td>{state?.label}</td>
                          <td>{state?.definition}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <div className="ce-technical-domain-list">
                {selectedScenario.domains.map((domain) => (
                  <article key={domain.domainId}>
                    <h4>{domainById.get(domain.domainId)?.label}</h4>
                    <p>{domain.state}</p>
                    <span>{domain.mechanism}</span>
                  </article>
                ))}
              </div>
            </details>

            <details className="ce-distribution-details">
              <summary>Ver quem pode sentir mais os efeitos</summary>
              <div className="ce-distribution-grid">
                {selectedScenario.distributionalEffects.map((effect) => (
                  <article key={effect.publicId}>
                    <UsersRound aria-hidden="true" />
                    <h4>{effect.publicLabel}</h4>
                    <p>{effect.exposure}</p>
                    <dl>
                      <div><dt>Possível benefício</dt><dd>{effect.potentialUpside}</dd></div>
                      <div><dt>Possível dificuldade</dt><dd>{effect.potentialDownside}</dd></div>
                      <div><dt>Pergunta que precisa ser respondida</dt><dd>{effect.equityQuestion}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            </details>
          </section>
        </section>

        <section aria-labelledby="ce-municipio" className="ce-section ce-municipal-section">
          <div className="ce-municipal-section__heading">
            <div>
              <span className="ce-eyebrow">04 · Nova Santa Rita</span>
              <h2 id="ce-municipio">O que “{selectedScenario.title}” pode significar para Nova Santa Rita</h2>
              <p>Esta leitura mostra possíveis efeitos locais. Ela não afirma que o município já está vivendo esse futuro.</p>
            </div>
            <span className="ce-municipal-seal"><Building2 aria-hidden="true" /> IBGE 4313375</span>
          </div>
          <article className="ce-municipal-headline">
            <strong>{municipalCopy?.headline ?? municipalExposure.headline}</strong>
          </article>
          <div className="ce-exposure-grid">
            {Object.entries(municipalCopy?.exposures ?? municipalExposure.exposures).map(([dimension, content]) => (
              <article key={dimension}>
                <span>{EXPOSURE_LABELS[dimension as keyof typeof EXPOSURE_LABELS]}</span>
                <p>{content}</p>
              </article>
            ))}
          </div>
          <div className="ce-municipal-decision-grid">
            <article>
              <BriefcaseBusiness aria-hidden="true" />
              <h3>Ações que merecem atenção</h3>
              <ul>{municipalLevers.map((action) => <li key={action.actionId}>{action.title}</li>)}</ul>
            </article>
            <article>
              <Network aria-hidden="true" />
              <h3>O que depende da região</h3>
              <ul>{(municipalCopy?.regionalNeeds ?? municipalExposure.regionalDependencies).map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
          </div>
          <details className="ce-small-number-note">
            <summary><CircleAlert aria-hidden="true" /> Por que números pequenos exigem cuidado?</summary>
            <p>{selectedMunicipality.smallNumberCaveat}</p>
          </details>
        </section>

        <section aria-labelledby="ce-pne" className="ce-section ce-pne-section">
          <SectionHeading
            description="As metas do Plano Nacional de Educação continuam as mesmas. O que muda é a facilidade ou a dificuldade de colocá-las em prática."
            eyebrow="05 · PNE e ações"
            id="ce-pne"
            title="Como este futuro pode afetar o Plano Nacional de Educação"
          />
          <div className="ce-pne-selected">
            <div>
              <span className="ce-eyebrow">Possibilidade escolhida</span>
              <h3>{selectedScenario.title}</h3>
            </div>
            <div className="ce-pne-selected__grid">
              {pneAssessment.impacts.map((impact) => (
                <article key={impact.clusterId}>
                  <PneStatusBadge status={impact.status} />
                  <h4>{clusterById.get(impact.clusterId)?.label}</h4>
                  <p>{impact.mechanism}</p>
                  <span>Ação para considerar: {actionsById.get(impact.response)?.title}</span>
                </article>
              ))}
            </div>
          </div>
          <details className="ce-pne-all-futures">
            <summary>Comparar os quatro futuros no PNE</summary>
            <div className="ce-table-scroll" tabIndex={0} aria-label="Comparação do PNE nos quatro futuros">
              <table className="ce-pne-matrix">
                <caption>Como as mesmas metas podem ser favorecidas ou pressionadas em cada possibilidade.</caption>
                <thead><tr><th scope="col">Tema do PNE</th>{bundle.scenarios.map((scenario) => <th scope="col" key={scenario.scenarioId}>{scenario.shortLabel}</th>)}</tr></thead>
                <tbody>
                  {bundle.pneStressTest.clusters.map((cluster) => (
                    <tr key={cluster.clusterId}>
                      <th scope="row"><strong>{cluster.label}</strong><span>{cluster.goalIds.join(' · ')}</span></th>
                      {bundle.pneStressTest.scenarioAssessments.map((assessment) => {
                        const impact = assessment.impacts.find((candidate) => candidate.clusterId === cluster.clusterId)
                        return <td key={assessment.scenarioId}>{impact ? <PneStatusBadge status={impact.status} /> : '—'}</td>
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <details className="ce-goal-baseline">
            <summary>Ver os valores atuais de Nova Santa Rita usados nesta leitura</summary>
            <div className="ce-goal-grid">
              {bundle.pneStressTest.goalBaseline.map((goal) => (
                <article key={goal.goalId}>
                  <span>{goal.goalId} · {AVAILABILITY_LABELS[goal.availability]}</span>
                  <h4>{goal.title}</h4>
                  <strong>{formatGoalValue(goal.valueRaw, goal.unit)}</strong>
                  <p>Referência: {formatGoalValue(goal.referenceRaw, goal.unit)}{goal.year ? ' · ' + goal.year : ''}</p>
                </article>
              ))}
            </div>
          </details>

          <div className="ce-subsection-heading">
            <span className="ce-eyebrow">O que gestores podem considerar</span>
            <h3 id="ce-decisoes">Ações organizadas pelo momento de decisão</h3>
            <p>As ações não são recomendações automáticas. Cada uma deve ser avaliada conforme a situação observada.</p>
          </div>
          <div className="ce-action-groups">
            {ACTION_TYPES.map((type) => {
              const actions = bundle.actions.filter((action) => action.type === type)
              const copy = ACTION_TYPE_PLAIN_LANGUAGE[type]
              return (
                <details className="ce-action-group" key={type}>
                  <summary>
                    <span><strong>{copy.title}</strong><small>{copy.description}</small></span>
                    <b>{actions.length} ações</b>
                  </summary>
                  <div>
                    {actions.map((action) => (
                      <article key={action.actionId}>
                        <span>{AUTHORITY_PLAIN_LABELS[action.authority]}</span>
                        <h4>{action.title}</h4>
                        <p>{action.description}</p>
                        <dl>
                          <div><dt>Quando considerar</dt><dd>{action.trigger}</dd></div>
                          <div><dt>Se for preciso mudar depois</dt><dd>{action.lockInRisk}</dd></div>
                        </dl>
                      </article>
                    ))}
                  </div>
                </details>
              )
            })}
          </div>
        </section>

        <section aria-labelledby="ce-sinais" className="ce-section ce-sentinel-section">
          <SectionHeading
            description={'Estes sinais ajudam a perceber mudanças e rever o planejamento em ' + bundle.horizons.checkpoint + '. Eles não escolhem um futuro automaticamente.'}
            eyebrow="06 · O que acompanhar"
            id="ce-sinais"
            title="Sinais que ajudam a perceber mudanças cedo"
          />
          <div className="ce-monitoring-groups">
            {MONITORING_GROUPS.map((group) => {
              const indicators = bundle.sentinelIndicators.filter((indicator) => group.cadences.includes(indicator.cadence))
              return (
                <details className="ce-monitoring-group" key={group.id} open={group.id === 'regular'}>
                  <summary>
                    <span><strong>{group.title}</strong><small>{group.description}</small></span>
                    <b>{indicators.length} sinais</b>
                  </summary>
                  <div className="ce-sentinel-grid">
                    {indicators.map((indicator) => {
                      const copy = SENTINEL_PLAIN_LANGUAGE[indicator.indicatorId]
                      return (
                        <article className={'ce-sentinel-card ce-sentinel-card--' + indicator.availability} key={indicator.indicatorId}>
                          <div>
                            <span>{AVAILABILITY_LABELS[indicator.availability]}</span>
                            <small>{CADENCE_PLAIN_LABELS[indicator.cadence] ?? indicator.cadence}</small>
                          </div>
                          <h3>{copy?.label ?? indicator.label}</h3>
                          <p>{copy?.use ?? indicator.decisionUse}</p>
                        </article>
                      )
                    })}
                  </div>
                </details>
              )
            })}
          </div>
        </section>

        <section aria-labelledby="ce-metodo" className="ce-section ce-method-section">
          <SectionHeading
            description="Esta parte é opcional. Abra os blocos abaixo se quiser conferir fontes, regras de cálculo e detalhes da construção dos futuros."
            eyebrow="Para quem quiser conferir"
            id="ce-metodo"
            title="Sobre os dados e o método"
          />
          <div className="ce-method-summary">
            <article><BookOpenCheck aria-hidden="true" /><strong>{bundle.diagnosticBridge.resolvedEvidenceRefCount} referências conferidas</strong><span>Todas apontam para o diagnóstico atual.</span></article>
            <article><Network aria-hidden="true" /><strong>4 futuros diferentes</strong><span>Cada um combina mudanças de forma própria.</span></article>
            <article><CalendarRange aria-hidden="true" /><strong>Revisão em {bundle.horizons.checkpoint}</strong><span>Momento para atualizar a leitura.</span></article>
            <article><ShieldCheck aria-hidden="true" /><strong>30 arquivos públicos</strong><span>Todos já estavam disponíveis localmente.</span></article>
          </div>
          <details className="ce-method-details">
            <summary>Ver fontes e códigos de integridade</summary>
            <p>Versão do conteúdo: <code>{bundle.contentVersion}</code></p>
            <SourceDescriptors bundle={bundle} />
          </details>
          <details className="ce-method-details">
            <summary>Ver como os quatro futuros foram diferenciados</summary>
            <p>Diferença técnica mínima entre as combinações: {bundle.morphologicalField.minimumObservedPairwiseHammingDistance} de 5 fatores.</p>
            <p>{bundle.methodology.selectionMethod}</p>
            <p>{bundle.methodology.aa4Role}</p>
            <p>{bundle.morphologicalField.blindSubstitutabilityReview.method}</p>
          </details>
          <details className="ce-method-details">
            <summary>Ver limites de uso desta análise</summary>
            <p>{bundle.methodology.notForecast}</p>
            <p>{bundle.methodology.independentReviewPolicy}</p>
            <p>{bundle.sourceGovernance.downloadPolicy}</p>
          </details>
        </section>
      </main>
    </div>
  )
}

export function CenariosEducacaoPage({ municipalityId }: { municipalityId: string | null }) {
  const state = useCenariosEducacaoBundle()
  if (state.status === 'loading') return <LoadingState message="Preparando o resumo para decisão…" />
  if (state.status === 'error') {
    return (
      <ErrorState
        message={state.error + ' A análise de Vocações continua disponível; nenhum conteúdo incompleto foi exibido.'}
        title="Não foi possível preparar este resumo."
      />
    )
  }
  return <CenariosEducacaoSummaryReport bundle={state.data} municipalityId={municipalityId} />
}

export function CenariosEducacaoDadosPage({ municipalityId }: { municipalityId: string | null }) {
  const state = useCenariosEducacaoBundle()
  if (state.status === 'loading') return <LoadingState message="Preparando dados e critérios da análise…" />
  if (state.status === 'error') {
    return (
      <ErrorState
        message={state.error + ' O resumo e a análise de Vocações continuam disponíveis; nenhum conteúdo incompleto foi exibido.'}
        title="Não foi possível conferir os dados e critérios."
      />
    )
  }
  return <CenariosEducacaoReport bundle={state.data} municipalityId={municipalityId} />
}
