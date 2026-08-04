import { PnePageHeader } from '../components/PnePageHeader'

const GUIDING_QUESTIONS = [
  {
    title: 'Quais problemas apresentam indícios no município?',
    description: 'Reunir sinais e evidências relacionados a cada meta do PNE para apoiar a identificação dos problemas que merecem atenção.',
  },
  {
    title: 'Como cada problema parece se manifestar localmente?',
    description: 'Organizar as formas de manifestação observadas no contexto municipal, considerando públicos, territórios e etapas de ensino.',
  },
  {
    title: 'Quais causas e relações precisam ser investigadas?',
    description: 'Registrar hipóteses e conexões que ainda precisam de análise antes da definição de prioridades e caminhos de ação.',
  },
]

export function PriorityMatrixPage({ onNavigate }) {
  return (
    <div className="page-stack priority-matrix-page">
      <PnePageHeader
        asideLabel="Status da Matriz de Prioridades"
        asideContent={(
          <>
            <span className="pne-page-header__aside-title">Status</span>
            <strong className="priority-matrix-page__status">Em construção</strong>
            <p className="pne-page-header__aside-description">
              A ferramenta ainda não está disponível para preenchimento.
            </p>
          </>
        )}
        description="Uma ferramenta de apoio para transformar evidências municipais em perguntas de investigação e prioridades para cada meta do PNE."
        eyebrow="Planejamento municipal"
        title="Matriz de Prioridades"
        variant="editorial"
      />

      <section className="page-card priority-matrix-page__preview" aria-labelledby="priority-matrix-preview-title">
        <div className="priority-matrix-page__heading">
          <span className="priority-matrix-page__label">O que a ferramenta vai apoiar</span>
          <h2 id="priority-matrix-preview-title">Três perguntas para orientar a leitura de cada meta</h2>
          <p>
            A futura matriz ajudará gestores a estruturar uma análise inicial. As respostas não serão conclusões automáticas: servirão como ponto de partida para investigação e planejamento local.
          </p>
        </div>

        <ol className="priority-matrix-page__questions">
          {GUIDING_QUESTIONS.map((question, index) => (
            <li key={question.title}>
              <span className="priority-matrix-page__question-index" aria-hidden="true">
                {String(index + 1).padStart(2, '0')}
              </span>
              <div>
                <h3>{question.title}</h3>
                <p>{question.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="priority-matrix-page__notice" aria-labelledby="priority-matrix-notice-title">
        <div>
          <span className="priority-matrix-page__label">Enquanto isso</span>
          <h2 id="priority-matrix-notice-title">Consulte as referências já disponíveis</h2>
          <p>
            As metas legais e o diagnóstico municipal continuarão sendo as bases de leitura para a futura matriz.
          </p>
        </div>
        <div className="priority-matrix-page__actions">
          <button className="pne-diagnostic-action" type="button" onClick={() => onNavigate?.('pne-legal-goals')}>
            Consultar metas legais
          </button>
          <button className="pne-diagnostic-action pne-diagnostic-action--primary" type="button" onClick={() => onNavigate?.('diagnostico')}>
            Abrir diagnóstico municipal
          </button>
        </div>
      </section>
    </div>
  )
}
