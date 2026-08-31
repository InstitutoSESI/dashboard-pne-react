# Decisão de promoção oficial — Vocações × PNE

**Data:** 2026-08-30

**Escopo:** Rio Grande do Sul · Vale do Sinos · 10 municípios

**Validação municipal principal:** Nova Santa Rita (`4313375`)

**Rota:** `#vocacoes-da-regiao`

**Classificação da implementação:** `DATA_LOGIC`, com impacto em
`DATA_PRESENTATION`

## 1. Decisão

A leitura construída para a gestora passa a ser a experiência oficial de
`Vocações da Região` no Vale do Sinos. O conteúdo deixa de ser um painel de
indicadores isolados e organiza os dados em duas direções:

1. educação → território: o que o contexto territorial ajuda a compreender no
   diagnóstico educacional;
2. território → educação: o que as mudanças do território colocam na agenda do
   planejamento educacional.

O relatório anterior continua disponível no código como rollback automático.
As demais regiões continuam na experiência já publicada porque a promoção está
fechada pela identidade do Vale do Sinos e pelos hashes dos bundles de origem.

## 2. O que sustenta a versão promovida

| Camada | Conteúdo público | Estado da evidência |
|---|---|---|
| Coortes × matrículas/oferta | leitura central nas duas direções | contraste estrutural observado; não reduz matrícula à demografia |
| Trajetória × mobilidade/oferta | leitura central | contexto territorial; padrão de mobilidade não se mostrou estável como explicação de trajetória |
| Trabalho juvenil × ensino médio/aprendizagem | leitura central nas duas direções | mudança territorial relevante; efeito escolar não demonstrado nos testes de robustez |
| Escolaridade adulta × EJA | leitura central | desencontro territorial entre moradores e oferta localizada |
| Ocupações/setores × EPT | agenda central | desencontro territorial; ponte normativa curso–ocupação, sem recomendar curso automaticamente |
| Contexto socioeconômico × trajetória | conexão complementar | diferenças entre municípios qualificam o diagnóstico; evolução longitudinal limitada |
| Ruralidade × oferta/transporte | conexão complementar | sinal descritivo de planejamento; não mede residência nem rota do estudante |
| Educação especial × AEE | conexão complementar | movimentos paralelos; não mede atendimento individual nem cobertura |

As relações centrais somam quatro histórias na primeira direção e três agendas
na segunda. Nova Santa Rita mostra também as três conexões complementares. A
visão regional mostra somente as conexões com medida regional válida.

## 3. Limite das conclusões

Os dados usados são municipais ou regionais e vêm de lentes diferentes:
moradores, matrículas e escolas localizadas, locais de trabalho, oferta de EPT e
execução administrativa. Não existe ligação das mesmas pessoas entre as bases e
não há desenho capaz de identificar causa.

Por isso a página pode:

- mostrar contrastes estruturais e mudanças ocorridas no mesmo período;
- apresentar relações territoriais testadas, inclusive quando o padrão não foi
  estável;
- explicar o mecanismo plausível que torna o cruzamento útil;
- formular perguntas, responsabilidades e indicadores para planejamento.

A página não pode:

- afirmar que trabalho, renda, mobilidade ou demografia causaram um resultado
  escolar;
- converter associação municipal em trajetória individual;
- criar previsão numérica municipal;
- recomendar abertura ou fechamento de curso automaticamente.

## 4. Contrato técnico e rollback

O arquivo
`src/features/vocacoes-regiao/generated/vocacoesPneOfficialPromotion.json`
fecha estado, região, quantidade de municípios, versão do relatório anterior,
política de evidência e SHA-256 dos três bundles usados. A nova superfície só é
ativada quando o documento regional carregado corresponde exatamente a esse
contrato.

Se a carga ou validação falhar, `VocacoesRegiaoPage` renderiza
`VocacoesResolvedReport`, preservando a experiência anterior. A promoção não
edita `public/data`: os bundles analíticos são artefatos versionados do frontend.

## 5. Relação com os Jobs 5J–5L

Os contratos históricos não são reescritos. O Gate 11 fechado continua valendo
para a publicação automatizada prevista como Job 5M e para capacidades ainda
ausentes, como ligação pessoa a pessoa. A decisão atual é uma autorização
separada e explícita para uma superfície agregada observacional, com resultados
negativos transformados em limites visíveis — nunca em relações positivas.
