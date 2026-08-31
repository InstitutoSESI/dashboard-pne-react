import { useMemo } from 'react'
import {
  ArrowDown,
  ArrowUp,
  ChartColumnIncreasing,
  Clock3,
  GraduationCap,
  MapPinned,
  School,
  Target,
  UsersRound,
} from 'lucide-react'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { ACTIVE_STATE_CONFIG } from '../../config/stateConfig'
import { useRegionalPanel } from '../../hooks/useRegionalPanel'
import type {
  RegionalCountPoint,
  RegionalCoverageIndicator,
  RegionalDistributionIndicator,
  RegionalDocument,
  RegionalEducationCountGroup,
  RegionalEducationCountIndicator,
  RegionalPneIndicator,
  RegionalPneCategory,
  RegionalPneMethod,
  RegionalPneReference,
  RegionalPneResult,
  RegionalVaarIndicator,
} from './regionalTypes'
import '../../styles/education-pages.css'
import '../../styles/regional-page.css'

/*
 * Panorama da Região.
 *
 * A região é derivada do município selecionado. A página apenas apresenta o
 * artefato publicado e validado: agregações, medianas e comparações com o PNE
 * são calculadas pelo gerador determinístico.
 */

const ENROLLMENT_BREAKDOWNS = [
  { key: 'por_etapa', label: 'Por etapa de ensino' },
  { key: 'por_dependencia', label: 'Por dependência administrativa' },
  { key: 'por_localizacao', label: 'Por localização' },
] as const

const CATEGORY_ORDER: Readonly<Record<string, readonly string[]>> = Object.freeze({
  por_etapa: [
    'infantil',
    'fundamental',
    'fundamental_anos_iniciais',
    'fundamental_anos_finais',
    'medio',
    'profissional',
    'eja',
  ],
  por_dependencia: ['publica', 'federal', 'estadual', 'municipal', 'privada'],
  por_localizacao: ['urbana', 'rural'],
})

const CATEGORY_LABELS: Readonly<Record<string, string>> = Object.freeze({
  infantil: 'Educação infantil',
  fundamental: 'Ensino fundamental',
  fundamental_anos_iniciais: 'Fundamental — anos iniciais',
  fundamental_anos_finais: 'Fundamental — anos finais',
  medio: 'Ensino médio',
  profissional: 'Educação profissional',
  eja: 'Educação de jovens e adultos',
  publica: 'Rede pública',
  federal: 'Rede federal',
  privada: 'Rede privada',
  estadual: 'Rede estadual',
  municipal: 'Rede municipal',
  urbana: 'Urbana',
  rural: 'Rural',
})

const EDUCATION_GROUP_LABELS: Readonly<Record<RegionalEducationCountGroup, string>> = Object.freeze({
  rede: 'Rede escolar',
  oferta: 'Oferta educacional',
  educacao_indigena: 'Educação escolar indígena',
  sistema_s: 'Sistema S',
})

const integerFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 0,
})
const decimalFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 2,
})
const percentFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})

function categoryLabel(key: string): string {
  return CATEGORY_LABELS[key] ?? key
}

function orderedCategories(breakdownKey: string, categories: readonly string[]): string[] {
  const preferred = CATEGORY_ORDER[breakdownKey] ?? []
  const known = preferred.filter((category) => categories.includes(category))
  const rest = categories.filter((category) => !preferred.includes(category)).sort()
  return [...known, ...rest]
}

function formatCount(value: number | null): string {
  return value === null ? 'não disponível' : integerFormatter.format(value)
}

function formatPercent(value: number | null): string {
  return value === null ? 'não disponível' : `${percentFormatter.format(value)}%`
}

function formatMetric(value: number | null, unit: RegionalDistributionIndicator['unidade']): string {
  if (value === null) return 'não disponível'
  return unit === 'percent' ? formatPercent(value) : decimalFormatter.format(value)
}

function lastWithValue<T extends { readonly valor: number | null }>(
  series: readonly T[],
): T | null {
  for (let index = series.length - 1; index >= 0; index -= 1) {
    if (series[index].valor !== null) return series[index]
  }
  return null
}

function firstWithValue<T extends { readonly valor: number | null }>(
  series: readonly T[],
): T | null {
  return series.find((point) => point.valor !== null) ?? null
}

function partialDataHint(municipalitiesWithData: number, totalMunicipalities: number): string | null {
  if (municipalitiesWithData === 0 || municipalitiesWithData === totalMunicipalities) return null
  return `${municipalitiesWithData} de ${totalMunicipalities} municípios com resultado`
}

function enrollmentShare(
  point: RegionalCountPoint | null,
  totals: readonly RegionalCountPoint[],
): number | null {
  if (point?.valor === null || point === null) return null
  const total = totals.find((candidate) => candidate.ano === point.ano)?.valor ?? null
  return total === null || total === 0 ? null : (point.valor / total) * 100
}

function pneMethodLabel(method: RegionalPneMethod): string {
  return method === 'regional_ratio' ? 'taxa regional' : 'mediana dos municípios'
}

function referenceStatus(result: RegionalPneResult, reference: RegionalPneReference | null): string {
  if (reference === null) return 'Acompanhamento sem meta quantitativa'
  if (result.valor === null || result.distanciaReferencia === null) return 'Resultado não disponível'
  if (result.distanciaReferencia >= 0) {
    return result.distanciaReferencia === 0
      ? 'Referência atingida'
      : `Referência atingida · margem de ${percentFormatter.format(result.distanciaReferencia)} p.p.`
  }
  const distance = percentFormatter.format(Math.abs(result.distanciaReferencia))
  return reference.direcao === 'at_most'
    ? `${distance} p.p. acima da referência`
    : `Faltam ${distance} p.p. para a referência`
}

function referenceStatusTone(
  result: RegionalPneResult,
  reference: RegionalPneReference | null,
): 'neutral' | 'success' | 'warning' {
  if (reference === null || result.valor === null || result.distanciaReferencia === null) {
    return 'neutral'
  }
  return result.distanciaReferencia >= 0 ? 'success' : 'warning'
}

function navigateWithinRegionalPage(targetId: string) {
  const heading = document.getElementById(targetId)
  if (!heading) return
  const target = heading.closest<HTMLElement>(
    '.regional-panel, .regional-pne-results, .regional-education-layout',
  ) ?? heading

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
}

/** Variação em pontos percentuais entre o primeiro e o último ano com valor. */
function CoverageRow({ indicator }: { indicator: RegionalCoverageIndicator }) {
  const first = firstWithValue(indicator.series)
  const last = lastWithValue(indicator.series)
  const change = first !== null && last !== null && first.ano !== last.ano
    ? (last.valor as number) - (first.valor as number)
    : null

  return (
    <tr>
      <th scope="row">
        <span className="regional-table__label">{indicator.titulo}</span>
        <span className="regional-table__hint">{indicator.faixaEtaria}</span>
      </th>
      <td>{formatPercent(last?.valor ?? null)}</td>
      <td>{last === null ? '—' : last.ano}</td>
      <td>
        {change === null
          ? '—'
          : `${change >= 0 ? '+' : '−'}${percentFormatter.format(Math.abs(change))} p.p.`}
      </td>
      <td>
        {last === null
          ? '—'
          : `${formatCount(last.numerador)} de ${formatCount(last.denominador)}`}
      </td>
    </tr>
  )
}

function EnrollmentRow({
  label,
  point,
  totals,
  totalMunicipalities,
}: {
  label: string
  point: RegionalCountPoint | null
  totals: readonly RegionalCountPoint[]
  totalMunicipalities: number
}) {
  const hint = point === null
    ? null
    : partialDataHint(point.municipiosComDado, totalMunicipalities)
  return (
    <tr>
      <th scope="row">
        <span className="regional-table__label">{label}</span>
        {hint === null ? null : <span className="regional-table__hint">{hint}</span>}
      </th>
      <td>{formatCount(point?.valor ?? null)}</td>
      <td>{formatPercent(enrollmentShare(point, totals))}</td>
      <td>{point === null ? '—' : point.ano}</td>
    </tr>
  )
}

type RegionalEducationGroupView = {
  readonly group: RegionalEducationCountGroup
  readonly indicators: readonly RegionalEducationCountIndicator[]
}

function EducationCountMetric({ indicator }: { indicator: RegionalEducationCountIndicator }) {
  return (
    <dl className="municipal-education-summary__group">
      <div className="municipal-education-summary__group-heading">
        <dt>{indicator.titulo}</dt>
        <dd>{formatCount(indicator.valor)}</dd>
        <p className="municipal-education-summary__group-share">
          {indicator.ano === null ? 'Ano não disponível' : `Resultado regional · ${indicator.ano}`}
        </p>
      </div>
    </dl>
  )
}

function EducationCountsOverview({
  description,
  groups,
  primaryIndicator,
  title,
}: {
  description: string
  groups: readonly RegionalEducationGroupView[]
  primaryIndicator: RegionalEducationCountIndicator | null
  title: string
}) {
  const visibleGroups = groups
    .map(({ group, indicators }) => ({
      group,
      indicators: indicators.filter((indicator) => indicator.chave !== primaryIndicator?.chave),
    }))
    .filter(({ indicators }) => indicators.length > 0)

  return (
    <section
      aria-labelledby="regiao-educacao-contagens"
      className="municipal-education-overview__section municipal-education-overview__section--summary"
    >
      <div className="municipal-education-overview__section-heading">
        <h2 id="regiao-educacao-contagens">{title}</h2>
        <p className="regional-panel__text">{description}</p>
      </div>
      <div className="municipal-education-summary">
        {primaryIndicator === null ? null : (
          <dl className="municipal-education-summary__primary">
            <div>
              <dt>{primaryIndicator.titulo}</dt>
              <dd>{formatCount(primaryIndicator.valor)}</dd>
              <span>
                {primaryIndicator.ano === null
                  ? 'Total regional · ano não disponível'
                  : `Total regional em ${primaryIndicator.ano}`}
              </span>
            </div>
          </dl>
        )}
        {visibleGroups.map(({ group, indicators }) => (
          <section
            aria-labelledby={`educacao-${group}`}
            className="municipal-education-summary__category municipal-education-summary__category--regular-stages"
            key={group}
          >
            <h3 id={`educacao-${group}`}>{EDUCATION_GROUP_LABELS[group]}</h3>
            <div className="municipal-education-summary__components">
              {indicators.map((indicator) => (
                <EducationCountMetric indicator={indicator} key={indicator.chave} />
              ))}
            </div>
          </section>
        ))}
        <div className="municipal-education-summary__notes" aria-label="Nota de leitura dos indicadores regionais">
          <p>Os valores são os resultados regionais publicados para o ano indicado em cada indicador.</p>
        </div>
      </div>
    </section>
  )
}

function RegionalQualitySection({
  category,
  regionName,
  totalMunicipalities,
}: {
  category: RegionalDocument['educacao']['qualidade'][number]
  regionName: string
  totalMunicipalities: number
}) {
  return (
    <section
      aria-labelledby={`qualidade-${category.chave}`}
      className="municipal-education-overview__section municipal-learning-outcomes"
    >
      <div className="municipal-education-overview__section-heading">
        <h2 id={`qualidade-${category.chave}`}>{category.label}</h2>
        <p>Resultados mais recentes: a região e o RS são apresentados pela mediana dos municípios.</p>
      </div>
      <div className="municipal-learning-outcomes__table-region" tabIndex={0}>
        <table>
          <caption>{`${category.label} na região ${regionName}`}</caption>
          <thead>
            <tr>
              <th scope="col">Indicador</th>
              <th scope="col">Mediana da região</th>
              <th scope="col">Mediana do RS</th>
              <th scope="col">Intervalo municipal</th>
            </tr>
          </thead>
          <tbody>
            {category.indicadores.map((indicator) => {
              const hint = partialDataHint(indicator.municipiosComDado, totalMunicipalities)
              const interval = indicator.minimoMunicipal === null || indicator.maximoMunicipal === null
                ? 'não disponível'
                : `${formatMetric(indicator.minimoMunicipal, indicator.unidade)} a ${formatMetric(indicator.maximoMunicipal, indicator.unidade)}`
              const year = indicator.ano === null ? 'ano não disponível' : String(indicator.ano)
              return (
                <tr key={indicator.chave}>
                  <th scope="row">
                    <span className="regional-table__label">{indicator.titulo}</span>
                    {hint === null ? null : <span className="regional-table__hint">{hint}</span>}
                  </th>
                  <td data-label="Mediana da região">
                    <span className="municipal-learning-outcomes__value">
                      <strong>{formatMetric(indicator.valor, indicator.unidade)}</strong>
                      <small>{year}</small>
                    </span>
                  </td>
                  <td data-label="Mediana do RS">
                    <span className="municipal-learning-outcomes__value">
                      <strong>{formatMetric(indicator.valorEstado, indicator.unidade)}</strong>
                      <small>{year}</small>
                    </span>
                  </td>
                  <td data-label="Intervalo municipal">
                    <span className="municipal-learning-outcomes__value"><strong>{interval}</strong></span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="municipal-learning-outcomes__note">
        O intervalo mostra o menor e o maior resultado municipal publicável dentro da região.
      </p>
    </section>
  )
}

function RegionalVaarOverview({
  block,
  regionName,
}: {
  block: RegionalDocument['educacao']['vaar']
  regionName: string
}) {
  return (
    <section className="municipal-education-overview__section municipal-school-performance" aria-labelledby="regiao-vaar">
      <div className="municipal-education-overview__section-heading">
        <h2 id="regiao-vaar">{block.label}</h2>
        <p className="regional-panel__text">{block.descricao}</p>
      </div>
      <div className="municipal-school-performance__table-region" tabIndex={0}>
        <table>
          <caption>{`${block.label} na região ${regionName}`}</caption>
          <thead>
            <tr>
              <th scope="col">Condição</th>
              <th scope="col">Região</th>
              <th scope="col">RS</th>
            </tr>
          </thead>
          <tbody>
            {block.indicadores.map((indicator: RegionalVaarIndicator) => (
              <tr key={indicator.chave}>
                <th scope="row">{indicator.titulo}</th>
                <td data-label="Região">{formatCount(indicator.valor)}</td>
                <td data-label="RS">{formatCount(indicator.valorEstado)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="municipal-school-performance__note">
        {`Resultados publicados para ${block.ano ?? 'ano não disponível'}.`}
      </p>
    </section>
  )
}

function formatSignedPercentagePoints(value: number | null): string {
  if (value === null) return '—'
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}${percentFormatter.format(Math.abs(value))} p.p.`
}

function regionalPneStatusLabel(
  result: RegionalPneResult,
  reference: RegionalPneReference | null,
): string {
  if (reference === null) return 'Indicador de acompanhamento'
  if (result.valor === null || result.distanciaReferencia === null) return 'Resultado não disponível'
  if (result.distanciaReferencia >= 0) return 'Referência alcançada'
  return reference.direcao === 'at_most' ? 'Acima do limite' : 'Abaixo da referência'
}

function RegionalPneResultCard({
  indicator,
  totalMunicipalities,
}: {
  indicator: RegionalPneIndicator
  totalMunicipalities: number
}) {
  const { referencia, resultado } = indicator
  const statusTone = referenceStatusTone(resultado, referencia)
  const statusState = statusTone === 'success' ? 'maintain' : statusTone === 'warning' ? 'advance' : 'neutral'
  const statusLabel = regionalPneStatusLabel(resultado, referencia)
  const stateDifference = resultado.valor === null || resultado.valorEstado === null
    ? null
    : resultado.valor - resultado.valorEstado
  const interval = resultado.minimoMunicipal === null || resultado.maximoMunicipal === null
    ? null
    : `${formatPercent(resultado.minimoMunicipal)} a ${formatPercent(resultado.maximoMunicipal)}`
  const hasComparison = resultado.valorEstado !== null
    || resultado.municipiosNaReferencia !== null
    || interval !== null
  const coverageHint = partialDataHint(resultado.municipiosComDado, totalMunicipalities)
  const methodReading = resultado.metodo === 'regional_ratio'
    ? 'Taxa regional formada pela razão entre os totais publicados da região.'
    : 'Mediana dos resultados municipais; não representa uma taxa agregada da região.'
  const DistanceIcon = resultado.distanciaReferencia !== null && resultado.distanciaReferencia >= 0
    ? ArrowUp
    : ArrowDown

  return (
    <article
      aria-labelledby={`pne-regional-${indicator.chave}`}
      className={`pne-diagnostic-result pne-diagnostic-result--${statusState} pne-diagnostic-result--standalone`}
    >
      <header className="pne-diagnostic-result__head">
        <span className="pne-diagnostic-result__icon" aria-hidden="true"><Target /></span>
        <div className="pne-diagnostic-result__id">
          <p className="pne-diagnostic-result__goal-context">
            {referencia?.label ?? 'Indicador de acompanhamento'}
          </p>
          <h4 className="pne-diagnostic-result__name" id={`pne-regional-${indicator.chave}`}>
            {indicator.titulo}
          </h4>
        </div>
        <span className={`pne-diagnostic-result__status pne-diagnostic-result__status--${statusState}`}>
          {statusLabel}
        </span>
      </header>

      <div className="pne-diagnostic-result__legal">
        <p className="pne-diagnostic-result__legal-label">O que mede</p>
        <p className="pne-diagnostic-result__legal-text">{indicator.descricao}</p>
      </div>

      <div className="pne-diagnostic-result__panels">
        <section className="pne-diagnostic-result__panel pne-diagnostic-result__panel--meta" aria-label="Resultado regional em relação à referência do PNE">
          <p className="pne-diagnostic-result__panel-label">Resultado regional</p>
          <p className="pne-diagnostic-result__hero">
            <strong>{formatPercent(resultado.valor)}</strong>
            {resultado.ano === null ? null : <span>{`resultado ${resultado.ano}`}</span>}
          </p>
          <p className="pne-diagnostic-result__target">
            {referencia === null ? (
              'Sem referência quantitativa publicada'
            ) : (
              <>
                {referencia.tipo === 'monitoring' ? 'Referência de acompanhamento: ' : 'Referência: '}
                <b>{formatPercent(referencia.valor)}</b>
                {referencia.ano === null ? null : <> até <b>{referencia.ano}</b></>}
              </>
            )}
          </p>
          {referencia === null || resultado.distanciaReferencia === null ? null : (
            <span className="pne-diagnostic-result__gap" title="Distância para a referência">
              <DistanceIcon aria-hidden="true" />
              {referenceStatus(resultado, referencia)}
            </span>
          )}
        </section>

        {hasComparison ? (
          <section className="pne-diagnostic-result__panel pne-diagnostic-result__panel--compare" aria-label="Comparação com o Rio Grande do Sul e com os municípios da região">
            <p className="pne-diagnostic-result__panel-label">Como se compara</p>
            <dl className="pne-diagnostic-result__compare">
              {resultado.valorEstado === null ? null : (
                <div className="pne-diagnostic-result__compare-row">
                  <dt>
                    <span className="pne-diagnostic-result__compare-icon" aria-hidden="true"><ChartColumnIncreasing /></span>
                    Rio Grande do Sul
                  </dt>
                  <dd className="pne-diagnostic-result__compare-values">
                    <span className="pne-diagnostic-result__compare-value">{formatPercent(resultado.valorEstado)}</span>
                    <span className="pne-diagnostic-result__compare-diff">{formatSignedPercentagePoints(stateDifference)}</span>
                  </dd>
                </div>
              )}
              {resultado.municipiosNaReferencia === null ? null : (
                <div className="pne-diagnostic-result__compare-row">
                  <dt>
                    <span className="pne-diagnostic-result__compare-icon" aria-hidden="true"><UsersRound /></span>
                    Municípios na referência
                  </dt>
                  <dd className="pne-diagnostic-result__compare-values">
                    <span className="pne-diagnostic-support-reading__badge">
                      {`${resultado.municipiosNaReferencia} de ${resultado.municipiosComDado}`}
                    </span>
                  </dd>
                </div>
              )}
              {interval === null ? null : (
                <div className="pne-diagnostic-result__compare-row">
                  <dt>
                    <span className="pne-diagnostic-result__compare-icon" aria-hidden="true"><MapPinned /></span>
                    Intervalo municipal
                  </dt>
                  <dd className="pne-diagnostic-result__compare-values">
                    <span className="pne-diagnostic-result__compare-note">{interval}</span>
                  </dd>
                </div>
              )}
            </dl>
          </section>
        ) : null}
      </div>

      <footer className="pne-diagnostic-result__foot">
        <span className="pne-diagnostic-result__evo">
          <span className="pne-diagnostic-result__evo-icon" aria-hidden="true"><ChartColumnIncreasing /></span>
          {pneMethodLabel(resultado.metodo)}
        </span>
        <p className="pne-diagnostic-result__reading">
          {coverageHint === null ? methodReading : `${methodReading} ${coverageHint}.`}
        </p>
      </footer>
    </article>
  )
}

function RegionalPneTheme({
  category,
  index,
  totalMunicipalities,
}: {
  category: RegionalPneCategory
  index: number
  totalMunicipalities: number
}) {
  const reached = category.indicadores.filter(({ referencia, resultado }) => (
    referencia !== null
    && resultado.valor !== null
    && resultado.distanciaReferencia !== null
    && resultado.distanciaReferencia >= 0
  )).length
  const below = category.indicadores.filter(({ referencia, resultado }) => (
    referencia !== null
    && resultado.valor !== null
    && resultado.distanciaReferencia !== null
    && resultado.distanciaReferencia < 0
  )).length
  const titleId = `pne-${category.chave}`

  return (
    <article className="pne-diagnostic-theme" aria-labelledby={titleId} id={`pne-theme-${category.chave}`}>
      <details className="pne-diagnostic-theme__disclosure" open>
        <summary className="pne-diagnostic-theme__header">
          <div className="pne-diagnostic-theme__heading">
            <span className="pne-diagnostic-theme__icon" aria-hidden="true"><Target /></span>
            <div>
              <p>{`Tema ${index + 1}`}</p>
              <h3 id={titleId}>{category.label}</h3>
            </div>
          </div>
          <dl className="pne-diagnostic-theme-summary">
            <div><dt>Indicadores</dt><dd>{category.indicadores.length}</dd></div>
            <div><dt>Referências alcançadas</dt><dd>{reached}</dd></div>
            <div><dt>Abaixo da referência</dt><dd>{below}</dd></div>
          </dl>
        </summary>
        <div className="pne-diagnostic-theme__results">
          {category.indicadores.map((indicator) => (
            <RegionalPneResultCard
              indicator={indicator}
              key={indicator.chave}
              totalMunicipalities={totalMunicipalities}
            />
          ))}
        </div>
      </details>
    </article>
  )
}

function RegionalPanel({
  document,
  selectedMunicipalityId,
}: {
  document: RegionalDocument
  selectedMunicipalityId: string | null
}) {
  const { atendimento, educacao, matriculas, pagina, pne2026, regiao } = document
  const totalPoint = lastWithValue(matriculas.series.total)
  const integralPoint = lastWithValue(matriculas.series.integral)
  const integralShare = enrollmentShare(integralPoint, matriculas.series.total)
  const visibleCoverageIndicators = atendimento.indicadores.filter(
    (indicator) => lastWithValue(indicator.series) !== null,
  )
  const enrollmentBreakdownGroups = ENROLLMENT_BREAKDOWNS
    .map(({ key, label }) => {
      const breakdown = matriculas.series[key]
      const rows = orderedCategories(key, Object.keys(breakdown)).flatMap((category) => {
        const point = lastWithValue(breakdown[category])
        return point === null ? [] : [{ category, point }]
      })
      return { key, label, rows }
    })
    .filter(({ rows }) => rows.length > 0)
  const hasEnrollmentIndicators = totalPoint !== null
    || integralPoint !== null
    || enrollmentBreakdownGroups.length > 0
  const visibleEducationCounts = educacao.contagens.filter((indicator) => indicator.valor !== null)
  const schoolCount = visibleEducationCounts.find((indicator) => indicator.chave === 'escolas') ?? null
  const countGroups = (Object.keys(EDUCATION_GROUP_LABELS) as RegionalEducationCountGroup[])
    .map((group) => ({
      group,
      indicators: visibleEducationCounts.filter((indicator) => indicator.grupo === group),
    }))
    .filter(({ indicators }) => indicators.length > 0)
  const visibleQualityCategories = educacao.qualidade
    .map((category) => ({
      ...category,
      indicadores: category.indicadores.filter((indicator) => indicator.valor !== null),
    }))
    .filter(({ indicadores }) => indicadores.length > 0)
  const visibleVaarIndicators = educacao.vaar.indicadores.filter(
    (indicator) => indicator.valor !== null,
  )
  const hasEducationIndicators = visibleEducationCounts.length > 0
    || visibleQualityCategories.length > 0
    || visibleVaarIndicators.length > 0
  const visiblePneCategories = pne2026.categorias
    .map((category) => ({
      ...category,
      indicadores: category.indicadores.filter((indicator) => indicator.resultado.valor !== null),
    }))
    .filter(({ indicadores }) => indicadores.length > 0)
  const visiblePneIndicatorCount = visiblePneCategories.reduce(
    (total, category) => total + category.indicadores.length,
    0,
  )
  const visiblePneReferenceCount = visiblePneCategories.reduce(
    (total, category) => total + category.indicadores.filter(({ referencia }) => referencia !== null).length,
    0,
  )
  const navigationItems = [
    { label: 'Síntese', targetId: 'regiao-resumo' },
    ...(visiblePneIndicatorCount > 0
      ? [{ label: 'PNE 2026–2036', targetId: 'regiao-pne' }]
      : []),
    ...(visibleCoverageIndicators.length > 0 || hasEnrollmentIndicators
      ? [{
          label: 'Acesso e oferta',
          targetId: visibleCoverageIndicators.length > 0 ? 'regiao-atendimento' : 'regiao-matriculas',
        }]
      : []),
    ...(hasEducationIndicators
      ? [{ label: 'Indicadores', targetId: 'regiao-educacao' }]
      : []),
    { label: 'Território e fontes', targetId: 'regiao-municipios' },
  ]

  const municipalities = useMemo(
    () => [...regiao.municipios].sort((left, right) => left.nome.localeCompare(right.nome, 'pt-BR')),
    [regiao.municipios],
  )
  const selectedMunicipality = regiao.municipios.find(
    (municipality) => municipality.ibgeCode === selectedMunicipalityId,
  ) ?? null

  return (
    <div className="page-stack regional-page">
      <PnePageHeader
        actions={null}
        asideContent={(
          <>
            <span className="pne-page-header__aside-title">Abrangência</span>
            <strong className="pne-page-header__aside-highlight">
              {`${regiao.totalMunicipios} municípios`}
            </strong>
            <dl className="pne-page-header__facts">
              <div>
                <dt>Estado</dt>
                <dd>{ACTIVE_STATE_CONFIG.stateCode}</dd>
              </div>
              <div>
                <dt>Referência</dt>
                <dd>{selectedMunicipality?.nome ?? 'Município selecionado'}</dd>
              </div>
            </dl>
          </>
        )}
        asideLabel="Contexto territorial"
        context={null}
        description={pagina.descricao}
        eyebrow={pagina.eyebrow}
        title={pagina.titulo}
        variant="editorial"
      />

      <nav className="pne-overview-internal-nav regional-internal-nav" aria-label="Navegação nesta página">
        {navigationItems.map((item) => (
          <button
            key={item.targetId}
            type="button"
            onClick={() => navigateWithinRegionalPage(item.targetId)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <section aria-labelledby="regiao-resumo" className="regional-panel regional-panel--summary">
        <div className="regional-panel__head">
          <span className="eyebrow regional-panel__eyebrow">Síntese territorial</span>
          <h2 className="regional-panel__title" id="regiao-resumo">Resumo da região</h2>
          <p className="regional-panel__text">
            Estrutura da rede e posição nas referências quantitativas do PNE 2026–2036.
          </p>
        </div>
        <dl className="regional-highlights">
          <div className="regional-highlight">
            <dt><MapPinned aria-hidden="true" />Municípios</dt>
            <dd>{integerFormatter.format(regiao.totalMunicipios)}</dd>
            <span className="regional-highlight__meta">na região FIERGS</span>
          </div>
          {totalPoint === null ? null : (
            <div className="regional-highlight">
              <dt>
                <GraduationCap aria-hidden="true" />
                {`Matrículas${totalPoint.ano === null ? '' : ` em ${totalPoint.ano}`}`}
              </dt>
              <dd>{formatCount(totalPoint.valor)}</dd>
              <span className="regional-highlight__meta">total agregado</span>
            </div>
          )}
          {schoolCount === null ? null : (
            <div className="regional-highlight">
              <dt><School aria-hidden="true" />{`Escolas${schoolCount.ano === null ? '' : ` em ${schoolCount.ano}`}`}</dt>
              <dd>{formatCount(schoolCount.valor)}</dd>
              <span className="regional-highlight__meta">unidades escolares</span>
            </div>
          )}
          {integralShare === null ? null : (
            <div className="regional-highlight">
              <dt><Clock3 aria-hidden="true" />Matrículas em tempo integral</dt>
              <dd>{formatPercent(integralShare)}</dd>
              <span className="regional-highlight__meta">participação regional</span>
            </div>
          )}
          {pne2026.referenciasAvaliadas === 0 ? null : (
            <div className="regional-highlight regional-highlight--pne">
              <dt><Target aria-hidden="true" />Referências do PNE atingidas</dt>
              <dd>{`${pne2026.referenciasAtingidas} de ${pne2026.referenciasAvaliadas}`}</dd>
              <span className="regional-highlight__meta">entre as referências avaliadas</span>
            </div>
          )}
        </dl>
      </section>

      {visiblePneIndicatorCount === 0 ? null : (
        <section aria-labelledby="regiao-pne" className="pne-diagnostic-results regional-pne-results">
          <div className="pne-diagnostic-section-heading pne-diagnostic-section-heading--results">
            <p>Plano Nacional de Educação</p>
            <h2 id="regiao-pne">Metas e indicadores do PNE 2026–2036</h2>
            <span>{`${pne2026.referenciasAtingidas} de ${pne2026.referenciasAvaliadas} referências alcançadas`}</span>
          </div>
          <p className="regional-panel__text">{pne2026.descricao}</p>
          <p className="regional-panel__text">
            {`${visiblePneIndicatorCount} indicadores com resultado regional · ${visiblePneReferenceCount} com meta ou referência quantitativa.`}
          </p>
          <div className="regional-table-note">
            “Taxa regional” é a razão entre totais somados. “Mediana dos municípios” descreve a
            distribuição municipal e não deve ser lida como uma taxa agregada da região.
          </div>
          <div className="pne-diagnostic-themes">
            {visiblePneCategories.map((category, index) => (
              <RegionalPneTheme
                category={category}
                index={index}
                key={category.chave}
                totalMunicipalities={regiao.totalMunicipios}
              />
            ))}
          </div>
        </section>
      )}

      {visibleCoverageIndicators.length === 0 ? null : (
        <section aria-labelledby="regiao-atendimento" className="regional-panel">
          <div className="regional-panel__head">
            <span className="eyebrow regional-panel__eyebrow">Acesso educacional</span>
            <h2 className="regional-panel__title" id="regiao-atendimento">{atendimento.label}</h2>
            <p className="regional-panel__text">{atendimento.descricao}</p>
          </div>
          <div className="regional-table-scroll">
            <table className="regional-table">
              <caption className="u-sr-only">
                {`Atendimento por faixa etária na região ${regiao.nome}`}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Indicador</th>
                  <th scope="col">Resultado</th>
                  <th scope="col">Ano</th>
                  <th scope="col">Desde o início da série</th>
                  <th scope="col">Matrículas sobre população</th>
                </tr>
              </thead>
              <tbody>
                {visibleCoverageIndicators.map((indicator) => (
                  <CoverageRow indicator={indicator} key={indicator.chave} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {hasEnrollmentIndicators ? (
        <section aria-labelledby="regiao-matriculas" className="regional-panel">
          <div className="regional-panel__head">
            <span className="eyebrow regional-panel__eyebrow">Oferta e composição</span>
            <h2 className="regional-panel__title" id="regiao-matriculas">{matriculas.label}</h2>
            <p className="regional-panel__text">{matriculas.descricao}</p>
          </div>
          <p className="regional-panel__text">
            Os recortes não são divisões mutuamente exclusivas do total. Redes federal,
            estadual e municipal integram a rede pública; algumas etapas também se sobrepõem.
          </p>
          <div className="regional-table-scroll">
            <table className="regional-table">
              <caption className="u-sr-only">{`Matrículas na região ${regiao.nome}`}</caption>
              <thead>
                <tr>
                  <th scope="col">Recorte</th>
                  <th scope="col">Matrículas</th>
                  <th scope="col">Participação no total regional</th>
                  <th scope="col">Ano</th>
                </tr>
              </thead>
              <tbody>
                {totalPoint === null ? null : (
                  <EnrollmentRow
                    label="Total da educação básica"
                    point={totalPoint}
                    totalMunicipalities={regiao.totalMunicipios}
                    totals={matriculas.series.total}
                  />
                )}
                {integralPoint === null ? null : (
                  <EnrollmentRow
                    label="Em tempo integral"
                    point={integralPoint}
                    totalMunicipalities={regiao.totalMunicipios}
                    totals={matriculas.series.total}
                  />
                )}
                {enrollmentBreakdownGroups.flatMap(({ key, label, rows }) => {
                  return [
                    <tr className="regional-table__section" key={key}>
                      <th colSpan={4} scope="colgroup">{label}</th>
                    </tr>,
                    ...rows.map(({ category, point }) => (
                      <EnrollmentRow
                        key={`${key}-${category}`}
                        label={categoryLabel(category)}
                        point={point}
                        totalMunicipalities={regiao.totalMunicipios}
                        totals={matriculas.series.total}
                      />
                    )),
                  ]
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {hasEducationIndicators ? (
        <section
          aria-label="Indicadores educacionais"
          className="educacao-page regional-education-layout"
          id="regiao-educacao"
        >
          <div className="municipal-education-overview">
            {visibleEducationCounts.length === 0 ? null : (
              <EducationCountsOverview
                description={educacao.descricao}
                groups={countGroups}
                primaryIndicator={schoolCount}
                title={educacao.label}
              />
            )}
            {visibleQualityCategories.map((category) => (
              <RegionalQualitySection
                category={category}
                key={category.chave}
                regionName={regiao.nome}
                totalMunicipalities={regiao.totalMunicipios}
              />
            ))}
            {visibleVaarIndicators.length === 0 ? null : (
              <RegionalVaarOverview
                block={{ ...educacao.vaar, indicadores: visibleVaarIndicators }}
                regionName={regiao.nome}
              />
            )}
          </div>
        </section>
      ) : null}

      <section aria-labelledby="regiao-municipios" className="regional-panel">
        <div className="regional-panel__head">
          <span className="eyebrow regional-panel__eyebrow">Território</span>
          <h2 className="regional-panel__title" id="regiao-municipios">Municípios desta região</h2>
          <p className="regional-panel__text">
            A região é derivada do município selecionado; ele aparece destacado na lista.
          </p>
        </div>
        <ul className="regional-municipalities">
          {municipalities.map((municipality) => {
            const isSelected = municipality.ibgeCode === selectedMunicipalityId
            return (
              <li
                className={isSelected
                  ? 'regional-municipalities__item is-selected'
                  : 'regional-municipalities__item'}
                key={municipality.ibgeCode}
              >
                {municipality.nome}
                {isSelected ? <span className="u-sr-only"> (município selecionado)</span> : null}
              </li>
            )
          })}
        </ul>
      </section>

      <section aria-labelledby="regiao-metodologia" className="regional-panel regional-panel--support">
        <div className="regional-panel__head">
          <span className="eyebrow regional-panel__eyebrow">Transparência</span>
          <h2 className="regional-panel__title" id="regiao-metodologia">Como estes números são formados</h2>
        </div>
        <ul className="regional-list">
          {document.metodologia.map((note) => <li key={note}>{note}</li>)}
        </ul>
        <h3 className="regional-subtitle">Fontes</h3>
        <ul className="regional-list">
          {document.fontes.map((source) => (
            <li key={source.nome}>{`${source.nome} — ${source.uso}`}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export function AnaliseRegionalPage({
  municipalityId,
  selectedMunicipio,
}: {
  municipalityId: string | null
  selectedMunicipio: string | null
}) {
  const { data, loading } = useRegionalPanel(municipalityId)

  if (loading) {
    return <LoadingState message="Carregando o panorama da região…" />
  }

  if (!data) {
    return (
      <div className="page-stack regional-page">
        <PnePageHeader
          actions={null}
          asideContent={null}
          asideLabel={null}
          context={null}
          description={
            municipalityId
              ? `Não há região publicada para ${selectedMunicipio ?? 'o município selecionado'}.`
              : 'Selecione um município para ver a região a que ele pertence.'
          }
          eyebrow="Análise regional"
          title="Panorama da Região"
          variant="editorial"
        />
      </div>
    )
  }

  return <RegionalPanel document={data.document} selectedMunicipalityId={municipalityId} />
}
