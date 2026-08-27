import { buildAppHash } from '../../app/appHash.js'
import { ContentState } from '../../components/ContentState'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { loadEducationMunicipio } from '../../data/educationData.js'
import { useMunicipioMatriz } from '../../hooks/useMunicipioMatriz.js'
import { useVocacoesRegiao } from '../../hooks/useVocacoesRegiao'
import { useAsyncData } from '../../utils/useAsyncData.js'
import {
  buildMatrizTerritorialContext,
} from './matrizTerritorialContext.js'
import type { MatrizTerritorialContext } from './matrizTerritorialContext.js'
import {
  buildMatrizEducationContext,
  resolveMatrizEducationContextFact,
} from './matrizEducationContext.js'
import type { MatrizEducationContext } from './matrizEducationContext.js'
import { matrizFrenteKey, resolveMatrizFrentes } from './matrizFrentes.js'
import { resolveMatrizGoalInsight } from './matrizInsights.js'
import type {
  MatrizDistanceToTarget,
  MatrizDocument,
  MatrizPeerDeviation,
  MatrizPriorityGoal,
} from './matrizTypes.js'
import {
  formatMatrizGoalSituation,
  formatMatrizReferenceDate,
  MATRIZ_DISTANCE_LABEL,
  MATRIZ_PEER_DEVIATION_LABEL,
  MATRIZ_SEVERITY_LABEL,
  matrizPeerBenchmarkComparison,
  matrizPriorityPeerSummary,
  matrizTrendReading,
  resolveMatrizContextReadings,
  resolveMatrizNetworkConcentrationReading,
} from './matrizVocabulary.js'
import '../../styles/matriz-page.css'

function plural(value: number, singular: string, pluralText: string): string {
  return `${value} ${value === 1 ? singular : pluralText}`
}

const MATRIZ_DISTANCE_ORDER: readonly MatrizDistanceToTarget[] = [
  'far_from_target',
  'below_target',
  'near_or_at_target',
]

const MATRIZ_PEER_ORDER: readonly MatrizPeerDeviation[] = [
  'much_worse_than_peers',
  'worse_than_peers',
  'in_line_with_peers',
  'better_than_peers',
]

const MATRIZ_PEER_MATRIX_LABEL: Readonly<Record<MatrizPeerDeviation, string>> = Object.freeze({
  much_worse_than_peers: 'Entre as que mais precisam avançar',
  worse_than_peers: 'Abaixo da maioria',
  in_line_with_peers: 'Na média',
  better_than_peers: 'Acima da maioria',
})

function focusMatrizGoal(goalIndex: number): void {
  if (typeof window === 'undefined') return
  const target = document.getElementById('matriz-goal-' + goalIndex)
  if (!target) return
  target.scrollIntoView({
    behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    block: 'start',
  })
  target.focus({ preventScroll: true })
}

function MatrizPriorityOverview({ matriz }: { matriz: MatrizDocument }) {
  const indexedGoals = matriz.priorityGoals.map((goal, goalIndex) => ({ goal, goalIndex }))
  if (indexedGoals.length === 0) return null

  const distanceBands = MATRIZ_DISTANCE_ORDER.filter((distance) => (
    indexedGoals.some(({ goal }) => goal.severity.distanceToTarget === distance)
  ))
  const peerBands = MATRIZ_PEER_ORDER.filter((peerDeviation) => (
    indexedGoals.some(({ goal }) => goal.severity.peerDeviation === peerDeviation)
  ))

  return (
    <section aria-labelledby="matriz-priority-title" className="matriz-panorama">
      <header className="matriz-panorama__head">
        <h2 id="matriz-priority-title">Matriz comparativa das metas</h2>
        <p>Distância da referência × situação entre cidades parecidas.</p>
      </header>
      <div className="matriz-priority-table-wrap">
        <table className="matriz-priority-table">
          <caption className="u-sr-only">
            Metas prioritárias organizadas pela distância da referência e pela situação entre cidades parecidas.
          </caption>
          <thead>
            <tr>
              <th className="matriz-priority-table__corner" rowSpan={2} scope="col">
                Distância da referência
              </th>
              <th className="matriz-priority-table__axis" colSpan={peerBands.length} scope="colgroup">
                Situação entre cidades parecidas
              </th>
            </tr>
            <tr>
              {peerBands.map((peerDeviation) => (
                <th
                  aria-label={MATRIZ_PEER_DEVIATION_LABEL[peerDeviation]}
                  className="matriz-priority-table__peer"
                  data-peer={peerDeviation}
                  key={peerDeviation}
                  scope="col"
                >
                  {MATRIZ_PEER_MATRIX_LABEL[peerDeviation]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {distanceBands.map((distance) => (
              <tr className="matriz-priority-table__row" data-distance={distance} key={distance}>
                <th scope="row">{MATRIZ_DISTANCE_LABEL[distance]}</th>
                {peerBands.map((peerDeviation) => {
                  const cellGoals = indexedGoals.filter(({ goal }) => (
                    goal.severity.distanceToTarget === distance
                    && goal.severity.peerDeviation === peerDeviation
                  ))
                  return (
                    <td
                      className={cellGoals.length === 0 ? 'is-empty' : undefined}
                      data-peer={peerDeviation}
                      data-peer-label={MATRIZ_PEER_MATRIX_LABEL[peerDeviation]}
                      key={peerDeviation}
                    >
                      {cellGoals.map(({ goal, goalIndex }) => (
                        <button
                          className="matriz-priority-card"
                          key={goal.goalId}
                          onClick={() => focusMatrizGoal(goalIndex)}
                          type="button"
                        >
                          <span className="matriz-priority-card__title">{goal.title}</span>
                          <span className="matriz-priority-card__situation">{formatMatrizGoalSituation(goal)}</span>
                        </button>
                      ))}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function MatrizGoalActions({
  educationContext,
  goal,
  matriz,
}: {
  educationContext: MatrizEducationContext | null
  goal: MatrizPriorityGoal
  matriz: MatrizDocument
}) {
  const insight = resolveMatrizGoalInsight(goal.goalId)
  if (!insight) return null

  const goals = [...matriz.priorityGoals, ...matriz.goalsWithoutOwnCause]
  const frentes = resolveMatrizFrentes(goal.goalId)

  return (
    <div className="matriz-goal__actions">
      <header className="matriz-goal__actions-head">
        <h3>Caminhos para avançar</h3>
        <p>{insight.focus}</p>
      </header>
      <div className="matriz-frente-list">
        {frentes.map((frente) => {
          const mechanism = insight.mechanisms.find((candidate) => (
            candidate.id === frente.mechanismId
          ))
          if (!mechanism) return null

          const frontKey = matrizFrenteKey(goal.goalId, frente.id)
          const reading = mechanism.measure
            ? resolveMatrizContextReadings(matriz, [mechanism.measure])[0]
            : null
          const relatedGoal = mechanism.relatedGoal
            ? goals.find((candidate) => candidate.goalId === mechanism.relatedGoal?.goalId)
            : null
          const educationFact = mechanism.educationContext
            ? resolveMatrizEducationContextFact(educationContext, mechanism.educationContext)
            : null

          return (
            <article className="matriz-frente" key={frontKey}>
              {frente.startHere ? (
                <span className="matriz-frente__start">Comece por aqui</span>
              ) : null}
              <h4 className="matriz-frente__title">{frente.title}</h4>
              <p className="matriz-frente__explanation">{mechanism.explanation}</p>
              {relatedGoal && mechanism.relatedGoal ? (
                <div className="matriz-frente__fact">
                  <strong>{relatedGoal.title}: {formatMatrizGoalSituation(relatedGoal)}</strong>
                  <p>{mechanism.relatedGoal.use}</p>
                </div>
              ) : null}
              {reading ? (
                <div className="matriz-frente__fact">
                  <strong>{reading.label}: {reading.display} ({reading.period})</strong>
                  <p>{reading.use}</p>
                  {reading.peerBenchmarkComparison && reading.peerUse ? (
                    <p>{reading.peerBenchmarkComparison}. {reading.peerUse}</p>
                  ) : null}
                </div>
              ) : null}
              {educationFact ? (
                <div className="matriz-frente__fact">
                  <strong>{educationFact.label}: {educationFact.display} ({educationFact.period})</strong>
                  <p>{educationFact.use}</p>
                </div>
              ) : null}
              <p className="matriz-frente__verification">
                <strong>Antes de agir, confira:</strong> {mechanism.verification}
              </p>
              <div className="matriz-frente__milestone">
                <span>Resultado esperado</span>
                <p>{frente.implementationMilestone}</p>
              </div>
              <div className="matriz-frente__monitoring">
                <span>Sinal de acompanhamento</span>
                <p>{frente.monitoringSignal}</p>
              </div>
              <details className="matriz-frente__more">
                <summary>Como avançar e onde buscar apoio</summary>
                <div className="matriz-frente__section">
                  <h5>Etapas sugeridas</h5>
                  <ul>
                    {frente.steps.map((step, index) => (
                      <li key={`${frontKey}-step-${index}`}>{step}</li>
                    ))}
                  </ul>
                </div>
                <div className="matriz-frente__section">
                  <h5>Apoio federal</h5>
                  <ul className="matriz-frente__programs">
                    {frente.programs.map((program, index) => (
                      <li key={`${frontKey}-program-${index}`}>
                        {program.url ? (
                          <a href={program.url} rel="noreferrer" target="_blank">{program.name}</a>
                        ) : <strong>{program.name}</strong>}
                        <span>{program.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                {frente.bridge ? (
                  <div className="matriz-frente__bridge">
                    <h5>Informações relacionadas no painel</h5>
                    <a href={buildAppHash(frente.bridge.page, {
                      ...frente.bridge.params,
                      municipio: matriz.municipality.ibge7,
                    })}>
                      {frente.bridge.label}
                    </a>
                  </div>
                ) : null}
                <p className="matriz-frente__legal">Base: {frente.legalRef}</p>
              </details>
            </article>
          )
        })}
      </div>
    </div>
  )
}

function MatrizGoalBlock({
  educationContext,
  goal,
  goalIndex,
  matriz,
}: {
  educationContext: MatrizEducationContext | null
  goal: MatrizPriorityGoal
  goalIndex: number
  matriz: MatrizDocument
}) {
  const trendReading = matrizTrendReading(goal)
  const networkConcentrationReading = resolveMatrizNetworkConcentrationReading(goal)
  return (
    <section
      aria-labelledby={`matriz-goal-title-${goalIndex}`}
      className="matriz-goal"
      id={'matriz-goal-' + goalIndex}
      tabIndex={-1}
    >
      <header className="matriz-goal__head">
        <div>
          <h2 id={`matriz-goal-title-${goalIndex}`}>{goal.title}</h2>
          <p className="matriz-goal__situation">
            {formatMatrizGoalSituation(goal)} · {MATRIZ_DISTANCE_LABEL[goal.severity.distanceToTarget]}. {matrizPeerBenchmarkComparison(goal, matriz.municipality.uf)}.
          </p>
          {trendReading ? <p className="matriz-goal__trend">{trendReading}</p> : null}
          {networkConcentrationReading ? (
            <p className="matriz-goal__network">{networkConcentrationReading}</p>
          ) : null}
        </div>
        <span className={`matriz-severity matriz-severity--${goal.severity.level}`}>
          {MATRIZ_SEVERITY_LABEL[goal.severity.level]}
        </span>
      </header>

      <MatrizGoalActions educationContext={educationContext} goal={goal} matriz={matriz} />
    </section>
  )
}

function HonestyBlocks({ matriz }: { matriz: MatrizDocument }) {
  const goalsById = new Map(matriz.priorityGoals.map((goal) => [goal.goalId, goal]))

  return (
    <section aria-label="Limites e contrapontos da matriz" className="matriz-honesty">
      <details>
        <summary>Outras metas abaixo do esperado <span>{matriz.goalsWithoutOwnCause.length}</span></summary>
        {matriz.goalsWithoutOwnCause.length > 0 ? (
          <ul className="matriz-related-goals">
            {matriz.goalsWithoutOwnCause.map((goal) => {
              const destinations = goal.causesShownIn
                .map((goalId) => goalsById.get(goalId)?.title)
                .filter((title): title is string => Boolean(title))
              return (
                <li key={goal.goalId}>
                  <strong>{goal.title}</strong>
                  <span>{formatMatrizGoalSituation(goal)} · {MATRIZ_SEVERITY_LABEL[goal.severity.level]}</span>
                  {destinations.length > 0 ? (
                    <small>As frentes ligadas a esta meta aparecem em: {destinations.join(', ')}.</small>
                  ) : null}
                </li>
              )
            })}
          </ul>
        ) : <p>Não há outras metas abaixo do esperado nesta leitura.</p>}
      </details>

      <details>
        <summary>Onde o município está bem <span>{matriz.summary.goalsOnTrack.length}</span></summary>
        {matriz.summary.goalsOnTrack.length > 0 ? (
          <p>{plural(matriz.summary.goalsOnTrack.length, 'meta está', 'metas estão')} com os resultados esperados alcançados.</p>
        ) : <p>A leitura atual ainda não reúne uma meta inteira com todos os resultados esperados alcançados.</p>}
      </details>
    </section>
  )
}

/*
 * Bloco ponte PNE → Vocações. Aparece só quando a região do município tem
 * pacote regional publicado; sem ele, o bloco não existe — fail-closed por
 * ausência, sem seção vazia e sem erro. A linguagem é a do módulo de contexto:
 * "a região do município apresenta…", nunca "isto explica o município".
 */
function MatrizTerritorialContextBlock({
  territorialContext,
}: {
  territorialContext: MatrizTerritorialContext
}) {
  return (
    <section aria-labelledby="matriz-territorio-title" className="matriz-territorio">
      <header className="matriz-territorio__head">
        <h2 id="matriz-territorio-title">Contexto territorial da região</h2>
        <p>{territorialContext.intro}</p>
      </header>
      <ul className="matriz-territorio__list">
        {territorialContext.readings.map((reading) => (
          <li
            className={reading.reading ? 'matriz-territorio__item matriz-territorio__item--with-reading' : 'matriz-territorio__item'}
            key={reading.title}
          >
            {reading.reading ? (
              <div className="matriz-territorio__reading-row">
                <p className="matriz-territorio__reading">{reading.reading}</p>
                {reading.correlationStrength ? (
                  <span
                    aria-hidden="true"
                    className="matriz-territorio__strength"
                    data-strength={reading.correlationStrength}
                  >
                    <i />
                    <i />
                    <i />
                  </span>
                ) : null}
              </div>
            ) : null}
            <div className="matriz-territorio__entities">
              <strong className="matriz-territorio__entity matriz-territorio__entity--education">
                <i aria-hidden="true" className="matriz-territorio__entity-mark" />
                {reading.title}
              </strong>
              {reading.factors ? (
                <span className="matriz-territorio__entity matriz-territorio__entity--territory">
                  <i aria-hidden="true" className="matriz-territorio__entity-mark" />
                  {reading.factors}
                </span>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
      <a className="matriz-territorio__link" href={territorialContext.link.href}>
        {territorialContext.link.label}
      </a>
      <details className="matriz-territorio__method">
        <summary>Nota metodológica — o que estas leituras não dizem</summary>
        <p className="matriz-territorio__note">{territorialContext.readingNote}</p>
      </details>
    </section>
  )
}

export function MatrizDocumentView({
  educationContext,
  matriz,
  territorialContext = null,
}: {
  educationContext: MatrizEducationContext | null
  matriz: MatrizDocument
  territorialContext?: MatrizTerritorialContext | null
}) {
  const frontCount = matriz.priorityGoals.reduce(
    (total, goal) => total + resolveMatrizFrentes(goal.goalId).length,
    0,
  )

  return (
    <>
      <section aria-label="Resumo da matriz" className="matriz-summary">
        <div>
          <p className="matriz-summary__count">
            {plural(matriz.priorityGoals.length, 'meta prioritária', 'metas prioritárias')} · {plural(frontCount, 'caminho para avançar', 'caminhos para avançar')}
          </p>
          <p className="matriz-summary__peers">{matrizPriorityPeerSummary(matriz)}</p>
          <p className="matriz-summary__method">
            Dados públicos ajudam a escolher o que investigar; a confirmação acontece com registros e equipes da rede.
          </p>
        </div>
      </section>

      <MatrizPriorityOverview matriz={matriz} />

      {territorialContext ? (
        <MatrizTerritorialContextBlock territorialContext={territorialContext} />
      ) : null}

      {matriz.priorityGoals.length > 0 ? (
        <div aria-label="Metas prioritárias" className="matriz-goal-list">
          {matriz.priorityGoals.map((goal, index) => (
            <MatrizGoalBlock
              educationContext={educationContext}
              goal={goal}
              goalIndex={index}
              key={goal.goalId}
              matriz={matriz}
            />
          ))}
        </div>
      ) : <ContentState kind="empty">Esta matriz não contém metas prioritárias para detalhar.</ContentState>}

      <HonestyBlocks matriz={matriz} />
    </>
  )
}

export function MatrizPage({
  municipalityId,
  selectedMunicipio,
}: {
  municipalityId: string | null
  selectedMunicipio: string | null
}) {
  const { data, error, loading } = useMunicipioMatriz(municipalityId)
  const educationContextState = useAsyncData<MatrizEducationContext>(async () => {
    if (!municipalityId) return { accessibilityByNetwork: null }
    const educationDocument = await loadEducationMunicipio(municipalityId)
    return buildMatrizEducationContext(educationDocument)
  }, [municipalityId])
  /*
   * O pacote regional da região do município, lido do que já está publicado. O
   * hook devolve `null` quando não há região mapeada ou a região não está
   * publicada — e o bloco ponte simplesmente não aparece.
   */
  const vocacoes = useVocacoesRegiao(municipalityId)
  const matriz = data?.matriz ?? null

  if (loading) {
    return <LoadingState message={`Carregando a Matriz de Prioridades de ${selectedMunicipio ?? 'município selecionado'}…`} />
  }
  if (error || !matriz) {
    return (
      <ContentState kind="empty">
        <strong>A Matriz de Prioridades ainda não está disponível para este município.</strong>
        <p>A publicação está sendo feita município a município. O diagnóstico municipal continua disponível.</p>
      </ContentState>
    )
  }

  const territorialContext = vocacoes.data
    ? buildMatrizTerritorialContext(vocacoes.data.document, matriz.municipality.ibge7)
    : null

  const scopeKey = `${matriz.municipality.ibge7}:${matriz.referenceDate}`
  return (
    <LoadedMatrizPage
      educationContext={educationContextState.data}
      key={scopeKey}
      matriz={matriz}
      territorialContext={territorialContext}
    />
  )
}

export function LoadedMatrizPage({
  educationContext = null,
  matriz,
  territorialContext = null,
}: {
  educationContext?: MatrizEducationContext | null
  matriz: MatrizDocument
  territorialContext?: MatrizTerritorialContext | null
}) {
  return (
    <div className="page-stack matriz-page">
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={`${matriz.municipality.name}/${matriz.municipality.uf}`}
        description={`Referência de ${formatMatrizReferenceDate(matriz.referenceDate)}. Cada meta reúne o contexto essencial, o que confirmar na rede e os caminhos para avançar.`}
        eyebrow="Planejamento municipal"
        title="Matriz de Prioridades"
        variant="editorial"
      />
      <MatrizDocumentView
        educationContext={educationContext}
        matriz={matriz}
        territorialContext={territorialContext}
      />
    </div>
  )
}
