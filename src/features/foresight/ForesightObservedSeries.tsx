import type { ForesightObservedSerie, ForesightObservedWindow } from './foresightTypes'

/*
 * Séries observadas do município.
 *
 * Cada faixa mostra o valor de partida, o valor mais recente e a direção que a
 * camada de pesquisa declarou para aquela janela — nas mesmas palavras do texto
 * aprovado. A direção é informação factual sobre o passado, não juízo: por isso
 * não recebe cor de aprovação ou alerta, nem seta de progresso.
 *
 * A barra é proporcional apenas dentro da própria série e só existe para
 * percentuais, onde 100 é a escala natural. Contagens não ganham barra, porque
 * não têm teto conhecido e a proporção seria inventada.
 */

const PERCENT_UNIT = 'por cento'

function parsePercent(value: string): number | null {
  const match = /^(\d+(?:,\d+)?)%$/.exec(value)
  if (!match) return null
  const parsed = Number(match[1].replace(',', '.'))
  return Number.isFinite(parsed) ? Math.min(100, Math.max(0, parsed)) : null
}

function ObservedWindow({
  isRecent,
  unitLabel,
  window,
}: {
  isRecent: boolean
  unitLabel: string
  window: ForesightObservedWindow
}) {
  const start = unitLabel === PERCENT_UNIT ? parsePercent(window.startValue) : null
  const end = unitLabel === PERCENT_UNIT ? parsePercent(window.endValue) : null

  return (
    <div className={isRecent ? 'foresight-window foresight-window--recent' : 'foresight-window'}>
      <p className="foresight-window__period">
        {isRecent ? `Trecho mais recente · ${window.periodLabel}` : `Período completo · ${window.periodLabel}`}
      </p>
      <p className="foresight-window__values">
        <span className="foresight-window__value">{window.startValue}</span>
        <span className="foresight-window__link" aria-hidden="true" />
        <span className="foresight-window__value foresight-window__value--end">{window.endValue}</span>
        <span className="foresight-window__direction">{window.directionLabel}</span>
      </p>
      {start !== null && end !== null ? (
        <div className="foresight-window__scale" aria-hidden="true">
          <span className="foresight-window__scale-mark" style={{ insetInlineStart: `${start}%` }} />
          <span
            className="foresight-window__scale-span"
            style={{
              insetInlineStart: `${Math.min(start, end)}%`,
              inlineSize: `${Math.abs(end - start)}%`,
            }}
          />
          <span className="foresight-window__scale-mark foresight-window__scale-mark--end" style={{ insetInlineStart: `${end}%` }} />
        </div>
      ) : null}
      {window.caveat ? <p className="foresight-window__caveat">{window.caveat}</p> : null}
    </div>
  )
}

export function ForesightObservedSeriesList({ items }: { items: readonly ForesightObservedSerie[] }) {
  return (
    <ul className="foresight-series">
      {items.map((serie) => (
        <li className="foresight-serie" key={serie.label}>
          <div className="foresight-serie__head">
            <h4 className="foresight-serie__label">{serie.label}</h4>
            <span className="foresight-serie__unit">{serie.unitLabel}</span>
          </div>
          <ObservedWindow isRecent={false} unitLabel={serie.unitLabel} window={serie.fullPeriod} />
          {serie.recentWindow ? (
            <ObservedWindow isRecent unitLabel={serie.unitLabel} window={serie.recentWindow} />
          ) : null}
        </li>
      ))}
    </ul>
  )
}
