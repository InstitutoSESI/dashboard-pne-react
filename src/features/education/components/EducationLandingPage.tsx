import { ArrowRight } from 'lucide-react'
import { buildAppHash } from '../../../app/appHash'
import { EDUCATION_SECTION_KEYS } from '../../../data/educationIndicatorCatalog.js'
import {
  formatOverviewEnrollments,
  getOverviewNumericValue,
} from '../municipalEducationOverviewPresentation'
import type { MunicipalEducationOverviewState } from '../hooks/useMunicipalEducationOverview'
import type {
  MunicipalEducationOverviewV1,
  SnapshotValue,
} from '../municipalEducationOverviewTypes'

interface EducationLandingPageProps {
  municipalitySlug?: string | null
  overview?: MunicipalEducationOverviewState
}

const DEEP_DIVE_PATHS = [
  {
    key: EDUCATION_SECTION_KEYS.attendance,
    title: 'Atendimento e oferta',
    description: 'Matrículas, escolas, etapas de ensino, redes responsáveis e alcance do atendimento educacional.',
  },
  {
    key: EDUCATION_SECTION_KEYS.trajectory,
    title: 'Trajetória escolar e aprendizagem',
    description: 'Fluxo, rendimento, distorção idade-série, IDEB, SAEB e alfabetização.',
  },
  {
    key: EDUCATION_SECTION_KEYS.professionals,
    title: 'Profissionais da educação',
    description: 'Docentes, organização das turmas e condições de trabalho observadas nas bases disponíveis.',
  },
  {
    key: EDUCATION_SECTION_KEYS.infrastructure,
    title: 'Infraestrutura e condições de oferta',
    description: 'Espaços, acessibilidade, conectividade, equipamentos e recursos das escolas.',
  },
  {
    key: EDUCATION_SECTION_KEYS.modalities,
    title: 'Modalidades, inclusão e territórios',
    description: 'EJA, educação profissional, educação especial e recortes territoriais disponíveis.',
  },
  {
    key: EDUCATION_SECTION_KEYS.higherEducation,
    title: 'Educação Superior',
    description: 'Matrículas, instituições, polos, acesso, fluxo e docentes da graduação no município.',
  },
  {
    key: EDUCATION_SECTION_KEYS.demand,
    title: 'Cenários de atendimento escolar',
    description: 'Evolução observada, cobertura e trajetórias futuras para apoiar o planejamento da rede.',
  },
] as const

const CONCEPTS = [
  ['Matrícula', 'Vínculo de um estudante a uma etapa, modalidade ou curso. Uma pessoa pode ter mais de uma matrícula.'],
  ['Atendimento da população', 'Relação entre matrículas compatíveis com uma faixa etária e a população estimada dessa faixa.'],
  ['Dependência administrativa', 'Esfera responsável pela escola: municipal, estadual, federal ou privada.'],
  ['Localização da escola', 'Classificação territorial da unidade escolar, como urbana ou rural; não identifica por si só uma população específica.'],
  ['Variação percentual', 'Mudança relativa entre dois valores, calculada em relação ao valor inicial.'],
  ['Pontos percentuais', 'Diferença direta entre duas taxas percentuais; não é o mesmo que variação percentual.'],
] as const

const shareFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
})

function educationHref(section: string, municipalitySlug?: string | null) {
  return buildAppHash('educacao', {
    municipio: municipalitySlug || undefined,
    secao: section,
  })
}

function shareOfTotal(value: SnapshotValue, total: SnapshotValue): string | null {
  const amount = getOverviewNumericValue(value)
  const base = getOverviewNumericValue(total)
  if (amount === null || base === null || base <= 0) return null
  return `${shareFormatter.format((amount / base) * 100)}% da Educação Básica`
}

export function EducationLandingPage({ municipalitySlug, overview }: EducationLandingPageProps) {
  return (
    <main className="education-landing-page">
      <section className="education-landing-summary" aria-labelledby="education-landing-title">
        <div className="education-landing-summary__intro">
          <h1 id="education-landing-title">Panorama da educação do município</h1>
          <p>Matrículas, oferta, trajetória escolar e financiamento em uma base única. Comece pela síntese e aprofunde por tema.</p>
          <a className="platform-navigation-button" href={educationHref(EDUCATION_SECTION_KEYS.panorama, municipalitySlug)}>
            Abrir Panorama educacional completo
          </a>
        </div>
        <EducationMunicipalKeyFigures overview={overview} />
      </section>

      <section className="education-landing-paths" aria-labelledby="education-paths-title">
        <header>
          <h2 id="education-paths-title">Aprofunde por tema</h2>
          <p>Cada frente reúne os indicadores de um recorte da rede, com período e fonte declarados no próprio dado.</p>
        </header>
        <div className="education-landing-paths__grid">
          {DEEP_DIVE_PATHS.map((path) => (
            <article className="page-card education-landing-path" key={path.key}>
              <h3>{path.title}</h3>
              <p>{path.description}</p>
              <a href={educationHref(path.key, municipalitySlug)}>Abrir página <ArrowRight aria-hidden="true" size={16} /></a>
            </article>
          ))}
        </div>
      </section>

      <details className="page-card education-landing-concepts">
        <summary>
          <strong>Termos para interpretar os dados</strong>
          <span>Seis conceitos que evitam leituras equivocadas dos indicadores.</span>
        </summary>
        <dl>
          {CONCEPTS.map(([term, description]) => (
            <div key={term}><dt>{term}</dt><dd>{description}</dd></div>
          ))}
        </dl>
      </details>

      <aside className="education-landing-sources" aria-labelledby="education-landing-sources-title">
        <h2 id="education-landing-sources-title">Fontes e metodologia</h2>
        <p>Os indicadores utilizam principalmente Censo Escolar, Sinopse Estatística, taxas de rendimento, SAEB e IDEB do INEP, além de estimativas populacionais do IBGE. Períodos, universos e limitações aparecem junto de cada indicador.</p>
        <a href={educationHref(EDUCATION_SECTION_KEYS.methodology, municipalitySlug)}>Consultar metodologia e fontes</a>
      </aside>
    </main>
  )
}

function EducationMunicipalKeyFigures({ overview }: { overview?: EducationLandingPageProps['overview'] }) {
  if (!overview || overview.status === 'idle' || overview.status === 'loading') {
    return (
      <div className="education-landing-figures education-landing-figures--loading" aria-hidden="true">
        <span /><span /><span /><span />
      </div>
    )
  }

  if (overview.status !== 'ready' || !overview.data) {
    return (
      <p className="education-landing-figures education-landing-figures--hint">
        A síntese das matrículas aparece aqui assim que os dados do município estiverem disponíveis.
      </p>
    )
  }

  return <EducationMunicipalKeyFiguresReady data={overview.data} />
}

function EducationMunicipalKeyFiguresReady({ data }: { data: MunicipalEducationOverviewV1 }) {
  const { components } = data.basicEducationComposition
  const total = data.basicEducationComposition.total
  const stages = [
    { key: 'infantil', label: 'Educação Infantil', value: components.earlyChildhood.total },
    { key: 'fundamental', label: 'Ensino Fundamental', value: components.elementary.total },
    { key: 'medio', label: 'Ensino Médio', value: components.highSchool.total },
  ] as const

  return (
    <div className="education-landing-figures" aria-label={`Síntese das matrículas em ${data.reference.year}`}>
      <dl className="education-landing-figures__grid">
        <div className="education-landing-figure education-landing-figure--primary">
          <dt>Matrículas na Educação Básica</dt>
          <dd>{formatOverviewEnrollments(data.basicEducation.total)}</dd>
          <span className="education-landing-figure__meta">Censo Escolar {data.reference.year}</span>
        </div>
        {stages.map((stage) => {
          const share = shareOfTotal(stage.value, total)
          return (
            <div className="education-landing-figure" key={stage.key}>
              <dt>{stage.label}</dt>
              <dd>{formatOverviewEnrollments(stage.value)}</dd>
              {share ? <span className="education-landing-figure__meta">{share}</span> : null}
            </div>
          )
        })}
      </dl>
    </div>
  )
}
