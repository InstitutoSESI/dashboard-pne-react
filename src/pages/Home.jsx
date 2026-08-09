import { ArrowRight, MapPin } from 'lucide-react'
import { ACTIVE_STATE_CONFIG, PLATFORM_LABEL } from '../config/stateConfig'

const ICON_STROKE = 1.7

const PLATFORM_MOVES = [
  {
    label: 'Metas e ciclos do PNE',
    n: '01',
    verb: 'Planejar',
  },
  {
    label: 'Indicadores educacionais',
    n: '02',
    verb: 'Compreender',
  },
  {
    label: 'Financiamento da educação',
    n: '03',
    verb: 'Sustentar',
  },
  {
    label: 'Relatório Técnico Municipal',
    n: '04',
    verb: 'Documentar',
  },
]

const FRONTS = [
  {
    action: 'Explorar o PNE',
    key: 'pne-overview',
    n: '01',
    scope: 'Planejamento e metas',
    summary: 'Metas legais, diagnóstico municipal e leitura dos ciclos 2014–2024 e 2026–2036.',
    title: 'Plano Nacional de Educação',
  },
  {
    action: 'Abrir indicadores',
    key: 'educacao',
    n: '02',
    scope: 'Panorama educacional',
    summary: 'Atendimento, trajetória, aprendizagem, profissionais, infraestrutura e modalidades.',
    title: 'Indicadores educacionais',
  },
  {
    action: 'Ver financiamento',
    key: 'financeiros',
    n: '03',
    scope: 'Recursos públicos',
    summary: 'SIOPE, FUNDEB, complementação VAAR, PNATE e aplicação dos recursos da educação.',
    title: 'Financiamento da educação',
  },
  {
    action: 'Abrir relatório',
    key: 'relatorio-tecnico-municipal',
    n: '04',
    scope: 'Síntese e impressão',
    summary: 'Evidências educacionais e financeiras reunidas em um documento municipal único.',
    title: 'Relatório Técnico Municipal',
  },
]

// Acento por destino na Home: cor = area para onde a frente leva. Financiamento
// e navy (identidade da area), Relatorio e slate (sintese/analise), PNE e
// Educacao ficam no verde institucional padrao.
const FRONT_ACCENTS = {
  financeiros: 'navy',
  'relatorio-tecnico-municipal': 'slate',
}

const NAVIGATION_STEPS = [
  {
    body: 'O seletor no topo define o território que acompanha toda a navegação.',
    n: '01',
    title: 'Selecione o município',
  },
  {
    body: 'Use este índice ou os grupos da barra lateral para escolher um tema.',
    n: '02',
    title: 'Escolha uma frente',
  },
  {
    body: 'Cada tela organiza período, unidade, fonte e referências para orientar a leitura.',
    n: '03',
    title: 'Aprofunde o contexto',
  },
  {
    body: 'Consolide as evidências no relatório municipal, preparado para impressão.',
    n: '04',
    title: 'Reúna a síntese',
  },
]

export function Home({ onNavigate }) {
  return (
    <div className="home-portal">
      <header className="home-portal__hero">
        <div className="home-portal__hero-copy">
          <p className="home-portal__identity">
            {PLATFORM_LABEL} · Inteligência Analítica Municipal
          </p>
          <h1 className="home-portal__title">
            Uma leitura integrada da educação nos municípios{' '}
            <span className="home-portal__state-name">
              {ACTIVE_STATE_CONFIG.stateNameForms.withDe}
            </span>
            .
          </h1>
          <p className="home-portal__lead">
            A plataforma reúne planejamento, indicadores educacionais e financiamento em um só
            percurso. Escolha um município, explore cada frente e reúna as evidências em uma
            síntese técnica.
          </p>

          <div className="home-portal__start-note">
            <MapPin aria-hidden="true" strokeWidth={ICON_STROKE} />
            <p className="home-portal__start-copy">
              <strong>Comece pelo território.</strong> Use o seletor de município no topo da tela; a
              escolha permanece ativa enquanto você navega.
            </p>
          </div>
        </div>

        <div className="home-portal__route" aria-labelledby="home-route-title">
          <p className="home-portal__route-title" id="home-route-title">
            Um percurso em quatro movimentos
          </p>
          <ol className="home-portal__route-list">
            {PLATFORM_MOVES.map((move) => (
              <li className="home-portal__route-item" key={move.n}>
                <span className="home-portal__route-number" aria-hidden="true">{move.n}</span>
                <span className="home-portal__route-copy">
                  <strong>{move.verb}</strong>
                  <span>{move.label}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </header>

      <section className="home-portal__explore" aria-labelledby="home-fronts-title">
        <div className="home-portal__section-head">
          <div className="home-portal__section-copy">
            <h2 id="home-fronts-title">Escolha por onde começar</h2>
            <p>
              Cada frente responde a uma pergunta diferente, mas todas preservam o mesmo município
              como referência.
            </p>
          </div>

        </div>

        <div className="home-portal__front-index">
          {FRONTS.map((front) => (
            <button
              aria-label={`${front.action}: ${front.title}`}
              className="home-portal__front"
              data-entry-accent={FRONT_ACCENTS[front.key] ?? 'green'}
              key={front.key}
              onClick={() => onNavigate?.(front.key)}
              type="button"
            >
              <span className="home-portal__front-number" aria-hidden="true">{front.n}</span>
              <span className="home-portal__front-content">
                <span className="home-portal__front-scope">{front.scope}</span>
                <span className="home-portal__front-title">{front.title}</span>
                <span className="home-portal__front-summary">{front.summary}</span>
                <span className="home-portal__front-action">
                  {front.action}
                  <ArrowRight aria-hidden="true" strokeWidth={ICON_STROKE} />
                </span>
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="home-portal__guide" aria-labelledby="home-guide-title">
        <div className="home-portal__guide-intro">
          <h2 id="home-guide-title">Do território à síntese, sem perder o contexto</h2>
          <p>
            A navegação foi organizada para que o município selecionado continue sendo o fio
            condutor entre os conteúdos.
          </p>
        </div>

        <ol className="home-portal__steps">
          {NAVIGATION_STEPS.map((step) => (
            <li className="home-portal__step" key={step.n}>
              <span className="home-portal__step-number" aria-hidden="true">{step.n}</span>
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
