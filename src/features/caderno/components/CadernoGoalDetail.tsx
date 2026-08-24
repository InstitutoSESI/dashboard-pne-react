import { CadernoCause, CadernoTerritoryContext } from './CadernoHypothesis.js'
import {
  goalFullTitle,
  PROTECTIVE_SECTION_KEY,
} from '../cadernoVocabulary.js'
import {
  formatPublicDistance,
  formatPublicValue,
  getPublicCurrentValue,
  getPublicResultStatus,
} from '../../diagnostic/diagnosticPresentation.js'
import { cadernoFrontKey } from '../../../domain/cadernoFrontsStorage.js'
import { PNE_2026_FEDERAL_GUIDANCE } from '../../../data/pne2026FederalGuidance.js'
import type { CadernoGoal } from '../cadernoTypes'
import type { Pne2026DiagnosticResultViewModel } from '../../diagnostic/diagnosticTypes'

/*
 * Painel do objetivo selecionado.
 *
 * O resultado do indicador é o MESMO publicado no PNE 2026–2036: valor, ano,
 * meta e distância vêm do diagnóstico municipal da plataforma pelos mesmos
 * formatadores da página de Diagnóstico, para que o município nunca veja dois
 * números para o mesmo indicador. O caderno não recalcula indicador — ele
 * acrescenta as possíveis causas. Indicador sem resultado publicado
 * simplesmente não aparece.
 *
 * Só este painel troca quando o usuário escolhe outra meta no índice: nada ao
 * redor se move. A ordem das causas é a do artefato.
 */

function referenceOf(result: Pne2026DiagnosticResultViewModel) {
  return 'indicatorReference' in result ? result.indicatorReference : null
}

function distanceOf(result: Pne2026DiagnosticResultViewModel): number | null {
  return 'distance' in result ? result.distance : null
}

function historyOf(result: Pne2026DiagnosticResultViewModel): string {
  return 'trajectory' in result ? result.trajectory?.historicalReading ?? '' : ''
}

export function CadernoGoalDetail({
  goal,
  onToggleFront,
  resultsByRelation,
  selectedKeys,
}: {
  goal: CadernoGoal
  onToggleFront: (factorId: string) => void
  resultsByRelation: ReadonlyMap<string, Pne2026DiagnosticResultViewModel>
  selectedKeys: ReadonlySet<string>
}) {
  const adverse = goal.hypotheses.adverse_signal
  const investigate = goal.hypotheses.no_public_data
  const protective = goal.hypotheses[PROTECTIVE_SECTION_KEY]
  const federalGuidance = PNE_2026_FEDERAL_GUIDANCE[goal.goalId]

  const measured: Pne2026DiagnosticResultViewModel[] = []
  const caveatsByResult = new Map<Pne2026DiagnosticResultViewModel, string>()
  for (const indicator of goal.indicators) {
    const result = resultsByRelation.get(`${indicator.relationId}|${indicator.indicatorId}`)
    if (result && result.dataStatus === 'available') {
      if (!measured.includes(result)) measured.push(result)
      if (indicator.caveat.trim() && !caveatsByResult.has(result)) {
        caveatsByResult.set(result, indicator.caveat)
      }
    }
  }

  return (
    <article aria-live="polite" className="caderno-detail">
      <header className="caderno-detail__head">
        <p className="caderno-detail__eyebrow">Objetivo {goal.goalId}</p>
        <h3 className="caderno-detail__title">{goalFullTitle(goal)}</h3>
      </header>

      {measured.length > 0 ? (
        <section className="caderno-section">
          <h4 className="caderno-section__title">Como a meta está hoje</h4>
          <p className="caderno-section__lead">
            Resultado publicado no PNE 2026–2036 para este município.
          </p>
          <ul className="caderno-results">
            {measured.map((result) => {
              const reference = referenceOf(result)
              const distance = distanceOf(result)
              const history = historyOf(result)
              const unit = result.current?.unit ?? null
              const caveat = caveatsByResult.get(result)
              const status = getPublicResultStatus(result)
              return (
                <li
                  className={`caderno-result caderno-result--${status.key}`}
                  key={`${result.goalId}-${result.indicatorId}`}
                >
                  <p className="caderno-result__name">{result.publicName}</p>
                  <p className="caderno-result__figures">
                    <span className="caderno-result__value">{getPublicCurrentValue(result)}</span>
                    {result.current?.year ? (
                      <span className="caderno-result__year">em {result.current.year}</span>
                    ) : null}
                    {reference ? (
                      <span className="caderno-result__target">
                        meta {formatPublicValue(reference.value, unit)}
                      </span>
                    ) : null}
                    {Number.isFinite(distance) ? (
                      <span className="caderno-result__gap">
                        {formatPublicDistance(distance, unit)}
                      </span>
                    ) : null}
                  </p>
                  <p className="caderno-result__status">
                    <span className="caderno-result__status-badge">{status.label}</span>
                    {history ? <span className="caderno-result__history">{history}</span> : null}
                  </p>
                  {caveat ? <p className="caderno-result__caveat">{caveat}</p> : null}
                </li>
              )
            })}
          </ul>
        </section>
      ) : null}

      {federalGuidance ? (
        <section className="caderno-section caderno-guidance">
          <h4 className="caderno-section__title">O que o novo PNE pede</h4>
          <p className="caderno-section__lead">
            Referência da Lei nº 15.388/2026 para esta meta no ciclo 2026–2036.
          </p>
          <p className="caderno-guidance__summary">{federalGuidance.summary}</p>
          <details className="caderno-guidance__strategies">
            <summary>Ver metas e estratégias relacionadas</summary>
            <ul>
              {federalGuidance.strategies.map((strategy) => (
                <li key={strategy.ref}>
                  <strong>{strategy.ref}</strong>
                  <span>{strategy.text}</span>
                </li>
              ))}
            </ul>
          </details>
          <footer className="caderno-guidance__sources">
            <span>Fontes oficiais</span>
            {federalGuidance.sources.map((source) => (
              <a
                href={source.url}
                key={source.url}
                rel="noopener noreferrer"
                target="_blank"
              >
                {source.name}
              </a>
            ))}
          </footer>
        </section>
      ) : null}

      {adverse.length > 0 ? (
        <section className="caderno-section caderno-section--causes">
          <h4 className="caderno-section__title">Possíveis causas</h4>
          <p className="caderno-section__lead">
            Por que a meta pode não estar avançando neste município. Marque as que o município quer
            atacar — elas entram no seu plano de ação.
          </p>
          <div className="caderno-cause-list">
            {adverse.map((hypothesis) => (
              <CadernoCause
                goalId={goal.goalId}
                hypothesis={hypothesis}
                isSelected={selectedKeys.has(cadernoFrontKey(goal.goalId, hypothesis.factorId))}
                key={hypothesis.factorId}
                onToggleFront={() => onToggleFront(hypothesis.factorId)}
                origin="signal"
              />
            ))}
          </div>
        </section>
      ) : null}

      {investigate.length > 0 ? (
        <section className="caderno-section caderno-section--causes">
          <h4 className="caderno-section__title">Para verificar na oficina</h4>
          <p className="caderno-section__lead">
            Causas plausíveis pela literatura, sem sinal público que confirme neste município. A
            oficina confirma ou descarta cada uma.
          </p>
          <div className="caderno-cause-list">
            {investigate.map((hypothesis) => (
              <CadernoCause
                goalId={goal.goalId}
                hypothesis={hypothesis}
                isSelected={selectedKeys.has(cadernoFrontKey(goal.goalId, hypothesis.factorId))}
                key={hypothesis.factorId}
                onToggleFront={() => onToggleFront(hypothesis.factorId)}
                origin="investigate"
              />
            ))}
          </div>
        </section>
      ) : null}

      {protective.length > 0 ? (
        <section className="caderno-section caderno-section--favor">
          <h4 className="caderno-section__title">O que já joga a favor</h4>
          <p className="caderno-section__lead">
            Pontos que os dados públicos indicam estar sustentando esta meta. Vale proteger.
          </p>
          <div className="caderno-cause-list">
            {protective.map((hypothesis) => (
              <CadernoCause
                goalId={goal.goalId}
                hypothesis={hypothesis}
                isSelected={selectedKeys.has(cadernoFrontKey(goal.goalId, hypothesis.factorId))}
                key={hypothesis.factorId}
                onToggleFront={() => onToggleFront(hypothesis.factorId)}
                origin={null}
              />
            ))}
          </div>
        </section>
      ) : null}

      <CadernoTerritoryContext contexts={goal.monitoring_context} />
    </article>
  )
}
