import { ArrowRight } from 'lucide-react'
import { buildAppHash } from '../../../app/appHash'
import { hasRelevantNetworkComparison } from '../enrollmentComparisonPresentation'
import type {
  BreakdownValue,
  EnrollmentComparisonValue,
  MunicipalEducationOverviewV1,
  SnapshotPercentage,
  SnapshotValue,
  StageSnapshot,
} from '../municipalEducationOverviewTypes'
import {
  describeOverviewMatrixValue,
  formatOverviewEnrollments,
  formatOverviewPercentage,
  formatSchoolPerformanceRate,
  getMunicipalOverviewMethodologyHighlights,
  getOverviewNumericValue,
} from '../municipalEducationOverviewPresentation'
import {
  formatMunicipalLearningChange,
  formatMunicipalLearningValue,
  getMunicipalLearningChangeTone,
  type MunicipalLearningMetricSnapshot,
  type MunicipalLearningStageSnapshot,
} from '../municipalEducationLearningPresentation'

/*
 * Etapa e uma sequencia (Infantil -> Fundamental -> Medio), entao a composicao
 * usa a rampa sequencial. Rede e categoria sem ordem e usa hues distintos.
 * Ver o bloco "Barras de proporcao" em design-tokens.css.
 */
interface EducationOverviewSectionProps {
  data: MunicipalEducationOverviewV1
  learningStages: readonly MunicipalLearningStageSnapshot[]
}

interface SnapshotMatrixRow {
  label: string
  select: (stage: StageSnapshot) => BreakdownValue
}

const NETWORK_ROWS: ReadonlyArray<SnapshotMatrixRow> = [
  { label: 'Rede pública', select: (stage) => stage.byNetwork.publicSubtotal },
  { label: 'Municipal', select: (stage) => stage.byNetwork.municipal },
  { label: 'Estadual', select: (stage) => stage.byNetwork.state },
  { label: 'Federal', select: (stage) => stage.byNetwork.federal },
  { label: 'Privada', select: (stage) => stage.byNetwork.private },
]

const LOCATION_ROWS: ReadonlyArray<SnapshotMatrixRow> = [
  { label: 'Urbana', select: (stage) => stage.bySchoolLocation.urban },
  { label: 'Rural', select: (stage) => stage.bySchoolLocation.rural },
]

export function EducationOverviewSection({ data, learningStages }: EducationOverviewSectionProps) {
  return (
    <div className="municipal-education-overview">
      <EducationOverviewSummary data={data} />
      <SpecialEducationSummary data={data} />
      <EducationStageSnapshot
        data={data}
        detailsHref={buildAppHash('educacao', {
          municipio: data.municipality.slug,
          secao: 'atendimento',
          detalhe: 'mat-infantil',
        })}
        detailsLabel={'Ver indicadores da Educa\u00e7\u00e3o Infantil'}
        stage="earlyChildhood"
        title="Educação Infantil — 2025"
      />
      <EducationStageSnapshot
        data={data}
        detailsHref={buildAppHash('educacao', {
          municipio: data.municipality.slug,
          secao: 'atendimento',
          detalhe: 'mat-fundamental',
        })}
        detailsLabel={'Ver indicadores do Ensino Fundamental'}
        stage="elementary"
        title="Ensino Fundamental — 2025"
      />
      <HighSchoolStageSnapshot data={data} />
      <SchoolPerformanceSection data={data} />
      <LearningOutcomesSection stages={learningStages} />
      <EnrollmentComparisonSection data={data} />
      <EducationOverviewSources data={data} />
    </div>
  )
}

function EducationOverviewSummary({ data }: Pick<EducationOverviewSectionProps, 'data'>) {
  const composition = data.basicEducationComposition
  const components = composition.components
  const regularStages = [
    {
      key: 'early-childhood',
      label: 'Educação Infantil',
      value: components.earlyChildhood.total,
      details: [
        ['Creche', components.earlyChildhood.details.creche],
        ['Pré-escola', components.earlyChildhood.details.preSchool],
      ],
    },
    {
      key: 'elementary',
      label: 'Ensino Fundamental',
      value: components.elementary.total,
      details: [
        ['Anos Iniciais', components.elementary.details.initialYears],
        ['Anos Finais', components.elementary.details.finalYears],
      ],
    },
    {
      key: 'high-school',
      label: 'Ensino Médio',
      value: components.highSchool.total,
      details: [['Técnico integrado', components.highSchool.details.integratedTechnical]],
    },
  ] as const
  const modalities = [
    {
      key: 'eja',
      label: 'Educação de Jovens e Adultos — EJA',
      value: components.youthAndAdultEducation.total,
      details: [
        ['EJA — Ensino Fundamental', components.youthAndAdultEducation.details.elementary],
        ['EJA — Ensino Médio', components.youthAndAdultEducation.details.highSchool],
      ],
    },
    {
      key: 'professional',
      label: 'Educação profissional — outras ofertas',
      value: components.otherProfessionalOffers.total,
      details: [
        ['Curso técnico concomitante', components.otherProfessionalOffers.details.concomitantTechnical],
        ['Curso técnico subsequente', components.otherProfessionalOffers.details.subsequentTechnical],
        ['Outras ofertas profissionais', components.otherProfessionalOffers.details.otherOffers],
      ],
    },
  ] as const

  return (
    <section className="municipal-education-overview__section municipal-education-overview__section--summary" aria-labelledby="municipal-education-summary-title">
      <div className="municipal-education-overview__section-heading">
        <h2 id="municipal-education-summary-title">Composição das matrículas da Educação Básica — 2025</h2>
      </div>
      <div className="municipal-education-summary">
        <dl className="municipal-education-summary__primary">
          <div>
            <dt>Educação Básica</dt>
            <dd>{formatOverviewEnrollments(composition.total)}</dd>
            <span>Total oficial do Censo Escolar</span>
          </div>
        </dl>
        <CompositionCategory id="regular-stages" label="Etapas regulares" groups={regularStages} total={composition.total} />
        <CompositionCategory id="modalities" label="Modalidades e outras ofertas" groups={modalities} total={composition.total} />
        <div className="municipal-education-summary__notes" aria-label="Notas sobre a composição das matrículas">
          <p>As matrículas do técnico integrado já estão incluídas no total do Ensino Médio.</p>
          <p>As outras ofertas profissionais apresentadas não estão incluídas no Ensino Médio ou na EJA.</p>
          <p>Somente os cinco componentes principais participam da composição da Educação Básica; os detalhamentos não são somados novamente.</p>
        </div>
      </div>
    </section>
  )
}

/*
 * Participacao do componente na Educacao Basica.
 *
 * A proporcao entre etapas e a leitura que faltava no cartao: sem ela o gestor
 * precisa dividir de cabeca para saber o peso do Fundamental na rede. Fica ao
 * lado do numero, dentro do proprio cartao, em vez de num grafico separado.
 *
 * Devolve null quando o componente ou o total nao sao publicaveis: ausente e
 * nao aplicavel nao viram zero.
 */
function formatCompositionShare(value: SnapshotValue, total: SnapshotValue): string | null {
  const amount = getOverviewNumericValue(value)
  const base = getOverviewNumericValue(total)
  if (amount === null || base === null || base <= 0) return null
  return `${shareFormatter.format((amount / base) * 100)}% da Educação Básica`
}

const shareFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

function CompositionCategory({
  groups,
  id,
  label,
  total,
}: {
  groups: ReadonlyArray<{
    key: string
    label: string
    value: SnapshotValue
    details: ReadonlyArray<readonly [string, SnapshotValue]>
  }>
  id: string
  label: string
  total: SnapshotValue
}) {
  const headingId = `municipal-education-summary-${id}`
  return (
    <section className={`municipal-education-summary__category municipal-education-summary__category--${id}`} aria-labelledby={headingId}>
      <h3 id={headingId}>{label}</h3>
      <div className="municipal-education-summary__components">
        {groups.map((group) => {
          const share = formatCompositionShare(group.value, total)
          return (
            <dl className="municipal-education-summary__group" key={group.key}>
              <div className="municipal-education-summary__group-heading">
                <dt>{group.label}</dt>
                <dd>{formatOverviewEnrollments(group.value)}</dd>
                {share ? (
                  <p className="municipal-education-summary__group-share">{share}</p>
                ) : null}
              </div>
              <div className="municipal-education-summary__details">
                {group.details.map(([detailLabel, value]) => (
                  <div key={detailLabel}><dt>{detailLabel}</dt><dd>{formatOverviewEnrollments(value)}</dd></div>
                ))}
              </div>
            </dl>
          )
        })}
      </div>
    </section>
  )
}

function SpecialEducationSummary({ data }: Pick<EducationOverviewSectionProps, 'data'>) {
  const special = data.specialEducation
  return (
    <section className="municipal-education-overview__section municipal-special-education" aria-labelledby="municipal-special-education-title">
      <div>
        <h2 id="municipal-special-education-title">Educação Especial — 2025</h2>
        <p>As matrículas da Educação Especial já estão incluídas nas etapas e modalidades apresentadas acima.</p>
      </div>
      <dl>
        <div><dt>Educação Especial</dt><dd>{formatOverviewEnrollments(special.total)}</dd></div>
        <div><dt>Classes comuns</dt><dd>{formatOverviewEnrollments(special.commonClasses)}</dd></div>
        <div><dt>Classes exclusivas</dt><dd>{formatOverviewEnrollments(special.exclusiveClasses)}</dd></div>
      </dl>
    </section>
  )
}

function HighSchoolStageSnapshot({ data }: Pick<EducationOverviewSectionProps, 'data'>) {
  const detailsHref = buildAppHash('educacao', {
    municipio: data.municipality.slug,
    secao: 'atendimento',
    detalhe: 'mat-medio',
  })

  return (
    <section className="municipal-education-overview__section municipal-education-stage" aria-labelledby="high-school-snapshot-title">
      <div className="municipal-education-overview__section-heading">
        <h2 id="high-school-snapshot-title">Ensino Médio — 2025</h2>
      </div>
      <dl className="municipal-education-stage__summary municipal-education-stage__summary--two-columns">
        <OverviewMetric
          label="Ensino Médio"
          value={data.highSchool.total.total}
          share={data.highSchool.total.shareOfBasicEducation}
          shareLabel="Ensino Médio em relação à Educação Básica"
          primary
        />
        <OverviewMetric
          label="Técnico integrado"
          value={data.highSchool.integratedTechnical.total}
          share={data.highSchool.integratedTechnical.shareOfHighSchool}
          shareLabel="Técnico integrado em relação ao Ensino Médio"
        />
      </dl>
      <p className="municipal-education-stage__note">As matrículas do técnico integrado já estão incluídas no total do Ensino Médio.</p>
      <div className="municipal-education-stage__matrices">
        <EducationSnapshotMatrix id="high-school-network-title" rows={NETWORK_ROWS} splitSingleStage columnsLabel="Recorte" stages={[{ label: 'Ensino Médio', value: data.highSchool.total }]} title="Dependência administrativa" />
        <EducationSnapshotMatrix id="high-school-location-title" rows={LOCATION_ROWS} splitSingleStage columnsLabel="Localização da escola" stages={[{ label: 'Ensino Médio', value: data.highSchool.total }]} title="Localização da escola" />
      </div>
      <a className="municipal-education-stage__detail-link" href={detailsHref}>
        <span>Ver indicadores do Ensino Médio</span><ArrowRight aria-hidden="true" size={16} />
      </a>
    </section>
  )
}

function SchoolPerformanceSection({ data }: Pick<EducationOverviewSectionProps, 'data'>) {
  const rows = [
    ['Ensino Fundamental', data.schoolPerformance.stages.elementary],
    ['Anos Iniciais', data.schoolPerformance.stages.initialYears],
    ['Anos Finais', data.schoolPerformance.stages.finalYears],
    ['Ensino Médio', data.schoolPerformance.stages.highSchool],
  ] as const
  return (
    <section className="municipal-education-overview__section municipal-school-performance" aria-labelledby="municipal-school-performance-title">
      <div className="municipal-education-overview__section-heading">
        <h2 id="municipal-school-performance-title">Rendimento escolar — 2025</h2>
      </div>
      <div className="municipal-school-performance__table-region" tabIndex={0}>
        <table>
          <caption>Taxas municipais de aprovação, reprovação e abandono em 2025</caption>
          <thead><tr><th scope="col">Etapa</th><th scope="col">Aprovação</th><th scope="col">Reprovação</th><th scope="col">Abandono</th></tr></thead>
          <tbody>{rows.map(([label, stage]) => (
            <tr key={label}><th scope="row">{label}</th><td data-label="Aprovação">{formatSchoolPerformanceRate(stage.approval)}</td><td data-label="Reprovação">{formatSchoolPerformanceRate(stage.failure)}</td><td data-label="Abandono">{formatSchoolPerformanceRate(stage.dropout)}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <p className="municipal-school-performance__note">As taxas correspondem ao resultado escolar informado pelo INEP para o conjunto das redes do município. Aprovação, reprovação e abandono totalizam 100%.</p>
    </section>
  )
}

function LearningOutcomesSection({
  stages,
}: {
  stages: readonly MunicipalLearningStageSnapshot[]
}) {
  return (
    <section className="municipal-education-overview__section municipal-learning-outcomes" aria-labelledby="municipal-learning-outcomes-title">
      <div className="municipal-education-overview__section-heading">
        <h2 id="municipal-learning-outcomes-title">IDEB e notas do SAEB</h2>
        <p>Resultados mais recentes por etapa. A variação mostra a diferença, em pontos, para a edição anterior disponível.</p>
      </div>
      <div className="municipal-learning-outcomes__table-region" tabIndex={0}>
        <table>
          <caption>IDEB e notas do SAEB por etapa, com variação desde a edição anterior disponível</caption>
          <thead>
            <tr>
              <th scope="col">Etapa</th>
              <th scope="col">IDEB</th>
              <th scope="col">SAEB Língua Portuguesa</th>
              <th scope="col">SAEB Matemática</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((stage) => (
              <tr key={stage.key}>
                <th scope="row">{stage.label}</th>
                <LearningMetricCell label="IDEB" metric={stage.metrics.ideb} />
                <LearningMetricCell label="SAEB Língua Portuguesa" metric={stage.metrics.saebLp} />
                <LearningMetricCell label="SAEB Matemática" metric={stage.metrics.saebMt} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="municipal-learning-outcomes__note">IDEB e SAEB são divulgados pelo INEP. O ano de referência pode variar quando não houver resultado municipal publicável para uma etapa.</p>
    </section>
  )
}

function LearningMetricCell({
  label,
  metric,
}: {
  label: string
  metric: MunicipalLearningMetricSnapshot
}) {
  const tone = getMunicipalLearningChangeTone(metric)
  const changePeriod = metric.previousYear && metric.currentYear
    ? `${metric.previousYear}–${metric.currentYear}`
    : null

  return (
    <td data-label={label}>
      <span className="municipal-learning-outcomes__value">
        <strong>{formatMunicipalLearningValue(metric)}</strong>
        {metric.currentYear ? <small>{metric.currentYear}</small> : null}
      </span>
      <span className={`municipal-learning-outcomes__change municipal-learning-outcomes__change--${tone}`}>
        {formatMunicipalLearningChange(metric)}
        {changePeriod ? <small>{changePeriod}</small> : null}
      </span>
    </td>
  )
}

const COMPARISON_STAGES = [
  ['basicEducation', 'Educação Básica'],
  ['earlyChildhood', 'Educação Infantil'],
  ['creche', 'Creche'],
  ['preSchool', 'Pré-escola'],
  ['elementary', 'Ensino Fundamental'],
  ['initialYears', 'Anos Iniciais'],
  ['finalYears', 'Anos Finais'],
  ['highSchool', 'Ensino Médio'],
  ['youthAndAdultEducation', 'Educação de Jovens e Adultos — EJA'],
] as const

const COMPARISON_NETWORKS = [
  ['publicSubtotal', 'Rede pública'],
  ['municipal', 'Municipal'],
  ['state', 'Estadual'],
  ['federal', 'Federal'],
  ['private', 'Privada'],
] as const

const COMPARISON_LOCATIONS = [
  ['urban', 'Urbana'],
  ['rural', 'Rural'],
] as const

function EnrollmentComparisonSection({ data }: Pick<EducationOverviewSectionProps, 'data'>) {
  const stages = data.enrollmentComparison.stages
  const breakdownStages = COMPARISON_STAGES.filter(([key]) => key !== 'basicEducation')
  return (
    <section className="municipal-education-overview__section municipal-enrollment-comparison" aria-labelledby="municipal-enrollment-comparison-title">
      <div className="municipal-education-overview__section-heading">
        <h2 id="municipal-enrollment-comparison-title">Comparação das matrículas — 2015 e 2025</h2>
        <p>Os valores mostram as matrículas registradas em 2015 e 2025. A variação corresponde à mudança percentual entre os dois anos.</p>
      </div>
      <ComparisonTable
        caption="Matrículas por etapa e modalidade em 2015 e 2025"
        rows={COMPARISON_STAGES.map(([key, label]) => ({ label, value: stages[key].total }))}
        title="Matrículas por etapa e modalidade"
      />
      <div className="municipal-enrollment-comparison__group">
        <h3>Dependência administrativa por etapa</h3>
        <p className="municipal-enrollment-comparison__note">Rede pública corresponde à soma das matrículas municipal, estadual e federal. Redes sem matrículas registradas em 2015 e 2025 não são exibidas.</p>
        {breakdownStages.map(([key, label]) => {
          const rows = COMPARISON_NETWORKS.map(([network, networkLabel]) => ({
              label: networkLabel,
              value: stages[key].byNetwork![network],
            })).filter(({ value }) => hasRelevantNetworkComparison(value))
          return rows.length ? (
            <ComparisonTable
              caption={`${label}: matrículas por dependência administrativa em 2015 e 2025`}
              key={key}
              rows={rows}
              title={label}
            />
          ) : null
        })}
      </div>
      <div className="municipal-enrollment-comparison__group">
        <h3>Localização da escola por etapa</h3>
        {breakdownStages.map(([key, label]) => (
          <ComparisonTable
            caption={`${label}: matrículas por localização da escola em 2015 e 2025`}
            key={key}
            rows={COMPARISON_LOCATIONS.map(([location, locationLabel]) => ({
              label: locationLabel,
              value: stages[key].bySchoolLocation![location],
            }))}
            title={label}
          />
        ))}
      </div>
    </section>
  )
}

function ComparisonTable({
  caption,
  rows,
  title,
}: {
  caption: string
  rows: Array<{ label: string; value: EnrollmentComparisonValue }>
  title: string
}) {
  return (
    <section className="municipal-enrollment-comparison__table">
      <h4>{title}</h4>
      <table>
        <caption>{caption}</caption>
        <thead><tr><th scope="col">Etapa ou recorte</th><th scope="col">2015</th><th scope="col">2025</th><th scope="col">Variação 2015–2025</th></tr></thead>
        <tbody>{rows.map(({ label, value }) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td data-label="2015">{formatOverviewEnrollments(value.value2015)}</td>
            <td data-label="2025">{formatOverviewEnrollments(value.value2025)}</td>
            <td className={`municipal-enrollment-comparison__variation municipal-enrollment-comparison__variation--${getComparisonVariationTone(value)}`} data-label="Variação">
              {formatComparisonPercentage(value)}
            </td>
          </tr>
        ))}</tbody>
      </table>
    </section>
  )
}

function formatComparisonPercentage(value: EnrollmentComparisonValue): string {
  const percentage = value.percentageChange
  if (percentage.state !== 'observed' || percentage.value === null) return '—'
  if (percentage.value === 0) return '0,0%'
  const formatted = new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(Math.abs(percentage.value))
  return `${percentage.value > 0 ? '+' : '−'}${formatted}%`
}

function getComparisonVariationTone(value: EnrollmentComparisonValue): 'positive' | 'negative' | 'neutral' {
  const percentage = value.percentageChange
  if (percentage.state !== 'observed' || percentage.value === null || percentage.value === 0) return 'neutral'
  return percentage.value > 0 ? 'positive' : 'negative'
}

function EducationStageSnapshot({
  data,
  detailsHref,
  detailsLabel,
  stage,
  title,
}: {
  data: MunicipalEducationOverviewV1
  detailsHref: string
  detailsLabel: string
  stage: 'earlyChildhood' | 'elementary'
  title: string
}) {
  const isEarlyChildhood = stage === 'earlyChildhood'
  const snapshot = isEarlyChildhood ? data.earlyChildhood : data.elementary
  const substageOne = isEarlyChildhood ? data.earlyChildhood.creche : data.elementary.initialYears
  const substageTwo = isEarlyChildhood ? data.earlyChildhood.preSchool : data.elementary.finalYears
  const substageOneLabel = isEarlyChildhood ? 'Creche' : 'Anos Iniciais'
  const substageTwoLabel = isEarlyChildhood ? 'Pré-escola' : 'Anos Finais'
  const headingId = `${stage}-snapshot-title`

  return (
    <section className="municipal-education-overview__section municipal-education-stage" aria-labelledby={headingId}>
      <div className="municipal-education-overview__section-heading">
        <h2 id={headingId}>{title}</h2>
      </div>

      <dl className="municipal-education-stage__summary">
        <OverviewMetric
          label={isEarlyChildhood ? 'Educação Infantil' : 'Ensino Fundamental'}
          value={snapshot.total.total}
          share={snapshot.total.shareOfBasicEducation}
          shareLabel={`${isEarlyChildhood ? 'Educação Infantil' : 'Ensino Fundamental'} em relação à Educação Básica`}
          primary
        />
        <OverviewMetric
          label={substageOneLabel}
          value={substageOne.total}
          share={substageOne.shareOfParentStage}
          shareLabel={`${substageOneLabel} em relação ${isEarlyChildhood ? 'à Educação Infantil' : 'ao Ensino Fundamental'}`}
        />
        <OverviewMetric
          label={substageTwoLabel}
          value={substageTwo.total}
          share={substageTwo.shareOfParentStage}
          shareLabel={`${substageTwoLabel} em relação ${isEarlyChildhood ? 'à Educação Infantil' : 'ao Ensino Fundamental'}`}
        />
      </dl>

      <div className="municipal-education-stage__matrices">
        <EducationSnapshotMatrix
          id={`${stage}-network-title`}
          rows={NETWORK_ROWS}
          stages={[
            { label: isEarlyChildhood ? 'Educação Infantil' : 'Ensino Fundamental', value: snapshot.total },
            { label: substageOneLabel, value: substageOne },
            { label: substageTwoLabel, value: substageTwo },
          ]}
          title="Dependência administrativa"
        />
        <EducationSnapshotMatrix
          id={`${stage}-location-title`}
          rows={LOCATION_ROWS}
          stages={[
            { label: isEarlyChildhood ? 'Educação Infantil' : 'Ensino Fundamental', value: snapshot.total },
            { label: substageOneLabel, value: substageOne },
            { label: substageTwoLabel, value: substageTwo },
          ]}
          title="Localização da escola"
        />
      </div>
      <a className="municipal-education-stage__detail-link" href={detailsHref}>
        <span>{detailsLabel}</span><ArrowRight aria-hidden="true" size={16} />
      </a>
    </section>
  )
}

function OverviewMetric({
  label,
  value,
  share,
  shareLabel,
  primary = false,
}: {
  label: string
  value: SnapshotValue
  share?: SnapshotPercentage
  shareLabel: string
  primary?: boolean
}) {
  return (
    <div className={`municipal-education-stage__metric${primary ? ' municipal-education-stage__metric--primary' : ''}`}>
      <dt>{label}</dt>
      <dd>{formatOverviewEnrollments(value)}</dd>
      <span className="municipal-education-stage__metric-share">
        <strong>{formatOverviewPercentage(share)}</strong>
        <span>{shareLabel}</span>
      </span>
    </div>
  )
}

function EducationSnapshotMatrix({
  columnsLabel = 'Recorte',
  id,
  rows,
  splitSingleStage = false,
  stages,
  title,
}: {
  columnsLabel?: string
  id: string
  rows: ReadonlyArray<SnapshotMatrixRow>
  splitSingleStage?: boolean
  stages: ReadonlyArray<{ label: string; value: StageSnapshot }>
  title: string
}) {
  const splitStage = splitSingleStage ? stages[0] : undefined

  return (
    <section className={`municipal-education-matrix${splitStage ? ' municipal-education-matrix--split' : ''}`} aria-labelledby={id}>
      <h3 id={id}>{title}</h3>
      <div className="municipal-education-matrix__table-region" tabIndex={0} aria-label={`${title}: matrículas e participação por etapa`}>
        <table className="municipal-education-matrix__table">
          <caption>{title}: número de matrículas e participação em cada etapa</caption>
          <thead>
            <tr>
              <th scope="col">{columnsLabel}</th>
              {splitStage ? (
                <><th scope="col">Matrículas</th><th scope="col">Participação no Ensino Médio</th></>
              ) : stages.map((stage) => <th scope="col" key={stage.label}>{stage.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className={row.label === 'Rede pública' ? 'municipal-education-matrix__subtotal' : undefined} key={row.label}>
                <th scope="row">{row.label}</th>
                {splitStage ? (() => {
                  const value = row.select(splitStage.value)
                  return <>
                    <td aria-label={`Matrículas: ${formatOverviewEnrollments(value.enrollments)}`} data-label="Matrículas"><MatrixEnrollment value={value} /></td>
                    <td aria-label={`Participação no Ensino Médio: ${formatOverviewPercentage(value.share)}`} data-label="Participação"><MatrixPercentage value={value} /></td>
                  </>
                })() : stages.map((stage) => {
                  const value = row.select(stage.value)
                  return (
                    <td aria-label={`${stage.label}: ${describeOverviewMatrixValue(value)}`} data-label={stage.label} key={stage.label}>
                      <MatrixValue value={value} />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="municipal-education-matrix__mobile" aria-label={`${title}: matrículas e participação por etapa`}>
        {splitStage ? (
          <section className="municipal-education-matrix__mobile-stage" aria-label="Matrículas e participação no Ensino Médio">
            <h4>Matrículas e participação no Ensino Médio</h4>
            <dl className="municipal-education-matrix__mobile-split">
              {rows.map((row) => {
                const value = row.select(splitStage.value)
                return <div className={row.label === 'Rede pública' ? 'municipal-education-matrix__mobile-subtotal' : undefined} key={row.label}>
                  <dt>{row.label}</dt>
                  <dd><span>Matrículas:</span><MatrixEnrollment value={value} /></dd>
                  <dd><span>Participação:</span><MatrixPercentage value={value} /></dd>
                </div>
              })}
            </dl>
          </section>
        ) : stages.map((stage, stageIndex) => {
          const stageId = `${id}-mobile-stage-${stageIndex}`
          return (
            <section className="municipal-education-matrix__mobile-stage" aria-labelledby={stageId} key={stage.label}>
              <h4 id={stageId}>{stage.label}</h4>
              <dl>
                {rows.map((row) => {
                  const value = row.select(stage.value)
                  return (
                    <div className={row.label === 'Rede pública' ? 'municipal-education-matrix__mobile-subtotal' : undefined} key={row.label}>
                      <dt>{row.label}</dt>
                      <dd aria-label={describeOverviewMatrixValue(value)}><MatrixValue value={value} /></dd>
                    </div>
                  )
                })}
              </dl>
            </section>
          )
        })}
      </div>
    </section>
  )
}

function MatrixEnrollment({ value }: { value: BreakdownValue }) {
  return <span className="municipal-education-matrix__enrollments">{formatOverviewEnrollments(value.enrollments)}</span>
}

function MatrixPercentage({ value }: { value: BreakdownValue }) {
  return <span className="municipal-education-matrix__percentage">{formatOverviewPercentage(value.share)}</span>
}

function MatrixValue({ value }: { value: BreakdownValue }) {
  const enrollments = formatOverviewEnrollments(value.enrollments)

  if (enrollments === '—') {
    return <span className="municipal-education-matrix__value municipal-education-matrix__value--unavailable" aria-hidden="true">—</span>
  }

  return (
    <span className="municipal-education-matrix__value" aria-hidden="true">
      <span className="municipal-education-matrix__enrollments">{enrollments}</span>
      <span className="municipal-education-matrix__separator">·</span>
      <span className="municipal-education-matrix__percentage">{formatOverviewPercentage(value.share)}</span>
    </span>
  )
}

function EducationOverviewSources({ data }: Pick<EducationOverviewSectionProps, 'data'>) {
  const methodology = getMunicipalOverviewMethodologyHighlights(data)

  return (
    <footer className="municipal-education-overview__section municipal-education-sources" aria-labelledby="municipal-education-sources-title">
      <div className="municipal-education-overview__section-heading">
        <h2 id="municipal-education-sources-title">Fontes das informações</h2>
      </div>
      {data.sources.length ? (
        <ul className="municipal-education-sources__list">
          {data.sources.map((source) => (
            <li key={source.id}>
              <div>
                <strong>{source.organization}</strong>
                <span>{source.title} · {source.referenceYear}</span>
              </div>
              {source.url ? <a href={source.url} rel="noreferrer" target="_blank">Abrir fonte oficial</a> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {methodology.length ? (
        <div className="municipal-education-sources__methodology">
          <h3>Como ler estes dados</h3>
          <ul>{methodology.map((note) => <li key={note}>{note}</li>)}</ul>
        </div>
      ) : null}
    </footer>
  )
}
