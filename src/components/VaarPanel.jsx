import { isMissing } from '../utils/educationFormatters'
import { isPublishableFinancialValue } from '../utils/financialPresentation'
import {
  FinancialKpiCard,
  FinancialKpiGrid,
  FinancialNarrativeCard,
  FinancialSection,
  FinancialSourcesFooter,
} from './FinancialIndicatorPrimitives'
import { DisclosureChevron } from './DisclosureChevron'
import { StatusBadge } from './StatusBadge'

const EM = '\u2014'

const FIELD_HELP = {
  habilitado_condicionalidades: {
    label: 'Habilitação',
    short: 'Indica se o município cumpriu as condicionalidades de gestão exigidas para concorrer ao VAAR.',
  },
  indicador_aprendizagem: {
    label: 'Indicador de aprendizagem',
    short: 'Síntese em escala de 0 a 10 que combina aprendizagem, avanço, aprovação, participação no Saeb e equidade.',
  },
  delta_aprendizagem: {
    label: 'Variação da aprendizagem',
    short: 'Diferença do indicador de aprendizagem entre ciclos do próprio município.',
  },
  delta_aprendizagem_ajustado: {
    label: 'Variação ajustada de aprendizagem',
    short: 'Variação após aplicação da regra metodológica, quando disponível.',
  },
  iad: {
    label: 'IAD - avanço de desempenho',
    short: 'Indicador de avanço de desempenho entre edições do Saeb.',
  },
  iad_ajustado: {
    label: 'IAD ajustado',
    short: 'IAD após tratamento de pequenas oscilações dentro da margem de erro.',
  },
  proporcao_adequada_saeb_2019: {
    label: 'Aprendizado adequado - Saeb 2019',
    short: 'Percentual de estudantes com desempenho igual ou acima do nível adequado no Saeb.',
  },
  proporcao_adequada_saeb_2023: {
    label: 'Aprendizado adequado - Saeb 2023',
    short: 'Percentual de estudantes com desempenho igual ou acima do nível adequado no Saeb.',
  },
  taxa_aprovacao_penalizada_2019: {
    label: 'Aprovação penalizada - 2019',
    short: 'Taxa de aprovação ajustada pela ausência de informação de rendimento ou movimento.',
  },
  taxa_aprovacao_penalizada_2023: {
    label: 'Aprovação penalizada - 2023',
    short: 'Taxa de aprovação ajustada pela ausência de informação de rendimento ou movimento.',
  },
  equidade_2023: {
    label: 'Índice de equidade calculado com Saeb 2023',
    short: 'Medida associada à aprendizagem de grupos vulneráveis.',
  },
  indicador_atendimento_anterior: {
    label: 'Indicador de atendimento anterior',
    short: 'Indicador do ano-base anterior, usado para leitura da variação.',
  },
  indicador_atendimento_atual: {
    label: 'Indicador de atendimento atual',
    short: 'Indicador do ano-base atual. Mede permanência dos estudantes.',
  },
  delta_atendimento: {
    label: 'Variação do atendimento',
    short: 'Diferença entre o indicador atual e o anterior.',
  },
  delta_atendimento_ajustado: {
    label: 'Variação ajustada do atendimento',
    short: 'Variação após aplicação da regra metodológica, quando disponível.',
  },
  estudantes_areas_prioritarias_anterior: {
    label: 'Estudantes em áreas prioritárias - anterior',
    short: 'Total de estudantes considerados no cálculo no ano-base anterior.',
  },
  estudantes_areas_prioritarias_atual: {
    label: 'Estudantes em áreas prioritárias - atual',
    short: 'Total de estudantes considerados no cálculo no ano-base atual.',
  },
  proporcao_abandono_anterior: {
    label: 'Abandono anterior',
    short: 'Proporção de estudantes que deixaram de frequentar a escola no ano-base anterior.',
  },
  proporcao_abandono_atual: {
    label: 'Abandono atual',
    short: 'Proporção de estudantes que deixaram de frequentar a escola no ano-base atual.',
  },
  proporcao_sem_informacao_anterior: {
    label: 'Sem informação anterior',
    short: 'Proporção de estudantes sem informação final de rendimento ou movimento no ano-base anterior.',
  },
  proporcao_sem_informacao_atual: {
    label: 'Sem informação de rendimento/movimento - atual',
    short: 'Proporção de estudantes sem informação final de rendimento ou movimento no ano-base atual.',
  },
  indicador_atendimento_metodologia_anterior: {
    label: 'Indicador atendimento',
    short: 'Indicador de melhoria do atendimento na regra histórica do VAAR.',
  },
  evolucao_atendimento_metodologia_anterior: {
    label: 'Evolução atendimento',
    short: 'Evolução da melhoria do atendimento na regra histórica do VAAR.',
  },
  coeficiente_atendimento: {
    label: 'Coeficiente atendimento',
    short: 'Coeficiente de distribuição do componente atendimento.',
  },
  indicador_aprendizagem_metodologia_anterior: {
    label: 'Indicador aprendizagem',
    short: 'Indicador de melhoria de aprendizagem com equidade na regra histórica do VAAR.',
  },
  evolucao_aprendizagem_metodologia_anterior: {
    label: 'Evolução aprendizagem',
    short: 'Evolução da melhoria de aprendizagem na regra histórica do VAAR.',
  },
  coeficiente_aprendizagem: {
    label: 'Coeficiente aprendizagem',
    short: 'Coeficiente de distribuição do componente aprendizagem com equidade.',
  },
  coeficiente_total: {
    label: 'Coeficiente de distribuição total',
    short: 'Coeficiente total de distribuição da complementação VAAR no exercício.',
  },
  apresentou_evolucao_nos_dois_indicadores: {
    label: 'Evolução nos dois indicadores',
    short: 'Indica se a fonte registrou evolução simultânea nos componentes de aprendizagem e atendimento.',
  },
}

const LEARNING_DETAIL_METRICS = [
  ['indicador_aprendizagem', 'decimal'],
  ['delta_aprendizagem', 'signedDecimal'],
  ['delta_aprendizagem_ajustado', 'signedDecimal'],
  ['iad', 'decimal'],
  ['iad_ajustado', 'decimal'],
  ['proporcao_adequada_saeb_2019', 'percent'],
  ['proporcao_adequada_saeb_2023', 'percent'],
  ['taxa_aprovacao_penalizada_2019', 'percent'],
  ['taxa_aprovacao_penalizada_2023', 'percent'],
  ['equidade_2023', 'decimal'],
]

const ATTENDANCE_DETAIL_METRICS = [
  ['indicador_atendimento_atual', 'decimal'],
  ['proporcao_abandono_atual', 'percent'],
  ['proporcao_sem_informacao_atual', 'percent'],
  ['delta_atendimento', 'signedDecimal'],
  ['delta_atendimento_ajustado', 'signedDecimal'],
  ['indicador_atendimento_anterior', 'decimal'],
  ['proporcao_abandono_anterior', 'percent'],
  ['proporcao_sem_informacao_anterior', 'percent'],
  ['estudantes_areas_prioritarias_atual', 'integer'],
  ['estudantes_areas_prioritarias_anterior', 'integer'],
]

const HISTORICAL_METRICS = [
  ['indicador_atendimento_metodologia_anterior', 'decimal'],
  ['evolucao_atendimento_metodologia_anterior', 'decimal'],
  ['coeficiente_atendimento', 'decimal'],
  ['indicador_aprendizagem_metodologia_anterior', 'decimal'],
  ['evolucao_aprendizagem_metodologia_anterior', 'decimal'],
  ['coeficiente_aprendizagem', 'decimal'],
  ['coeficiente_total', 'decimal'],
  ['apresentou_evolucao_nos_dois_indicadores', 'boolean'],
]

const GLOSSARY_ITEMS = [
  ['VAAR', 'Complementação financeira do Fundeb baseada em condicionalidades e evolução de resultados.'],
  ['Condicionalidades', 'Requisitos de gestão que habilitam o município a concorrer à complementação.'],
  ['Aprendizagem com Equidade', 'Componente que observa evolução da aprendizagem com critérios de equidade.'],
  ['Atendimento', 'Componente associado à permanência dos estudantes, abandono e completude dos registros.'],
  ['Variação', 'Diferença entre ciclos do próprio indicador do município.'],
  ['Abandono', 'Estudantes que deixaram de frequentar a escola no ano letivo; menor valor é mais favorável.'],
  ['Sem informação', 'Estudantes sem registro final de rendimento ou movimento; isso pode reduzir o indicador de atendimento.'],
  ['Coeficiente de distribuição', 'Número usado para calcular a participação do município na parcela de recursos do componente, quando elegível.'],
  ['Histórico de 2023/2024', 'Anos que seguem regras anteriores e aparecem como consulta histórica de recebimento.'],
]

function formatBoolean(value) {
  if (value === true) return 'Sim'
  if (value === false) return 'Não'
  return EM
}

function formatReceived(value) {
  if (value === true) return 'Recebeu'
  if (value === false) return 'Não recebeu'
  return EM
}

function hasNumber(value) {
  return !isMissing(value) && isPublishableFinancialValue(Number(value))
}

function hasMetricValue(row, key, type) {
  const value = row?.[key]
  if (type === 'boolean') return value === true || value === false
  return hasNumber(value)
}

function hasMetricValues(row, metrics) {
  return metrics.some(([key, type]) => hasMetricValue(row, key, type))
}

function formatMetric(value, type = 'decimal') {
  if (type === 'boolean') return formatBoolean(value)
  if (type === 'signedDecimal') return formatSignedMetric(value)
  if (type === 'signedDecimalOptional') return hasNumber(value) ? formatSignedMetric(value) : null
  if (!hasNumber(value)) return EM
  const numeric = Number(value)
  if (type === 'integer') return numeric.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
  if (type === 'percent') {
    return `${(numeric * 100).toLocaleString('pt-BR', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })}%`
  }
  return numeric.toLocaleString('pt-BR', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 4,
  })
}

function formatSignedMetric(value) {
  if (!hasNumber(value)) return EM
  const numeric = Number(value)
  const formatted = Math.abs(numeric).toLocaleString('pt-BR', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 4,
  })
  if (numeric > 0) return `+${formatted}`
  if (numeric < 0) return `-${formatted}`
  return formatted
}

function formatCurrency(value) {
  if (!hasNumber(value)) return EM
  return Number(value).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
}

function buildResultText(summary, year) {
  const learning = summary?.recebe_aprendizagem
  const attendance = summary?.recebe_atendimento
  if (learning === true && attendance === true) {
    return `O município recebeu os componentes de Aprendizagem e Atendimento em ${year}.`
  }
  if (learning === true && attendance === false) {
    return `O município recebeu Aprendizagem em ${year}, mas não recebeu Atendimento.`
  }
  if (learning === false && attendance === true) {
    return `O município recebeu Atendimento em ${year}, mas não recebeu Aprendizagem.`
  }
  if (learning === false && attendance === false) {
    return `O município não recebeu os componentes de Aprendizagem e Atendimento em ${year}.`
  }
  return null
}

function compareNumbers(current, previous) {
  if (!hasNumber(current) || !hasNumber(previous)) return null
  const diff = Number(current) - Number(previous)
  if (Math.abs(diff) < 0.0000001) return 'stable'
  return diff > 0 ? 'up' : 'down'
}

function buildObservedChange(indicator, value) {
  if (!hasNumber(value)) return null
  if (Number(value) > 0) return `O indicador de ${indicator} aumentou no período considerado.`
  if (Number(value) < 0) return `O indicador de ${indicator} reduziu no período considerado.`
  return `O indicador de ${indicator} permaneceu estável no período considerado.`
}

function getLatestRow(rows, year) {
  if (!rows.length) return {}
  return rows.find((row) => Number(row.ano_fundeb) === Number(year)) ?? rows.at(-1) ?? {}
}

function FieldLabel({ field, label: customLabel }) {
  const help = FIELD_HELP[field]
  const label = customLabel ?? help?.label ?? field
  return (
    <span className="vaar-field-label">
      <span>{label}</span>
      {help?.short ? (
        <span
          aria-label={`${label}: ${help.short}`}
          className="vaar-help"
          data-help={help.short}
          role="img"
          tabIndex="0"
          title={help.short}
        >
          i
        </span>
      ) : null}
    </span>
  )
}

function VaarStatusPill({ value }) {
  if (value !== true && value !== false) return null
  const tone = value === true ? 'success' : value === false ? 'warning' : 'default'
  return <StatusBadge className="vaar-status-badge" displayStatus={formatReceived(value)} status={formatReceived(value)} tone={tone} />
}

function VaarResultMetric({ label, value, note, tone = 'default' }) {
  if (value === EM || value === null || value === undefined) return null
  return <FinancialKpiCard label={label} meta={note} tone={tone} value={value} />
}

function VaarAccordionSummary({ children }) {
  return (
    <><div><h3>{children}</h3></div><DisclosureChevron /></>
  )
}

function MetricList({ labels = {}, row, metrics }) {
  const visibleMetrics = metrics.filter(([key, type]) => hasMetricValue(row, key, type))
  if (!visibleMetrics.length) return null

  return (
    <dl className="vaar-metric-list">
      {visibleMetrics.map(([key, type]) => {
        const formatted = formatMetric(row?.[key], type)
        return (
          <div className="vaar-metric-row" key={key}>
            <dt><FieldLabel field={key} label={labels[key]} /></dt>
            <dd>{formatted}</dd>
          </div>
        )
      })}
    </dl>
  )
}

function VaarHistory({ history, lastYear }) {
  const orderedHistory = [...history]
    .filter((row) => (
      row.recebe_aprendizagem === true
      || row.recebe_aprendizagem === false
      || row.recebe_atendimento === true
      || row.recebe_atendimento === false
    ))
    .sort((a, b) => Number(b.ano_fundeb) - Number(a.ano_fundeb))
  const currentMethod = orderedHistory.filter((row) => Number(row.ano_fundeb) >= 2025)
  const previousMethod = orderedHistory.filter((row) => Number(row.ano_fundeb) <= 2024)
  if (!currentMethod.length && !previousMethod.length) return null

  return (
    <FinancialSection
      className="vaar-section"
      description="Os exercícios são apresentados em blocos distintos porque as metodologias não formam uma série contínua."
      eyebrow="Histórico"
      title="Histórico"
      titleId="vaar-history-title"
    >
      {currentMethod.length ? (
        <section aria-labelledby="vaar-current-method-title">
          <h3 id="vaar-current-method-title">Metodologia 2025–2026</h3>
          <p className="vaar-subtle-note">Resultados publicados segundo a metodologia atual.</p>
          <VaarHistoryCards rows={currentMethod} lastYear={lastYear} />
        </section>
      ) : null}
      {previousMethod.length ? (
        <section aria-labelledby="vaar-previous-method-title">
          <h3 id="vaar-previous-method-title">Metodologia 2023–2024</h3>
          <p className="vaar-subtle-note">Consulta histórica com regras anteriores, sem continuidade direta com 2025–2026.</p>
          <VaarHistoryCards rows={previousMethod} lastYear={lastYear} />
        </section>
      ) : null}
    </FinancialSection>
  )
}

function VaarHistoryCards({ rows, lastYear }) {
  return (
    <div className="vaar-history-grid">
      {rows.map((row) => {
        const isLatest = Number(row.ano_fundeb) === Number(lastYear)
        return (
          <FinancialNarrativeCard className={`platform-info-card vaar-history-card${isLatest ? ' is-latest' : ''}`} key={row.ano_fundeb}>
            <div className="vaar-history-card__top">
              <strong>{row.ano_fundeb}</strong>
              {isLatest ? <StatusBadge status="Mais recente" tone="info" /> : null}
            </div>
            <dl>
              {row.recebe_aprendizagem === true || row.recebe_aprendizagem === false ? (
                <div><dt>Aprendizagem</dt><dd>{formatBoolean(row.recebe_aprendizagem)}</dd></div>
              ) : null}
              {row.recebe_atendimento === true || row.recebe_atendimento === false ? (
                <div><dt>Atendimento</dt><dd>{formatBoolean(row.recebe_atendimento)}</dd></div>
              ) : null}
            </dl>
          </FinancialNarrativeCard>
        )
      })}
    </div>
  )
}

function TechnicalDetails({ title, rows, metrics }) {
  const visibleRows = rows.filter((row) => hasMetricValues(row, metrics))
  if (!visibleRows.length) return null

  return (
    <details className="platform-support-disclosure vaar-detail-toggle vaar-technical-details">
      <summary className="platform-support-disclosure__summary"><VaarAccordionSummary>{title}</VaarAccordionSummary></summary>
      <div className="vaar-year-grid">
        {visibleRows.map((row) => (
          <FinancialNarrativeCard className="platform-info-card vaar-year-card" key={row.ano_fundeb}>
            <div className="vaar-year-card__header">
              <span>Exercício financeiro</span>
              <strong>{row.ano_fundeb ?? EM}</strong>
            </div>
            <MetricList row={row} metrics={metrics} />
          </FinancialNarrativeCard>
        ))}
      </div>
    </details>
  )
}

function VaarHistoricalDetails({ rows }) {
  const visibleRows = rows.filter((row) => hasMetricValues(row, HISTORICAL_METRICS))
  if (!visibleRows.length) return null

  return (
    <details className="platform-support-disclosure vaar-detail-toggle vaar-technical-details">
      <summary className="platform-support-disclosure__summary"><VaarAccordionSummary>Consultar dados históricos de 2023/2024</VaarAccordionSummary></summary>
      <div className="vaar-year-grid">
          {visibleRows.map((row) => (
            <FinancialNarrativeCard className="platform-info-card vaar-year-card" key={row.ano_fundeb}>
              <div className="vaar-year-card__header">
                <span>Exercício financeiro</span>
                <strong>{row.ano_fundeb ?? EM}</strong>
              </div>
              <MetricList row={row} metrics={HISTORICAL_METRICS} />
            </FinancialNarrativeCard>
          ))}
      </div>
      <div className="vaar-reading__notes">
        <small>Os dados de 2023/2024 seguem a metodologia anterior e não formam série contínua com 2025/2026.</small>
      </div>
    </details>
  )
}

function VaarMainSummary({ financialData, summary, lastYear }) {
  const hasStatus = summary?.habilitado_condicionalidades === true
    || summary?.habilitado_condicionalidades === false
    || summary?.recebe_aprendizagem === true
    || summary?.recebe_aprendizagem === false
    || summary?.recebe_atendimento === true
    || summary?.recebe_atendimento === false
  if (!hasStatus) return null

  const forecast = financialData?.amounts?.fundebVaarAnnualForecast
  const hasForecast = isPublishableFinancialValue(forecast)
  const resultText = buildResultText(summary, lastYear ?? EM)

  return (
    <FinancialSection
      className="vaar-executive-result"
      description="Habilitação e situação dos componentes no exercício."
      eyebrow="Resumo principal"
      title={`Resultado do município em ${lastYear ?? EM}`}
      titleId="vaar-result-title"
    >
      {resultText ? <p className="vaar-executive-result__reading">{resultText}</p> : null}
      <FinancialKpiGrid className="vaar-result-metrics">
        <VaarResultMetric label="Habilitação" value={formatBoolean(summary.habilitado_condicionalidades)} note="Condicionalidades" />
        <VaarResultMetric label="Componente Aprendizagem" value={formatReceived(summary.recebe_aprendizagem)} note="Resultado no exercício" />
        <VaarResultMetric label="Componente Atendimento" value={formatReceived(summary.recebe_atendimento)} note="Resultado no exercício" />
        {hasForecast ? (
          <VaarResultMetric
            label="Previsão VAAR"
            value={formatCurrency(forecast.value)}
            note={`Previsão oficial${forecast.referenceYear ? ` · ${forecast.referenceYear}` : ''}`}
            tone="forecast"
          />
        ) : null}
      </FinancialKpiGrid>
    </FinancialSection>
  )
}

function VaarComponentReason({ label, labels, metrics, reason, row, status, variation }) {
  const visibleMetrics = metrics.filter(([key, type]) => hasMetricValue(row, key, type))

  return (
    <FinancialNarrativeCard className="platform-info-card vaar-component-card">
      <div className="vaar-component-card__header">
        <h3>{label}</h3>
        <VaarStatusPill value={status} />
      </div>
      <div className="vaar-component-card__result">
        <span>Resultado do componente</span>
        <p>{reason || 'Resultado publicado para o componente no exercício.'}</p>
      </div>
      {variation ? (
        <div className="vaar-component-card__variation">
          <span>Mudança observada</span>
          <strong>{variation}</strong>
        </div>
      ) : null}
      {visibleMetrics.length ? (
        <div className="vaar-component-card__evidence">
          <span>Informações que ajudam a explicar</span>
          <MetricList labels={labels} row={row} metrics={metrics} />
        </div>
      ) : null}
    </FinancialNarrativeCard>
  )
}

function VaarResultReasons({ summary, learningRow, attendanceRow, lastYear }) {
  const learningMetrics = [
    ['proporcao_adequada_saeb_2023', 'percent'],
    ['taxa_aprovacao_penalizada_2023', 'percent'],
  ]
  const attendanceMetrics = [
    ['proporcao_abandono_atual', 'percent'],
    ['estudantes_areas_prioritarias_atual', 'integer'],
  ]
  const showLearning = summary?.recebe_aprendizagem === true
    || summary?.recebe_aprendizagem === false
    || hasMetricValues(learningRow, learningMetrics)
  const showAttendance = summary?.recebe_atendimento === true
    || summary?.recebe_atendimento === false
    || hasMetricValues(attendanceRow, attendanceMetrics)
  if (!showLearning && !showAttendance) return null

  return (
    <FinancialSection
      className="vaar-section"
      description={`Resultado publicado para os componentes no exercício de ${lastYear ?? EM}.`}
      eyebrow="Resultado por componente"
      title="Por que o município recebeu ou não recebeu?"
      titleId="vaar-explain-title"
    >
      <div className="vaar-explain-grid">
        {showLearning ? (
          <VaarComponentReason
            label="Aprendizagem"
            labels={{
              proporcao_adequada_saeb_2023: 'Aprendizado adequado',
              taxa_aprovacao_penalizada_2023: 'Aprovação considerada',
            }}
            metrics={learningMetrics}
            reason={summary.motivo_aprendizagem}
            row={learningRow}
            status={summary.recebe_aprendizagem}
            variation={buildObservedChange('aprendizagem', learningRow.delta_aprendizagem)}
          />
        ) : null}
        {showAttendance ? (
          <VaarComponentReason
            label="Atendimento"
            labels={{
              proporcao_abandono_atual: 'Abandono',
              estudantes_areas_prioritarias_atual: 'Estudantes considerados',
            }}
            metrics={attendanceMetrics}
            reason={summary.motivo_atendimento}
            row={attendanceRow}
            status={summary.recebe_atendimento}
            variation={buildObservedChange('atendimento', attendanceRow.delta_atendimento)}
          />
        ) : null}
      </div>
    </FinancialSection>
  )
}

function buildDataReadingCards(attendanceRow) {
  const cards = []
  const abandonment = compareNumbers(attendanceRow.proporcao_abandono_atual, attendanceRow.proporcao_abandono_anterior)
  if (abandonment) {
    cards.push({
      title: 'Abandono',
      text: abandonment === 'up'
        ? 'O abandono aumentou no período considerado.'
        : abandonment === 'down'
          ? 'O abandono reduziu no período considerado.'
          : 'O abandono permaneceu estável no período considerado.',
      values: [],
    })
  }

  const missingInfo = compareNumbers(attendanceRow.proporcao_sem_informacao_atual, attendanceRow.proporcao_sem_informacao_anterior)
  if (missingInfo) {
    cards.push({
      title: 'Registros sem informação',
      text: missingInfo === 'up'
        ? `A proporção sem informação aumentou de ${formatMetric(attendanceRow.proporcao_sem_informacao_anterior, 'percent')} para ${formatMetric(attendanceRow.proporcao_sem_informacao_atual, 'percent')}.`
        : missingInfo === 'down'
          ? `A proporção sem informação reduziu de ${formatMetric(attendanceRow.proporcao_sem_informacao_anterior, 'percent')} para ${formatMetric(attendanceRow.proporcao_sem_informacao_atual, 'percent')}.`
          : `A proporção sem informação permaneceu em ${formatMetric(attendanceRow.proporcao_sem_informacao_atual, 'percent')}.`,
      values: [
        ['Anterior', formatMetric(attendanceRow.proporcao_sem_informacao_anterior, 'percent')],
        ['Atual', formatMetric(attendanceRow.proporcao_sem_informacao_atual, 'percent')],
      ],
    })
  }

  const students = compareNumbers(
    attendanceRow.estudantes_areas_prioritarias_atual,
    attendanceRow.estudantes_areas_prioritarias_anterior,
  )
  if (students) {
    cards.push({
      title: 'Estudantes considerados',
      text: students === 'up'
        ? 'A quantidade de estudantes considerados aumentou no período considerado.'
        : students === 'down'
          ? 'A quantidade de estudantes considerados reduziu no período considerado.'
          : 'A quantidade de estudantes considerados permaneceu estável no período considerado.',
      values: [],
    })
  }

  return cards.slice(0, 3)
}

function VaarDataReadings({ cards }) {
  if (!cards.length) return null

  return (
    <FinancialSection
      className="vaar-section"
      description="Leituras objetivas produzidas a partir dos dados publicados para o município."
      eyebrow="Leituras do município"
      title="O que os dados mostram"
      titleId="vaar-attention-title"
    >
      <div className="vaar-attention-grid">
        {cards.map((card) => (
          <FinancialNarrativeCard className="platform-info-card vaar-insight-card" key={`${card.title}-${card.text}`}>
            <strong>{card.title}</strong>
            <p>{card.text}</p>
            {card.values.length ? (
              <dl className="vaar-insight-values">
                {card.values.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </FinancialNarrativeCard>
        ))}
      </div>
    </FinancialSection>
  )
}

function VaarCalculationData({ attendance, historicalRows, learning }) {
  const hasLearning = learning.some((row) => hasMetricValues(row, LEARNING_DETAIL_METRICS))
  const hasAttendance = attendance.some((row) => hasMetricValues(row, ATTENDANCE_DETAIL_METRICS))
  const hasHistory = historicalRows.some((row) => hasMetricValues(row, HISTORICAL_METRICS))
  if (!hasLearning && !hasAttendance && !hasHistory) return null

  return (
    <details className="platform-support-disclosure vaar-calculation-data">
      <summary className="platform-support-disclosure__summary">
        <div><h3>Dados usados no cálculo</h3><p>Valores e parâmetros publicados para consulta do cálculo.</p></div>
        <DisclosureChevron />
      </summary>
      <div className="platform-support-disclosure__body vaar-calculation-data__items">
        {hasLearning ? <TechnicalDetails title="Dados de Aprendizagem" rows={learning} metrics={LEARNING_DETAIL_METRICS} /> : null}
        {hasAttendance ? <TechnicalDetails title="Dados de Atendimento" rows={attendance} metrics={ATTENDANCE_DETAIL_METRICS} /> : null}
        {hasHistory ? <VaarHistoricalDetails rows={historicalRows} /> : null}
      </div>
    </details>
  )
}

function VaarGlossary() {
  return (
    <details className="platform-support-disclosure vaar-detail-toggle vaar-technical-details">
      <summary className="platform-support-disclosure__summary"><VaarAccordionSummary>Conceito e interpretação</VaarAccordionSummary></summary>
      <div className="vaar-glossary">
        {GLOSSARY_ITEMS.map(([title, text]) => (
          <article className="platform-info-card vaar-glossary-card" key={title}>
            <strong>{title}</strong>
            <p>{text}</p>
          </article>
        ))}
      </div>
    </details>
  )
}

export function VaarPanel({ financialData, vaarData }) {
  const data = vaarData ?? {}
  const summary = data.resumo_ultimo_ano ?? {}
  const history = Array.isArray(data.historico_recebimento) && data.historico_recebimento.length
    ? data.historico_recebimento
    : Array.isArray(data.historico) ? data.historico : []
  const learning = Array.isArray(data.aprendizagem) ? data.aprendizagem.filter((row) => row.metodologia_vaar !== 'metodologia_anterior') : []
  const attendance = Array.isArray(data.atendimento) ? data.atendimento.filter((row) => row.metodologia_vaar !== 'metodologia_anterior') : []
  const historicalRows = Array.isArray(data.metodologia_anterior) ? data.metodologia_anterior : []
  const lastYear = data.ultimo_ano ?? summary.ano_fundeb ?? null
  const latestLearning = getLatestRow(learning, lastYear)
  const latestAttendance = getLatestRow(attendance, lastYear)
  const attentionCards = buildDataReadingCards(latestAttendance)
  const hasData = history.length > 0 || learning.length > 0 || attendance.length > 0 || historicalRows.length > 0

  if (!hasData) {
    return (
      <div className="vaar-panel financial-vaar-panel">
        <div className="vaar-empty">
          <p>Não há informações financeiras da complementação VAAR para este município.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="vaar-panel financial-vaar-panel">
      <VaarMainSummary financialData={financialData} summary={summary} lastYear={lastYear} />
      <VaarResultReasons summary={summary} learningRow={latestLearning} attendanceRow={latestAttendance} lastYear={lastYear} />
      <VaarDataReadings cards={attentionCards} />
      <VaarHistory history={history} lastYear={lastYear} />

      <VaarCalculationData attendance={attendance} historicalRows={historicalRows} learning={learning} />
      <VaarGlossary />

      <FinancialSourcesFooter
        periods={`Exercícios separados por metodologia: 2023–2024 e 2025–2026, conforme publicação disponível.`}
        source={data.fonte || 'VAAR/Fundeb'}
      >
        Os componentes de Aprendizagem e Atendimento não formam uma série contínua entre metodologias diferentes. Ausência de registro não permite concluir que não houve recebimento.
      </FinancialSourcesFooter>
    </div>
  )
}
