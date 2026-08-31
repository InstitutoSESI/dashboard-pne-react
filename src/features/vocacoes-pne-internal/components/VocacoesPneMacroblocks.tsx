import { useState } from 'react'
import {
  evidenceForEntity,
  findDistribution,
  findFact,
  findSeries,
  formatUiValue,
  latestObservedPoint,
  REGION_ENTITY_ID,
  unitLabel,
} from '../vocacoesPneSelectors'
import type {
  UiV2Fact,
  UiV2Macroblock,
  UiV2Series,
  UiV2Source,
  UiV2VisualContract,
  VocacoesPneCoreBundle,
} from '../vocacoesPneUiV2Types'
import { MacroblockFrame, TabList } from './MacroblockFrame'
import {
  AvailabilityValue,
  DistributionPlot,
  EndpointCard,
  EvidenceDisclosure,
  SeriesComparisonChart,
  UnavailablePanel,
  VisualMeta,
} from './VocacoesPneVisuals'

export interface MacroblockProps {
  core: VocacoesPneCoreBundle
  series: UiV2Series[]
  municipalityEntityId: string | null
  municipalityName: string | null
  municipalityNames: Map<string, string>
  sourceRegistry: Map<string, UiV2Source>
  macroblock: UiV2Macroblock
  visualContract: UiV2VisualContract
}

function commonFrameProps(props: MacroblockProps) {
  return {
    macroblock: props.macroblock,
    visualContract: props.visualContract,
    sourceRegistry: props.sourceRegistry,
    limits: props.core.limitRegistry,
  }
}

function selectedLabel(props: MacroblockProps) {
  return props.municipalityName ?? 'Visão regional'
}

function seriesPair(
  props: MacroblockProps,
  familyId: string,
  metricId: string,
  educationalStage?: string,
  ageGroup?: string,
) {
  const region = findSeries(props.series, {
    familyId,
    entityId: REGION_ENTITY_ID,
    metricId,
    educationalStage,
    ageGroup,
  })
  const municipality = props.municipalityEntityId ? findSeries(props.series, {
    familyId,
    entityId: props.municipalityEntityId,
    metricId,
    educationalStage,
    ageGroup,
  }) : null
  return { region, municipality }
}

function FactTile({ fact, title }: { fact: UiV2Fact | null; title: string }) {
  return (
    <article className="vpi-fact-tile">
      <h4>{title}</h4>
      <AvailabilityValue
        state={fact?.availabilityState ?? 'unavailable'}
        value={fact?.displayValue ?? null}
        unit={fact?.displayUnit ?? 'count'}
        fractionDigits={fact?.unit === 'percent' ? 1 : undefined}
      />
      {fact ? (
        <p>{fact.period} · {fact.note || unitLabel(fact.unit)}</p>
      ) : <p>Não materializado para esta leitura.</p>}
    </article>
  )
}

function SnapshotTile({ series, title }: { series: UiV2Series | null; title: string }) {
  const point = latestObservedPoint(series)
  return (
    <article className="vpi-fact-tile">
      <h4>{title}</h4>
      <AvailabilityValue
        state={point?.availabilityState ?? 'unavailable'}
        value={point?.displayValue ?? null}
        unit={point?.displayUnit ?? series?.unit ?? 'count'}
        fractionDigits={series?.unit === 'percent' ? 1 : undefined}
      />
      <p>{point ? `${point.year} · ${unitLabel(series?.unit ?? point.unit)}` : 'Sem ponto disponível.'}</p>
    </article>
  )
}

export function DemographyOfferBlock(props: MacroblockProps) {
  const [stage, setStage] = useState<'pre_school_age_4_5' | 'fundamental' | 'high_school'>('pre_school_age_4_5')
  const metric = 'located_enrollments'
  const { region, municipality } = seriesPair(props, 'D1_COHORT_OFFER_CAPACITY', metric, stage)
  const schools = seriesPair(props, 'D1_COHORT_OFFER_CAPACITY', 'schools', 'all')
  const classes = seriesPair(
    props,
    'D1_COHORT_OFFER_CAPACITY',
    stage === 'pre_school_age_4_5' ? 'school_classes' : 'classes',
    stage === 'pre_school_age_4_5' ? 'early_childhood' : stage,
  )
  const pressureEntity = props.municipalityEntityId ?? REGION_ENTITY_ID
  const pressure = findFact(props.core, {
    familyId: 'D1_COHORT_OFFER_CAPACITY',
    entityId: pressureEntity,
    metricId: 'mechanical_cohort_to_2025_enrollment_ratio',
    educationalStage: stage,
  })
  const population = seriesPair(props, 'D1_COHORT_OFFER_CAPACITY', 'resident_population', stage)
  const crecheUnavailable = findFact(props.core, {
    familyId: 'D1_COHORT_OFFER_CAPACITY',
    entityId: pressureEntity,
    metricId: 'creche_located_enrollments',
    educationalStage: 'creche_age_0_3',
  })

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver coortes, turmas e disponibilidade da creche" testId="evidence-demography">
          <div className="vpi-evidence-grid">
            <EndpointCard label="População residente da coorte — Vale" series={population.region} compact />
            {props.municipalityEntityId ? <EndpointCard label={`População residente — ${selectedLabel(props)}`} series={population.municipality} compact /> : null}
            <EndpointCard label="Turmas — Vale" series={classes.region} compact />
            {props.municipalityEntityId ? <EndpointCard label={`Turmas — ${selectedLabel(props)}`} series={classes.municipality} compact /> : null}
            <FactTile fact={crecheUnavailable} title="Creche 0–3 isolada" />
          </div>
          <p className="vpi-method-note">A fonte congelada mantém a população 0–3 e a oferta total da educação infantil, mas não materializou matrículas localizadas de creche separadamente. O estado indisponível é preservado.</p>
        </EvidenceDisclosure>
      )}
    >
      <TabList
        label="Etapa educacional"
        value={stage}
        onChange={setStage}
        options={[
          { value: 'pre_school_age_4_5', label: 'Pré-escola' },
          { value: 'fundamental', label: 'Fundamental' },
          { value: 'high_school', label: 'Ensino médio' },
        ]}
      />
      <div role="tabpanel" className="vpi-primary-grid">
        <div className="vpi-primary-grid__visual">
          <h3>Oferta observada por etapa</h3>
          <SeriesComparisonChart
            title={`Matrículas localizadas — ${stage}`}
            description="Série observada de matrículas localizadas, sem converter população residente em cobertura."
            region={{ label: 'Vale do Sinos', series: region, role: 'region' }}
            municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: municipality, role: 'municipality' } : null}
          />
          <VisualMeta
            contract={props.visualContract}
            sourceLabels={new Map([...props.sourceRegistry].map(([key, value]) => [key, value.label]))}
            sourceRefs={region?.points[0]?.sourceRef ? [region.points[0].sourceRef] : props.visualContract.sourceRefs}
            period={region?.period ?? '2014–2025'}
            unit={region?.unit ?? 'enrollments'}
            lens={region?.territorialLens ?? 'school_location'}
          />
        </div>
        <aside className="vpi-primary-grid__aside">
          <EndpointCard label={props.municipalityEntityId ? `Escolas — ${selectedLabel(props)}` : 'Escolas — Vale'} series={props.municipalityEntityId ? schools.municipality : schools.region} />
          <FactTile fact={pressure} title="Pressão mecânica" />
          <p className="vpi-caution-note">Marcador mecânico separado: não é previsão, demanda, cobertura ou capacidade.</p>
        </aside>
      </div>
    </MacroblockFrame>
  )
}

export function TrajectoryConditionsBlock(props: MacroblockProps) {
  const [metric, setMetric] = useState<'approval_rate_percent' | 'failure_rate_percent' | 'dropout_rate_percent' | 'age_grade_distortion_rate_percent'>('approval_rate_percent')
  const municipalitySeries = props.municipalityEntityId ? findSeries(props.series, {
    familyId: 'D1_TRAJECTORY_CONDITIONS',
    entityId: props.municipalityEntityId,
    metricId: metric,
    educationalStage: 'high_school',
  }) : null
  const distribution = findDistribution(props.core, metric, 'high_school', 2025)
  const conditionMetrics = [
    ['percentual_tempo_integral', 'Matrículas em tempo integral'],
    ['teacher_adequacy_percent', 'Adequação docente'],
    ['schools_with_internet_percent', 'Escolas com internet'],
    ['schools_with_broadband_percent', 'Escolas com banda larga'],
  ] as const

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver condições escolares em detalhe" testId="evidence-conditions">
          <div className="vpi-evidence-grid">
            {conditionMetrics.map(([metricId, label]) => (
              <EndpointCard
                key={metricId}
                label={label}
                compact
                series={props.municipalityEntityId ? findSeries(props.series, {
                  familyId: 'D1_TRAJECTORY_CONDITIONS',
                  entityId: props.municipalityEntityId,
                  metricId,
                  educationalStage: metricId.startsWith('schools_') ? 'all' : 'high_school',
                }) : null}
              />
            ))}
          </div>
          <p className="vpi-method-note">Condições são contexto para acompanhamento. Nenhuma mudança de trajetória é atribuída a elas.</p>
        </EvidenceDisclosure>
      )}
    >
      <TabList
        label="Indicador de trajetória"
        value={metric}
        onChange={setMetric}
        options={[
          { value: 'approval_rate_percent', label: 'Aprovação' },
          { value: 'failure_rate_percent', label: 'Reprovação' },
          { value: 'dropout_rate_percent', label: 'Abandono' },
          { value: 'age_grade_distortion_rate_percent', label: 'Distorção' },
        ]}
      />
      <div role="tabpanel" className="vpi-split-visuals">
        <div>
          <h3>{props.municipalityEntityId ? `Série municipal — ${selectedLabel(props)}` : 'Selecione um município para ver a série'}</h3>
          {props.municipalityEntityId ? (
            <SeriesComparisonChart
              title={`${metric} — ${selectedLabel(props)}`}
              description="Taxa oficial municipal; 2020 e 2021 têm cautela explícita de continuidade."
              region={{ label: 'Vale — mostrado apenas como distribuição', series: null, role: 'region' }}
              municipality={{ label: selectedLabel(props), series: municipalitySeries, role: 'municipality' }}
            />
          ) : <UnavailablePanel title="Série municipal" state="not_applicable" note="A visão regional não cria uma taxa agregada." />}
        </div>
        <div>
          <h3>Distribuição de 2025</h3>
          <DistributionPlot
            distribution={distribution}
            municipalityNames={props.municipalityNames}
            selectedMunicipalityId={props.municipalityEntityId}
          />
        </div>
      </div>
      <p className="vpi-caution-note">2020–2021: cautela de continuidade. O Vale é uma distribuição municipal; a linha regional não é calculada.</p>
    </MacroblockFrame>
  )
}

export function MobilityHighSchoolBlock(props: MacroblockProps) {
  const entity = props.municipalityEntityId ?? REGION_ENTITY_ID
  const snapshots = (['total', 'fundamental', 'high_school'] as const).map((stage) => findSeries(props.series, {
    familyId: 'D1_MOBILITY_HIGH_SCHOOL_OFFER',
    entityId: entity,
    metricId: 'residents_studying_other_municipality_share',
    educationalStage: stage,
  }))
  const offer = seriesPair(props, 'D1_COHORT_OFFER_CAPACITY', 'located_enrollments', 'high_school')
  const classes = seriesPair(props, 'D1_COHORT_OFFER_CAPACITY', 'classes', 'high_school')

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver oferta localizada, turmas e comparação municipal">
          <div className="vpi-evidence-grid">
            <EndpointCard label="Matrículas de ensino médio — Vale" series={offer.region} compact />
            {props.municipalityEntityId ? <EndpointCard label={`Matrículas — ${selectedLabel(props)}`} series={offer.municipality} compact /> : null}
            <EndpointCard label="Turmas de ensino médio — Vale" series={classes.region} compact />
            {props.municipalityEntityId ? <EndpointCard label={`Turmas — ${selectedLabel(props)}`} series={classes.municipality} compact /> : null}
          </div>
          <p className="vpi-method-note">A fonte informa apenas se a pessoa estudava em outro município. Destino, deslocamento entre pares e trajeto não estão disponíveis.</p>
        </EvidenceDisclosure>
      )}
    >
      <div className="vpi-primary-grid">
        <div className="vpi-primary-grid__visual">
          <h3>Fotografia de 2022</h3>
          <div className="vpi-fact-grid vpi-fact-grid--three">
            <SnapshotTile series={snapshots[0]} title="Total" />
            <SnapshotTile series={snapshots[1]} title="Fundamental" />
            <SnapshotTile series={snapshots[2]} title="Ensino médio" />
          </div>
          <p className="vpi-method-note">Percentual de residentes que estudavam em outro município; país estrangeiro permanece componente separado na fonte.</p>
        </div>
        <aside className="vpi-primary-grid__aside">
          <EndpointCard label={props.municipalityEntityId ? `Oferta de ensino médio — ${selectedLabel(props)}` : 'Oferta de ensino médio — Vale'} series={props.municipalityEntityId ? offer.municipality : offer.region} />
        </aside>
      </div>
    </MacroblockFrame>
  )
}

export function RuralityTransportBlock(props: MacroblockProps) {
  const rural = seriesPair(props, 'D1_RURALITY_PNATE_PLANNING', 'rural_enrollments', 'high_school')
  const pnateEntity = props.municipalityEntityId ?? REGION_ENTITY_ID
  const forecast = findSeries(props.series, {
    familyId: 'D1_RURALITY_PNATE_PLANNING',
    entityId: pnateEntity,
    metricId: 'pnate_adjusted_forecast',
  })
  const execution = findSeries(props.series, {
    familyId: 'D1_RURALITY_PNATE_PLANNING',
    entityId: pnateEntity,
    metricId: 'pnate_executed_amount',
  })
  const beneficiaries = findSeries(props.series, {
    familyId: 'D1_RURALITY_PNATE_PLANNING',
    entityId: pnateEntity,
    metricId: 'pnate_beneficiary_students',
  })

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver escolas, turmas rurais e estágios do PNATE">
          <div className="vpi-evidence-grid">
            <EndpointCard label="Escolas rurais" series={(props.municipalityEntityId ? seriesPair(props, 'D1_RURALITY_PNATE_PLANNING', 'rural_schools', 'all').municipality : seriesPair(props, 'D1_RURALITY_PNATE_PLANNING', 'rural_schools', 'all').region)} compact />
            <EndpointCard label="Turmas rurais" series={(props.municipalityEntityId ? seriesPair(props, 'D1_RURALITY_PNATE_PLANNING', 'rural_classes', 'all').municipality : seriesPair(props, 'D1_RURALITY_PNATE_PLANNING', 'rural_classes', 'all').region)} compact />
            <EndpointCard label="Beneficiários informados para o cálculo" series={beneficiaries} compact />
            <EndpointCard label="Execução informada — 2026 indisponível" series={execution} compact />
          </div>
          <p className="vpi-method-note">Beneficiários administrativos não são tratados como usuários observados do transporte.</p>
        </EvidenceDisclosure>
      )}
    >
      <div className="vpi-primary-grid">
        <div className="vpi-primary-grid__visual">
          <h3>Ensino médio rural</h3>
          <SeriesComparisonChart
            title="Matrículas rurais localizadas no ensino médio"
            description="Séries observadas por localização da oferta rural."
            region={{ label: 'Vale do Sinos', series: rural.region, role: 'region' }}
            municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: rural.municipality, role: 'municipality' } : null}
          />
        </div>
        <aside className="vpi-primary-grid__aside">
          {props.municipalityEntityId ? <EndpointCard label={`Oferta rural — ${selectedLabel(props)}`} series={rural.municipality} /> : null}
          <EndpointCard label="PNATE — previsão de planejamento" series={forecast} />
          <p className="vpi-caution-note">2026 é planejamento. Não representa execução, pagamento ou uso observado.</p>
        </aside>
      </div>
    </MacroblockFrame>
  )
}

export function InclusionAdultsBlock(props: MacroblockProps) {
  const [reading, setReading] = useState<'adult_eja' | 'special_aee'>('adult_eja')
  const entity = props.municipalityEntityId ?? REGION_ENTITY_ID
  const eja = findSeries(props.series, {
    familyId: 'D1_ADULT_SCHOOLING_EJA',
    entityId: entity,
    metricId: 'total_context',
    educationalStage: 'total_context',
  })
  const fundamentalIncomplete = findSeries(props.series, {
    familyId: 'D1_ADULT_SCHOOLING_EJA',
    entityId: entity,
    metricId: 'without_fundamental_completed',
  })
  const highCompleted = findSeries(props.series, {
    familyId: 'D1_ADULT_SCHOOLING_EJA',
    entityId: entity,
    metricId: 'high_school_completed_or_more',
  })
  const special = findSeries(props.series, {
    familyId: 'D1_SPECIAL_AEE_TERRITORY',
    entityId: entity,
    metricId: 'special_enrollments',
    educationalStage: 'all',
  })
  const aee = findSeries(props.series, {
    familyId: 'D1_SPECIAL_AEE_TERRITORY',
    entityId: entity,
    metricId: 'schools_offering_aee',
    educationalStage: 'all',
  })
  const integrated = findSeries(props.series, {
    familyId: 'D1_ADULT_SCHOOLING_EJA',
    entityId: entity,
    metricId: 'integrated_total',
  })

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver etapas da EJA, integração à EPT e AEE">
          <div className="vpi-evidence-grid">
            <EndpointCard label="EJA fundamental" series={findSeries(props.series, { familyId: 'D1_ADULT_SCHOOLING_EJA', entityId: entity, metricId: 'fundamental', educationalStage: 'fundamental' })} compact />
            <EndpointCard label="EJA ensino médio" series={findSeries(props.series, { familyId: 'D1_ADULT_SCHOOLING_EJA', entityId: entity, metricId: 'high_school', educationalStage: 'high_school' })} compact />
            <EndpointCard label="EJA integrada à EPT" series={integrated} compact />
            <EndpointCard label="Escolas que informam AEE" series={aee} compact />
          </div>
          <p className="vpi-method-note">Zero em EJA integrada é observação administrativa; não conclui cobertura, acesso ou necessidade de criar oferta.</p>
        </EvidenceDisclosure>
      )}
    >
      <TabList
        label="Subleitura de inclusão"
        value={reading}
        onChange={setReading}
        options={[
          { value: 'adult_eja', label: 'Escolaridade adulta e EJA' },
          { value: 'special_aee', label: 'Educação especial e AEE' },
        ]}
      />
      <div role="tabpanel">
        {reading === 'adult_eja' ? (
          <div className="vpi-primary-grid">
            <div className="vpi-primary-grid__visual">
              <h3>Escolaridade residente e EJA localizada</h3>
              <div className="vpi-fact-grid">
                <EndpointCard label="Sem fundamental concluído" series={fundamentalIncomplete} />
                <EndpointCard label="Ensino médio concluído ou mais" series={highCompleted} />
                <EndpointCard label="Matrículas EJA" series={eja} />
              </div>
            </div>
            <aside className="vpi-primary-grid__aside">
              <p className="vpi-caution-note">Público residente e matrículas localizadas têm lentes diferentes. O denominador de 2010 mantém seu limite explícito.</p>
            </aside>
          </div>
        ) : (
          <div className="vpi-primary-grid">
            <div className="vpi-primary-grid__visual">
              <h3>Educação especial e AEE</h3>
              <SeriesComparisonChart
                title="Matrículas localizadas da educação especial"
                description="Série por localização escolar, sem conclusão de cobertura ou acesso."
                region={{ label: 'Vale do Sinos', series: findSeries(props.series, { familyId: 'D1_SPECIAL_AEE_TERRITORY', entityId: REGION_ENTITY_ID, metricId: 'special_enrollments', educationalStage: 'all' }), role: 'region' }}
                municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: special, role: 'municipality' } : null}
              />
            </div>
            <aside className="vpi-primary-grid__aside"><EndpointCard label="Escolas que informam AEE" series={aee} /></aside>
          </div>
        )}
      </div>
    </MacroblockFrame>
  )
}

export function YouthWorkTrainingBlock(props: MacroblockProps) {
  const [age, setAge] = useState<'15_17' | '18_24'>('15_17')
  const familyId = age === '15_17' ? 'D2_YOUTH_WORK_15_17' : 'D2_YOUTH_WORK_18_24'
  const rais = seriesPair(props, familyId, 'total', undefined, age)
  const caged = seriesPair(props, familyId, 'caged_youth_admissions', undefined, age)
  const apprentice = seriesPair(props, 'D2_APPRENTICESHIP', 'apprentice_admissions', undefined, age)
  const ratioEntity = props.municipalityEntityId ?? REGION_ENTITY_ID
  const ratio = findFact(props.core, {
    familyId: 'D2_APPRENTICESHIP',
    entityId: ratioEntity,
    metricId: 'apprenticeship_share_of_youth_admission_events',
    ageGroup: age,
    period: '2025',
  })
  const education = props.municipalityEntityId && age === '15_17' ? findSeries(props.series, {
    familyId: 'D2_YOUTH_WORK_15_17',
    entityId: props.municipalityEntityId,
    metricId: 'education_approval_rate_percent',
    educationalStage: 'high_school',
  }) : null

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver fluxos, aprendizagem e educação em paralelo" testId="evidence-youth">
          <div className="vpi-split-visuals">
            <div>
              <h4>Fluxo Caged — admissões</h4>
              <SeriesComparisonChart
                title={`Admissões de ${age === '15_17' ? '15 a 17' : '18 a 24'} anos`}
                description="Fluxo anual de eventos ajustados, separado do estoque RAIS."
                region={{ label: 'Vale do Sinos', series: caged.region, role: 'region' }}
                municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: caged.municipality, role: 'municipality' } : null}
              />
            </div>
            <div>
              <h4>Aprendizagem profissional</h4>
              <SeriesComparisonChart
                title={`Eventos de aprendizagem — ${age === '15_17' ? '15 a 17' : '18 a 24'}`}
                description="Eventos de admissão classificados como aprendizagem profissional."
                region={{ label: 'Vale do Sinos', series: apprentice.region, role: 'region' }}
                municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: apprentice.municipality, role: 'municipality' } : null}
              />
              <FactTile fact={ratio} title="Parcela dos eventos juvenis em 2025" />
            </div>
          </div>
          {education ? <EndpointCard label="Aprovação no ensino médio — acompanhada em paralelo" series={education} compact /> : null}
          <p className="vpi-method-note">Séries educacionais e de trabalho não identificam as mesmas pessoas, não recebem teste associativo e não formam escore combinado.</p>
        </EvidenceDisclosure>
      )}
    >
      <TabList
        label="Faixa etária"
        value={age}
        onChange={setAge}
        options={[
          { value: '15_17', label: '15–17 anos' },
          { value: '18_24', label: '18–24 anos' },
        ]}
      />
      <div role="tabpanel" className="vpi-primary-grid">
        <div className="vpi-primary-grid__visual">
          <h3>Vínculos formais ativos — estoque RAIS</h3>
          <SeriesComparisonChart
            title={`Vínculos formais ativos — ${age === '15_17' ? '15 a 17' : '18 a 24'} anos`}
            description="Estoque anual de vínculos por local de trabalho."
            region={{ label: 'Vale do Sinos', series: rais.region, role: 'region' }}
            municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: rais.municipality, role: 'municipality' } : null}
          />
        </div>
        <aside className="vpi-primary-grid__aside">
          <FactTile fact={ratio} title="Aprendizagem em 2025" />
          <p className="vpi-caution-note">Estoque RAIS e fluxo Caged não são fundidos. Eventos não equivalem a pessoas únicas.</p>
        </aside>
      </div>
    </MacroblockFrame>
  )
}

function EvidenceList({
  title,
  items,
}: {
  title: string
  items: ReturnType<typeof evidenceForEntity>
}) {
  return (
    <section className="vpi-change-list">
      <h4>{title}</h4>
      {items.length === 0 ? <p>Nenhuma mudança material elegível nesta direção.</p> : (
        <ul>
          {items.map((item) => (
            <li key={item.evidenceId}>
              <span><b>{item.label}</b><small>{item.initialYear}–{item.finalYear} · {item.kind === 'occupation' ? 'ocupação' : 'setor'}</small></span>
              <span><b>{formatUiValue(item.initialValue, item.unit)} → {formatUiValue(item.finalValue, item.unit)}</b><small>Δ {formatUiValue(item.absoluteChange, item.unit)}</small></span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function EconomyEptCoordinationBlock(props: MacroblockProps) {
  const entity = props.municipalityEntityId ?? REGION_ENTITY_ID
  const evidence = evidenceForEntity(props.core, entity)
  const positive = evidence.filter((item) => (item.absoluteChange ?? 0) > 0)
  const negative = evidence.filter((item) => (item.absoluteChange ?? 0) < 0)
  const ept = seriesPair(props, 'D2_EPT_TERRITORIAL_OFFER', 'technical_enrollments')
  const share = props.municipalityEntityId ? findFact(props.core, {
    familyId: 'D2_EPT_TERRITORIAL_OFFER',
    entityId: props.municipalityEntityId,
    metricId: 'share_of_regional_technical_enrollments',
    period: '2025',
  }) : null
  const bridge = props.core.bridgeSummaries.find((item) => item.entityId === entity) ?? null

  return (
    <MacroblockFrame
      {...commonFrameProps(props)}
      evidence={(
        <EvidenceDisclosure title="Ver mudanças materiais e cobertura completa da ponte" testId="evidence-economy">
          <div className="vpi-split-visuals">
            <EvidenceList title="Mudanças positivas materiais" items={positive} />
            <EvidenceList title="Mudanças negativas materiais" items={negative} />
          </div>
          <p className="vpi-method-note">A lista expandida preserva valores inicial e final, variação, volume, período, fonte e lente. A seleção não é prioridade ou ranking e não usa código como desempate.</p>
        </EvidenceDisclosure>
      )}
    >
      <div className="vpi-economy-layout">
        <div className="vpi-economy-layout__changes">
          <h3>Ocupações e setores em transformação</h3>
          <div className="vpi-split-visuals">
            <EvidenceList title="Ganhos materiais — síntese" items={positive.slice(0, 4)} />
            <EvidenceList title="Perdas materiais — síntese" items={negative.slice(0, 4)} />
          </div>
        </div>
        <div className="vpi-economy-layout__ept">
          <h3>Oferta territorial da EPT</h3>
          <SeriesComparisonChart
            title="Matrículas EPT localizadas"
            description="Série observada de 2023 a 2025 por localização escolar."
            region={{ label: 'Vale do Sinos', series: ept.region, role: 'region' }}
            municipality={props.municipalityEntityId ? { label: selectedLabel(props), series: ept.municipality, role: 'municipality' } : null}
          />
          {share ? <FactTile fact={share} title="Participação municipal em 2025" /> : null}
        </div>
        <div className="vpi-economy-layout__bridge">
          <h3>Correspondências disponíveis e áreas não cobertas pela ponte</h3>
          {!bridge || bridge.availabilityState === 'unavailable' ? (
            <UnavailablePanel
              title="Ponte local"
              state="unavailable"
              note={bridge?.note ?? 'A fonte congelada não materializou a ponte para esta seleção.'}
            />
          ) : (
            <div className="vpi-fact-grid vpi-fact-grid--five">
              <article><span>Cursos observados</span><b>{bridge.observedCourses}</b></article>
              <article><span>Mapeados</span><b>{bridge.mappedCourses}</b></article>
              <article><span>Não mapeados</span><b>{bridge.unmappedCourses}</b></article>
              <article><span>Matrículas mapeadas</span><b>{formatUiValue(bridge.mappedEnrollments, 'enrollments')}</b></article>
              <article><span>Não mapeadas</span><b>{formatUiValue(bridge.unmappedEnrollments, 'enrollments')}</b></article>
            </div>
          )}
          <p className="vpi-method-note">Matrículas são deduplicadas por escola e curso. Linhas da ponte não são aditivas e não demonstram inserção profissional.</p>
        </div>
      </div>
    </MacroblockFrame>
  )
}
