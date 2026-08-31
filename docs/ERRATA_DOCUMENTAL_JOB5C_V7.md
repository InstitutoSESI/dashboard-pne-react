# Errata documental do Job 5C — V7

**Classificação:** `DATA_PRESENTATION`
**Natureza:** correções prospectivas para os artefatos do Job 5E; os arquivos
do Job 5C permanecem byte a byte inalterados
**publication_allowed_now:** `false`
**interface_allowed_now:** `false`
**compiler_allowed_now:** `false`

## 1. Cobertura do produto

O mapa revisado passa a registrar separadamente:

1. trajetória escolar;
2. trabalho juvenil ou trabalho e escolaridade;
3. cenários do Vale do Sinos;
4. validação humana.

O estado de trabalho juvenil é:

```text
LACUNA_TRABALHO_JUVENIL_ESCOLARIDADE =
UNRESOLVED_AFTER_H3_RETENTION_AND_A3_CONTEXT_DISCARD
```

Esse registro não restaura H3, não restaura A2 e não cria candidata.

## 2. Integridade referencial dos fatos

A matriz de módulos do Job 5C referenciava:

- `H1-MUNICIPALITY-4313375-CRECHE-2014-2025`;
- `H1-MUNICIPALITY-4313375-PRESCHOOL-2014-2025`.

Os registros reais foram localizados em
`.tmp/vocacoes-pne/v7-job3/candidate_facts.json` e na prioridade factual
versionada de Nova Santa Rita. Eles passam a integrar a matriz factual revisada:

| Fact ID | Evidência observada 2014–2025 |
|---|---|
| `H1-MUNICIPALITY-4313375-CRECHE-2014-2025` | matrículas 319→591; população compatível 1.611→1.587 |
| `H1-MUNICIPALITY-4313375-PRESCHOOL-2014-2025` | matrículas 459→823; população compatível 759→848 |

O fato `A3-MUN-4313375-LOGISTICA-2019-2025` já existia na matriz factual do
Job 5C, mas não estava referenciado pelo módulo. Ele passa a integrar
`approved_fact_ids` de A3 na matriz revisada.

Resultado esperado do QA: todo `approved_fact_id` existe na matriz factual e
todo fato autorizado para o protótipo é referenciado por exatamente um módulo.
Nenhum fato foi inventado.

## 3. H4 — matrículas por mil

`matriculas_por_mil` permanece apenas como cálculo interno de documentação ou
QA:

```text
matriculas_por_mil.public_eligible = false
matriculas_por_mil.editorial_message_allowed = false
```

Ele é removido da função de mensagem dos fatos editoriais. O módulo usa somente
participações municipais e diferenças distributivas, com fundamental e médio
separados. As lentes continuam sendo população residente e matrícula
localizada; a leitura não mede comportamento individual.

## 4. Títulos internos revisados

Os títulos são opções de trabalho para revisão da gestora e não títulos
públicos definitivos.

| Módulo interno | Opções de título, no máximo três | Recomendação do protótipo |
|---|---|---|
| H1 | População e organização educacional mudam em ritmos diferentes; Gerações e matrículas seguem ritmos diferentes no Vale; Etapas e municípios mostram mudanças distintas | **População e organização educacional mudam em ritmos diferentes** |
| H4 | Público adulto e matrículas de EJA têm distribuições diferentes; A distribuição da EJA muda entre fundamental e médio; Moradia e matrículas de EJA formam mapas distintos | **Público adulto e matrículas de EJA têm distribuições diferentes** |
| A3 | Mudanças nas ocupações e composição da formação profissional; Ocupações e formação profissional em dois retratos do Vale; Trabalho formal e cursos técnicos mostram composições territoriais | **Mudanças nas ocupações e composição da formação profissional** |
| A4 | Moradia e local de estudo ultrapassam limites municipais; Estudar fora do município pede acompanhamento compartilhado; Mobilidade educacional varia por etapa e município | **Moradia e local de estudo ultrapassam limites municipais** |

As opções evitam apresentar procura diretamente medida, localizar uma oferta
não observada ou sugerir correspondência entre trabalho e formação.

## 5. Visual de H1

População e matrícula continuam no mesmo módulo, mas em painéis distintos:

- população residente, em contagens próprias;
- matrículas, escolas e turmas por localização da escola, em painel separado;
- séries visualmente diferenciadas;
- unidades e períodos explícitos;
- nenhuma razão implícita;
- nenhum eixo compartilhado que sugira cobertura ou equivalência individual.

## 6. Vigência

Esta errata corrige somente os novos artefatos do Job 5E. Não reescreve nem
normaliza os Jobs 5B, 5C ou 5D, não altera fatos, fórmulas, fontes ou
metodologia e não autoriza compilador, interface ou publicação.
