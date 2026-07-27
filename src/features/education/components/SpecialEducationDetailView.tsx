import { useMemo } from 'react'
import { ContentState } from '../../../components/ContentState.jsx'
import { DataSourceNote } from '../../../components/DataSourceNote.jsx'
import { EducationBarChart } from '../../../components/EducationBarChart.jsx'
import { EducationLineChart } from '../../../components/EducationLineChart.jsx'
import { EducationQuickReading } from '../../../components/EducationQuickReading.jsx'
import { IndicatorChartHeader } from '../../../components/IndicatorChartHeader.jsx'
import { MetricCard } from '../../../components/MetricCard.jsx'
import {
  buildIndicatorSeries,
  formatSpecialEducationValue,
  isPublishableSpecialEducationPoint,
  isResolvedSpecialEducationPoint,
  SPECIAL_EDUCATION_REFERENCE_YEAR,
  SPECIAL_EDUCATION_DEFINITIONS,
  specialEducationCutLabel,
} from '../specialEducationViewModel'
import type {
  SpecialEducationCut,
  SpecialEducationIndicatorId,
  SpecialEducationMunicipalDocument,
  SpecialEducationPoint,
  SpecialEducationYearCut,
} from '../specialEducationTypes'
import {
  EducationIndicatorDetailShell,
  EducationMetricGrid,
  EducationMetricSummary,
  EducationSupportDataCard,
  EducationSupportDataSection,
} from './EducationIndicatorDetailShell'

interface SpecialEducationDetailViewProps {
  cut: SpecialEducationCut
  document: SpecialEducationMunicipalDocument
  indicatorId: SpecialEducationIndicatorId
}

interface SupportHistory {
  description: string
  eyebrow: string
  key: string
  percent?: boolean
  series: Array<{ ano: number; valor: number | null }>
  title: string
}

const SOURCE = 'Censo Escolar da Educação Básica — INEP.'
const numberFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const percentFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export function SpecialEducationDetailView({
  cut,
  document,
  indicatorId,
}: SpecialEducationDetailViewProps) {
  const definition = SPECIAL_EDUCATION_DEFINITIONS[indicatorId]
  const reference = document.years.find(({ year }) => year === SPECIAL_EDUCATION_REFERENCE_YEAR)
  const referenceCut = reference?.cuts[cut]
  const referencePoint = referenceCut ? pointForDetailIndicator(referenceCut, indicatorId) : undefined
  const percent = indicatorId === 'educacao-especial-inclusao-classes-comuns'
  const snapshotOnly = indicatorId === 'educacao-bilingue-surdos'
  const primarySeries = useMemo(
    () => buildIndicatorSeries(document, indicatorId, cut),
    [cut, document, indicatorId],
  )
  const resolvedPoints = primarySeries.filter(
    (point): point is typeof point & { valor: number } => point.valor != null,
  )
  const initialPoint = primarySeries.find((point) => point.ano === 2014 && point.valor != null)
  const referenceSeriesPoint = primarySeries.find(
    (point): point is typeof point & { valor: number } =>
      point.ano === SPECIAL_EDUCATION_REFERENCE_YEAR && point.valor != null,
  )
  const variation = buildVariation(initialPoint?.valor, referenceSeriesPoint?.valor, percent)
  const cutLabel = specialEducationCutLabel(cut)
  const supportHistories = useMemo(
    () => buildSupportHistories(document, indicatorId, cut),
    [cut, document, indicatorId],
  )

  if (!isPublishableSpecialEducationPoint(referencePoint)) {
    return (
      <ContentState className="state-box special-education-reference-state" kind="unavailable">
        Este indicador não possui valor disponível para 2025 neste município.
      </ContentState>
    )
  }

  const summary = snapshotOnly && referenceCut
    ? <BilingualSnapshotSummary cut={referenceCut} year={SPECIAL_EDUCATION_REFERENCE_YEAR} />
    : (
        <EducationMetricSummary
          currentLabel={percent ? 'Percentual em 2025' : 'Valor em 2025'}
          currentValue={formatSeriesValue(referenceSeriesPoint?.valor, percent)}
          currentYear={SPECIAL_EDUCATION_REFERENCE_YEAR}
          initialLabel={percent ? 'Percentual inicial' : 'Valor inicial'}
          initialValue={formatSeriesValue(initialPoint?.valor, percent)}
          initialYear={initialPoint?.ano}
          statusDetail="Tendência calculada até 2025"
          statusLabel={trendLabel(variation.raw)}
          statusTone={variation.tone}
          variation={variation}
          variationLabel={percent ? 'Variação de 2014 a 2025 em pontos percentuais' : 'Variação de 2014 a 2025'}
        />
      )

  const primaryPanel = (
    <article className="educacao-main-chart-card indicator-chart-card">
      <IndicatorChartHeader
        subtitle={`${definition.label} · Recorte exibido: ${cutLabel}`}
        summary={null}
        title={snapshotOnly ? 'Situação do indicador em 2025' : 'Evolução do indicador'}
      >{null}</IndicatorChartHeader>
      {snapshotOnly ? (
        <BilingualPrimaryChart cut={referenceCut} year={SPECIAL_EDUCATION_REFERENCE_YEAR} />
      ) : resolvedPoints.length >= 2 ? (
        <EducationLineChart
          formatLabel={percent ? formatPercent : numberFormatter.format}
          hideTitle
          integerTicks={!percent}
          scaleType={percent ? 'percent' : 'count'}
          series={primarySeries}
          showPointLabels
          title={`Evolução de ${definition.label}`}
        />
      ) : (
        <ContentState kind="empty">
          {resolvedPoints.length === 1
            ? `Há somente um ponto utilizável, referente a ${resolvedPoints[0].ano}.`
            : 'Não há pontos utilizáveis para formar uma série histórica.'}
        </ContentState>
      )}
      <DataSourceNote context={undefined} source={SOURCE} />
    </article>
  )

  const quickReading = (
    <EducationQuickReading
      items={[
        {
          icon: snapshotOnly ? 'measure' : 'trend',
          key: 'evolution',
          label: snapshotOnly ? 'Situação observada em 2025' : 'Evolução observada',
          text: snapshotOnly
            ? buildSnapshotReading(referenceCut, SPECIAL_EDUCATION_REFERENCE_YEAR, cutLabel)
            : buildEvolutionReading(referenceSeriesPoint, initialPoint, variation, percent, definition.unit),
        },
        {
          icon: 'measure',
          key: 'measure',
          label: 'O que o indicador mede',
          text: definition.description,
        },
        {
          icon: 'cut',
          key: 'cut',
          label: 'Recorte exibido',
          text: `${cutLabel}.`,
        },
      ]}
      tone={snapshotOnly ? 'default' : variation.tone}
    />
  )

  return (
    <EducationIndicatorDetailShell
      primaryPanel={primaryPanel}
      quickReading={quickReading}
      summary={summary}
    >
      {referenceCut ? (
        <SpecialEducationSupportData
          cut={referenceCut}
          histories={supportHistories}
          indicatorId={indicatorId}
          year={SPECIAL_EDUCATION_REFERENCE_YEAR}
        />
      ) : null}
    </EducationIndicatorDetailShell>
  )
}

function BilingualSnapshotSummary({ cut, year }: { cut: SpecialEducationYearCut; year: number }) {
  const cards = [
    ['Matrículas em classes bilíngues', cut.bilingualDeafEducation.enrollments, 'matrículas', 'current'],
    ['Escolas com matrícula ou turma bilíngue', cut.bilingualDeafEducation.schools, 'escolas', 'type'],
    ['Turmas bilíngues', cut.bilingualDeafEducation.classes, 'turmas', 'comparison'],
    ['Docentes em atuação nas escolas', cut.bilingualDeafEducation.teacherAssignments, 'docentes', 'status'],
  ] as const

  return (
    <EducationMetricGrid>
      {cards.map(([label, point, , icon], index) => (
        <MetricCard
          detail={index === 0 ? `Retrato disponível em ${year}` : 'Ano de referência'}
          icon={icon}
          key={label}
          label={label}
          size={index === 0 ? 'large' : 'normal'}
          value={formatSpecialEducationValue(point)}
        />
      ))}
    </EducationMetricGrid>
  )
}

function BilingualPrimaryChart({
  cut,
  year,
}: {
  cut?: SpecialEducationYearCut
  year: number
}) {
  const data = resolvedEntries([
    ['Escolas com oferta', cut?.bilingualDeafEducation.schools],
    ['Turmas bilíngues', cut?.bilingualDeafEducation.classes],
  ])

  return data.length ? (
    <EducationBarChart
      data={data}
      formatLabel={numberFormatter.format}
      preserveOrder
      size="large"
      title={`Oferta bilíngue em ${year}`}
    />
  ) : (
    <ContentState kind="empty">Sem informação utilizável para este recorte.</ContentState>
  )
}

function SpecialEducationSupportData({
  cut,
  histories,
  indicatorId,
  year,
}: {
  cut: SpecialEducationYearCut
  histories: SupportHistory[]
  indicatorId: SpecialEducationIndicatorId
  year: number
}) {
  const cards = buildSnapshotSupportCards(indicatorId, cut, year)
  if (!histories.length && !cards.length) return null

  return (
    <EducationSupportDataSection
      footer={<DataSourceNote context={undefined} source={SOURCE} />}
      id={`special-education-support-${indicatorId}`}
    >
      {histories.map((history) => (
        <EducationSupportDataCard
          description={history.description}
          eyebrow={history.eyebrow}
          id={`special-education-${indicatorId}-${history.key}`}
          key={history.key}
          title={history.title}
        >
          <EducationLineChart
            formatLabel={history.percent ? formatPercent : numberFormatter.format}
            hideTitle
            integerTicks={!history.percent}
            scaleType={history.percent ? 'percent' : 'count'}
            series={history.series}
            showPointLabels
            title={history.title}
          />
        </EducationSupportDataCard>
      ))}
      {cards}
    </EducationSupportDataSection>
  )
}

function buildSnapshotSupportCards(
  indicatorId: SpecialEducationIndicatorId,
  cut: SpecialEducationYearCut,
  year: number,
) {
  if (indicatorId === 'educacao-especial-matriculas') {
    const stageData = resolvedEntries(Object.entries(cut.specialEducation.stages).map(
      ([key, point]) => [formatStageLabel(key), point] as [string, SpecialEducationPoint],
    ))
    const complementary = [
      ['Tempo integral', cut.specialEducation.fullTimeEnrollments, 'matrículas'],
      ['Turmas', cut.specialEducation.classes, 'turmas'],
      ['Docentes em atuação nas escolas', cut.specialEducation.teacherAssignmentsInSchools, 'docentes'],
    ] as const
    return [
      stageData.length ? (
        <EducationSupportDataCard
          className="education-support-data__item--full-row"
          description="Distribuição das matrículas pelos níveis e etapas disponíveis."
          eyebrow="Por etapa"
          id="special-education-enrollments-stages"
          key="stages"
          title={`Matrículas da Educação Especial por etapa — ${year}`}
        >
          <EducationBarChart data={stageData} formatLabel={numberFormatter.format} preserveOrder size="large" title={`Matrículas por etapa em ${year}`} />
        </EducationSupportDataCard>
      ) : null,
      resolvedEntries(complementary.map(([label, point]) => [label, point])).length ? (
        <EducationSupportDataCard
          className="education-support-data__item--full-row"
          description="Informações complementares disponíveis para o mesmo recorte."
          eyebrow="Perfil da oferta"
          id="special-education-enrollments-complementary"
          key="complementary"
          title={`Tempo integral, turmas e docentes — ${year}`}
        >
          <div className="metric-grid metric-grid--three">
            {complementary
              .filter(([, point]) => isPublishableSpecialEducationPoint(point))
              .map(([label, point, unit]) => (
                <MetricCard
                  detail={`${year} · ${unit}${point.state === 'partial' ? ' · Dado parcial' : ''}`}
                  key={label}
                  label={label}
                  value={formatSpecialEducationValue(point)}
                />
              ))}
          </div>
        </EducationSupportDataCard>
      ) : null,
    ].filter(Boolean)
  }

  if (indicatorId === 'educacao-especial-inclusao-classes-comuns') {
    const composition = resolvedEntries([
      ['Classes comuns', cut.specialEducation.commonClassEnrollments],
      ['Classes exclusivas', cut.specialEducation.exclusiveClassEnrollments],
    ])
    return composition.length ? [
      <EducationSupportDataCard
        className="education-support-data__item--full-row"
        description="Quantidade de matrículas em cada tipo de classe no ano mais recente."
        eyebrow="Composição"
        id="special-education-inclusion-composition"
        key="composition"
        title={`Matrículas por tipo de classe — ${year}`}
      >
        <EducationBarChart data={composition} formatLabel={numberFormatter.format} preserveOrder size="large" title={`Composição das matrículas em ${year}`} />
      </EducationSupportDataCard>,
    ] : []
  }

  if (indicatorId === 'aee') {
    const offer = resolvedEntries([
      ['Oferecem AEE', cut.aee.schoolsOfferingAee],
      ['AEE exclusivo', cut.aee.schoolsExclusiveAee],
      ['Sala de recursos', cut.aee.schoolsWithResourceRoom],
    ])
    return offer.length ? [
      <EducationSupportDataCard
        className="education-support-data__item--full-row"
        description="Síntese das estruturas e formas de oferta registradas no recorte."
        eyebrow="Oferta em 2025"
        id="special-education-aee-offer"
        key="offer"
        title={`AEE, AEE exclusivo e salas de recursos — ${year}`}
      >
        <EducationBarChart data={offer} formatLabel={numberFormatter.format} preserveOrder size="large" title={`Oferta de AEE em ${year}`} />
      </EducationSupportDataCard>,
    ] : []
  }

  const offer = resolvedEntries([
    ['Escolas', cut.bilingualDeafEducation.schools],
    ['Turmas bilíngues', cut.bilingualDeafEducation.classes],
  ])
  const professionals = resolvedEntries([
    ['Docentes', cut.bilingualDeafEducation.teacherAssignments],
    ['Intérpretes de Libras', cut.bilingualDeafEducation.interpreterAssignments],
    ['Guia-intérpretes', cut.bilingualDeafEducation.guideInterpreterAssignments],
  ])
  const partialProfessionals = partialEntries([
    ['Docentes', cut.bilingualDeafEducation.teacherAssignments],
    ['Intérpretes de Libras', cut.bilingualDeafEducation.interpreterAssignments],
    ['Guia-intérpretes', cut.bilingualDeafEducation.guideInterpreterAssignments],
  ])
  const conditions = [
    ['Escolas com materiais', cut.bilingualDeafEducation.schoolsWithMaterials, 'escolas'],
    ['Turmas com Libras no currículo', cut.bilingualDeafEducation.librasCurriculumClasses, 'turmas'],
    ['Docentes com especialização bilíngue', cut.bilingualDeafEducation.bilingualSpecializationTeacherAssignments, 'docentes'],
    ['Docentes com especialização em gestão', cut.bilingualDeafEducation.managementSpecializationTeacherAssignments, 'docentes'],
  ] as const

  return [
    offer.length ? (
      <EducationSupportDataCard
        description="Escolas e turmas com oferta bilíngue registrada."
        eyebrow="Oferta"
        id="special-education-bilingual-offer"
        key="offer"
        title="Escolas e turmas bilíngues"
      >
        <EducationBarChart data={offer} formatLabel={numberFormatter.format} preserveOrder title={`Oferta bilíngue em ${year}`} />
      </EducationSupportDataCard>
    ) : null,
    professionals.length || partialProfessionals.length ? (
      <EducationSupportDataCard
        description="Vínculos docentes e de profissionais de apoio registrados."
        eyebrow="Profissionais"
        id="special-education-bilingual-professionals"
        key="professionals"
        title="Docentes e profissionais de apoio"
      >
        {professionals.length ? (
          <EducationBarChart data={professionals} formatLabel={numberFormatter.format} preserveOrder title={`Profissionais em ${year}`} />
        ) : null}
        {partialProfessionals.length ? (
          <div className="metric-grid metric-grid--three">
            {partialProfessionals.map(({ label, point }) => (
              <MetricCard
                detail={`${year} · Dado parcial`}
                key={label}
                label={label}
                value={formatSpecialEducationValue(point)}
              />
            ))}
          </div>
        ) : null}
      </EducationSupportDataCard>
    ) : null,
    resolvedEntries(conditions.map(([label, point]) => [label, point])).length ? (
      <EducationSupportDataCard
        className="education-support-data__item--full-row"
        description="Cada valor mantém sua própria unidade para evitar comparações em escala incompatível."
        eyebrow="Condições de atendimento"
        id="special-education-bilingual-conditions"
        key="conditions"
        title="Materiais, Libras e apoio especializado"
      >
        <div className="metric-grid metric-grid--four">
          {conditions
            .filter(([, point]) => isPublishableSpecialEducationPoint(point))
            .map(([label, point, unit]) => (
              <MetricCard
                detail={`${year} · ${unit}${point.state === 'partial' ? ' · Dado parcial' : ''}`}
                key={label}
                label={label}
                value={formatSpecialEducationValue(point)}
              />
            ))}
        </div>
      </EducationSupportDataCard>
    ) : null,
  ].filter(Boolean)
}

function pointForDetailIndicator(
  cut: SpecialEducationYearCut,
  indicatorId: SpecialEducationIndicatorId,
) {
  if (indicatorId === 'educacao-especial-matriculas') return cut.specialEducation.enrollments
  if (indicatorId === 'educacao-especial-inclusao-classes-comuns') return cut.commonClassInclusionRate
  if (indicatorId === 'aee') return cut.aee.schoolsOfferingAee
  return cut.bilingualDeafEducation.enrollments
}

function buildSupportHistories(
  document: SpecialEducationMunicipalDocument,
  indicatorId: SpecialEducationIndicatorId,
  cut: SpecialEducationCut,
): SupportHistory[] {
  if (indicatorId === 'educacao-bilingue-surdos') return []

  const definitions = indicatorId === 'educacao-especial-matriculas'
    ? [
        {
          description: 'Histórico das matrículas da Educação Especial incluídas em classes comuns.',
          eyebrow: 'Por tipo de classe',
          key: 'common-classes',
          point: (payload: SpecialEducationYearCut) => payload.specialEducation.commonClassEnrollments,
          title: 'Matrículas em classes comuns',
        },
        {
          description: 'Histórico das matrículas da Educação Especial em classes exclusivas.',
          eyebrow: 'Por tipo de classe',
          key: 'exclusive-classes',
          point: (payload: SpecialEducationYearCut) => payload.specialEducation.exclusiveClassEnrollments,
          title: 'Matrículas em classes exclusivas',
        },
      ]
    : indicatorId === 'educacao-especial-inclusao-classes-comuns'
      ? [
          {
            description: 'Participação das matrículas em classes comuns no total da Educação Especial.',
            eyebrow: 'Por tipo de classe',
            key: 'common-share',
            percent: true,
            point: (payload: SpecialEducationYearCut) => payload.commonClassInclusionRate,
            title: 'Participação em classes comuns',
          },
          {
            description: 'Participação das matrículas em classes exclusivas no total da Educação Especial.',
            eyebrow: 'Por tipo de classe',
            key: 'exclusive-share',
            percent: true,
            point: exclusiveClassShare,
            title: 'Participação em classes exclusivas',
          },
        ]
      : [
          {
            description: 'Histórico de escolas com sala de recursos multifuncionais.',
            eyebrow: 'Estrutura',
            key: 'resource-rooms',
            point: (payload: SpecialEducationYearCut) => payload.aee.schoolsWithResourceRoom,
            title: 'Escolas com sala de recursos',
          },
          {
            description: 'Histórico do universo de escolas com matrículas da Educação Especial.',
            eyebrow: 'Universo',
            key: 'eligible-schools',
            point: (payload: SpecialEducationYearCut) => payload.aee.eligibleSchools,
            title: 'Escolas com matrículas da Educação Especial',
          },
        ]

  return definitions.flatMap((definition) => {
    const series = document.years.map(({ year, cuts }) => {
      const point = definition.point(cuts[cut])
      return { ano: year, valor: isResolvedSpecialEducationPoint(point) ? Number(point?.value) : null }
    })
    return series.filter((point) => point.valor != null).length >= 2
      ? [{ ...definition, series }]
      : []
  })
}

function exclusiveClassShare(payload: SpecialEducationYearCut): SpecialEducationPoint | undefined {
  const exclusive = payload.specialEducation.exclusiveClassEnrollments
  const total = payload.specialEducation.enrollments
  if (!isResolvedSpecialEducationPoint(exclusive) || !isResolvedSpecialEducationPoint(total) || total.value === 0) return undefined
  return { ...exclusive, value: 100 * Number(exclusive.value) / Number(total.value) }
}

function buildVariation(initialValue: number | undefined, currentValue: number | undefined, percent: boolean) {
  if (initialValue == null || currentValue == null) return { display: '—', raw: null, tone: 'muted' }
  const difference = currentValue - initialValue
  if (percent) {
    return {
      display: `${difference > 0 ? '+' : ''}${percentFormatter.format(difference)} p.p.`,
      raw: difference,
      tone: difference > 0 ? 'success' : difference < 0 ? 'warning' : 'muted',
    }
  }
  if (initialValue === 0) {
    return {
      display: `${difference > 0 ? '+' : ''}${numberFormatter.format(difference)}`,
      raw: difference,
      tone: difference > 0 ? 'success' : difference < 0 ? 'warning' : 'muted',
    }
  }
  const relative = 100 * difference / Math.abs(initialValue)
  return {
    display: `${relative > 0 ? '+' : ''}${percentFormatter.format(relative)}%`,
    raw: relative,
    tone: difference > 0 ? 'success' : difference < 0 ? 'warning' : 'muted',
  }
}

function trendLabel(raw: number | null) {
  if (raw == null) return 'Sem série'
  if (raw > 0) return 'Alta'
  if (raw < 0) return 'Queda'
  return 'Estável'
}

function buildEvolutionReading(
  latest: { ano: number; valor: number } | undefined,
  initial: { ano: number; valor: number } | undefined,
  variation: ReturnType<typeof buildVariation>,
  percent: boolean,
  unit: string,
) {
  if (!latest || !initial || variation.raw == null) return 'Não há série histórica suficiente para comparar o período.'
  const movement = variation.raw > 0 ? 'aumento' : variation.raw < 0 ? 'redução' : 'estabilidade'
  const unitText = percent ? '' : ` ${unit}`
  return `Em ${latest.ano}, o município registrou ${formatSeriesValue(latest.valor, percent)}${unitText}. Em relação a ${initial.ano}, houve ${movement} de ${variation.display.replace(/^\+/, '')}.`
}

function buildSnapshotReading(cut: SpecialEducationYearCut | undefined, year: number, cutLabel: string) {
  const enrollments = cut?.bilingualDeafEducation.enrollments
  const schools = cut?.bilingualDeafEducation.schools
  if (!isResolvedSpecialEducationPoint(enrollments) && !isResolvedSpecialEducationPoint(schools)) {
    return `Não há informação utilizável para o recorte ${cutLabel.toLocaleLowerCase('pt-BR')} em ${year}.`
  }
  return `Em ${year}, o recorte registra ${formatSpecialEducationValue(enrollments)} matrículas em classes bilíngues e ${formatSpecialEducationValue(schools)} escolas com matrícula ou turma bilíngue.`
}

function resolvedEntries(entries: ReadonlyArray<readonly [string, SpecialEducationPoint | undefined]>) {
  return entries
    .filter((entry): entry is readonly [string, SpecialEducationPoint] => isResolvedSpecialEducationPoint(entry[1]))
    .map(([label, point]) => ({ label, value: Number(point.value) }))
}

function partialEntries(entries: ReadonlyArray<readonly [string, SpecialEducationPoint | undefined]>) {
  return entries
    .filter((entry): entry is readonly [string, SpecialEducationPoint] => (
      entry[1]?.state === 'partial' && entry[1].value != null
    ))
    .map(([label, point]) => ({ label, point }))
}

function formatSeriesValue(value: number | null | undefined, percent: boolean) {
  if (value == null) return '—'
  return percent ? formatPercent(value) : numberFormatter.format(value)
}

function formatPercent(value: number) {
  return `${percentFormatter.format(value)}%`
}

const SPECIAL_EDUCATION_STAGE_LABELS: Record<string, string> = {
  creche: 'Creche',
  earlyChildhood: 'Educação Infantil',
  elementary: 'Ensino Fundamental',
  finalYears: 'Anos Finais',
  highSchool: 'Ensino Médio',
  initialYears: 'Anos Iniciais',
  preSchool: 'Pré-escola',
  professional: 'Educação Profissional',
  youthAndAdult: 'Educação de Jovens e Adultos',
}

function formatStageLabel(value: string) {
  return SPECIAL_EDUCATION_STAGE_LABELS[value] ?? value
    .replace(/_/g, ' ')
    .replace(/\b\p{L}/gu, (letter: string) => letter.toLocaleUpperCase('pt-BR'))
}
