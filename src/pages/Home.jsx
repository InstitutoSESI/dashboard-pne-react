import { NavigationEntryCard } from '../components/NavigationEntryCard'
import { StatCard } from '../components/StatCard'

const ENTRY_CARDS = [
  {
    action: 'Abrir PNE',
    detail: 'Acompanhe as metas legais, os resultados do ciclo 2014–2024 e o ciclo 2026–2036.',
    icon: TargetIcon,
    key: 'pne2026',
    title: 'Plano Nacional de Educação',
  },
  {
    action: 'Abrir indicadores',
    detail: 'Explore atendimento, trajetória, aprendizagem, profissionais, infraestrutura, modalidades, territórios e projeções.',
    icon: EducationIcon,
    key: 'educacao',
    title: 'Indicadores educacionais',
  },
  {
    action: 'Abrir financiamento',
    detail: 'Analise SIOPE, FUNDEB, VAAR, PNATE, execução e aplicação dos recursos.',
    icon: FinanceIcon,
    key: 'financeiros',
    title: 'Financiamento da educação',
  },
  {
    action: 'Abrir relatório',
    detail: 'Reúne, em um único documento, as principais evidências educacionais e financeiras do município para leitura, impressão e planejamento.',
    icon: ReportIcon,
    key: 'relatorio-tecnico-municipal',
    title: 'Relatório Técnico Municipal',
  },
]

const NAVIGATION_STEPS = [
  {
    detail: 'Escolha o território na barra superior. A seleção será mantida durante a navegação.',
    number: '01',
    title: 'Selecione o município',
  },
  {
    detail: 'Acesse o PNE, os indicadores educacionais, o financiamento ou o Relatório Técnico Municipal.',
    number: '02',
    title: 'Escolha uma frente de análise',
  },
  {
    detail: 'Utilize filtros, históricos, comparações, capítulos e painéis de detalhamento para aprofundar a leitura.',
    number: '03',
    title: 'Explore os detalhes',
  },
  {
    detail: 'Verifique períodos, conceitos, fontes oficiais e cuidados de interpretação apresentados em cada módulo.',
    number: '04',
    title: 'Consulte fontes e metodologia',
  },
]

const CONTEXT_BULLETS = [
  'Leitura territorial do município.',
  'Papel da rede municipal na educação básica.',
  'Apoio à gestão com base em evidências.',
  'Organização do acompanhamento educacional.',
]

const HOME_GUIDANCE_STEPS = [
  {
    detail: 'Use o seletor da barra superior para definir o território.',
    number: '01',
    title: 'Selecione o município',
  },
  {
    detail: 'Acesse o PNE, os indicadores, o financiamento ou o Relatório Técnico Municipal.',
    number: '02',
    title: 'Escolha uma frente de análise',
  },
  {
    detail: 'Use filtros e painéis para aprofundar a leitura.',
    number: '03',
    title: 'Explore os dados',
  },
  {
    detail: 'Verifique períodos, conceitos e fontes oficiais.',
    number: '04',
    title: 'Consulte fontes e metodologia',
  },
]

const ORIENTATION_CARDS = [
  {
    detail: 'Metas, indicadores e financiamento aparecem em uma leitura comum do território selecionado.',
    title: 'Visão municipal integrada',
  },
  {
    detail: 'Períodos, fontes oficiais e limites de interpretação acompanham os dados apresentados.',
    title: 'Evidências oficiais',
  },
  {
    detail: 'A organização por domínios ajuda a acompanhar prioridades e sustentar decisões da gestão.',
    title: 'Planejamento e decisão',
  },
]

export function Home({ onNavigate, selectedMunicipio }) {
  const municipioLabel = selectedMunicipio || 'Nenhum município selecionado'

  return (
    <div className="page-stack home-page home-page--foundation">
      <section className="home-hero home-hero--institutional">
        <div className="home-hero__content">
          <p className="home-hero__identity">Painel SESI-RS de Inteligência Analítica Municipal</p>
          <h1>Informação para compreender, acompanhar e planejar a educação municipal</h1>
          <p className="home-hero__description">
            Uma leitura municipal integrada de metas do PNE, indicadores educacionais, financiamento
            e relatório técnico, organizada a partir de fontes oficiais.
          </p>
        </div>

        <aside className="home-context-card" aria-label="Contexto municipal">
          <span className="home-context-card__label">Contexto municipal</span>
          <strong>{municipioLabel}</strong>
          <ul className="home-context-card__list">
            {CONTEXT_BULLETS.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        </aside>

        <aside className="home-guidance-card" aria-label="Como usar o painel">
          <span className="home-context-card__label">Como usar o painel</span>
          <ol className="home-guidance-list">
            {HOME_GUIDANCE_STEPS.map((step) => (
              <li className="home-guidance-step" key={step.number}>
                <span className="home-guidance-step__number" aria-hidden="true">{step.number}</span>
                <div>
                  <strong>{step.title}</strong>
                  <p>{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </aside>
      </section>

      <section className="home-entry-section" aria-labelledby="home-entry-title">
        <div className="home-section__heading">
          <span className="home-section__label">Acessos principais</span>
          <h2 id="home-entry-title">Escolha uma frente de análise</h2>
        </div>

        <div className="home-entry-grid">
          {ENTRY_CARDS.map((card) => {
            const Icon = card.icon
            return (
              <NavigationEntryCard
                aria-label={`Abrir ${card.title}`}
                bodyText={card.detail}
                footerText={card.action}
                icon={Icon}
                key={card.key}
                onClick={() => onNavigate?.(card.key)}
                title={card.title}
              />
            )
          })}
        </div>
      </section>

      <section className="home-section home-navigation-section" aria-labelledby="home-navigation-title">
        <div className="home-section__heading">
          <span className="home-section__label">Como navegar</span>
          <h2 id="home-navigation-title">Encontre a informação em poucos passos</h2>
          <p className="home-section__intro">
            O painel organiza a leitura municipal por território, domínio temático e nível de detalhamento.
          </p>
        </div>

        <div className="home-navigation-grid">
          {NAVIGATION_STEPS.map((step) => (
            <article className="home-navigation-step" key={step.number}>
              <span className="home-navigation-step__number">{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-section home-section--foundation" aria-labelledby="home-reading-title">
        <div className="home-section__heading">
          <span className="home-section__label">Como usar o painel</span>
          <h2 id="home-reading-title">Uma base comum para leitura e planejamento</h2>
        </div>
        <div className="foundation-stat-grid">
          {ORIENTATION_CARDS.map((card) => (
            <StatCard detail={card.detail} key={card.title} title={card.title} />
          ))}
        </div>
      </section>

      <section className="home-about-panel" aria-labelledby="home-about-title">
        <div className="home-about-panel__heading">
          <span className="home-section__label">Sobre o painel</span>
          <h2 id="home-about-title">Sobre o painel</h2>
        </div>
        <div className="home-about-panel__copy">
          <p>
            O Painel SESI-RS de Inteligência Analítica Municipal organiza dados públicos para apoiar gestores
            na leitura de metas, condições educacionais e financiamento.
          </p>
          <p>
            As informações são apresentadas conforme a disponibilidade e o período de atualização de cada fonte oficial.
          </p>
        </div>
      </section>
    </div>
  )
}

function TargetIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1" />
      <path d="m15.2 8.8 4.8-4.8M16 4h4v4" />
    </svg>
  )
}

function EducationIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m2.5 9.4 9.5-4.8 9.5 4.8-9.5 4.8-9.5-4.8Z" />
      <path d="M6.5 11.5v4.2c0 1.4 2.5 2.8 5.5 2.8s5.5-1.4 5.5-2.8v-4.2" />
      <path d="M21.5 9.6v5" />
    </svg>
  )
}

function FinanceIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 19.5h18" />
      <path d="m4 15 5-5 4 3 7-8" />
      <path d="M16.5 5H20v3.5" />
    </svg>
  )
}

function ReportIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 3.5h8l4 4V20.5H6z" />
      <path d="M14 3.5v4h4M9 12h6M9 15.5h6" />
    </svg>
  )
}
