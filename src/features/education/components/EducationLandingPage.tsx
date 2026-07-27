import { buildAppHash } from '../../../app/appHash'
import { EDUCATION_SECTION_KEYS } from '../../../data/educationIndicatorCatalog.js'

interface EducationLandingPageProps {
  municipalitySlug?: string | null
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

const ORGANIZATION = [
  ['Atendimento e oferta', 'Mostra quem está sendo atendido, em quais etapas, redes e localidades.'],
  ['Trajetória e aprendizagem', 'Acompanha permanência, rendimento e resultados educacionais.'],
  ['Profissionais e condições da rede', 'Reúne docentes, turmas, infraestrutura e recursos de oferta.'],
  ['Modalidades, inclusão e territórios', 'Expõe recortes específicos sem confundir localização, público e modalidade.'],
] as const

const CONCEPTS = [
  ['Matrícula', 'Vínculo de um estudante a uma etapa, modalidade ou curso. Uma pessoa pode ter mais de uma matrícula.'],
  ['Atendimento da população', 'Relação entre matrículas compatíveis com uma faixa etária e a população estimada dessa faixa.'],
  ['Dependência administrativa', 'Esfera responsável pela escola: municipal, estadual, federal ou privada.'],
  ['Localização da escola', 'Classificação territorial da unidade escolar, como urbana ou rural; não identifica por si só uma população específica.'],
  ['Variação percentual', 'Mudança relativa entre dois valores, calculada em relação ao valor inicial.'],
  ['Pontos percentuais', 'Diferença direta entre duas taxas percentuais; não é o mesmo que variação percentual.'],
] as const

function educationHref(section: string, municipalitySlug?: string | null) {
  return buildAppHash('educacao', {
    municipio: municipalitySlug || undefined,
    secao: section,
  })
}

export function EducationLandingPage({ municipalitySlug }: EducationLandingPageProps) {
  return (
    <main className="education-landing-page">
      <section className="page-card education-landing-hero">
        <div>
          <span className="eyebrow">INDICADORES EDUCACIONAIS</span>
          <h1>Conheça a educação do município</h1>
          <p>Consulte informações sobre matrículas, atendimento, trajetória escolar, profissionais, infraestrutura, modalidades, inclusão e demanda educacional.</p>
        </div>
      </section>

      <section className="page-card education-landing-feature" aria-labelledby="education-panorama-entry-title">
        <div>
          <span className="eyebrow">ENTRADA RECOMENDADA</span>
          <h2 id="education-panorama-entry-title">Panorama educacional</h2>
          <p>Síntese das matrículas, da oferta educacional, do rendimento escolar e das mudanças observadas no município.</p>
        </div>
        <a className="platform-navigation-button" href={educationHref(EDUCATION_SECTION_KEYS.panorama, municipalitySlug)}>
          Abrir Panorama educacional
        </a>
      </section>

      <section className="education-landing-paths" aria-labelledby="education-paths-title">
        <header>
          <span className="eyebrow">CAMINHOS PARA APROFUNDAR</span>
          <h2 id="education-paths-title">Explore os indicadores por tema</h2>
        </header>
        <div className="education-landing-paths__grid">
          {DEEP_DIVE_PATHS.map((path) => (
            <article className="page-card education-landing-path" key={path.key}>
              <h3>{path.title}</h3>
              <p>{path.description}</p>
              <a href={educationHref(path.key, municipalitySlug)}>Abrir página <span aria-hidden="true">→</span></a>
            </article>
          ))}
        </div>
      </section>

      <section className="page-card education-landing-organization" aria-labelledby="education-organization-title">
        <header>
          <span className="eyebrow">LEITURA ORIENTADA</span>
          <h2 id="education-organization-title">Como os indicadores se organizam</h2>
          <p>Os temas se complementam para formar um retrato da rede sem misturar universos, períodos ou recortes diferentes.</p>
        </header>
        <dl>
          {ORGANIZATION.map(([term, description]) => (
            <div key={term}><dt>{term}</dt><dd>{description}</dd></div>
          ))}
        </dl>
      </section>

      <section className="page-card education-landing-concepts" aria-labelledby="education-concepts-title">
        <header>
          <span className="eyebrow">CONCEITOS ESSENCIAIS</span>
          <h2 id="education-concepts-title">Termos para interpretar os dados</h2>
        </header>
        <dl>
          {CONCEPTS.map(([term, description]) => (
            <div key={term}><dt>{term}</dt><dd>{description}</dd></div>
          ))}
        </dl>
      </section>

      <aside className="education-landing-sources" aria-labelledby="education-landing-sources-title">
        <h2 id="education-landing-sources-title">Fontes e metodologia</h2>
        <p>Os indicadores utilizam principalmente Censo Escolar, Sinopse Estatística, taxas de rendimento, SAEB e IDEB do INEP, além de estimativas populacionais do IBGE. Períodos, universos e limitações aparecem junto de cada indicador.</p>
        <a href={educationHref(EDUCATION_SECTION_KEYS.methodology, municipalitySlug)}>Consultar metodologia e fontes</a>
      </aside>
    </main>
  )
}
