# Revisão Opus — AA0 avanço analítico Vocações × PNE

**Estágio auditado:** AA0 — auditoria, preservação e contrato
**Executor guardado:** `opus-verifier`
**Modelo:** Claude Opus 5
**Esforço:** máximo
**Primeiro veredito:** `AT_RISK`
**Confiança do primeiro parecer:** `0,68`
**Segundo veredito:** `ON_TRACK`
**Confiança do segundo parecer:** `0,60`
**Estado da reconciliação:** `FECHADA`; nenhum achado alto permanece aberto

## 1. Pacotes enviados

Em cada chamada foram enviados à Anthropic apenas dois arquivos temporários de texto.
O primeiro pacote totalizou 6.725 bytes. O segundo continha o plano corrigido
(24.856 bytes) e um resumo de evidências (4.680 bytes). Os quatro arquivos foram
triados antes do envio: nenhuma credencial, `.env`, banco, dado pessoal, microdado ou
conteúdo fora do escopo foi transmitido. O backup local e os arquivos do repositório
não foram enviados.

## 2. Achados reconciliados

| Achado do Opus | Decisão Codex | Verificação no repositório | Ajuste aplicado | Estado |
| --- | --- | --- | --- | --- |
| Gates AA1–AA6 não estavam suficientemente exibidos no pacote | aceito | o plano possuía gates substantivos, mas não fixava todos os paths, comandos e limiares, e o pacote os resumia demais | seção 5.1 passou a nomear artefatos, comandos e condições booleanas/numéricas por estágio | `RESOLVIDO` |
| Nova Santa Rita não tinha baseline explícito | aceito | F1 contém 12 linhas de `4313375`; RAIS, 1.130; Job 5J, 9 linhas cobrindo R1–R8 | seção 3.2.2 registra períodos, estados, lentes, zeros e limite de interpretação | `RESOLVIDO` |
| Working tree e fallback estavam protegidos apenas por contagens | aceito | havia 19 paths rastreados e 224 não rastreados anteriores ao programa, sem manifesto de conteúdo | criado manifesto com SHA-256 por path e hashes de cinco bundles; criado backup local recuperável fora do worktree | `RESOLVIDO` |
| 33 contrastes versus 30 p-valores não estavam explicados | aceito | os três sem p-valor são duas distâncias de variação total da EJA e o contexto PNATE pré-registrado como não regressável | seção 3.2.3 registra a regra e a torna precondição de AA2 | `RESOLVIDO` |
| Matriz não cobria todas as oito perguntas | parcialmente procedente | a matriz no plano já continha oito linhas, mas o pacote não a exibia e a evidência agregada não nomeava todas | matriz mantida com estado e lacuna explícitos para P1–P8; o segundo pacote expôs seu conteúdo | `RESOLVIDO` |
| Invariantes eram afirmadas, não ligadas a provas | aceito | a lista existia, mas faltava o vínculo um-para-um com verificadores | seção 2.1 associa cada invariante à prova/teste obrigatório | `RESOLVIDO` |
| Toolchain não estava congelada | aceito | versões foram coletadas depois da primeira auditoria | manifesto registra Node 24.16.0, npm 11.16.0, uv 0.10.5, Python 3.13.5 e Git 2.49.0.windows.1 | `RESOLVIDO` |
| Build completo não foi executado | aceito como diferimento, não como falha | AA0 é documental; pelas regras do repositório o build completo copia dados e pertence à validação de release | seção 5.1 fixa build app-only/E2E em AA5 e build completo somente em AA6, se a validação de release for autorizada | `RESOLVIDO_POR_ESCOPO` |
| Cinco commits não enviados e lote não rastreado careciam de recuperação | aceito sem criar commit/push | commit/push não foram autorizados; a cópia integral era pequena o suficiente | backup local contém 238 arquivos existentes e preserva também cinco deleções no patch binário, totalizando 243 entradas protegidas | `RESOLVIDO` |

Nenhum achado alto do primeiro parecer permanece aberto.

## 3. Evidência de preservação aplicada

- Manifesto: `data_pipeline/manifests/vocacoes-pne-aa0-worktree-baseline.json`.
- SHA-256 do conjunto de entradas protegidas:
  `50a114ff0f94b36c7b4a1d9c8726cee42e487853d4c14ed1d7638350599a2082`.
- Baseline protegido: 19 paths rastreados e 224 não rastreados.
- Digest dos cinco bundles do fallback:
  `89ce02fe2b11456d2f7d4c680ee7fc1ae2f0abfb03d3c39be2be726bf4c9d95e`.
- Backup local:
  `C:\Users\rnbirck\.codex\backups\PNE-REACT-aa0-20260830-50a114ff0f94`.
- Patch binário contra `origin/main`:
  SHA-256 `c82aef15a6a53575e94837eabedc3c52469333ee59e8daa2a8772d25f174a48a`.

As 243 entradas protegidas correspondem a 238 arquivos existentes copiados e cinco
paths rastreados já deletados no lote anterior, cuja condição está preservada no
patch binário. O backup é local, não autoritativo e somente leitura; serve apenas como
rota de recuperação. Nenhum restore automático, commit, push, stash, reset ou troca
de branch foi executado.

## 4. Segundo parecer e decisão para o gate

O segundo parecer classificou o AA0 como `ON_TRACK`. O Opus considerou que as
correções resolveram as lacunas substantivas e limitou as recomendações residuais a
rastreabilidade e atestação: ledger explícito de achados, reconciliação 243 = 238 + 5,
semântica do verificador/allowlist, hashes, códigos de saída e triagem do pacote.
Esses itens foram verificados e incorporados ao relatório AA0 e a este registro.

**Decisão:** `AA0_APROVADO`. As recomendações residuais do segundo parecer também
estão fechadas. AA1 pode ser aberto mantendo o manifesto AA0 como baseline protegido.
