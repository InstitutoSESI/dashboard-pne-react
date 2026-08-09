import { loadJson } from './staticData'

const SIOPE_BASE_PATH = '/data/educacao/siope'

export const SIOPE_DASHBOARD_YEARS = [2021, 2022, 2023, 2024, 2025]
export const SIOPE_SELECTED_INDICATORS_COUNT = 14
const SIOPE_OFFICIAL_GROUPS = [
  { key: '1', label: 'Cumprimento legal', order: 1, prefix: '1' },
  { key: '2', label: 'Distribuição das despesas', order: 2, prefix: '2' },
  { key: '3', label: 'Despesas com pessoal', order: 3, prefix: '3' },
  { key: '4', label: 'Gasto por aluno', order: 4, prefix: '4' },
  { key: '5', label: 'Indicadores educacionais', order: 5, prefix: '5' },
  { key: '6', label: 'Composição da receita', order: 6, prefix: '6' },
  { key: '7', label: 'Resultado e saldos', order: 7, prefix: '7' },
  { key: '8', label: 'MDE em valores', order: 8, prefix: '8' },
]

export const SIOPE_INDICATOR_READING_GUIDES = {
  aplicacao_mde_percentual: {
    oQueMede: 'Mede o percentual da receita de impostos e transferências aplicado em manutenção e desenvolvimento do ensino.',
    comoInterpretar: 'A principal leitura é verificar se o município cumpriu o mínimo constitucional de 25%. Valor abaixo desse patamar exige atenção imediata; valor acima indica cumprimento.',
    atencaoLeitura: 'O indicador não mede, sozinho, a qualidade do gasto educacional.',
  },
  fundeb_remuneracao_profissionais_percentual: {
    oQueMede: 'Mede a parcela dos recursos do FUNDEB aplicada na remuneração dos profissionais da educação básica.',
    comoInterpretar: 'Ajuda a verificar o cumprimento do mínimo legal de 70% e o peso da folha financiada pelo Fundo.',
    atencaoLeitura: 'Percentuais muito baixos indicam risco de descumprimento; percentuais muito altos podem reduzir a margem para outras ações de manutenção e desenvolvimento do ensino.',
  },
  fundeb_nao_aplicado_percentual: {
    oQueMede: 'Mostra a parcela dos recursos do FUNDEB que não foi executada no próprio exercício.',
    comoInterpretar: 'A leitura principal é de execução financeira: quanto menor o percentual, menor o saldo não aplicado no ano.',
    atencaoLeitura: 'Valores próximos ou acima do limite exigem atenção ao planejamento, ao empenho e ao uso dos recursos no prazo legal.',
  },
  valor_aplicado_mde_reais: {
    oQueMede: 'Mostra, em reais, o volume aplicado em manutenção e desenvolvimento do ensino.',
    comoInterpretar: 'Ajuda a dimensionar o esforço financeiro absoluto do município.',
    atencaoLeitura: 'Deve ser lido junto ao porte da rede, número de alunos, receita disponível e inflação, pois os valores são nominais.',
  },
  fundeb_educacao_infantil_percentual: {
    oQueMede: 'Indica a parcela do FUNDEB aplicada na educação infantil.',
    comoInterpretar: 'Ajuda a observar o esforço financeiro direcionado a creches e pré-escolas.',
    atencaoLeitura: 'Aumento ou queda não deve ser interpretado automaticamente como melhora ou piora, pois depende da matrícula, da demanda, da rede conveniada e da organização da oferta.',
  },
  fundeb_ensino_fundamental_percentual: {
    oQueMede: 'Indica a parcela do FUNDEB aplicada no ensino fundamental.',
    comoInterpretar: 'Ajuda a entender como o fundo se distribui entre etapas da educação básica.',
    atencaoLeitura: 'A interpretação deve considerar o perfil da matrícula, a responsabilidade prioritária do município e eventuais mudanças na oferta.',
  },
  despesas_educacao_total_percentual: {
    oQueMede: 'Mostra o peso da educação no conjunto das despesas municipais.',
    comoInterpretar: 'Ajuda a entender a prioridade orçamentária relativa da área.',
    atencaoLeitura: 'Percentual maior não significa necessariamente melhor gasto, e percentual menor não significa problema automático, desde que os mínimos legais e as necessidades da rede estejam sendo atendidos.',
  },
  investimento_aluno_basica_reais: {
    oQueMede: 'Mostra o valor médio aplicado por estudante da educação básica.',
    comoInterpretar: 'É útil para acompanhar o esforço financeiro por aluno e comparar municípios com cautela.',
    atencaoLeitura: 'Redes menores, rurais ou territorialmente dispersas podem ter custos unitários mais altos. O indicador não mede qualidade nem eficiência sozinho.',
  },
  investimento_aluno_infantil_reais: {
    oQueMede: 'Mostra o gasto médio por aluno da educação infantil.',
    comoInterpretar: 'Ajuda a observar o esforço financeiro nessa etapa.',
    atencaoLeitura: 'A educação infantil pode ter custos diferenciados por infraestrutura, jornada, profissionais e demanda por creche e pré-escola.',
  },
  investimento_aluno_fundamental_reais: {
    oQueMede: 'Mostra o gasto médio por aluno do ensino fundamental.',
    comoInterpretar: 'Ajuda a acompanhar a sustentação financeira da principal etapa da rede municipal.',
    atencaoLeitura: 'A leitura deve considerar matrícula, transporte escolar, tempo integral, estrutura da rede e características territoriais.',
  },
  despesa_professores_aluno_basica_reais: {
    oQueMede: 'Mostra quanto a despesa com professores representa por estudante da educação básica.',
    comoInterpretar: 'Ajuda a entender o peso da remuneração docente na estrutura de gasto por aluno.',
    atencaoLeitura: 'Não indica, isoladamente, valorização adequada, eficiência ou resultado de aprendizagem.',
  },
  receitas_impostos_total_percentual: {
    oQueMede: 'Mostra quanto as receitas de impostos representam no total das receitas municipais.',
    comoInterpretar: 'Ajuda a entender a composição da base de financiamento da educação e o grau de dependência de transferências.',
    atencaoLeitura: 'Quando houver baixa cobertura em anos recentes, o dado deve ser lido com cautela.',
  },
  resultado_financeiro_exercicio_reais: {
    oQueMede: 'Indica superávit ou déficit financeiro informado no exercício.',
    comoInterpretar: 'Ajuda a observar o equilíbrio financeiro geral.',
    atencaoLeitura: 'Não deve ser usado sozinho para avaliar a política educacional. A interpretação depende do contexto fiscal, contábil e orçamentário do município.',
  },
  saldo_financeiro_fundeb_reais: {
    oQueMede: 'Mostra o saldo financeiro associado aos recursos do FUNDEB no exercício.',
    comoInterpretar: 'Ajuda a acompanhar recursos disponíveis ou remanescentes do Fundo.',
    atencaoLeitura: 'A existência de saldo não é necessariamente irregular; a leitura depende do calendário de repasses, despesas empenhadas, restos a pagar e prazo legal de utilização.',
  },
}

export function getSiopeOfficialGroup(codigoIndicador) {
  const prefix = String(codigoIndicador ?? '').split('.')[0]
  return SIOPE_OFFICIAL_GROUPS.find((group) => group.prefix === prefix) ?? null
}

export function loadSiopeDashboardData() {
  return Promise.all([
    loadJson(`${SIOPE_BASE_PATH}/siope_indicadores_dashboard_wide.json`),
    loadJson(`${SIOPE_BASE_PATH}/siope_indicadores_dashboard_catalogo.json`),
  ]).then(([wide, catalogo]) => ({
    catalogo,
    wide,
  }))
}

export function buildSiopeMdeAnalysis(municipality) {
  const series = SIOPE_DASHBOARD_YEARS.map((year) => {
    const rawValue = municipality?.anos?.[String(year)]?.indicadores?.aplicacao_mde_percentual?.valor
    const rate = rawValue === null || rawValue === undefined || !Number.isFinite(Number(rawValue))
      ? null
      : Number(rawValue)
    return {
      year,
      rate,
      marginFromMinimum: rate === null ? null : rate - 25,
    }
  }).filter((point) => point.rate !== null)

  if (!series.length) return null
  const first = series[0]
  const latest = series[series.length - 1]
  const rates = series.map((point) => point.rate)
  return {
    series,
    firstYear: first.year,
    latestYear: latest.year,
    latestRate: latest.rate,
    latestMarginFromMinimum: latest.marginFromMinimum,
    compliantYears: series.filter((point) => point.rate >= 25).length,
    minimumRate: Math.min(...rates),
    maximumRate: Math.max(...rates),
    variationFromFirst: latest.rate - first.rate,
  }
}

function formatPercentForReading(value) {
  return `${Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`
}

function formatPointsForReading(value) {
  return `${Math.abs(Number(value)).toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} p.p.`
}

export function buildSiopeExerciseReading(mdeAnalysis, execution, stateNameForms) {
  const sentences = []

  if (
    mdeAnalysis
    && Number.isFinite(mdeAnalysis.latestRate)
    && Number.isFinite(mdeAnalysis.latestMarginFromMinimum)
    && mdeAnalysis.series.length > 0
  ) {
    const years = mdeAnalysis.series.length
    const marginDirection = mdeAnalysis.latestMarginFromMinimum >= 0 ? 'acima' : 'abaixo'
    let complianceText
    if (mdeAnalysis.compliantYears === years) {
      complianceText = years === 1
        ? 'cumpriu o mínimo no exercício analisado'
        : `cumpriu o mínimo em todos os ${years} exercícios analisados`
    } else {
      complianceText = years === 1
        ? 'não cumpriu o mínimo no exercício analisado'
        : `cumpriu o mínimo em ${mdeAnalysis.compliantYears} dos ${years} exercícios analisados`
    }
    sentences.push(
      `O município aplicou ${formatPercentForReading(mdeAnalysis.latestRate)} em MDE, `
      + `${formatPointsForReading(mdeAnalysis.latestMarginFromMinimum)} ${marginDirection} do mínimo constitucional, `
      + `e ${complianceText}.`,
    )
  }

  const history = execution?.history ?? []
  const latestExecution = history.at(-1)
  const paidRate = latestExecution?.derivedRates?.paidToCommittedRate?.value
  if (latestExecution && Number.isFinite(paidRate)) {
    const stateRate = latestExecution.stateReference?.paidToCommittedRate?.value
    let stateText = ''
    if (Number.isFinite(stateRate)) {
      const difference = paidRate - stateRate
      stateText = Math.abs(difference) < 0.000001
        ? `, resultado igual à referência ${stateNameForms.withDe}`
        : `, resultado ${formatPointsForReading(difference)} ${difference > 0 ? 'acima' : 'abaixo'} da referência ${stateNameForms.withDe}`
    }
    sentences.push(
      `Em ${latestExecution.referenceYear}, ${formatPercentForReading(paidRate)} das despesas empenhadas `
      + `na função Educação foram pagas${stateText}.`,
    )
  }

  return sentences.join(' ')
}
