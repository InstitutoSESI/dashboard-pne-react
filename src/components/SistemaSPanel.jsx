import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { EducationLineChart } from './EducationLineChart'
import { ChartEmptyState } from './ChartPrimitives'
import { DataSourceNote } from './DataSourceNote'
import { DetailNavigation } from './DetailNavigation'
import { EducationQuickReading } from './EducationQuickReading'
import { MetricCard } from './MetricCard'
import { formatNumber, isMissing } from '../utils/educationFormatters'

const EM = '\u2014'
const SISTEMA_S_SOURCE_CONTEXT = { block: 'educacao', themeKey: 'sistema_s' }

const EAD_KEYWORDS = ['EAD', 'ADMINISTRACAO REGIONAL', 'ADMINISTRAÇÃO REGIONAL', ' REGIONAL ']

const PRESERVE_ACRONYMS = new Set(['SENAI', 'SENAC', 'SESC', 'SESI', 'SENAR', 'SEST', 'SENAT', 'EAD', 'RS', 'CNPJ', 'IES'])

const LOWER_WORDS = new Set(['do', 'da', 'de', 'dos', 'das', 'e', 'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'com', 'a', 'o', 'ao', 'aos'])

const INDICATOR_CONFIG = [
  { key: 'total_escolas', label: 'Escolas do Sistema S', shortLabel: 'Escolas', description: 'Total de escolas mantidas pelo Sistema S no município.', color: '#0f766e' },
  { key: 'matriculas', label: 'Matrículas nas escolas do Sistema S', shortLabel: 'Matrículas', description: 'Total de matrículas nas escolas do Sistema S.', color: '#16713a' },
  { key: 'turmas', label: 'Turmas nas escolas do Sistema S', shortLabel: 'Turmas', description: 'Total de turmas nas escolas do Sistema S.', color: '#2563eb' },
  { key: 'docentes', label: 'Docentes nas escolas do Sistema S', shortLabel: 'Docentes', description: 'Total de docentes nas escolas do Sistema S.', color: '#7c3aed' },
]

function formatSchoolName(name) {
  if (!name) return ''
  return name
    .toLowerCase()
    .split(' ')
    .map((word, i) => {
      const upper = word.toUpperCase()
      if (PRESERVE_ACRONYMS.has(upper)) return upper
      if (LOWER_WORDS.has(word) && i > 0) return word
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join(' ')
}

function detectEadRegional(nome) {
  const upper = (nome ?? '').toUpperCase()
  if (upper.includes('EAD')) return 'EAD'
  if (EAD_KEYWORDS.some((kw) => kw !== 'EAD' && upper.includes(kw.toUpperCase()))) return 'Regional'
  return null
}

function calcDiferenca(initialValue, currentValue) {
  if (isMissing(initialValue) || isMissing(currentValue)) return { display: EM, pctDisplay: null, tone: 'muted' }
  const diff = Number(currentValue) - Number(initialValue)
  let display, tone
  if (diff > 0) { display = `+${formatNumber(diff)}`; tone = 'success' }
  else if (diff < 0) { display = formatNumber(diff); tone = 'warning' }
  else { display = '0'; tone = 'muted' }
  let pctDisplay = null
  const init = Number(initialValue)
  if (init !== 0 && Number.isFinite(init)) {
    const pct = (diff / Math.abs(init)) * 100
    const sign = pct > 0 ? '+' : ''
    pctDisplay = `${sign}${pct.toFixed(1)}%`
  }
  return { display, pctDisplay, tone }
}

function maiorEtapa(distribuicao) {
  if (!distribuicao.length) return null
  return distribuicao.reduce((a, b) => ((a.matriculas ?? 0) > (b.matriculas ?? 0) ? a : b))
}

function quickReading(activeKey, currentDisplay, currentYear, hasDistribuicao) {
  if (isMissing(currentYear) || isMissing(currentDisplay)) return null
  if (activeKey === 'total_escolas') {
    return `Em ${currentYear}, o município possui ${currentDisplay} escolas do Sistema S com atendimento registrado no município.`
  }
  if (activeKey === 'matriculas') {
    if (hasDistribuicao) {
      const maior = maiorEtapa(hasDistribuicao)
      return maior
        ? `Em ${currentYear}, o município registra ${currentDisplay} matrículas em escolas do Sistema S, com maior concentração em ${maior.etapa}.`
        : `Em ${currentYear}, o município registra ${currentDisplay} matrículas em escolas do Sistema S.`
    }
    return `Em ${currentYear}, o município registra ${currentDisplay} matrículas em escolas do Sistema S.`
  }
  if (activeKey === 'turmas') {
    return `Em ${currentYear}, o município registra ${currentDisplay} turmas em escolas do Sistema S.`
  }
  if (activeKey === 'docentes') {
    return `Em ${currentYear}, o município registra ${currentDisplay} docentes vinculados às escolas do Sistema S.`
  }
  return null
}

function temEadOuRegional(escolas) {
  if (!escolas.length) return false
  return escolas.some((e) => detectEadRegional(e.nome_escola))
}

const ETAPA_PALETTE = ['#16713a', '#2d7d4a', '#5a9a6f', '#88b79a', '#b5d4c2']

export function SistemaSPanel({ blocos, initialIndicatorKey = 'total_escolas', mode = 'detail', onOpenDetails }) {
  const data = blocos?.sistema_s ?? {}
  const series = data.series ?? {}
  const resumo = data.resumo_ultimo_ano ?? {}
  const ultimo_ano = data.ultimo_ano
  const distribuicao = data.distribuicao_etapa ?? []
  const escolas = data.escolas ?? []
  const avisos = data.avisos ?? []
  const hasData = series.total_escolas?.length > 0
  const [activeKey, setActiveKey] = useState(initialIndicatorKey)

  if (!hasData) return null

  const activeConfig = INDICATOR_CONFIG.find((c) => c.key === activeKey) ?? INDICATOR_CONFIG[0]
  const activeSeries = series[activeKey] ?? []
  const firstPoint = activeSeries[0] ?? null
  const lastPoint = activeSeries.at(-1) ?? null
  const initialValue = firstPoint?.valor ?? null
  const currentValue = lastPoint?.valor ?? null
  const initialYear = firstPoint?.ano ?? null
  const currentYear = lastPoint?.ano ?? null
  const currentDisplay = !isMissing(currentValue) ? formatNumber(currentValue) : EM
  const diferenca = calcDiferenca(initialValue, currentValue)
  const hasSeries = activeSeries.length >= 2
  const reading = quickReading(activeKey, currentDisplay, currentYear, activeKey === 'matriculas' ? distribuicao : null)
  const mostraNotaEad = temEadOuRegional(escolas)

  const sidebarValues = {
    total_escolas: resumo.total_escolas,
    matriculas: resumo.total_matriculas,
    turmas: resumo.total_turmas,
    docentes: resumo.total_docentes,
  }

  const totalMatEtapa = distribuicao.reduce((sum, item) => sum + (item.matriculas ?? 0), 0)
  const sortedDist = [...distribuicao]
    .sort((a, b) => (b.matriculas ?? 0) - (a.matriculas ?? 0))
    .map((item, i) => ({
      ...item,
      pct: totalMatEtapa > 0 ? ((item.matriculas ?? 0) / totalMatEtapa * 100) : 0,
      color: i === 0 ? '#16713a' : ETAPA_PALETTE[i % ETAPA_PALETTE.length],
      isPrimary: i === 0,
    }))

  const detalheDiferenca = !isMissing(initialValue) && diferenca.pctDisplay
    ? `${diferenca.pctDisplay} desde ${initialYear}`
    : initialYear ? `Desde ${initialYear}` : null

  const anoResumo = ultimo_ano ?? 2025

  if (mode === 'summary') {
    return (
      <div className="sistema-s-panel sistema-s-panel--summary">
        <p className="education-indicator-group__description sistema-s-group-description">
          Oferta educacional mantida pelo Sistema S no município, com histórico dos indicadores, distribuição por etapa e relação de escolas.
        </p>
        <div className="sistema-s-shortcuts" aria-label="Indicadores do Sistema S">
          {INDICATOR_CONFIG.map((indicator) => {
            const value = sidebarValues[indicator.key]
            return (
              <button
                className="sistema-s-shortcut"
                key={indicator.key}
                onClick={() => onOpenDetails?.(indicator.key)}
                type="button"
              >
                <span className="sistema-s-shortcut__label">{indicator.shortLabel}</span>
                <strong>{!isMissing(value) ? formatNumber(value) : EM}</strong>
                <small>Ano {anoResumo}</small>
                <span className="sistema-s-shortcut__action">Ver indicador <ArrowRight aria-hidden="true" size={16} /></span>
              </button>
            )
          })}
        </div>
        <div className="sistema-s-summary-footer">
          <DataSourceNote context={SISTEMA_S_SOURCE_CONTEXT} />
          <button className="platform-navigation-button sistema-s-open-detail" onClick={() => onOpenDetails?.('total_escolas')} type="button">
            Abrir detalhamento
            <ArrowRight aria-hidden="true" size={16} />
          </button>
        </div>
      </div>
    )
  }

  const activeIndex = INDICATOR_CONFIG.findIndex((indicator) => indicator.key === activeKey)
  const previousIndicator = activeIndex > 0 ? INDICATOR_CONFIG[activeIndex - 1] : null
  const nextIndicator = activeIndex < INDICATOR_CONFIG.length - 1 ? INDICATOR_CONFIG[activeIndex + 1] : null

  return (
    <div className="sistema-s-panel sistema-s-panel--detail">
      <DetailNavigation
        activeIndex={activeIndex}
        itemLabel="Indicador"
        nextItem={nextIndicator}
        onNext={setActiveKey}
        onPrevious={setActiveKey}
        previousItem={previousIndicator}
        showBack={false}
        total={INDICATOR_CONFIG.length}
      />

      <section className="detail-panel educacao-detail-panel educacao-detail-panel--organized">
          <div className="detail-heading educacao-detail-heading">
            <div className="detail-heading__copy">
              <span className="eyebrow">Sistema S · Indicador selecionado</span>
              <h3>{activeConfig.label}</h3>
              <p>{activeConfig.description}</p>
            </div>
            <div className="educacao-detail-heading__badges">
              <span className="indicator-stage-badge">Municipal</span>
              <span className="indicator-stage-badge">{currentYear ?? anoResumo}</span>
            </div>
          </div>

          <div className="sistema-s-indicator-tabs" role="tablist" aria-label="Indicadores do Sistema S">
            {INDICATOR_CONFIG.map((indicator) => (
              <button
                aria-selected={activeKey === indicator.key}
                className={`infra-dep-pill${activeKey === indicator.key ? ' is-active' : ''}`}
                key={indicator.key}
                onClick={() => setActiveKey(indicator.key)}
                role="tab"
                type="button"
              >
                {indicator.shortLabel}
              </button>
            ))}
          </div>

          <div className="metric-grid metric-grid--three education-metric-summary">
            <MetricCard icon="start" label="Valor inicial" value={!isMissing(initialValue) ? formatNumber(initialValue) : EM} detail={initialYear ? `Ano ${initialYear}` : null} />
            <MetricCard icon="current" label="Valor atual" value={currentDisplay} detail={currentYear ? `Ano ${currentYear}` : null} size="large" />
            <MetricCard icon={Number(currentValue) < Number(initialValue) ? 'variationDown' : 'variation'} label="Diferença" value={diferenca.display} detail={detalheDiferenca} tone={diferenca.tone} />
          </div>

          <div className="education-primary-analysis sistema-s-primary-analysis">
            <div className="indicator-chart-card educacao-main-chart-card sistema-s-chart">
              <div className="education-chart-heading">
                <div>
                  <span>Evolução do indicador</span>
                  <p>{activeConfig.label}</p>
                </div>
              </div>
              {hasSeries ? (
                <EducationLineChart
                  color={activeConfig.color}
                  formatLabel={formatNumber}
                  scaleType="count"
                  series={activeSeries}
                  showPointLabels
                  title={null}
                />
              ) : (
                <ChartEmptyState message="Histórico não disponível." />
              )}
            </div>

            <EducationQuickReading
              items={[
                { key: 'trend', icon: 'trend', label: 'Evolução observada', text: reading },
                { key: 'measure', icon: 'measure', label: 'O que o indicador mede', text: activeConfig.description },
                { key: 'period', icon: 'period', label: 'Período exibido', text: initialYear && currentYear ? `${initialYear} a ${currentYear}` : null },
              ]}
            />
          </div>

          <section className="educacao-explore education-support-data education-support-data--organized sistema-s-support-data" aria-labelledby="sistema-s-support-title">
            <header className="education-support-data__header">
              <div className="education-support-data__summary">
                <span className="educacao-explore__eyebrow">Aprofundamento</span>
                <h3 id="sistema-s-support-title">Dados de apoio do indicador</h3>
                <p>Distribuição das matrículas por etapa e estabelecimentos vinculados ao Sistema S.</p>
              </div>
            </header>
            <div className="sistema-s-detail-stack">
            {sortedDist.length > 0 && (
              <div className="education-support-data__item sistema-s-detail-card sistema-s-detail-card--etapas">
                <div className="educacao-explore__heading">
                  <span className="sistema-s-detail-title">Distribuição por etapa</span>
                  <p>Matrículas do Sistema S por etapa de ensino no último ano disponível.</p>
                </div>
                <div className="sistema-s-etapas">
                  {sortedDist.map((item) => (
                    <div key={item.etapa} className={'sistema-s-etapa-row' + (item.isPrimary ? ' is-primary' : '')}>
                      <span className="sistema-s-etapa-row__label">{item.etapa}</span>
                      <div className="sistema-s-etapa-row__bar-track">
                        <span
                          className="sistema-s-etapa-row__bar-fill"
                          style={{ width: `${item.pct}%`, background: item.color }}
                        />
                      </div>
                      <span className="sistema-s-etapa-row__value">{formatNumber(item.matriculas)}</span>
                      <span className="sistema-s-etapa-row__pct">{item.pct.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {escolas.length > 0 && (
              <div className="education-support-data__item sistema-s-detail-card sistema-s-detail-card--escolas">
                <div className="educacao-explore__heading">
                  <span className="sistema-s-detail-title">Escolas do Sistema S</span>
                  <p>Lista de escolas do Sistema S no último ano disponível.</p>
                </div>
                <div className="sistema-s-table-wrap" role="region" aria-label="Lista de escolas do Sistema S. Role horizontalmente para consultar todas as colunas quando necessário." tabIndex={0}>
                  <table className="sistema-s-table">
                    <caption className="u-sr-only">Lista de escolas do Sistema S no último ano disponível</caption>
                    <thead>
                      <tr>
                        <th scope="col">Escola</th>
                        <th scope="col">Matrículas</th>
                        <th scope="col">Turmas</th>
                        <th scope="col">Docentes</th>
                        <th scope="col">Etapas</th>
                      </tr>
                    </thead>
                    <tbody>
                      {escolas.map((escola) => {
                        const chip = detectEadRegional(escola.nome_escola)
                        return (
                          <tr key={escola.cod_escola}>
                            <td title={escola.nome_escola}>
                              {formatSchoolName(escola.nome_escola)}
                              {chip && <span className="sistema-s-chip">{chip}</span>}
                            </td>
                            <td className="sistema-s-table__num">{!isMissing(escola.matriculas) ? formatNumber(escola.matriculas) : <span className="platform-data-missing" aria-label="Dado não disponível" title="Dado não disponível">{EM}</span>}</td>
                            <td className="sistema-s-table__num">{!isMissing(escola.turmas) ? formatNumber(escola.turmas) : <span className="platform-data-missing" aria-label="Dado não disponível" title="Dado não disponível">{EM}</span>}</td>
                            <td className="sistema-s-table__num">{!isMissing(escola.docentes) ? formatNumber(escola.docentes) : <span className="platform-data-missing" aria-label="Dado não disponível" title="Dado não disponível">{EM}</span>}</td>
                            <td>{escola.etapas?.join(', ') || <span className="platform-data-missing" aria-label="Dado não disponível" title="Dado não disponível">{EM}</span>}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                {mostraNotaEad && (
                  <p className="sistema-ead-note">
                    Observação: parte das matrículas pode estar vinculada a unidades EAD ou sedes regionais declaradas no município.
                  </p>
                )}
              </div>
            )}
            </div>
            <footer className="education-support-data__footer">
              <DataSourceNote context={SISTEMA_S_SOURCE_CONTEXT} />
            </footer>
          </section>

          {avisos.length > 0 && (
            <div className="educacao-explore">
              {avisos.map((aviso, i) => (
                <p key={i} className="educacao-explore__note">{aviso}</p>
              ))}
            </div>
          )}
      </section>

      <DetailNavigation
        activeIndex={activeIndex}
        isBottom
        itemLabel="Indicador"
        nextItem={nextIndicator}
        onNext={setActiveKey}
        onPrevious={setActiveKey}
        previousItem={previousIndicator}
        showBack={false}
        total={INDICATOR_CONFIG.length}
      />
    </div>
  )
}
