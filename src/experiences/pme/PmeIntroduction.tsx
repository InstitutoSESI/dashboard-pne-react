import { ChartNoAxesCombined, ClipboardList, FileDown } from 'lucide-react'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeMunicipalityIdentity } from './pmeTypes'
import './styles/pme-introduction.css'

export function PmeIntroduction({ route, municipality }: { route: PmeRoute; municipality?: PmeMunicipalityIdentity }) {
  function selectMunicipality() {
    const selector = document.querySelector<HTMLInputElement>('.pme-topbar .municipio-selector__input')
    selector?.scrollIntoView({ block: 'center' })
    selector?.focus()
    selector?.select()
  }
  return <>
    <section className="pme-introduction">
      <div className="pme-introduction-copy">
        <h1 tabIndex={-1}>Evidências para planejar a educação municipal</h1>
        <p>O Painel SESI de Educação reúne dados públicos dos municípios do Rio Grande do Sul para apoiar a elaboração e o acompanhamento do Plano Municipal de Educação (PME).</p>
        <p>Parta dos <strong>19 objetivos e das 73 metas do PNE</strong> para conhecer os resultados, examinar o que ainda falta saber e preparar a discussão com as equipes e os conselhos municipais.</p>
        <div className="pme-introduction-start">
          {municipality ? <><span>Continue a leitura de <strong>{municipality.name}</strong></span><a className="pme-button" href={pmeLink(route, 'inicio', { objectiveId: null, themeId: null })}>Ver panorama municipal</a></>
            : <><span>Comece pela realidade do seu município.</span><button type="button" className="pme-button" onClick={selectMunicipality}>Selecionar município</button></>}
          <a href={pmeLink(route, 'objetivos', { objectiveId: null, themeId: null })}>Conhecer os objetivos do PNE</a>
        </div>
      </div>
      <aside className="pme-introduction-guide">
        <h2>Da leitura à discussão do PME</h2>
        <ol>
          <li><strong>Conheça o município</strong><span>Veja o panorama, os indicadores e a evolução dos resultados.</span></li>
          <li><strong>Aprofunde as perguntas</strong><span>Consulte as metas, os limites dos dados e o contexto financeiro.</span></li>
          <li><strong>Leve evidências à reunião</strong><span>Prepare uma síntese, um caderno por objetivo ou uma agenda em PDF e Excel.</span></li>
        </ol>
      </aside>
    </section>
    <section className="pme-section" aria-labelledby="pme-introduction-content">
      <h2 id="pme-introduction-content">O que você encontra aqui</h2>
      <div className="pme-introduction-links">
        <a href={pmeLink(route, 'evidencias', { objectiveId: null, themeId: null })}><ChartNoAxesCombined aria-hidden="true" size={23} /><span><strong>Resultados com contexto</strong><span>Indicadores, séries históricas, fontes e limites de cada leitura.</span></span></a>
        <a href={pmeLink(route, 'agenda', { objectiveId: null, themeId: null })}><ClipboardList aria-hidden="true" size={23} /><span><strong>Perguntas para o planejamento</strong><span>Situações observadas e caminhos para aprofundar a análise local.</span></span></a>
        <a href={pmeLink(route, 'relatorios', { objectiveId: null, themeId: null })}><FileDown aria-hidden="true" size={23} /><span><strong>Materiais para compartilhar</strong><span>Relatórios e planilhas para consulta, reuniões e acompanhamento.</span></span></a>
      </div>
    </section>
    <div className="pme-introduction-principles"><p><strong>Dados oficiais, decisões municipais.</strong> Cada resultado mantém fonte e período. A falta de informação também fica visível; as prioridades e ações são definidas pelo município.</p><a href={pmeLink(route, 'transparencia')}>Entender as fontes e os critérios</a></div>
  </>
}
