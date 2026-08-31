# Relatório AA0 — avanço analítico Vocações × PNE

**Objetivo:** congelar o estado real, preservar o lote existente e transformar o
plano recomendado em um programa verificável AA0–AA6.
**Classificação:** `DATA_LOGIC`, com alteração documental e infraestrutura de
preservação; nenhuma lógica analítica oficial foi alterada.
**Estado:** `AA0_CLOSED`; parecer Opus final `ON_TRACK`.

## 1. Fontes e evidências inspecionadas

- planos V3–V6, plano de aprofundamento, contrato do produto e decisão de promoção;
- Jobs 5J, 5I, 5K e 5L-final, incluindo matrizes, QA, manifestos e código;
- bundles oficiais locais e componentes da rota promovida;
- registros municipais e regionais canônicos do RS e estado do Git;
- artefatos locais do repositório de pesquisa, somente leitura.

Não houve nova fonte externa de dados, download ou consulta a banco. As duas únicas
chamadas externas foram as auditorias autorizadas do Opus. Cada pacote foi triado e
continha somente dois textos de plano/evidência; nenhuma credencial, `.env`, PII,
microdado ou arquivo alheio foi enviado. O backup local não foi enviado à Anthropic.

## 2. Resultado e gate

- programa AA0–AA6 com objetivo terminal, invariantes, classes de evidência, oito
  perguntas, entregáveis, comandos e limiares;
- baseline reproduzido: 103/103 testes JavaScript, 17/17 testes Python,
  `check:fast` e `git diff --check` aprovados;
- matriz de reaproveitamento P1–P8 e baseline de Nova Santa Rita para F1, RAIS e
  R1–R8;
- multiplicidade 33/30 reconciliada;
- manifesto de preservação por path, hashes de fallback e backup local somente
  leitura;
- primeiro parecer Opus `AT_RISK` integralmente reconciliado;
- segundo parecer Opus `ON_TRACK` (`0,60` de confiança); recomendações residuais de
  rastreabilidade também aplicadas.

Nenhum achado alto permanece aberto. O gate `AA0` está aprovado e `AA1` pode usar o
manifesto como baseline protegido.

## 3. Fórmulas, fontes e dados públicos

- Fórmulas preservadas: todas.
- Fórmulas alteradas: nenhuma.
- `public/data`: nenhuma alteração; digest antes/depois registrado pelo Job 5L-final:
  `4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1`.
- Fonte, ano, indicador, schema ou metodologia oficial: nenhuma alteração.
- RS/AL: isolamento preservado; nenhum arquivo da publicação AL foi alterado.

## 4. Arquivos do AA0

### Criados

- `docs/PLANO_EXECUCAO_AVANCO_ANALITICO_VOCACOES_PNE.md`;
- `docs/RELATORIO_AA0_AVANCO_ANALITICO_VOCACOES_PNE.md`;
- `docs/REVISAO_OPUS_AA0_AVANCO_ANALITICO_VOCACOES_PNE.md`;
- `scripts/checks/generate-vocacoes-pne-aa0-baseline.mjs`;
- `data_pipeline/manifests/vocacoes-pne-aa0-worktree-baseline.json`.

Nenhum path anterior foi alterado, removido ou movido pelo AA0. Temporários de
inspeção e pacotes Opus permanecem em `.tmp`, ignorados pelo Git.

## 5. Manifesto, allowlist e recuperação

Sem allowlist, `node scripts/checks/generate-vocacoes-pne-aa0-baseline.mjs --check`
recompõe o manifesto e exige igualdade byte a byte. Com `--allowlist`, somente os
paths exatos ou prefixos `/**` declarados para o estágio ficam mutáveis; entradas
anteriores fora da lista, novos paths inesperados, bundles oficiais, plano, `HEAD` e
upstream continuam protegidos. Os dois modos foram exercitados com código de saída
zero.

O baseline contém 243 entradas: 19 rastreadas e 224 não rastreadas. A recuperação
local contém 238 arquivos existentes copiados mais quatro artefatos de controle
(242 arquivos, todos somente leitura); cinco paths já deletados no lote anterior são
preservados no patch binário. Assim, 243 = 238 existentes + 5 deleções. O backup é
local, não autoritativo e não foi restaurado.

## 6. Hashes e contagens

- `HEAD`: `4b62e17ff83e811e6826dee6c268e6b2974c9824`;
- upstream: `d881436d6d17c91987e365e4de62036c1c0c560e`;
- divergência: 5 commits à frente, 0 atrás;
- digest das 243 entradas protegidas:
  `50a114ff0f94b36c7b4a1d9c8726cee42e487853d4c14ed1d7638350599a2082`;
- plano: 25.625 bytes, SHA-256
  `063e44ab88c763f8563b28a826c96a10585de8b92d9dc04b0b0cc04f1c465b71`;
- manifesto: 75.460 bytes, SHA-256
  `ae311d58100f25f3f500d7c7d4f2b41e7208773a027ea9a75d57004e00c4f9af`;
- o hash do plano dentro do manifesto é exatamente
  `063e44ab88c763f8563b28a826c96a10585de8b92d9dc04b0b0cc04f1c465b71`;
- verificador: 11.734 bytes, SHA-256
  `38018551cfb9cf7323b0f1c1fd047fa07529df65b8b3d4488d6a86cf6df03c6c`;
- digest conjunto dos cinco bundles oficiais:
  `89ce02fe2b11456d2f7d4c680ee7fc1ae2f0abfb03d3c39be2be726bf4c9d95e`;
- hashes individuais: `e32f524ff629e546a94b2db4af2d6bc3a15f4d63a189b209a127297cfb2d65a9`,
  `09c0f13c1143663b29f2f11040af0a098ef332f480d969da905588783d9eb152`,
  `5dae871eb80dead9ccbbe46eaaa7eb1c6ad06fd6dde31af5eaff4b640aeb99cf`,
  `7ec8061bfa8ec1de5b68bfe16a78691d3df441e600226f0b92454390616360f7` e
  `8f9515bf35283bb2622f823830dc1c5ff5cad4aa711158ce120edc07eab64f2c`;
- patch binário contra `origin/main`: 513.044 bytes, SHA-256
  `c82aef15a6a53575e94837eabedc3c52469333ee59e8daa2a8772d25f174a48a`.

## 7. Testes executados

| Comando | Resultado | Código de saída |
| --- | --- | --- |
| `npm run test:vocacoes-pne` | 103/103 | `0` |
| pytest focado Jobs 5J/5L-final | 17/17 | `0` |
| `npm run check:fast` | typecheck, lint, compiler check e build app-only aprovados | `0` |
| `git diff --check` | aprovado; apenas avisos LF/CRLF preexistentes | `0` |
| verificador AA0 em modo exato | 19/224 e cinco bundles preservados | `0` |
| verificador AA0 com allowlist de prova | 243 entradas guardadas; uma regra permitida | `0` |

## 8. Estado operacional

- Git: `main`; lote anterior continua sujo e preservado; nenhum commit, push, pull,
  stash, reset ou troca de branch.
- Banco: não usado.
- Rede de dados do projeto: não usada.
- Rede externa: somente duas auditorias Opus, explicitamente autorizadas.
- Build completo: não executado; `build:app` integrou `check:fast`. O build completo
  permanece reservado ao AA6 se houver validação de release autorizada.
- Publicação/deploy: não executados.
- Pendência do AA0: nenhuma. Próximo gate: painel estadual alinhado do AA1.
