import { ExplorableIndicatorCardFrame } from './ExplorableIndicatorCardFrame'
import {
  formatSchoolInfrastructurePercentage,
  formatSchoolInfrastructureQuantity,
} from '../data/schoolInfrastructureContract'

const EM = '\u2014'
const EDUCATION_CARD_CLASS_CONTRACT = Object.freeze({
  root: 'education-indicator-card',
  statusModifier: (tone) => `education-indicator-card--${tone}`,
  topline: 'education-indicator-card__topline',
  context: 'education-indicator-card__theme',
  title: 'education-indicator-card__title',
  description: 'education-indicator-card__description',
  valueRow: 'education-indicator-card__value-row',
  metadata: 'education-indicator-card__metadata',
  metadataItem: 'education-indicator-card__metadata-item',
  metadataLabel: 'education-indicator-card__metadata-label',
  metadataValue: 'education-indicator-card__metadata-value',
  divider: 'education-indicator-card__divider',
  insight: 'education-indicator-card__insight',
  insightItem: 'education-indicator-card__insight-item',
  insightLabel: 'education-indicator-card__insight-label',
  insightValue: 'education-indicator-card__insight-value',
  footer: 'education-indicator-card__footer',
  action: 'education-indicator-card__action',
})

const PEDAGOGICAL_RESOURCE_CARD_COPY = Object.freeze({
  proposta_pedagogica: {
    title: 'Escolas públicas com projeto político-pedagógico',
    description: 'Escolas públicas com projeto político-pedagógico ou proposta pedagógica.',
  },
  desktop_aluno: {
    title: 'Escolas com computadores de mesa para alunos',
    description: 'Escolas com computadores de mesa disponíveis para os alunos.',
  },
  comp_portatil_aluno: {
    title: 'Escolas com computadores portáteis para alunos',
    description: 'Escolas com computadores portáteis disponíveis para os alunos.',
  },
  tablet_aluno: {
    title: 'Escolas com tablets para alunos',
    description: 'Escolas com tablets disponíveis para os alunos.',
  },
})

export function EducationIndicatorCard({
  buttonRef,
  indicator,
  isDisabled = false,
  isSelected = false,
  onSelect,
}) {
  if (indicator.cardVariant === 'school-infrastructure-composite') {
    return (
      <SchoolInfrastructureCompositeCard
        buttonRef={buttonRef}
        indicator={indicator}
        isDisabled={isDisabled}
        onSelect={onSelect}
      />
    )
  }

  const isExploratory = indicator.cardVariant === 'exploratory'
  const isPedagogicalResource = indicator.groupKey === 'equipamentos-recursos'
  const pedagogicalCardCopy = isPedagogicalResource ? PEDAGOGICAL_RESOURCE_CARD_COPY[indicator.key] : null
  const exploratorySummary = indicator.exploratorySummary ?? {}
  const contextLabel = indicator.themeShortLabel ?? indicator.themeLabel ?? (isExploratory ? 'Escolas' : 'Indicador')
  const currentDisplay = indicator.currentDisplay ?? EM
  const currentYear = isExploratory ? exploratorySummary.latestYear : indicator.currentYear
  const hasCurrentValue = Number.isFinite(Number(indicator.currentValue)) && currentDisplay !== EM && currentDisplay !== ''
  const comparison = !isExploratory && !indicator.snapshotOnly && hasCurrentValue
    ? getPreviousComparablePoint(indicator, currentYear)
    : null
  const variationDisplay = comparison ? formatCardVariation(indicator, comparison.value) : null
  const seriesPeriod = isExploratory ? null : getCardSeriesPeriod(indicator.series, currentYear)
  const hasSeries = !indicator.snapshotOnly && Boolean(seriesPeriod)
  const direction = getCardDirection({
    comparison,
    hasCurrentValue,
    isExploratory,
  })
  const reading = indicator.cardReading ?? getCardReading({
    comparison,
    currentValue: indicator.currentValue,
    direction,
    hasCurrentValue,
    initialYear: seriesPeriod?.initialYear,
    isExploratory,
    neutralTrend: indicator.neutralTrend,
    zeroMessage: indicator.zeroMessage,
  })
  /*
   * O selo descreve a MESMA comparacao que o cartao exibe.
   *
   * Antes o rotulo preferia indicator.statusLabel, que vem de
   * getIndicatorStatus e compara o valor atual com o primeiro ano da serie
   * inteira, enquanto o marcador (seta) sempre saiu de comparison.difference,
   * que e a variacao ano a ano mostrada logo abaixo em "Var. desde". Os dois
   * periodos podem divergir com toda razao -- e o cartao entao exibia
   * "aumento 95 alunos" ao lado de um selo escrito "Queda".
   *
   * Havendo comparacao no cartao, ela manda no rotulo, no tom e na seta.
   * O rotulo externo continua valendo quando nao ha comparacao, que e o caso
   * de "Situacao em 2025" e de series com um unico ano.
   */
  const comparisonLabel = comparison ? getDirectionLabel(direction, indicator.neutralTrend) : null
  const statusLabel = comparisonLabel ?? indicator.statusLabel ?? null
  const comparisonTone = comparison
    ? (indicator.neutralTrend ? 'muted' : getDirectionTone(direction))
    : null
  const statusTone = comparisonTone ?? indicator.statusTone ?? 'default'
  const unitLabel = getCardUnitLabel(indicator)
  const footerLabel = isExploratory
    ? 'Abrir panorama'
    : hasSeries
      ? 'Ver série histórica'
      : 'Abrir detalhes'
  const footerContext = isPedagogicalResource
    ? 'Recursos pedagógicos'
    : indicator.stageLabel
    ?? indicator.mainCutLabel
    ?? indicator.recortePrincipal
    ?? indicator.categoryLabel
    ?? contextLabel
  const title = isExploratory
    ? indicator.cardTitle
    : pedagogicalCardCopy?.title ?? indicator.label
  const description = String(
    isExploratory
      ? 'Condições básicas, espaços escolares, conectividade e equipamentos disponíveis nas escolas.'
      : pedagogicalCardCopy?.description ?? indicator.description ?? '',
  ).trim()
  const value = isExploratory
    ? {
        display: exploratorySummary.count ?? EM,
        metaLabel: 'indicadores',
      }
    : {
        display: currentDisplay,
        metaLabel: unitLabel,
      }
  const ariaLabel = isExploratory
    ? [
        `Abrir panorama da infraestrutura escolar. ${title}.`,
        `${exploratorySummary.count ?? EM} indicadores, ano ${exploratorySummary.latestYear ?? 'indisponível'}.`,
        description ? `Descrição: ${description}.` : '',
      ].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim()
    : [
        `Abrir detalhe do indicador ${title}.`,
        `Valor ${currentDisplay},`,
        currentYear ? `ano ${currentYear}.` : 'ano indisponível.',
        statusLabel ? `${statusLabel}.` : '',
        variationDisplay ? `Variação em relação a ${comparison.year}: ${variationDisplay}.` : '',
        description ? `Descrição: ${description}.` : '',
      ].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim()

  const viewModel = {
    anatomy: 'education',
    ariaLabel,
    contextLabel,
    description,
    footer: {
      icon: null,
      primary: isExploratory ? footerLabel : footerContext,
      actionLabel: footerLabel,
    },
    featureMeta: isExploratory
      ? [
          {
            label: 'indicadores',
            value: exploratorySummary.count ?? EM,
            valueFirst: true,
          },
          {
            label: 'Referência',
            value: exploratorySummary.latestYear ?? 'Indisponível',
          },
        ]
      : null,
    hideStatus: !comparison && !indicator.snapshotOnly,
    hideContext: isExploratory || isPedagogicalResource,
    insight: {
      context: null,
      direction,
      emphasis: reading,
      label: indicator.snapshotOnly && currentYear ? `Situação em ${currentYear}` : 'Leitura',
      marker: null,
      reading,
      period: null,
    },
    metadata: {
      year: currentYear ?? 'Indisponível',
      yearLabel: isExploratory ? 'Referência' : 'Ano',
      variation: comparison
        ? {
            label: `Var. desde ${comparison.year}`,
            value: variationDisplay,
          }
        : null,
    },
    status: {
      direction,
      label: statusLabel,
      marker: getDirectionMarker(direction),
      tone: statusTone,
    },
    title,
    value,
    modifier: isExploratory
      ? ['panorama-entry', 'panorama-feature']
      : isPedagogicalResource
        ? 'compact-copy'
        : null,
    variant: indicator.cardVariant,
  }

  return (
    <ExplorableIndicatorCardFrame
      buttonRef={buttonRef}
      classContract={EDUCATION_CARD_CLASS_CONTRACT}
      disabled={isDisabled}
      isSelected={isSelected}
      onSelect={onSelect}
      viewModel={viewModel}
    />
  )
}

function SchoolInfrastructureCompositeCard({
  buttonRef,
  indicator,
  isDisabled,
  onSelect,
}) {
  const dimensions = indicator.schoolInfrastructureDimensions ?? []
  const ariaLabel = [
    `Abrir panorama de ${indicator.label}.`,
    ...dimensions.map(({ label, result }) =>
      `${label}: ${formatSchoolInfrastructurePercentage(result)}, ${formatSchoolInfrastructureQuantity(result)} escolas.`),
  ].join(' ')

  return (
    <button
      aria-label={ariaLabel}
      className="school-infrastructure-composite-card"
      disabled={isDisabled}
      onClick={onSelect}
      ref={buttonRef}
      type="button"
    >
      <span className="school-infrastructure-composite-card__heading">
        <span className="school-infrastructure-composite-card__copy">
          <strong>{indicator.label}</strong>
          <span>{indicator.description}</span>
        </span>
        <span className="school-infrastructure-composite-card__action">
          Abrir panorama <span aria-hidden="true">›</span>
        </span>
      </span>
      <span className="school-infrastructure-composite-card__metrics">
        {dimensions.map(({ key, label, result }) => {
          const quantity = formatSchoolInfrastructureQuantity(result)
          return (
            <span
              className="school-infrastructure-composite-card__metric"
              key={key}
            >
              <span className="school-infrastructure-composite-card__label">{label}</span>
              <strong className="school-infrastructure-composite-card__value">
                {formatSchoolInfrastructurePercentage(result)}
              </strong>
              <small>{quantity === 'Não se aplica' || quantity === 'Não disponível' ? quantity : `${quantity} escolas`}</small>
            </span>
          )
        })}
      </span>
    </button>
  )
}

function getCardDirection({ comparison, hasCurrentValue, isExploratory }) {
  if (!hasCurrentValue) return 'missing'
  if (isExploratory || !comparison) return 'data'
  if (comparison.difference > 0) return 'up'
  if (comparison.difference < 0) return 'down'
  return 'stable'
}

function getDirectionLabel(direction, neutralTrend = false) {
  if (direction === 'up') return neutralTrend ? 'Aumento' : 'Alta'
  if (direction === 'down') return neutralTrend ? 'Redução' : 'Queda'
  if (direction === 'stable') return neutralTrend ? 'Estabilidade' : 'Estável'
  return null
}

function getDirectionTone(direction) {
  if (direction === 'up') return 'success'
  if (direction === 'down') return 'warning'
  if (direction === 'stable') return 'muted'
  return 'default'
}

function getDirectionMarker(direction) {
  if (direction === 'up') return '\u2197'
  if (direction === 'stable') return '\u2192'
  if (direction === 'down') return '\u2198'
  return ''
}

function getCardReading({ comparison, currentValue, direction, hasCurrentValue, initialYear, isExploratory, neutralTrend, zeroMessage }) {
  if (isExploratory) return 'Panorama disponível por dimensão'
  if (!hasCurrentValue) return 'Leitura recente indisponível'
  if (Number(currentValue) === 0 && zeroMessage) return zeroMessage
  if (!comparison) return initialYear ? `Série disponível a partir de ${initialYear}` : 'Sem ano anterior comparável'
  if (direction === 'up') return neutralTrend ? 'Aumento recente' : 'Crescimento recente'
  if (direction === 'down') return 'Redução recente'
  return 'Estabilidade recente'
}

function getCardUnitLabel(indicator) {
  const unit = String(indicator.unit ?? '').trim()
  if (!unit || indicator.formatType === 'percent' || unit.toLocaleLowerCase('pt-BR') === 'percentual') return null
  return unit
}

function getPreviousComparablePoint(indicator, currentYear) {
  const currentValue = Number(indicator.currentValue)
  if (!Number.isFinite(currentValue)) return null

  const points = (Array.isArray(indicator.series) ? indicator.series : [])
    .filter((point) => point?.valor !== null && point?.valor !== undefined)
    .map((point) => ({ year: Number(point?.ano), value: Number(point?.valor) }))
    .filter((point) => Number.isFinite(point.year) && Number.isFinite(point.value))
    .sort((a, b) => a.year - b.year)
  const numericCurrentYear = Number(currentYear)
  const candidates = Number.isFinite(numericCurrentYear)
    ? points.filter((point) => point.year < numericCurrentYear)
    : points.slice(0, -1)
  const previous = candidates.at(-1)

  return previous
    ? { ...previous, difference: currentValue - previous.value }
    : null
}

function getCardSeriesPeriod(series, currentYear) {
  const years = (Array.isArray(series) ? series : [])
    .map((point) => Number(point?.ano))
    .filter(Number.isFinite)
    .sort((a, b) => a - b)
  if (!years.length) return null

  const numericCurrentYear = Number(currentYear)
  const initialYear = years[0]
  const finalYear = Number.isFinite(numericCurrentYear) ? numericCurrentYear : years.at(-1) ?? null

  if (!initialYear || !finalYear) return null
  return {
    initialYear,
    label: initialYear === finalYear ? `Desde ${initialYear}` : `${initialYear}\u2013${finalYear}`,
  }
}

function formatCardVariation(indicator, comparisonValue) {
  const previousValue = Number(comparisonValue)
  const currentValue = Number(indicator.currentValue)
  if (!Number.isFinite(previousValue) || !Number.isFinite(currentValue)) return null

  const difference = currentValue - previousValue
  const format = typeof indicator.formatValue === 'function'
    ? indicator.formatValue
    : (value) => Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  const formattedDifference = indicator.formatType === 'percent'
    ? Math.abs(difference).toLocaleString('pt-BR', { maximumFractionDigits: 1 })
    : String(format(Math.abs(difference))).replace(/^[+\-−]\s*/, '')
  const signedDifference = difference > 0
    ? `+${formattedDifference}`
    : difference < 0
      ? `−${formattedDifference}`
      : formattedDifference

  if (indicator.formatType === 'percent') return `${signedDifference} p.p.`
  const unit = getCardUnitLabel(indicator)
  return unit ? `${signedDifference} ${unit}` : signedDifference
}
