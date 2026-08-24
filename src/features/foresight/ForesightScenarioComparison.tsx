import type { ForesightScenario } from './foresightTypes'

/*
 * Comparação lado a lado dos quatro cenários.
 *
 * É um giro do que já foi publicado: as mesmas seções, reagrupadas por linha em
 * vez de por cenário. Nenhum texto é reescrito, resumido ou escolhido aqui — a
 * tabela só permite ler na horizontal o que a leitura de cada cenário mostra na
 * vertical, que é onde a diferença entre eles aparece.
 *
 * As colunas têm a mesma largura e a mesma superfície. A única marcação é a do
 * cenário aberto no detalhe, para o leitor não se perder entre as duas visões.
 */

/** As seções que efetivamente distinguem um cenário do outro. */
const COMPARED_SECTION_KEYS = [
  'como-este-cenario-se-forma',
  'o-que-pode-mudar-no-sistema-educacional',
  'o-que-precisa-ocorrer-para-este-cenario-ganhar-forca',
] as const

export function ForesightScenarioComparison({
  activeSlug,
  scenarios,
}: {
  activeSlug: string
  scenarios: readonly ForesightScenario[]
}) {
  const rows = COMPARED_SECTION_KEYS
    .map((key) => {
      const cells = scenarios.map((scenario) => ({
        items: scenario.sections.find((section) => section.key === key)?.items ?? [],
        slug: scenario.slug,
      }))
      const label = scenarios
        .flatMap((scenario) => scenario.sections)
        .find((section) => section.key === key)?.label
      return { cells, key, label }
    })
    .filter((row) => row.label !== undefined && row.cells.some((cell) => cell.items.length > 0))

  if (rows.length === 0) return null

  return (
    <div className="foresight-comparison__wrapper">
      <table className="foresight-comparison">
        <caption className="u-sr-only">
          Comparação dos quatro cenários pelas seções que os distinguem
        </caption>
        <thead>
          <tr>
            <th className="foresight-comparison__corner" scope="col">Leitura</th>
            {scenarios.map((scenario) => (
              <th
                className={scenario.slug === activeSlug
                  ? 'foresight-comparison__scenario is-active'
                  : 'foresight-comparison__scenario'}
                key={scenario.slug}
                scope="col"
              >
                {scenario.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <th className="foresight-comparison__row-label" scope="row">{row.label}</th>
              {row.cells.map((cell) => (
                <td
                  className={cell.slug === activeSlug
                    ? 'foresight-comparison__cell is-active'
                    : 'foresight-comparison__cell'}
                  key={cell.slug}
                >
                  {cell.items.map((item) => <p key={item}>{item}</p>)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
