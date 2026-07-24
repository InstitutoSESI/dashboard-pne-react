export const FUNDEB_INDICATORS = [
  {
    key: 'receitas',
    label: 'Receita do Fundeb declarada',
    tipo: 'financeiro',
    cardDescription: 'Receita do Fundeb declarada pelo município no ano.',
    description: 'Total da receita do Fundeb declarada pelo município no demonstrativo do exercício.',
  },
  {
    key: 'despesa_remuneracao_profissionais',
    label: 'Remuneração dos profissionais',
    tipo: 'financeiro',
    cardDescription: 'Valor do FUNDEB aplicado na remuneração da educação básica.',
    description: 'Valor aplicado na remuneração dos profissionais da educação básica com recursos do FUNDEB.',
  },
  {
    key: 'despesa_remuneracao_profissionais_ensino_fundamental',
    label: 'Remuneração no ensino fundamental',
    tipo: 'financeiro',
    cardDescription: 'Remuneração vinculada ao ensino fundamental.',
    description: 'Parte da remuneração dos profissionais vinculada ao ensino fundamental.',
  },
  {
    key: 'despesa_remuneracao_profissionais_ensino_infantil',
    label: 'Remuneração na educação infantil',
    tipo: 'financeiro',
    cardDescription: 'Remuneração vinculada à educação infantil.',
    description: 'Parte da remuneração dos profissionais vinculada à educação infantil.',
  },
  {
    key: 'despesa_remuneracao_profissionais_creche',
    label: 'Remuneração em creche',
    tipo: 'financeiro',
    cardDescription: 'Remuneração em creche; série disponível a partir de 2021.',
    description: 'Valor aplicado na remuneração dos profissionais que atuam em creche. Para este indicador, a série deve ser lida a partir de 2021.',
  },
  {
    key: 'despesa_remuneracao_profissionais_pre_escola',
    label: 'Remuneração na pré-escola',
    tipo: 'financeiro',
    cardDescription: 'Remuneração na pré-escola; série disponível a partir de 2021.',
    description: 'Valor aplicado na remuneração dos profissionais que atuam na pré-escola. Para este indicador, a série deve ser lida a partir de 2021.',
  },
  {
    key: 'despesa_total_fundeb',
    label: 'Despesa total do FUNDEB',
    tipo: 'financeiro',
    cardDescription: 'Despesas realizadas com recursos do FUNDEB no ano.',
    description: 'Total de despesas realizadas com recursos do FUNDEB no ano.',
  },
  {
    key: 'percentual_minimo_remuneracao_profissionais',
    label: 'Percentual aplicado em remuneração',
    tipo: 'percentual',
    cardDescription: 'Percentual do FUNDEB aplicado na remuneração profissional.',
    description: 'Percentual dos recursos do FUNDEB aplicado na remuneração dos profissionais da educação. Até 2020, o mínimo era 60%; desde 2021, passou a ser 70%.',
  },
  {
    key: 'disponibilidade_financeira_ano_anterior',
    label: 'Saldo do ano anterior',
    tipo: 'financeiro',
    cardDescription: 'Saldo do FUNDEB vindo do exercício anterior.',
    description: 'Saldo financeiro de recursos do FUNDEB vindo do exercício anterior.',
  },
  {
    key: 'ingresso_recursos_ate_bimestre',
    label: 'Ingressos do Fundeb declarados no ano',
    tipo: 'financeiro',
    cardDescription: 'Ingressos do Fundeb declarados pelo município ao longo do ano.',
    description: 'Total de ingressos do Fundeb declarados pelo município ao longo do exercício.',
  },
  {
    key: 'pagamentos_efetuados_ate_bimestre',
    label: 'Pagamentos efetuados no ano',
    tipo: 'financeiro',
    cardDescription: 'Pagamentos realizados com recursos do FUNDEB no ano.',
    description: 'Total de pagamentos realizados com recursos do FUNDEB ao longo do ano.',
  },
  {
    key: 'disponibilidade_financeira_ate_bimestre',
    label: 'Disponibilidade financeira no fim do ano',
    tipo: 'financeiro',
    cardDescription: 'Valor disponível após ingressos e pagamentos do período.',
    description: 'Valor financeiro disponível ao final do período analisado, após os ingressos e pagamentos registrados.',
  },
  {
    key: 'saldo_financeiro_conciliado',
    label: 'Saldo financeiro conciliado',
    tipo: 'financeiro',
    cardDescription: 'Saldo financeiro conciliado no demonstrativo do FUNDEB.',
    description: 'Saldo financeiro conciliado informado no demonstrativo do FUNDEB.',
  },
]

export function formatFundebValue(value, tipo) {
  if (value === null || value === undefined) return '—'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  if (tipo === 'percentual') {
    return `${Math.round(numeric).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
  }
  return numeric.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
}

export function formatFundebCompactValue(value, tipo) {
  if (value === null || value === undefined) return '—'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  if (tipo === 'percentual') {
    return `${Math.round(numeric).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
  }

  const absolute = Math.abs(numeric)
  const sign = numeric < 0 ? '-' : ''
  const formatUnit = (unit, suffix) => `${sign}R$ ${(absolute / unit).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ${suffix}`

  if (absolute >= 1e9) return formatUnit(1e9, 'bi')
  if (absolute >= 1e6) return formatUnit(1e6, 'mi')
  if (absolute >= 1e3) return formatUnit(1e3, 'mil')
  return numeric.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

export function getLimiteReferencia(ano) {
  return ano <= 2020 ? 60 : 70
}
