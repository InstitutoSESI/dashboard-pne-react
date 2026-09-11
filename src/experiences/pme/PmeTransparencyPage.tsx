import { PmePageHeading, PmeTableRegion } from './PmePrimitives'
import { PME_DATA_LABELS } from './pmeFormatting'
import type { PmeMunicipalModel, PmeSourceProvenance } from './pmeTypes'

export function PmeTransparencyPage({ sources, model }: { sources: PmeSourceProvenance[]; model?: PmeMunicipalModel }) {
  const diagnostic = model?.modules.diagnostic
  const matriz = model?.modules.matriz
  return <>
    <PmePageHeading title="Fontes e como usar esta leitura" description="Cada evidência informa a fonte, o período e seus limites. Use este percurso para organizar a discussão municipal com base no que foi publicado." />
    <div className="pme-reading-columns"><section className="pme-section"><h2>Para a discussão do PME</h2><p>A plataforma reúne informações públicas para apoiar a leitura do município. A Agenda destaca situações já classificadas no diagnóstico; as decisões sobre prioridades, ações e acompanhamento pertencem às instâncias municipais.</p><p>O percurso reúne os 19 objetivos e as 73 metas do PNE. Os títulos curtos e as perguntas de apoio facilitam a consulta, enquanto as fichas preservam a meta, a referência legal e as fontes correspondentes.</p></section>
    <section className="pme-section"><h2>Como são escolhidos os destaques</h2><p>As situações aparecem na ordem dos objetivos e metas que têm uma classificação publicada no diagnóstico. O Panorama municipal mostra até quatro delas, e a Agenda reúne as demais. Esse recorte de leitura não reduz o conjunto de evidências disponível.</p><p>“Avançar” informa a posição do indicador diante da referência publicada. Não representa, por si só, melhora ao longo do tempo. Leituras históricas só aparecem quando foram publicadas para a relação.</p><p>Os destaques ajudam a organizar a discussão e não são uma avaliação da qualidade do PME.</p></section></div>
    <section className="pme-section"><h2>Como interpretar a disponibilidade dos dados</h2><p>Algumas metas ainda não têm indicador municipal associado. Mesmo quando existe um indicador, o resultado pode não estar disponível. A tabela explica cada situação.</p>
      <PmeTableRegion label="Significado dos estados de disponibilidade"><table><caption>Estados utilizados na leitura</caption><thead><tr><th scope="col">Estado</th><th scope="col">Significado</th></tr></thead><tbody>
        <tr><th scope="row">{PME_DATA_LABELS.observed}</th><td>Há resultado público; zero é uma observação e permanece zero.</td></tr>
        <tr><th scope="row">{PME_DATA_LABELS.null}</th><td>O valor publicado é nulo. Não foi preenchido com zero.</td></tr>
        <tr><th scope="row">{PME_DATA_LABELS.unavailable}</th><td>A fonte informa que o resultado está indisponível.</td></tr>
        <tr><th scope="row">{PME_DATA_LABELS.suppressed}</th><td>O valor foi protegido na publicação e não pode ser exibido.</td></tr>
        <tr><th scope="row">{PME_DATA_LABELS.not_applicable}</th><td>O indicador não se aplica conforme a regra publicada.</td></tr>
        <tr><th scope="row">{PME_DATA_LABELS.not_published}</th><td>O indicador está associado à meta, mas ainda não há resultado publicado para o município.</td></tr>
        <tr><th scope="row">{PME_DATA_LABELS.not_loaded}</th><td>A consulta ainda não terminou ou apresentou uma falha. Tente novamente para verificar se há um resultado disponível.</td></tr>
      </tbody></table></PmeTableRegion>
    </section>
    <div className="pme-reading-columns"><section className="pme-section"><h2>Comparações e dados de apoio</h2><p>Comparações entre anos, territórios ou unidades só são apresentadas quando a própria publicação as permite. Matrículas pela localização da escola, por exemplo, podem representar um universo diferente da população residente.</p><p>A Matriz é um apoio opcional para organizar perguntas, hipóteses e verificações locais ligadas às metas. Ela ajuda a preparar a conversa municipal, mas não confirma causas nem substitui a análise das equipes e dos conselhos.</p><p>Os caminhos financeiros indicam onde consultar regras e condições. Eles não demonstram elegibilidade, adesão, saldo ou disponibilidade orçamentária.</p></section>
    <section className="pme-section"><h2>Informações desta consulta</h2>
      {model ? <dl className="pme-provenance"><dt>Município</dt><dd>{model.municipality.name} / RS</dd>
        <dt>Diagnóstico</dt><dd>{diagnostic?.status === 'available' ? <a href={`/data/pne2026-diagnostic-v3/releases/${diagnostic.value.diagnosticReleaseId}/municipios/${model.municipality.ibgeCode}.json`}>Documento municipal consultado</a> : diagnostic?.status === 'error' ? 'O diagnóstico não pôde ser carregado nesta consulta.' : 'O diagnóstico ainda está sendo preparado.'}</dd>
        <dt>Matriz de apoio</dt><dd>{matriz?.status === 'available' ? `Disponível para este município, com referência em ${matriz.value.referenceDate}.` : matriz?.status === 'not_published' ? 'Ainda não publicada para este município; os demais conteúdos continuam disponíveis.' : matriz?.status === 'error' ? 'A Matriz não pôde ser carregada nesta consulta.' : 'A Matriz ainda está sendo preparada.'}</dd>
      </dl> : <p>Selecione um município para consultar as informações municipais disponíveis.</p>}
      <p>As fontes podem ter períodos diferentes. Confira o período informado em cada evidência antes de comparar resultados ou apoiar uma decisão.</p>
    </section>
    </div><section className="pme-section"><h2>Fontes oficiais</h2><ul className="pme-source-list">{sources.map((source) => <li key={source.sourceId}>{source.officialUrl ? <a href={source.officialUrl}>{source.title}</a> : source.title}{source.period ? ` • Período: ${source.period}` : ''}</li>)}</ul><p className="pme-note">Os links levam às referências oficiais usadas nas evidências apresentadas.</p></section>
    <section className="pme-section"><h2>Como consultar e compartilhar</h2><p>Use a tecla Tab para navegar pelos controles e acessar os pontos dos gráficos. Nas tabelas maiores, role horizontalmente para consultar as demais colunas. Na página Relatórios, é possível imprimir, salvar em PDF e baixar uma planilha.</p><p>Para compartilhar a mesma consulta, copie o endereço da página: ele preserva o município e os filtros selecionados.</p></section>
  </>
}
