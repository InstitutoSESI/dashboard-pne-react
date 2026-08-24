import { useMemo } from 'react'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { ACTIVE_STATE_CONFIG } from '../../config/stateConfig'
import { useRegionalPanel } from '../../hooks/useRegionalPanel'
import type {
  RegionalCountPoint,
  RegionalCoverageIndicator,
  RegionalDocument,
} from './regionalTypes'
import '../../styles/regional-page.css'

/*
 * Panorama da Região.
 *
 * A região não é escolhida: ela é derivada do município selecionado. A página
 * apresenta o painel publicado e não calcula nada — a agregação inteira vive no
 * gerador determinístico, e o que chega aqui já foi conferido contra o
 * manifesto.
 *
 * O `null` é mostrado como ausência, nunca como zero: quando um ano não teve
 * cobertura completa na região, a página diz quantos municípios informaram em
 * vez de exibir um total que parece inteiro e não é.
 */

const ENROLLMENT_BREAKDOWNS = [
  { key: 'por_etapa', label: 'Por etapa de ensino' },
  { key: 'por_dependencia', label: 'Por dependência administrativa' },
  { key: 'por_localizacao', label: 'Por localização' },
] as const

/*
 * Ordem de leitura de cada recorte. Alfabética esconderia a estrutura: as redes
 * pública e privada particionam o total, e as redes federal, estadual e
 * municipal são partes da pública — lidas nessa sequência, a relação aparece
 * sozinha. Categoria que apareça no artefato e não esteja aqui vai para o fim,
 * em ordem alfabética, em vez de sumir.
 */
const CATEGORY_ORDER: Readonly<Record<string, readonly string[]>> = Object.freeze({
  por_etapa: [
    'infantil',
    'fundamental',
    'fundamental_anos_iniciais',
    'fundamental_anos_finais',
    'medio',
    'profissional',
    'eja',
  ],
  por_dependencia: ['publica', 'federal', 'estadual', 'municipal', 'privada'],
  por_localizacao: ['urbana', 'rural'],
})

const CATEGORY_LABELS: Readonly<Record<string, string>> = Object.freeze({
  infantil: 'Educação infantil',
  fundamental: 'Ensino fundamental',
  fundamental_anos_iniciais: 'Fundamental — anos iniciais',
  fundamental_anos_finais: 'Fundamental — anos finais',
  medio: 'Ensino médio',
  profissional: 'Educação profissional',
  eja: 'Educação de jovens e adultos',
  publica: 'Rede pública',
  federal: 'Rede federal',
  privada: 'Rede privada',
  estadual: 'Rede estadual',
  municipal: 'Rede municipal',
  urbana: 'Urbana',
  rural: 'Rural',
})

const integerFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 0,
})
const percentFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})

function categoryLabel(key: string): string {
  return CATEGORY_LABELS[key] ?? key
}

function orderedCategories(breakdownKey: string, categories: readonly string[]): string[] {
  const preferred = CATEGORY_ORDER[breakdownKey] ?? []
  const known = preferred.filter((category) => categories.includes(category))
  const rest = categories.filter((category) => !preferred.includes(category)).sort()
  return [...known, ...rest]
}

function formatCount(value: number | null): string {
  return value === null ? 'não disponível' : integerFormatter.format(value)
}

function formatPercent(value: number | null): string {
  return value === null ? 'não disponível' : `${percentFormatter.format(value)}%`
}

function lastWithValue<T extends { readonly valor: number | null }>(
  series: readonly T[],
): T | null {
  for (let index = series.length - 1; index >= 0; index -= 1) {
    if (series[index].valor !== null) return series[index]
  }
  return null
}

function firstWithValue<T extends { readonly valor: number | null }>(
  series: readonly T[],
): T | null {
  return series.find((point) => point.valor !== null) ?? null
}

/** Variação em pontos percentuais entre o primeiro e o último ano com valor. */
function CoverageRow({ indicator }: { indicator: RegionalCoverageIndicator }) {
  const first = firstWithValue(indicator.series)
  const last = lastWithValue(indicator.series)
  const change = first !== null && last !== null && first.ano !== last.ano
    ? (last.valor as number) - (first.valor as number)
    : null

  return (
    <tr>
      <th scope="row">
        <span className="regional-table__label">{indicator.titulo}</span>
        <span className="regional-table__hint">{indicator.faixaEtaria}</span>
      </th>
      <td>{formatPercent(last?.valor ?? null)}</td>
      <td>{last === null ? '—' : last.ano}</td>
      <td>
        {change === null
          ? '—'
          : `${change >= 0 ? '+' : '−'}${percentFormatter.format(Math.abs(change))} p.p.`}
      </td>
      <td>
        {last === null
          ? '—'
          : `${formatCount(last.numerador)} de ${formatCount(last.denominador)}`}
      </td>
    </tr>
  )
}

function EnrollmentRow({
  label,
  point,
  totalMunicipalities,
}: {
  label: string
  point: RegionalCountPoint | null
  totalMunicipalities: number
}) {
  return (
    <tr>
      <th scope="row">{label}</th>
      <td>{formatCount(point?.valor ?? null)}</td>
      <td>{point === null ? '—' : point.ano}</td>
      <td>
        {point === null || point.municipiosComDado === totalMunicipalities
          ? 'todos os municípios'
          : `${point.municipiosComDado} de ${totalMunicipalities} municípios`}
      </td>
    </tr>
  )
}

function RegionalPanel({
  document,
  selectedMunicipalityId,
}: {
  document: RegionalDocument
  selectedMunicipalityId: string | null
}) {
  const { atendimento, matriculas, pagina, regiao } = document
  const totalPoint = lastWithValue(matriculas.series.total)
  const integralPoint = lastWithValue(matriculas.series.integral)

  const municipalities = useMemo(
    () => [...regiao.municipios].sort((left, right) => left.nome.localeCompare(right.nome, 'pt-BR')),
    [regiao.municipios],
  )

  return (
    <div className="page-stack regional-page">
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={`${regiao.totalMunicipios} municípios · ${ACTIVE_STATE_CONFIG.stateCode}`}
        description={pagina.descricao}
        eyebrow={pagina.eyebrow}
        title={pagina.titulo}
        variant="editorial"
      />

      <section aria-labelledby="regiao-resumo" className="regional-panel">
        <div className="regional-panel__head">
          <h2 className="regional-panel__title" id="regiao-resumo">Resumo da região</h2>
          <p className="regional-panel__text">
            Os números abaixo somam os municípios da região; nenhum vem de estimativa própria.
          </p>
        </div>
        <dl className="regional-highlights">
          <div>
            <dt>Municípios</dt>
            <dd>{integerFormatter.format(regiao.totalMunicipios)}</dd>
          </div>
          <div>
            <dt>{`Matrículas${totalPoint === null ? '' : ` em ${totalPoint.ano}`}`}</dt>
            <dd>{formatCount(totalPoint?.valor ?? null)}</dd>
          </div>
          <div>
            <dt>Matrículas em tempo integral</dt>
            <dd>{formatPercent(integralPoint?.percentual ?? null)}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="regiao-atendimento" className="regional-panel">
        <div className="regional-panel__head">
          <h2 className="regional-panel__title" id="regiao-atendimento">{atendimento.label}</h2>
          <p className="regional-panel__text">{atendimento.descricao}</p>
        </div>
        <div className="regional-table-scroll">
          <table className="regional-table">
            <caption className="u-sr-only">
              {`Atendimento por faixa etária na região ${regiao.nome}`}
            </caption>
            <thead>
              <tr>
                <th scope="col">Indicador</th>
                <th scope="col">Resultado</th>
                <th scope="col">Ano</th>
                <th scope="col">Desde o início da série</th>
                <th scope="col">Matrículas sobre população</th>
              </tr>
            </thead>
            <tbody>
              {atendimento.indicadores.map((indicator) => (
                <CoverageRow indicator={indicator} key={indicator.chave} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="regiao-matriculas" className="regional-panel">
        <div className="regional-panel__head">
          <h2 className="regional-panel__title" id="regiao-matriculas">{matriculas.label}</h2>
          <p className="regional-panel__text">{matriculas.descricao}</p>
        </div>
        <p className="regional-panel__text">
          As redes pública e privada dividem o total; a federal, a estadual e a municipal são
          partes da rede pública e por isso somam mais do que ela.
        </p>
        <div className="regional-table-scroll">
          <table className="regional-table">
            <caption className="u-sr-only">{`Matrículas na região ${regiao.nome}`}</caption>
            <thead>
              <tr>
                <th scope="col">Recorte</th>
                <th scope="col">Matrículas</th>
                <th scope="col">Ano</th>
                <th scope="col">Cobertura</th>
              </tr>
            </thead>
            <tbody>
              <EnrollmentRow
                label="Total da educação básica"
                point={totalPoint}
                totalMunicipalities={regiao.totalMunicipios}
              />
              <EnrollmentRow
                label="Em tempo integral"
                point={integralPoint}
                totalMunicipalities={regiao.totalMunicipios}
              />
              {ENROLLMENT_BREAKDOWNS.flatMap(({ key, label }) => {
                const breakdown = matriculas.series[key]
                return [
                  <tr className="regional-table__section" key={key}>
                    <th colSpan={4} scope="colgroup">{label}</th>
                  </tr>,
                  ...orderedCategories(key, Object.keys(breakdown)).map((category) => (
                    <EnrollmentRow
                      key={`${key}-${category}`}
                      label={categoryLabel(category)}
                      point={lastWithValue(breakdown[category])}
                      totalMunicipalities={regiao.totalMunicipios}
                    />
                  )),
                ]
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="regiao-municipios" className="regional-panel">
        <div className="regional-panel__head">
          <h2 className="regional-panel__title" id="regiao-municipios">
            Municípios desta região
          </h2>
          <p className="regional-panel__text">
            A região é derivada do município selecionado; ele aparece destacado na lista.
          </p>
        </div>
        <ul className="regional-municipalities">
          {municipalities.map((municipality) => {
            const isSelected = municipality.ibgeCode === selectedMunicipalityId
            return (
              <li
                className={isSelected
                  ? 'regional-municipalities__item is-selected'
                  : 'regional-municipalities__item'}
                key={municipality.ibgeCode}
              >
                {municipality.nome}
                {isSelected ? <span className="u-sr-only"> (município selecionado)</span> : null}
              </li>
            )
          })}
        </ul>
      </section>

      <section aria-labelledby="regiao-metodologia" className="regional-panel">
        <div className="regional-panel__head">
          <h2 className="regional-panel__title" id="regiao-metodologia">Como estes números são formados</h2>
        </div>
        <ul className="regional-list">
          {document.metodologia.map((note) => <li key={note}>{note}</li>)}
        </ul>
        <h3 className="regional-subtitle">Fontes</h3>
        <ul className="regional-list">
          {document.fontes.map((source) => (
            <li key={source.nome}>{`${source.nome} — ${source.uso}`}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export function AnaliseRegionalPage({
  municipalityId,
  selectedMunicipio,
}: {
  municipalityId: string | null
  selectedMunicipio: string | null
}) {
  const { data, loading } = useRegionalPanel(municipalityId)

  if (loading) {
    return <LoadingState message="Carregando o panorama da região…" />
  }

  /*
   * Sem município selecionado não há região a derivar — e a página diz isso em
   * vez de mostrar uma região arbitrária. O caso de município fora de qualquer
   * região não existe por contrato (o mapa particiona o estado), mas cai aqui
   * se algum dia existir.
   */
  if (!data) {
    return (
      <div className="page-stack regional-page">
        <PnePageHeader
          actions={null}
          asideContent={null}
          asideLabel={null}
          context={null}
          description={
            municipalityId
              ? `Não há região publicada para ${selectedMunicipio ?? 'o município selecionado'}.`
              : 'Selecione um município para ver a região a que ele pertence.'
          }
          eyebrow="Análise regional"
          title="Panorama da Região"
          variant="editorial"
        />
      </div>
    )
  }

  return <RegionalPanel document={data.document} selectedMunicipalityId={municipalityId} />
}
