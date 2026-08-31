# ARQUIVADO — protocolo não operacional

> Este documento registra uma alternativa metodológica abandonada em 31/08/2026.
> Ele não integra o contrato, a operação, a publicação nem os testes correntes de
> Cenários da Educação.

# Oficina de validação humana — Cenários da Educação

Este protocolo `1.1.0` operacionaliza a revisão dirigida F5 e a validação F6 sem
transformar presença em aprovação automática.
O bundle continua como piloto enquanto não existir um recibo canônico íntegro,
vinculado exatamente à versão revisada dos quatro cenários.

## 1. Objetivo e limite

A oficina verifica coerência, pluralidade, impactos distributivos, transferibilidade
dos mecanismos entre Nova Santa Rita e Novo Hamburgo, utilidade para decisão e
linguagem pública. Ela não atribui probabilidade aos cenários, não valida uma previsão
e não autoriza recomendação automática de curso, investimento ou redimensionamento
de rede.

O registro versionado é um resumo sanitizado. Lista nominal, contato, assinatura e
ata integral permanecem no repositório institucional apropriado; não entram no Git.

## 2. Representação mínima

Devem participar, com pelo menos uma representação de cada grupo:

- gestão educacional municipal;
- coordenação ou representação regional;
- profissionais das redes ou unidades educacionais;
- política social, comunidade ou público territorialmente exposto.

Além dos quatro grupos, o recibo exige ao menos uma representação capaz de revisar
o caso de Nova Santa Rita e uma capaz de revisar o caso de Novo Hamburgo. Essas são
contagens complementares às categorias institucionais: uma mesma pessoa pode
representar um grupo e um caso municipal, mas nenhuma contagem pode exceder o total
de participantes. Presença não autoriza marcar `contrastCaseReviewed`; essa marca só
é válida depois da deliberação dirigida sobre cada futuro.

O recibo registra apenas contagens. A autoridade da decisão e a referência da ata
devem ser explícitas, sem nomes ou dados pessoais.

## 3. Quatro módulos obrigatórios

### M1 — Forças e sinais

Verificar fontes, fatos observados, lacunas, sinais sentinela e a separação entre
residentes, matrículas, vínculos e registros administrativos. Registrar quais forças
foram confirmadas, contestadas ou ficaram sem evidência.

### M2 — Coerência, distribuição e vieses

Revisar os quatro futuros sem títulos e sem ordenação valorativa. Para cada cenário,
testar encadeamento causal, oportunidades, riscos, trade-offs, efeitos em públicos
distintos, riscos de estigma e a lente de Nova Santa Rita. Registrar concordâncias e
dissensos, inclusive quando não houver consenso.

### M3 — Contraste municipal e transferibilidade

Aplicar os mesmos quatro mecanismos, ainda cegos, aos pares de evidência de Nova
Santa Rita e Novo Hamburgo. Verificar se a direção continua plausível, se escala ou
papel regional muda a interpretação, quais efeitos distributivos aparecem e qual
evidência adicional poderia refutar a leitura. O teste não cria ranking, benchmark,
quinto cenário nem permite inferir fluxo de origem e destino ausente.

### M4 — Ações e gatilhos

Separar ações robustas, contingentes e experimentos reversíveis. Verificar autoridade,
dependências, risco de lock-in e evidência necessária antes de agir. Nenhuma ação é
promovida por votação isolada ou pela aparência de um cenário preferido.

## 4. Decisões permitidas

- `VALIDATED_FOR_PILOT_USE`: os quatro cenários foram aceitos como instrumento
  exploratório; condições e dissensos continuam registrados.
- `REVISIONS_REQUIRED`: ao menos um cenário, impacto ou ação precisa mudar. O gate
  bloqueia a promoção até nova versão e nova vinculação por hash.
- `REJECTED`: a arquitetura não deve ser apresentada como validada.

Um cenário marcado `REVISIONS_REQUIRED` ou `REJECTED` torna incompatível o resultado
`VALIDATED_FOR_PILOT_USE`.

## 5. Fluxo executável

1. Confirmar que o bundle a revisar está íntegro:

   ```powershell
   npm run check:cenarios-educacao
   ```

2. Gerar e conferir o caderno cego vinculado ao bundle corrente:

   ```powershell
   npm run generate:cenarios-educacao:workshop
   npm run check:cenarios-educacao:workshop
   ```

   O arquivo gerado fica em
   [`generated/CADERNO_CEGO_OFICINA_VALE_DO_SINOS.md`](generated/CADERNO_CEGO_OFICINA_VALE_DO_SINOS.md).
   Ele contém quatro cartões A–D sem títulos, IDs ou rótulos curtos; nenhuma caixa
   vem marcada. Se versão ou hash mudar, descarte cópias anteriores e gere novamente.

3. Gerar no terminal o modelo de recibo já vinculado aos hashes e às quatro
   assinaturas:

   ```powershell
   npm run prepare:cenarios-educacao:human-record
   ```

   O modelo nasce deliberadamente inválido: `HUMAN_VALIDATION_DRAFT`, participação
   zerada, módulos não concluídos e decisões pendentes. Isso obriga o registro de
   cada escolha e evita uma aprovação por valores predefinidos. O validador também
   recusa marcador de preenchimento restante, data impossível, campo extra e padrões
   evidentes de e-mail, CPF ou telefone.

4. Conduzir os quatro módulos com o caderno cego e preencher o recibo fora do caminho
   canônico durante a coleta. Não incluir nomes, e-mails, telefones, documentos ou
   assinaturas. O caderno registra insumos de facilitação, mas não substitui a ata nem
   o recibo sanitizado.

5. Validar o rascunho:

   ```powershell
   npm run validate:cenarios-educacao:human-record -- --record <caminho-do-recibo.json>
   ```

6. Somente após decisão autorizada, promover o recibo sanitizado para
   `data_pipeline/validation/vocacoes-pne-foresight/vale-do-sinos.json` e executar o
   gerador transacional. Se a versão dos cenários mudar, o recibo anterior deixa de
   conferir e a publicação falha fechada.

## 6. Critério de aceite institucional

O gate humano só está concluído quando:

1. os quatro módulos têm referência de evidência e síntese;
2. os quatro grupos mínimos estão representados;
3. Nova Santa Rita e Novo Hamburgo têm ao menos uma representação registrada;
4. cada cenário registra coerência, equilíbrio de valência, efeitos distributivos,
   implicações para Nova Santa Rita e revisão dirigida do caso contrastante;
5. `contrastCaseReviewed=true` só é registrado após o M3 para os quatro futuros;
6. concordâncias e dissensos estão preservados;
7. a decisão identifica autoridade, condições e referência da ata;
8. o recibo não contém dados pessoais;
9. contrato, versão de conteúdo e assinaturas conferem byte a byte;
10. o resultado é `VALIDATED_FOR_PILOT_USE` e nenhum cenário pede revisão.

Até que esses dez itens sejam verdadeiros, a interface deve permanecer com
`Validação humana pendente`.
