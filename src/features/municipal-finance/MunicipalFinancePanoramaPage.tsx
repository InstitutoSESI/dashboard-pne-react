import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ArrowRight } from 'lucide-react'
import { buildAppHash } from '../../app/appHash'
import { ContentState } from '../../components/ContentState'
import { DisclosureChevron } from '../../components/DisclosureChevron'
import { FinancialCompactModuleSelector } from '../../components/FinancialCompactModuleSelector'
import {
  loadMunicipalFinanceCatalog,
  municipalFinanceLoader,
  type MunicipalFinanceCatalog,
  type MunicipalFinanceLoadStatus,
  type MunicipalFinanceSourceCatalogEntry,
} from '../../data/municipalFinance'
import { FINANCIAL_PAGE_KEYS } from '../../data/financialPageKeys'
import financingPrograms from '../../data/diagnostic/financingPrograms.json'
import indicatorCatalog from '../../data/diagnostic/indicatorCatalog.json'
import type { MunicipalFinanceDocumentV1, CompactFinancialValue } from '../diagnostic/municipalFinanceTypes'
import type { ParsedAppLocation } from '../../types/navigation'
import { isPublishableFinancialValue } from '../../utils/financialPresentation'
import {
  buildMunicipalFinancePresentation,
  formatCoefficient,
  formatCompactCurrency,
  formatCount,
  formatFullCurrency,
  formatIcmsSharePercent,
  formatIndexScore,
  formatPercent,
  splitFinanceContextIds,
} from './municipalFinancePresentation'
import { QseAnnualPanel } from './QseAnnualPanel'
import { FinancialKpiGrid, FinancialSection } from '../../components/FinancialIndicatorPrimitives'
import {
  FinancialCompactHeader,
  FinancialIcon,
  FinancialMetricCard,
  type FinancialIconName,
} from './FinancialPanoramaComponents'

interface MunicipalFinancePanoramaPageProps {
  municipalityIdentifier: string | null
  municipalityName: string | null
  navigationContext: ParsedAppLocation
}

interface PageLoadState {
  status: MunicipalFinanceLoadStatus
  document: MunicipalFinanceDocumentV1 | null
  catalog: MunicipalFinanceCatalog | null
}

const INITIAL_STATE: PageLoadState = {
  status: 'idle',
  document: null,
  catalog: null,
}

export function MunicipalFinancePanoramaPage({
  municipalityIdentifier,
  navigationContext,
}: MunicipalFinancePanoramaPageProps) {
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [loadState, setLoadState] = useState<PageLoadState>(INITIAL_STATE)
  const context = useMemo(() => ({
    indicatorIds: splitFinanceContextIds(navigationContext.params.get('indicatorId')),
    programIds: splitFinanceContextIds(navigationContext.params.get('programId')),
  }), [navigationContext])

  useEffect(() => {
    let cancelled = false
    if (!municipalityIdentifier) {
      setLoadState(INITIAL_STATE)
      return undefined
    }

    setLoadState({ status: 'loading', document: null, catalog: null })
    void Promise.all([
      municipalFinanceLoader.load(municipalityIdentifier),
      loadMunicipalFinanceCatalog().catch(() => null),
    ]).then(([document, catalog]) => {
      if (!cancelled) setLoadState({ status: 'ready', document, catalog })
    }).catch(() => {
      if (cancelled) return
      setLoadState({
        status: municipalFinanceLoader.getState(municipalityIdentifier).status,
        document: null,
        catalog: null,
      })
    })

    return () => {
      cancelled = true
    }
  }, [loadAttempt, municipalityIdentifier])

  if (!municipalityIdentifier) {
    return (
      <PageFrame returnHref={buildAppHash(FINANCIAL_PAGE_KEYS.overview, { municipio: municipalityIdentifier })}>
        <ContentState kind="unavailable" className="municipal-finance-state page-card">
          <h2>Selecione um município</h2>
          <p>Use o seletor da barra de contexto para abrir o panorama financeiro.</p>
        </ContentState>
      </PageFrame>
    )
  }

  if (loadState.status === 'idle' || loadState.status === 'loading') {
    return (
      <PageFrame returnHref={buildAppHash(FINANCIAL_PAGE_KEYS.overview, { municipio: municipalityIdentifier })}>
        <MunicipalFinanceSkeleton />
      </PageFrame>
    )
  }

  if (loadState.status !== 'ready' || !loadState.document) {
    const stateCopies: Partial<Record<MunicipalFinanceLoadStatus, { title: string; body: string }>> = {
      absent: {
        title: 'Sem informações financeiras para este município.',
        body: 'Não há informações financeiras publicáveis no momento.',
      },
      incompatible_version: {
        title: 'Sem informações financeiras para este município.',
        body: 'Não há informações financeiras publicáveis no momento.',
      },
      error: {
        title: 'Não foi possível carregar os dados financeiros.',
        body: 'Tente novamente. Os demais dados do município permanecem disponíveis.',
      },
    }
    const stateCopy = stateCopies[loadState.status] ?? {
      title: 'Não foi possível carregar os dados financeiros.',
      body: 'Tente novamente em instantes.',
    }
    return (
      <PageFrame returnHref={buildAppHash(FINANCIAL_PAGE_KEYS.overview, { municipio: municipalityIdentifier })}>
        <ContentState
          kind={loadState.status === 'error' ? 'error' : 'unavailable'}
          className="municipal-finance-state page-card"
        >
          <h2>{stateCopy.title}</h2>
          <p>{stateCopy.body}</p>
          {loadState.status === 'error' ? (
            <button className="platform-navigation-button" type="button" onClick={() => setLoadAttempt((value) => value + 1)}>
              Tentar novamente
            </button>
          ) : null}
        </ContentState>
      </PageFrame>
    )
  }

  const document = loadState.document
  const presentation = buildMunicipalFinancePresentation(
    document,
    financingPrograms,
    indicatorCatalog,
    context,
  )
  const summaryCards = [
    {
      key: 'paid',
      title: 'Recursos aplicados na educação',
      amount: document.execution.dcaEducation.paid,
      supportingText: `Valor executado em ${document.execution.dcaEducation.paid.referenceYear}`,
    },
    {
      key: 'mde',
      title: 'Aplicação em MDE',
      amount: document.constitutionalApplication.mdeAppliedRate.canonical,
      supportingText: `Mínimo constitucional: 25% · ${document.constitutionalApplication.mdeAppliedRate.canonical.referenceYear}`,
    },
    {
      key: 'remuneration',
      title: 'Remuneração dos profissionais (Fundeb)',
      amount: document.constitutionalApplication.fundebProfessionalRemunerationRate.canonical,
      supportingText: `Mínimo: 70% do Fundeb · ${document.constitutionalApplication.fundebProfessionalRemunerationRate.canonical.referenceYear}`,
    },
    {
      key: 'fundeb',
      title: 'Fundeb total previsto',
      amount: document.amounts.fundebTotalAnnualForecast,
      supportingText: `Previsto oficial · ${document.periods.annualForecastYear}`,
    },
    {
      key: 'vaar',
      title: 'VAAR previsto',
      amount: document.amounts.fundebVaarAnnualForecast,
      supportingText: `Previsto oficial · ${document.periods.annualForecastYear}`,
    },
  ].filter((card) => isPublishableFinancialValue(card.amount))

  return (
    <PageFrame returnHref={buildAppHash(FINANCIAL_PAGE_KEYS.overview, { municipio: document.municipality.slug })}>
      {summaryCards.length ? (
      <FinancialSection
        className="municipal-finance-summary"
        eyebrow="Resumo principal"
        title="Números mais recentes"
        titleId="municipal-finance-summary-title"
      >
        <FinancialKpiGrid className="municipal-finance-summary-grid">
          {summaryCards.map((card) => (
            <FinancialMetricCard
              icon={summaryIconFor(card.key)}
              key={card.key}
              label={card.title}
              meta={card.supportingText}
              tone={card.key === 'fundeb' || card.key === 'vaar' ? 'forecast' : 'observed'}
            >
              <FinanceValue value={card.amount} label={card.title} emphasized />
            </FinancialMetricCard>
          ))}
        </FinancialKpiGrid>
      </FinancialSection>
      ) : null}

      <IcmsEducationSection document={document} catalog={loadState.catalog} />

      <ConstitutionalApplicationSection document={document} catalog={loadState.catalog} />

      <BudgetExecutionSection document={document} />

      <FundebOverviewPanel
        document={document}
        nonBeneficiaryLabels={presentation.fundebNonBeneficiaryLabels}
      />

      {presentation.hasQseData ? <QseAnnualPanel document={document} /> : null}

      <RelatedProgramsSection
        document={document}
        relations={presentation.relations}
      />

    </PageFrame>
  )
}

function IcmsEducationSection({
  document,
  catalog,
}: {
  document: MunicipalFinanceDocumentV1
  catalog: MunicipalFinanceCatalog | null
}) {
  const icmsEducation = document.icmsEducation
  if (!icmsEducation) return null

  const latest = icmsEducation.latest
  const source = catalog?.sources.find((entry) => entry.sourceId === icmsEducation.sourceId) ?? null
  const history = [...icmsEducation.history].sort((left, right) => right.assessmentYear - left.assessmentYear)

  return (
    <FinancialSection
      className="municipal-finance-section municipal-finance-icms-education"
      description={`Resultado da avaliação de ${latest.assessmentYear}, aplicado à distribuição de ${latest.distributionYear}.`}
      eyebrow="ICMS Educação"
      title="Índice educacional e participação municipal"
      titleId="municipal-finance-icms-education-title"
    >
      <FinancialKpiGrid className="municipal-finance-icms-education__kpis">
        <FinancialMetricCard
          icon="allocation"
          label="Participação na quota-educação (PRE)"
          meta={`Distribuição de ${latest.distributionYear}`}
        >
          <span className="municipal-finance-icms-education__primary-value">
            {formatIcmsSharePercent(latest.preSharePercent)}
          </span>
        </FinancialMetricCard>
        <FinancialMetricCard
          icon="trend"
          label="IMERS"
          meta={`Avaliação SAERS ${latest.assessmentYear}`}
        >
          <span className="municipal-finance-icms-education__primary-value">
            {formatIndexScore(latest.imers)} <small>/ 100</small>
          </span>
        </FinancialMetricCard>
        <FinancialMetricCard
          icon="resources"
          label="Peso da educação no IPM"
          meta={`Regra de distribuição de ${latest.distributionYear}`}
        >
          <span className="municipal-finance-icms-education__primary-value">
            {formatPercent(latest.ipmEducationCriterionWeightPercent)}
          </span>
        </FinancialMetricCard>
      </FinancialKpiGrid>

      <div className="municipal-finance-icms-education__components">
        <div className="municipal-finance-icms-education__subheading">
          <h3>Componentes do IMERS</h3>
          <span>Avaliação {latest.assessmentYear}</span>
        </div>
        <dl>
          <div>
            <dt>Alfabetização <span>IQA</span></dt>
            <dd>
              <strong>{formatIndexScore(latest.components.iqa)}</strong>
              <span>2º ano: nível e evolução em Português e Matemática no SAERS.</span>
            </dd>
          </div>
          <div>
            <dt>Anos iniciais <span>IQI</span></dt>
            <dd>
              <strong>{formatIndexScore(latest.components.iqi)}</strong>
              <span>5º ano: nível e evolução em Português e Matemática no SAERS.</span>
            </dd>
          </div>
          <div>
            <dt>Anos finais <span>IQF</span></dt>
            <dd>
              <strong>{formatIndexScore(latest.components.iqf)}</strong>
              <span>9º ano: nível e evolução em Português e Matemática no SAERS.</span>
            </dd>
          </div>
          <div>
            <dt>Aprovação <span>IA</span></dt>
            <dd>
              <strong>{formatPercent(latest.components.approvalRate)}</strong>
              <span>Taxa de aprovação em todos os anos do ensino fundamental municipal.</span>
            </dd>
          </div>
        </dl>
      </div>

      <div className="municipal-finance-icms-education__history">
        <div className="municipal-finance-icms-education__subheading">
          <h3>Série oficial disponível</h3>
          <span>Avaliação → distribuição</span>
        </div>
        <div
          className="municipal-finance-icms-education__table-wrap platform-data-table-region"
          role="region"
          aria-label="Histórico municipal do ICMS Educação. Role horizontalmente para consultar todas as colunas quando necessário."
          tabIndex={0}
        >
          <table className="municipal-finance-icms-education__table platform-data-table">
            <caption className="u-sr-only">Histórico municipal do ICMS Educação</caption>
            <thead>
              <tr>
                <th scope="col">Avaliação</th>
                <th className="platform-data-cell--numeric" scope="col">Distribuição</th>
                <th className="platform-data-cell--numeric" scope="col">IMERS</th>
                <th className="platform-data-cell--numeric" scope="col">PRE</th>
                <th className="platform-data-cell--numeric" scope="col">Peso no IPM</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.assessmentYear}>
                  <td>{entry.assessmentYear}</td>
                  <td className="platform-data-cell--numeric">{entry.distributionYear}</td>
                  <td className="platform-data-cell--numeric">{formatIndexScore(entry.imers)}</td>
                  <td className="platform-data-cell--numeric">{formatIcmsSharePercent(entry.preSharePercent)}</td>
                  <td className="platform-data-cell--numeric">{formatPercent(entry.ipmEducationCriterionWeightPercent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="municipal-finance-icms-education__notes">
        <h3>Como interpretar</h3>
        <dl>
          <div>
            <dt>IMERS</dt>
            <dd>
              Nota de 0 a 100 que compara a qualidade educacional entre os municípios. Combina IQA (40%),
              IQI (35%), IQF (15%) e IA (10%).
            </dd>
          </div>
          <div>
            <dt>PRE</dt>
            <dd>
              Percentual do município no rateio da cota-parte da educação do ICMS; não é valor depositado
              nem estimativa em reais.
            </dd>
          </div>
          <div>
            <dt>Peso no IPM</dt>
            <dd>
              Parcela do Índice de Participação dos Municípios atribuída ao critério educacional no ano da
              distribuição.
            </dd>
          </div>
        </dl>
        <p className="municipal-finance-icms-education__method-note">
          Os resultados oficiais de 2024 são preservados como publicados, inclusive as regras excepcionais
          adotadas após as enchentes.
        </p>
        {source ? <SourceReference source={source} /> : null}
      </div>
    </FinancialSection>
  )
}

function BudgetExecutionSection({ document }: { document: MunicipalFinanceDocumentV1 }) {
  const execution = document.execution.dcaEducation
  const stages = [
    {
      key: 'committed',
      label: 'Empenhado',
      value: execution.committed,
      rate: 100,
    },
    {
      key: 'liquidated',
      label: 'Liquidado',
      value: execution.liquidated,
      rate: execution.derivedRates.liquidatedToCommittedRate.value,
    },
    {
      key: 'paid',
      label: 'Pago',
      value: execution.paid,
      rate: execution.derivedRates.paidToCommittedRate.value,
    },
  ].filter((stage) => isPublishableFinancialValue(stage.value))
  const paidRate = execution.derivedRates.paidToCommittedRate.value
  const executionYears = Array.from(new Set(stages.map((stage) => stage.value.referenceYear)))
  const sharedExecutionYear = executionYears.length === 1 ? executionYears[0] : null

  if (!stages.length) return null

  return (
    <FinancialSection
      className="municipal-finance-budget"
      eyebrow="Execução das despesas"
      title={`Execução orçamentária${sharedExecutionYear ? ` — ${sharedExecutionYear}` : ''} (SICONFI)`}
      titleId="municipal-finance-execution-title"
    >
      <div className="municipal-finance-budget__layout">
        <ol className="municipal-finance-budget__bars">
          {stages.map((stage) => (
            <li key={stage.key}>
              <strong>{stage.label}{sharedExecutionYear ? null : <small> · {stage.value.referenceYear}</small>}</strong>
              <progress
                aria-label={`${stage.label}: ${stage.rate === null ? 'percentual indisponível' : formatPercent(stage.rate)}`}
                max="100"
                value={stage.rate ?? 0}
              />
              <b>{stage.rate === null ? '—' : formatPercent(stage.rate)}</b>
              <FinanceValue value={stage.value} label={`${stage.label} em ${stage.value.referenceYear}`} />
            </li>
          ))}
        </ol>
        <aside className="municipal-finance-budget__reading" aria-label="Leitura rápida da execução">
          <div className="municipal-finance-budget__total">
            <span>Total empenhado</span>
            <FinanceValue value={execution.committed} label={`Total empenhado em ${execution.committed.referenceYear}`} emphasized />
          </div>
          <div><span>Base da despesa</span><strong>Empenhado</strong></div>
          <div>
            <span>Leitura rápida</span>
            <p>{paidRate === null
              ? 'A relação entre o valor pago e o empenhado não está disponível.'
              : `${formatPercent(paidRate)} do valor empenhado em ${execution.paid.referenceYear} já foi pago.`}</p>
          </div>
        </aside>
      </div>
    </FinancialSection>
  )
}

function getMinimumStatus(value: number | null, minimum: number) {
  if (value === null || !Number.isFinite(value)) return null
  const difference = Number((value - minimum).toFixed(2))
  if (difference === 0) {
    return { label: 'Cumpriu o mínimo', tone: 'met' as const }
  }
  const distance = formatPercent(Math.abs(difference)).replace('%', ' p.p.')
  return difference > 0
    ? { label: `${distance} acima do mínimo`, tone: 'above' as const }
    : { label: `${distance} abaixo do mínimo`, tone: 'below' as const }
}

function FundebOverviewPanel({
  document,
  nonBeneficiaryLabels,
}: {
  document: MunicipalFinanceDocumentV1
  nonBeneficiaryLabels: readonly string[]
}) {
  const components = [
    { key: 'vaat', label: 'VAAT', amount: document.amounts.fundebVaatAnnualForecast },
    { key: 'vaar', label: 'VAAR', amount: document.amounts.fundebVaarAnnualForecast },
  ]
  const visibleNonBeneficiaryLabels = nonBeneficiaryLabels.filter((label) => label !== 'VAAF')

  return (
    <FinancialSection
      className="municipal-finance-fundeb-overview"
      description="Síntese das previsões aplicáveis ao município, sem somar componentes novamente ao total."
      eyebrow={`Previsão oficial — ${document.periods.annualForecastYear}`}
      title="Fundeb e complementações"
      titleId="municipal-finance-fundeb-overview-title"
    >
      <div className="municipal-finance-fundeb-overview__grid">
        <article className="financial-card financial-composite-card municipal-finance-fundeb-overview__total">
          <span>Fundeb total previsto</span>
          <FinanceValue value={document.amounts.fundebTotalAnnualForecast} label="Fundeb total previsto" emphasized />
          <small>Previsão total · {document.periods.annualForecastYear}</small>
        </article>
        {components.map((component) => (
          <article className="financial-card financial-composite-card" key={component.key}>
            <span>{component.label} (previsto)</span>
            {isPublishableFinancialValue(component.amount)
              ? <FinanceValue value={component.amount} label={`${component.label} previsto`} emphasized />
              : <strong>Não beneficiário</strong>}
            <small>{isPublishableFinancialValue(component.amount) ? 'Valor anual total' : 'Sem previsão nominal'}</small>
          </article>
        ))}
      </div>
      <div className="municipal-finance-fundeb-overview__footer">
        <div>
          <p>Os valores de complementação dependem do cumprimento dos critérios oficiais de cada modalidade.</p>
          {visibleNonBeneficiaryLabels.length ? <p>Sem previsão para {visibleNonBeneficiaryLabels.join(' e ')}.</p> : null}
        </div>
        <a className="municipal-finance-row-link" href={buildAppHash(FINANCIAL_PAGE_KEYS.fundeb, { municipio: document.municipality.slug })}>
          Ver detalhes do Fundeb <ArrowRight aria-hidden="true" size={16} />
        </a>
      </div>
    </FinancialSection>
  )
}

function RelatedProgramsSection({
  document,
  relations,
}: {
  document: MunicipalFinanceDocumentV1
  relations: readonly {
    key: string
    programLabel: string
    relationLabel: string
  }[]
}) {
  return (
    <FinancialSection
      actions={<a className="municipal-finance-inline-action" href={buildAppHash(FINANCIAL_PAGE_KEYS.overview, { municipio: document.municipality.slug })}>
          Ver todos os programas <ArrowRight aria-hidden="true" size={16} />
        </a>}
      className="municipal-finance-programs municipal-finance-related-programs"
      eyebrow="Apoios relacionados"
      title="Outros programas e repasses relacionados"
      titleId="municipal-finance-related-programs-title"
    >
      <div className="municipal-finance-programs__related">
        <div className="municipal-finance-programs__rows">
          {relations.slice(0, 3).map((relation) => (
            <article key={relation.key}>
              <strong>{relation.programLabel}</strong>
              <div><small>{relation.relationLabel}</small></div>
              <ArrowRight aria-hidden="true" size={16} />
            </article>
          ))}
          {!relations.length ? <p>Nenhuma relação adicional documentada para este município.</p> : null}
        </div>
      </div>
    </FinancialSection>
  )
}

function ConstitutionalApplicationSection({
  document,
  catalog,
}: {
  document: MunicipalFinanceDocumentV1
  catalog: MunicipalFinanceCatalog | null
}) {
  const application = document.constitutionalApplication
  const reconciliation = document.reconciliation
  const metrics = [
    application.mdeAppliedAmount,
    application.mdeAppliedRate,
    application.fundebProfessionalRemunerationRate,
  ]
  const reasonCodes = [
    ...reconciliation.reasonCodes,
    ...metrics.flatMap((metric) => [
      ...metric.reconciliation.reasonCodes,
      metric.canonical.nullReasonCode,
      metric.siope.nullReasonCode,
      metric.rreo.nullReasonCode,
    ]),
    application.fundebRevenueReceivedDeclared.nullReasonCode,
  ].filter((reasonCode): reasonCode is string => Boolean(reasonCode))
  const uniqueReasonCodes = Array.from(new Set(reasonCodes))
  const revisionBlocked = uniqueReasonCodes.includes('source_revision_detected')
  const canPublishMainValues = !revisionBlocked
  const hasDivergence = metrics.some((metric) => metric.reconciliation.status.startsWith('divergent'))
  const hasMdeRate = canPublishMainValues && isPublishableFinancialValue(application.mdeAppliedRate.canonical)
  const hasMdeAmount = canPublishMainValues && isPublishableFinancialValue(application.mdeAppliedAmount.canonical)
  const hasFundebRate = canPublishMainValues && isPublishableFinancialValue(application.fundebProfessionalRemunerationRate.canonical)
  const hasFundebRevenue = canPublishMainValues && isPublishableFinancialValue(application.fundebRevenueReceivedDeclared)
  const mdeReferenceYear = hasMdeRate
    ? application.mdeAppliedRate.canonical.referenceYear
    : application.mdeAppliedAmount.canonical.referenceYear
  const mdeMinimumStatus = hasMdeRate
    ? getMinimumStatus(application.mdeAppliedRate.canonical.value, 25)
    : null
  const fundebMinimumStatus = hasFundebRate
    ? getMinimumStatus(application.fundebProfessionalRemunerationRate.canonical.value, 70)
    : null
  const displayedYears = [
    hasMdeRate ? application.mdeAppliedRate.canonical.referenceYear : null,
    hasMdeAmount ? application.mdeAppliedAmount.canonical.referenceYear : null,
    hasFundebRate ? application.fundebProfessionalRemunerationRate.canonical.referenceYear : null,
    hasFundebRevenue ? application.fundebRevenueReceivedDeclared.referenceYear : null,
  ].filter((year): year is number => year !== null)
  const sharedDisplayedYear = new Set(displayedYears).size === 1 ? displayedYears[0] : null
  const sourceIds = Array.from(new Set([
    ...metrics.flatMap((metric) => metric.reconciliation.sourceIds),
    ...reconciliation.availableSourceIds,
    application.fundebRevenueReceivedDeclared.sourceId,
  ]))
  const sourceNames = sourceIds.map((sourceId) => (
    catalog?.sources.find((source) => source.sourceId === sourceId)?.name
  )).filter((name): name is string => Boolean(name))
  if (!hasMdeRate && !hasMdeAmount && !hasFundebRate && !hasFundebRevenue) return null

  return (
    <FinancialSection
      className="municipal-finance-section municipal-finance-constitutional-application"
      eyebrow="Aplicação constitucional"
      title={`Aplicação constitucional da educação${sharedDisplayedYear ? ` — ${sharedDisplayedYear}` : ''}`}
      titleId="municipal-finance-constitutional-title"
    >
      <div className="municipal-finance-constitutional-primary-grid">
        {hasMdeRate || hasMdeAmount ? (
        <article
          className="financial-card financial-composite-card municipal-finance-constitutional-card municipal-finance-constitutional-card--mde"
        >
          <header className="municipal-finance-constitutional-card__header">
            <span className="municipal-finance-constitutional-card__icon" aria-hidden="true"><FinancialIcon name="allocation" /></span>
            <h3>Aplicação em MDE</h3>
            <span className="municipal-finance-constitutional-card__year">{mdeReferenceYear}</span>
          </header>
          {hasMdeRate ? (
          <div className="municipal-finance-constitutional-card__primary-value">
            <ConstitutionalCanonicalValue
              canPublish={canPublishMainValues}
              label="Percentual aplicado em MDE"
              value={application.mdeAppliedRate.canonical}
            />
          </div>
          ) : null}
          {mdeMinimumStatus ? (
            <span className={`municipal-finance-constitutional-card__status municipal-finance-constitutional-card__status--${mdeMinimumStatus.tone}`}>
              {mdeMinimumStatus.label}
            </span>
          ) : null}
          {hasMdeAmount ? (
            <div className="municipal-finance-constitutional-card__secondary-value">
              <ConstitutionalCanonicalValue
                canPublish={canPublishMainValues}
                label="Despesa computada em MDE"
                value={application.mdeAppliedAmount.canonical}
              />
              <span>aplicados em MDE</span>
            </div>
          ) : null}
          <p className="municipal-finance-constitutional-card__footer">Mínimo constitucional: 25%</p>
        </article>
        ) : null}

        {hasFundebRate ? (
        <article className="financial-card financial-composite-card municipal-finance-constitutional-card municipal-finance-constitutional-card--remuneration">
          <header className="municipal-finance-constitutional-card__header">
            <span className="municipal-finance-constitutional-card__icon" aria-hidden="true"><FinancialIcon name="resources" /></span>
            <h3>Remuneração dos profissionais</h3>
            <span className="municipal-finance-constitutional-card__year">{application.fundebProfessionalRemunerationRate.canonical.referenceYear}</span>
          </header>
          <div className="municipal-finance-constitutional-card__primary-value">
            <ConstitutionalCanonicalValue
              canPublish={canPublishMainValues}
              label="Percentual do Fundeb destinado à remuneração dos profissionais da educação"
              value={application.fundebProfessionalRemunerationRate.canonical}
            />
          </div>
          {fundebMinimumStatus ? (
            <span className={`municipal-finance-constitutional-card__status municipal-finance-constitutional-card__status--${fundebMinimumStatus.tone}`}>
              {fundebMinimumStatus.label}
            </span>
          ) : null}
          <p className="municipal-finance-constitutional-card__footer">Mínimo: 70% do Fundeb</p>
        </article>
        ) : null}
      {hasFundebRevenue ? (
        <article className="financial-card financial-composite-card municipal-finance-constitutional-card municipal-finance-constitutional-card--revenue">
          <header className="municipal-finance-constitutional-card__header">
            <span className="municipal-finance-constitutional-card__icon" aria-hidden="true"><FinancialIcon name="fundeb" /></span>
            <h3>Receita Fundeb declarada</h3>
            <span className="municipal-finance-constitutional-card__year">{application.fundebRevenueReceivedDeclared.referenceYear}</span>
          </header>
          <div className="municipal-finance-constitutional-card__primary-value">
            <ConstitutionalCanonicalValue
              canPublish={canPublishMainValues}
              label={`Receita Fundeb recebida declarada em ${application.fundebRevenueReceivedDeclared.referenceYear}`}
              value={application.fundebRevenueReceivedDeclared}
            />
          </div>
          <p className="municipal-finance-constitutional-card__notice">Valor declarado pelo município. Não equivale a uma transferência efetiva confirmada.</p>
          <p className="municipal-finance-constitutional-card__footer">Fonte: SIOPE/RREO · Período: {application.fundebRevenueReceivedDeclared.referenceYear}</p>
        </article>
      ) : null}
      </div>

      <div className="municipal-finance-constitutional-disclosures">
        <details className="platform-support-disclosure municipal-finance-constitutional-disclosure">
          <summary className="platform-support-disclosure__summary">
            <div>
              <h3>Fontes e metodologia</h3>
              <p>Valores por fonte, competência e critérios de conciliação.</p>
            </div>
            <DisclosureChevron />
          </summary>
          <div className="platform-support-disclosure__body">
            <div className="municipal-finance-constitutional-source-grid">
              <ConstitutionalSourceCard
                application={application}
                catalog={catalog}
                sourceKey="siope"
              />
              <ConstitutionalSourceCard
                application={application}
                catalog={catalog}
                sourceKey="rreo"
              />
            </div>
            <dl className="municipal-finance-constitutional-source-meta">
              <div><dt>Período</dt><dd>{application.period}º bimestre</dd></div>
              <div><dt>Base da despesa</dt><dd>{application.stageBasis}</dd></div>
              {sourceNames.length ? <div><dt>Fontes</dt><dd>{sourceNames.join(' · ')}</dd></div> : null}
            </dl>
            <p className="municipal-finance-method-note">
              A leitura canônica usa a média aritmética entre SIOPE e RREO quando a diferença fica dentro da tolerância de {formatFullCurrency(application.mdeAppliedAmount.reconciliation.tolerance)} para valores e de {formatCoefficient(application.mdeAppliedRate.reconciliation.tolerance)} ponto percentual para percentuais.
            </p>
            {hasDivergence ? (
              <p className="municipal-finance-method-note">
                Medidas com divergência acima da tolerância são omitidas da leitura principal e permanecem separadas por fonte neste detalhe.
              </p>
            ) : null}
            <p className="municipal-finance-method-note">
              MDE constitucional e despesa da função Educação na DCA representam universos contábeis e legais diferentes e não devem ser comparados diretamente.
            </p>
            <p className="municipal-finance-method-note">
              O valor da receita Fundeb é declarado pelo município no SIOPE e no RREO. Não representa transferência efetiva confirmada pelo concedente nem saldo disponível.
            </p>
          </div>
        </details>
      </div>
    </FinancialSection>
  )
}

function ConstitutionalCanonicalValue({
  canPublish,
  label,
  value,
}: {
  canPublish: boolean
  label: string
  value: CompactFinancialValue
}) {
  if (!canPublish || !isPublishableFinancialValue(value)) return null
  return <FinanceValue value={value} label={label} emphasized />
}

function ConstitutionalSourceCard({
  application,
  catalog,
  sourceKey,
}: {
  application: MunicipalFinanceDocumentV1['constitutionalApplication']
  catalog: MunicipalFinanceCatalog | null
  sourceKey: 'siope' | 'rreo'
}) {
  const sourceValue = application.mdeAppliedAmount[sourceKey]
  const source = catalog?.sources.find((entry) => entry.sourceId === sourceValue.sourceId) ?? null
  const sourceLabel = sourceKey === 'siope' ? 'SIOPE' : 'RREO'
  const metrics = [
    { label: 'Despesa computada em MDE', value: application.mdeAppliedAmount[sourceKey] },
    { label: 'Percentual aplicado em MDE', value: application.mdeAppliedRate[sourceKey] },
    { label: 'Remuneração dos profissionais', value: application.fundebProfessionalRemunerationRate[sourceKey] },
    ...(sourceKey === 'rreo'
      ? [{ label: 'Receita Fundeb declarada', value: application.fundebRevenueReceivedDeclared }]
      : []),
  ].filter((metric) => isPublishableFinancialValue(metric.value))
  const metricYears = Array.from(new Set(metrics.map((metric) => metric.value.referenceYear)))
  if (!metrics.length) return null

  return (
    <article>
      <header>
        <div>
          <span>{sourceLabel}</span>
          {source?.name ? <h4>{source.name}</h4> : null}
        </div>
      </header>
      <dl className="municipal-finance-constitutional-source-meta">
        <div><dt>Exercício</dt><dd>{metricYears.join(' · ') || source?.referenceYear || application.referenceYear}</dd></div>
        <div><dt>Período</dt><dd>{application.period}º bimestre</dd></div>
      </dl>
      <dl className="municipal-finance-constitutional-source-values">
        {metrics.map((metric) => (
          <div key={metric.label}>
            <dt>{metric.label} · {metric.value.referenceYear}</dt>
            <dd><FinanceValue value={metric.value} label={`${metric.label} — ${sourceLabel}`} /></dd>
          </div>
        ))}
      </dl>
      {source ? <SourceReference source={source} /> : null}
    </article>
  )
}

function PageFrame({
  children,
  returnHref,
}: {
  children: ReactNode
  returnHref: string
}) {
  return (
    <div className="page-stack financial-page municipal-finance-panorama">
      <FinancialCompactHeader
        backHref={returnHref}
        description="Visão geral dos recursos e da aplicação na educação do município."
      />
      <FinancialCompactModuleSelector activePageKey={FINANCIAL_PAGE_KEYS.panorama} />
      {children}
    </div>
  )
}

function summaryIconFor(key: string): FinancialIconName {
  const icons: Record<string, FinancialIconName> = {
    fundeb: 'fundeb',
    mde: 'allocation',
    paid: 'payment',
    remuneration: 'resources',
    vaar: 'trend',
  }
  return icons[key] ?? 'budget'
}

function FinanceValue({
  value,
  label,
  emphasized = false,
}: {
  value: CompactFinancialValue
  label: string
  catalog?: MunicipalFinanceCatalog | null
  emphasized?: boolean
}) {
  if (!isPublishableFinancialValue(value)) return null

  const formatted = formatFinanceValue(value, true)
  const full = formatFinanceValue(value, false)
  return (
    <span
      className={`municipal-finance-value${emphasized ? ' municipal-finance-value--emphasized' : ''}`}
      title={`${label}: ${full}`}
    >
      <span aria-hidden="true">{formatted}</span>
      <span className="u-sr-only">{label}: {full}</span>
    </span>
  )
}

function formatFinanceValue(value: CompactFinancialValue, compact: boolean): string {
  const numericValue = value.value as number
  if (value.unit === 'BRL') return compact ? formatCompactCurrency(numericValue) : formatFullCurrency(numericValue)
  if (value.unit === 'BRL_per_student') return `${formatFullCurrency(numericValue)} por matrícula`
  if (value.unit === 'percent') return formatPercent(numericValue)
  if (value.unit === 'count') return formatCount(numericValue)
  return formatCoefficient(numericValue)
}

function SourceReference({ source }: { source: MunicipalFinanceSourceCatalogEntry | null }) {
  if (!source?.name) return null
  return (
    <p className="municipal-finance-source-reference">
      <span>Fonte:</span>{' '}
      {source.url ? <a href={source.url} rel="noreferrer" target="_blank">{source.agency} — {source.name}</a> : source.name}
    </p>
  )
}

function MunicipalFinanceSkeleton() {
  return (
    <div className="municipal-finance-skeleton" role="status" aria-busy="true" aria-label="Carregando panorama financeiro">
      <div className="municipal-finance-summary-grid" aria-hidden="true">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="page-card municipal-finance-summary-card state-skeleton" key={index}>
            <span /><span /><span />
          </div>
        ))}
      </div>
      <div className="municipal-finance-primary-grid" aria-hidden="true">
        <div className="municipal-finance-primary-column municipal-finance-primary-column--left">
          {Array.from({ length: 2 }, (_, index) => (
            <div className="page-card municipal-finance-section state-skeleton" key={index}>
              <span /><span /><span />
            </div>
          ))}
        </div>
        <div className="municipal-finance-primary-column municipal-finance-primary-column--right">
          <div className="page-card municipal-finance-section state-skeleton">
            <span /><span /><span />
          </div>
        </div>
      </div>
      <span className="u-sr-only">Carregando dados financeiros.</span>
    </div>
  )
}
