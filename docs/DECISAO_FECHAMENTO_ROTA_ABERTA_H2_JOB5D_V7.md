# Decisão de fechamento da rota aberta de H2 — pós-Job 5D V7

**Classificação:** `DATA_PRESENTATION`
**Uso:** registro interno de produto
**Data de referência:** 28 de agosto de 2026
**publication_allowed_now:** `false`
**interface_allowed_now:** `false`
**compiler_allowed_now:** `false`

## 1. Decisão

`H2_TRAJETORIA_MUNICIPAL_V2` fica registrado com:

```text
analytical_state = NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT
current_product_handling = DEFERRED_FROM_CURRENT_OPEN_DATA_PILOT
open_data_exact_component_route = EXHAUSTED
```

H2 não integra o protótipo editorial atual e não deixa posição vazia no
percurso destinado à gestora. O percurso segue diretamente do módulo de
população e organização educacional para o módulo de EJA.

## 2. Evidência que sustenta o fechamento

Existem taxas oficiais municipais de aprovação, reprovação, abandono e
distorção idade-série. A auditoria do Job 5D, porém, não encontrou numeradores e
denominadores oficiais exatos no grão aceito
`município × ano × etapa × indicador × rede total` nas fontes abertas
autorizadas examinadas.

Os arquivos municipais do Inep auditados publicam percentuais. Os ETLs locais
leem essas mesmas colunas de taxa e não descartaram componentes durante a
carga. Os microdados abertos simplificados também não publicam a Situação do
Aluno no detalhe necessário nem o cruzamento idade × série exigido para
recompor a distorção.

Cobertura auditada:

| Universo | Linhas | Taxa oficial sem componente exato | Componente exato |
|---|---:|---:|---:|
| Rio Grande do Sul | 61.628 | 61.597 | 0 |
| Vale do Sinos | 1.240 | 1.240 | 0 |
| Nova Santa Rita (`4313375`) | 124 | 124 | 0 |

As 31 linhas restantes do RS estão marcadas como fonte indisponível. Nenhum
valor ausente foi convertido em zero.

## 3. Alcance exato da conclusão

O resultado esgota a rota aberta autorizada examinada. Ele não prova que os
componentes deixem de existir em acesso institucional restrito. Uma rota formal
junto ao Inep permanece uma trilha institucional opcional e paralela, não uma
condição executada neste job.

Não foram usados retrocálculo por arredondamento, matrícula genérica,
população, soma ou média de taxas, imputação ou estimativa. As fórmulas oficiais
foram preservadas e nenhuma fórmula foi alterada.

## 4. Consequências de produto

- nenhum fato dos Jobs 5A ou 5B é antecipado como narrativa;
- H2 não aparece como módulo disponível, cartão vazio ou aviso ao usuário;
- H3, A1 e A2 não são restauradas;
- o contexto juvenil opcional de A3 permanece descartado;
- o draft de pequeno denominador fica arquivado como contingência não
  congelada;
- nenhum limiar é escolhido;
- nenhum contrato descritivo baseado apenas em taxas é criado;
- nenhum pedido institucional é iniciado;
- `JOB_6` permanece dependente de decisão da gestora;
- `PILOT_GATE_11_V7` permanece bloqueado.

## 5. Fontes

- `.tmp/vocacoes-pne/v7-job5d/AUDITORIA_FONTES_DENOMINADORES_H2_V7.md`;
- `.tmp/vocacoes-pne/v7-job5d/LIMITACOES_AQUISICAO_H2_V7.json`;
- `.tmp/vocacoes-pne/v7-job5d/PACOTE_REVISAO_EXTERNA_JOB5D_V7.json`;
- `.tmp/vocacoes-pne/v7-job5d/MANIFEST_JOB5D_V7.json`;
- quatro documentos metodológicos oficiais do Inep preservados no Job 5D.

Este registro fecha somente a rota aberta examinada e não autoriza cálculo,
autoria pública, compilador, interface, publicação ou validação humana.
