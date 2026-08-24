import { useId } from 'react'
import { governabilityScope } from '../cadernoVocabulary.js'
import { resolveContextTitle, resolvePlainCause } from '../cadernoPlainLanguage.js'
import { resolveSignalReading } from '../cadernoSignalLanguage.js'
import { resolveFactorGuidance } from '../cadernoFederalGuidance.js'
import type {
  CadernoHypothesis as CadernoHypothesisModel,
  CadernoMonitoringContext,
  CadernoMonitoringSignal,
  CadernoSignal,
} from '../cadernoTypes'

/*
 * Uma possível causa, em linguagem de plano de ação.
 *
 * O texto é a reescrita acessível do fator (cadernoPlainLanguage); a base
 * técnica fica no artefato e não aparece. O único destaque de cor é o verde de
 * "plano": um cartão adicionado ao plano se compromete visualmente. A marca de
 * origem (dado x a confirmar) e o escopo de ação são rótulos calmos, sem
 * hierarquia de gravidade entre causas.
 */

export type CadernoCauseOrigin = 'signal' | 'investigate' | null

const ORIGIN_LABELS: Readonly<Record<'signal' | 'investigate', string>> = {
  signal: 'Os dados apontam para cá',
  investigate: 'A confirmar no município',
}

interface SignalValue {
  readonly display: string
  readonly key: string
  readonly period: string
}

interface SignalGroup {
  readonly cautions: string[]
  readonly label: string
  readonly values: SignalValue[]
}

type PublicSignal = CadernoSignal | CadernoMonitoringSignal

function groupSignalReadings(signals: readonly PublicSignal[]): readonly SignalGroup[] {
  const groups: SignalGroup[] = []
  const groupsByLabel = new Map<string, SignalGroup>()
  const seen = new Set<string>()

  for (const [index, signal] of signals.entries()) {
    const signalKey = JSON.stringify([signal.measureId, signal.period, signal.dimensions])
    if (seen.has(signalKey)) continue
    seen.add(signalKey)

    const reading = resolveSignalReading(signal)
    if (!reading) continue

    let group = groupsByLabel.get(reading.label)
    if (!group) {
      group = { cautions: [], label: reading.label, values: [] }
      groupsByLabel.set(reading.label, group)
      groups.push(group)
    }
    group.values.push({
      display: reading.display,
      key: `${signalKey}-${index}`,
      period: reading.period,
    })
    if (reading.caution && !group.cautions.includes(reading.caution)) {
      group.cautions.push(reading.caution)
    }
  }

  return groups
}

function SignalGroups({
  groups,
  listClassName,
}: {
  groups: readonly SignalGroup[]
  listClassName?: string
}) {
  return (
    <ul className={listClassName}>
      {groups.map((group) => (
        <li className="caderno-signal" key={group.label}>
          <p className="caderno-signal__label">{group.label}</p>
          {group.values.map((value) => (
            <p className="caderno-signal__value" key={value.key}>
              <span className="caderno-signal__period">{value.period}:</span>{' '}
              {value.display}
            </p>
          ))}
          {group.cautions.map((caution) => (
            <p className="caderno-signal__caution" key={caution}>{caution}</p>
          ))}
        </li>
      ))}
    </ul>
  )
}

export function CadernoCause({
  hypothesis,
  goalId,
  origin,
  isSelected,
  onToggleFront,
}: {
  hypothesis: CadernoHypothesisModel
  goalId: string
  origin: CadernoCauseOrigin
  isSelected: boolean
  onToggleFront: () => void
}) {
  const titleId = useId()
  const scope = governabilityScope(hypothesis.governability)
  const plain = resolvePlainCause(hypothesis, goalId, origin ? 'cause' : 'protective')
  const signalGroups = groupSignalReadings(hypothesis.signals)
  const federalGuidance = resolveFactorGuidance(hypothesis.factorId)

  return (
    <article
      aria-labelledby={titleId}
      className={`caderno-cause${isSelected ? ' is-in-plan' : ''}`}
    >
      <div className="caderno-cause__meta">
        {origin ? (
          <span className={`caderno-origin caderno-origin--${origin}`}>
            <span aria-hidden="true" className="caderno-origin__dot" />
            {ORIGIN_LABELS[origin]}
          </span>
        ) : (
          <span className="caderno-origin caderno-origin--favor">
            <span aria-hidden="true" className="caderno-origin__dot" />
            Ponto forte a proteger
          </span>
        )}
        <span className={`caderno-scope caderno-scope--${scope.tone}`}>{scope.label}</span>
      </div>

      <h5 className="caderno-cause__name" id={titleId}>{plain.title}</h5>

      {plain.why ? <p className="caderno-cause__why">{plain.why}</p> : null}
      {plain.help ? (
        <p className="caderno-cause__help">
          <span className="caderno-cause__help-label">O que costuma ajudar</span>
          {plain.help}
        </p>
      ) : null}

      {plain.look.length > 0 ? (
        <details className="caderno-cause__look">
          <summary>O que olhar no município</summary>
          <ul>
            {plain.look.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      ) : null}

      {signalGroups.length > 0 ? (
        <details className="caderno-cause__signals">
          <summary>O que os dados públicos mostram</summary>
          <SignalGroups groups={signalGroups} />
        </details>
      ) : null}

      {federalGuidance ? (
        <details className="caderno-cause__guidance">
          <summary>O que a orientação federal indica</summary>
          <p>{federalGuidance.text}</p>
          <ul>
            {federalGuidance.references.map((reference) => (
              <li key={reference.url}>
                <a
                  href={reference.url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {reference.label}
                </a>
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <button
        aria-pressed={isSelected}
        className="caderno-front-toggle"
        onClick={onToggleFront}
        type="button"
      >
        <span aria-hidden="true" className="caderno-front-toggle__mark" />
        {isSelected ? 'No plano de ação' : 'Adicionar ao plano de ação'}
      </button>
    </article>
  )
}

export function CadernoTerritoryContext({
  contexts,
}: {
  contexts: readonly CadernoMonitoringContext[]
}) {
  const titleId = useId()

  if (contexts.length === 0) return null

  return (
    <details aria-labelledby={titleId} className="caderno-context">
      <summary className="caderno-context__summary" id={titleId}>Condições do território</summary>
      <div className="caderno-context__body">
        <p className="caderno-context__intro">
          Condições do território que ajudam a ler o resultado. Não são causas escolhíveis; servem de pano de fundo para a oficina.
        </p>
        <div className="caderno-context__list">
          {contexts.map((context, index) => {
            const contextTitleId = `${titleId}-context-${index}`
            const signalGroups = groupSignalReadings(context.signals)
            return (
              <article
                aria-labelledby={contextTitleId}
                className="caderno-context__item"
                key={`${context.factorId}-${index}`}
              >
                <h5 className="caderno-context__title" id={contextTitleId}>
                  {resolveContextTitle(context)}
                </h5>
                {signalGroups.length > 0 ? (
                  <SignalGroups groups={signalGroups} listClassName="caderno-context__signals" />
                ) : null}
              </article>
            )
          })}
        </div>
      </div>
    </details>
  )
}
