const DIRECT_RELATIONS = new Set([
  'relation.1.c.pre_escola',
  'relation.4.a.basico_6_17',
  'relation.4.b.idade_regular_quinto',
  'relation.4.c.idade_regular_nono',
  'relation.4.d.idade_regular_medio',
  'relation.8.c.educacao_ambiental',
  'relation.11.a.alfabetizacao_pop_15_mais',
  'relation.11.b.fundamental_concluido_15_29',
  'relation.11.b.fundamental_concluido_15_mais',
  'relation.11.c.medio_concluido_18_29',
  'relation.11.c.medio_concluido_18_mais',
  'relation.12.c.eja_integrada_educacao_profissional_percentual',
  'relation.17.d.temporarios',
  'relation.17.f.pos_graduacao',
  'relation.18.b.conselho_escolar',
])
const CONTEXT_RELATIONS = new Set([
  'relation.4.a.basico_15_17',
])

export function getPne2026PublicDescription(relationId) {
  if (DIRECT_RELATIONS.has(relationId)) {
    return 'Este resultado acompanha diretamente o recorte definido para a meta.'
  }
  if (CONTEXT_RELATIONS.has(relationId)) {
    return 'Este resultado oferece contexto relacionado à meta, mas usa recorte ou base territorial diferente e não mede seu cumprimento.'
  }
  return 'Este é um dos resultados acompanhados nesta meta e não representa sozinho seu cumprimento integral.'
}

const FINAL_CYCLE_LABEL_RELATIONS = new Set([
  'relation.1.c.pre_escola',
  'relation.4.a.basico_6_17',
  'relation.17.a.adequacao_ai',
  'relation.17.a.adequacao_af',
  'relation.17.a.adequacao_em',
  'relation.19.c.salas_acessiveis',
])

export function getPne2026ReferenceLabel(relationId, referenceYear) {
  if (
    relationId
    === 'relation.12.c.eja_integrada_educacao_profissional_percentual'
  ) {
    return 'Referência intermediária PNE 2031'
  }
  if (FINAL_CYCLE_LABEL_RELATIONS.has(relationId)) {
    return 'Meta PNE 2036'
  }
  return `Meta PNE ${referenceYear}`
}
