# Matriz de prioridades — orientação de construção

> **Nota de 2026-08-18:** a camada de causas descrita aqui foi substituída na
> interface pelas frentes recomendadas — ver `docs/MATRIZ_FRENTES_RECOMENDADAS.md`.
> O artefato publicado e as regras de severidade seguem válidos.
>
> **Atualização de 2026-08-19:** o contrato `matriz-3.0.0` acrescentou a mediana
> anônima dos pares por indicador, sem alterar a classificação de severidade.

> **Estado em 2026-08-24:** a deleção descrita aqui foi executada. O caderno não existe
> mais na plataforma. As menções abaixo descrevem o estado anterior à substituição e são
> mantidas como registro histórico da decisão.
>
> **Estado em 2026-08-30:** a coleção `matriz-4.0.0` cobre os 497 municípios
> canônicos do RS. O manifesto público reconcilia 497 arquivos, e a orientação
> editorial cobre as 21 metas prioritárias distintas com 42 caminhos. Nova Santa
> Rita permanece byte a byte igual ao artefato publicado anteriormente.

Documento de decisão e de orientação. Registra a substituição do **caderno de hipóteses**
pela **matriz de prioridades** como camada de apoio à decisão municipal do PNE 2026–2036,
e descreve como construí-la: eixos, regras de entrada, artefato, interface, exportação e
plano de deleção do caderno.

- Decisão tomada em 2026-08-18.
- Antecedentes: `docs/CADERNO_HIPOTESES.md` (estado vigente do caderno),
  `docs/CADERNO_BALANCO_E_ROTA.md` (balanço da revisão de seletividade),
  `docs/CADERNO_VALIDACAO_AMOSTRA.md` (validação em 14 municípios do RS).
  **Os três arquivos foram deletados em 2026-08-24 junto com o caderno; o conteúdo
  permanece recuperável no git (`git show 91f061e61:docs/CADERNO_HIPOTESES.md`).**
- Camada de pesquisa: `SESI\PNE` (repositório separado). A plataforma só recebe artefato
  publicado, como hoje.

---

## 1. Por que substituir o caderno

O caderno, mesmo após a curadoria (106 → 47 cartões), continua sendo **leitura**, não
**ferramenta de reunião**. Diagnóstico dos problemas observados no piloto:

1. Volume: até 7 cartões por objetivo × 17 objetivos, com sinais, cautelas e orientação
   federal por cartão. Ninguém percorre isso numa oficina.
2. Repetição: a mesma causa (transporte, pobreza, busca ativa) reaparece em vários
   objetivos com o mesmo texto, porque a unidade de tela é objetivo×causa.
3. Falta de hierarquia: a regra "não ranqueia" deixa o gestor com dezenas de cartas de
   mesmo peso visual. A pergunta dele — *por onde começo?* — fica sem resposta.
4. Causas genéricas: sem comparação com outros municípios, um sinal local não distingue
   "problema deste município" de "condição comum a todo o estado".

A matriz inverte a lógica: em vez de **listar tudo por meta**, ela **posiciona poucas
cartas por município** em dois eixos que respondem diretamente às perguntas da oficina:
*isso é grave aqui?* e *a prefeitura consegue agir?*

---

## 2. Regras metodológicas — o que muda e o que fica

### Regras revogadas (decisão de produto de 2026-08-18)

| regra do caderno | o que passa a valer na matriz |
|---|---|
| Não pontua e não ranqueia | A matriz **posiciona** cartas em quadrantes a partir de regras determinísticas publicadas no artefato. Posição não é nota nem ordem fina: dentro de um quadrante não há ordenação. |
| Não compara municípios | A severidade usa **comparação com grupo de pares** (municípios parecidos do mesmo estado). A página pode mostrar a mediana anônima do grupo, nunca ranking público, posição ordinal, lista de vizinhos ou valor individual de outro município. |

### Regras mantidas (invioláveis, seguem testadas em código)

1. **Não recalcula indicador.** Valor, meta, distância e veredito vêm do diagnóstico
   oficial publicado.
2. **Nenhum dado é solicitado às prefeituras.** Tudo vem de fontes públicas; o que só o
   município sabe entra pela oficina.
3. **Fail-closed.** Vocabulário fechado em todo campo classificatório; valor fora do
   vocabulário interrompe a geração. Manifesto com hash; documento divergente é recusado.
4. **A seleção do gestor vive no navegador** e só sai na exportação.
5. **Rastreabilidade completa**: toda posição de carta carrega a justificativa
   (`placementRationale`) com os valores e limiares que a produziram.

---

## 3. Os dois eixos

### Eixo Y — tamanho do problema (severidade)

Combina duas leituras, ambas calculadas na camada de pesquisa e publicadas prontas:

1. **Distância à meta** — do diagnóstico oficial, sem recálculo. Vocabulário publicado:
   `far_from_target` / `below_target` / `near_or_at_target`.
2. **Desvio frente ao grupo de pares** — novo cálculo. Para cada indicador-âncora da
   carta, a posição do município na distribuição do grupo de pares:
   `much_worse_than_peers` (abaixo do P25 do grupo, na direção ruim) /
   `worse_than_peers` (entre P25 e mediana) / `in_line_with_peers` / `better_than_peers`.

**Grupo de pares**: municípios do mesmo estado e da mesma faixa de porte
populacional (cortes do IBGE: até 5 mil, 5–20 mil, 20–100 mil, 100 mil+). O `n`
do `peerGroup` descreve a faixa-base e pode ser menor que 20. Para cada indicador,
a mediana exige pelo menos 20 observações elegíveis; quando necessário, o pipeline
expande para faixa adjacente e registra em `peerGroup.expansions` as faixas e o `n`
efetivamente usados. A definição completa é publicada no manifesto.

**Leitura numérica opcional**: o contrato v3 publica a mediana somente quando as
observações do indicador usam a mesma unidade e o mesmo ano do resultado municipal.
Publica também a diferença bruta `município − mediana`; arredondamento ocorre apenas
na apresentação. Se ano ou unidade não forem homogêneos, `peerBenchmark` é `null`.

**Severidade alta** exige as duas condições: longe da meta **e** pior que os pares.
Longe da meta mas em linha com os pares = severidade média (problema real, porém
estrutural da região — a carta diz isso explicitamente).

### Eixo X — poder de ação da prefeitura (governabilidade)

Já existe no artefato do caderno, campo `governability`, vocabulário fechado:
`municipal` / `shared` / `external`. A matriz usa como está:

- `municipal` → coluna direita (prefeitura resolve).
- `shared` → coluna esquerda (depende de articulação — estado, União, famílias).
- `external` → a carta **não entra na matriz**; vira linha do bloco "fora do alcance
  municipal", sem quadrante e sem botão de plano (mesma honestidade dos objetivos 15/16
  no caderno atual).

### Quadrantes

| | prefeitura resolve | depende de articulação |
|---|---|---|
| **severidade alta** | **Atacar agora** | **Cobrar parceiros** |
| **severidade média** | **Ganho rápido** | **Acompanhar e articular** |

Cartas de severidade baixa (perto da meta e em linha com pares) não viram carta: o
indicador aparece só no resumo "onde o município está bem".

---

## 4. Regras de entrada de uma carta

A unidade da matriz é a **causa curada** (catálogo pós-revisão de seletividade), não o
vínculo objetivo×causa. Deduplica na origem: **uma carta por causa por município**,
listando as metas que ela afeta.

Uma causa vira carta quando **todas** as condições valem:

1. Está vinculada a pelo menos um indicador com resultado oficial publicado e veredito
   abaixo da referência ou meta não atingida.
2. Tem pelo menos um **sinal local discriminante**: sinal público com
   `maxInference` melhor que `declared_existence_only` **e** desvio frente aos pares
   (`worse_than_peers` ou pior) no indicador-âncora ou no próprio sinal.
3. Passou a curadoria vigente (`hypothesis`; `context` e `excluded` não viram carta).
4. `governability` é `municipal` ou `shared`.

Consequências deliberadas:

- **Sinais fracos nunca posicionam carta.** Proxies de existência declarada
  (`declared_existence_only`) entram apenas como **pergunta de oficina** dentro da carta
  (reaproveitando `howToConfirmLocally`), nunca como prova.
- **Causa sem desvio frente aos pares não vira carta**, mesmo com indício adverso. Ela
  cai para o bloco recolhido "outras causas possíveis" da meta correspondente, uma linha
  por causa, sem sinais expandidos. É isso que elimina o genérico.
- Teto duro: **no máximo 10 cartas por município**. Se as regras produzirem mais, sobem
  as de maior severidade composta (regra determinística registrada no artefato); as
  demais caem para "outras causas possíveis". O teto existe porque a matriz é para uma
  reunião de 2 horas.

### Anatomia de uma carta

Cada carta publicada carrega, nesta ordem de tela:

1. Título concreto da causa (camada editorial já existente).
2. Quadrante + as duas leituras que o produziram, em linguagem simples
   ("longe da meta" · "bem acima das cidades parecidas").
3. Metas afetadas (chips com número e título curto do objetivo).
4. **Uma prova por carta**: o sinal local mais forte, com valor, período e cautela.
5. **Um primeiro passo**: a primeira verificação local de `howToConfirmLocally` ou o
   instrumento federal aplicável (Fase 3 do balanço — PAR, PNATE, Pacto EJA etc.).
6. Botão *Adicionar ao plano* (mesmo armazenamento local de frentes de hoje).
7. Recolhidos: demais sinais, perguntas de oficina, orientação federal.

---

## 5. Artefato publicado

Novo artefato por município, gerado na camada de pesquisa (`SESI\PNE`) e publicado pelo
gerador da plataforma com validação de schema e hash, no mesmo padrão do caderno:

```
public/data/pne2026-matriz/
  manifest.json                  ← hashes, versão de contrato, definição do grupo de pares
  municipios/<ibge7>.json
```

Recorte do documento municipal vigente:

```jsonc
{
  "schemaVersion": "matriz-4.0.0",
  "municipality": { "ibge7": "4313375", "name": "…", "uf": "RS" },
  "referenceDate": "2026-08-14",
  "peerGroup": {
    "criteria": "uf+pop_band",
    "band": "20k_100k",
    "n": 88,
    "populationPeriod": "2025",
    "releaseId": "…",
    "expansions": []
  },
  "priorityGoals": [
    {
      "goalId": "1.a",
      "indicatorId": "creche",
      "valueRaw": "35.097668557025834",
      "unit": "percent",
      "year": "2025",
      "severity": {
        "distanceToTarget": "far_from_target",
        "peerDeviation": "much_worse_than_peers",
        "peerN": 88,
        "peerBenchmark": {
          "statistic": "median",
          "valueRaw": "50.93539509000826",
          "differenceRaw": "-15.837726532982423",
          "unit": "percent",
          "year": "2025",
          "n": 88
        },
        "placementRationale": "…"
      },
      "causes": ["…"]
    }
  ]
}
```

Regras de publicação:

- Nenhum município do grupo é identificado. A única síntese numérica entre pares
  permitida é a mediana anônima comparável, acompanhada de unidade, ano e `n`;
  quartis detalhados, ranking e posição ordinal continuam proibidos.
- O quadrante vem calculado da pesquisa. A plataforma **nunca** deriva posição — só
  renderiza. Mesmo princípio do veredito oficial no caderno.
- O gerador da plataforma valida vocabulários fechados, teto de cartas, presença de
  `placementRationale` em toda carta e consistência quadrante×severidade×governabilidade.

### Coleção estadual materializada

O pré-requisito foi concluído em 2026-08-30. A camada de pesquisa percorre uma
única vez as fontes normalizadas, calcula as distribuições por faixa, gera as 497
matrizes em staging, valida 995 arquivos e só então promove a coleção completa.
A plataforma repete a validação contra o registro municipal e o contrato canônico;
o `manifest.json` é promovido por último como marcador de commit do lote.

Publicação controlada a partir da coleção já validada, sem rede nem banco:

```powershell
npm run generate:pne-matriz:collection -- --collection <diretorio-da-colecao-rs>
```

---

## 6. Interface

Uma página nova (`#matriz`, substituindo `#caderno` na navegação), três blocos:

1. **Cabeçalho + resumo** — município, data, frase de propósito, e o resumo em uma linha:
   *N cartas · N no plano · onde o município está bem (recolhido)*.
2. **A matriz** — grade 2×2 com as cartas nos quadrantes, cada carta com título, leitura
   de severidade e chips de metas. Clique abre o detalhe (anatomia da seção 4). No
   celular, a grade vira lista agrupada por quadrante, na ordem: atacar agora → cobrar
   parceiros → ganho rápido → acompanhar.
3. **Blocos de honestidade** — "fora do alcance municipal", "outras causas possíveis" e
   "onde o município está bem", todos recolhidos por padrão.

Reaproveitar da plataforma atual (mover, não reescrever):

| peça atual | destino |
|---|---|
| `cadernoDecisionWorkbook.ts` / `cadernoDecisionXlsx.ts` | exportação da matriz — mesmas 26 colunas; `public_deliberation_class_at_decision` passa a registrar o quadrante vigente na data |
| `cadernoFederalGuidance.ts` + `pne2026FederalGuidance.js` | seção recolhida da carta |
| `cadernoPlainLanguage.ts` (títulos por fator) | título das cartas |
| `cadernoFrontsStorage.ts` | seleção de cartas para o plano (renomear domínio) |
| `pne2026CadernoLoader.js` (padrão fail-closed, cache, hash) | novo loader da matriz, mesmo desenho |
| roteiro de oficina (Fase 4 do balanço) | passa a ser por quadrante, não por objetivo |

---

## 7. Plano de migração e deleção

Fases pequenas, cada uma com a suíte verde antes da seguinte:

1. **Contrato e piloto na pesquisa** — fechar o schema `matriz-1.0.0` no repositório
   `SESI\PNE`, calcular a distribuição de pares do RS, gerar o artefato de Nova Santa
   Rita. Validar à mão contra o caderno atual: toda carta da matriz precisa ser
   explicável por dados que o caderno já mostrava.
2. **Publicação na plataforma** — gerador (`scripts/generate-pne-matriz.mjs`, derivado do
   `generate-pne-caderno.mjs`), loader, hook (`useMunicipioMatriz`), testes de loader
   espelhando os do caderno (hash, cache, fail-closed, vocabulários).
3. **Página nova** — `#matriz` atrás de rota, com exportação e orientação federal já
   portadas. Caderno continua no ar; validar a matriz com os mesmos 14 municípios da
   amostra de 2026-08-17.
4. **Troca e deleção** — *(concluída em 2026-08-24: o caderno foi removido da plataforma;
   `resolveSignalReading` foi portado para `src/features/matriz/matrizSignalLanguage.ts`.)*
   navegação aponta para `#matriz`; deletar `src/features/caderno/`,
   `src/hooks/useMunicipioCaderno.ts`, `src/styles/caderno-page.css`,
   `public/data/pne2026-caderno/`, `scripts/generate-pne-caderno.mjs` e os checks
   `caderno-*.test.mjs` / `pne2026-caderno-loader.test.mjs` (substituídos pelos da
   matriz). Atualizar `appRoutes.ts`, `AppPageRouter.tsx` e os checks de arquitetura.
   O que for reaproveitado (seção 6) move para `src/features/matriz/` **antes** da
   deleção, na fase 3.
5. **Documentação** — este arquivo vira o documento vigente; `CADERNO_*.md` ganham nota
   de encerramento apontando para cá (manter como histórico, não deletar).

### Testes novos obrigatórios

- Consistência posição×insumos: para toda carta, o quadrante bate com
  severidade+governabilidade declaradas (a plataforma recusa artefato inconsistente).
- Teto de 10 cartas e deduplicação por fator.
- Nenhuma carta com prova de `maxInference = declared_existence_only`.
- Nenhum valor individual, nome, ranking ou posição ordinal de município par no artefato;
  a mediana anônima deve reconciliar unidade, ano, `n` e diferença aritmética.
- Manifesto sem definição de grupo de pares → recusa do documento.
- Linguagem: vocabulário de severidade nunca vaza cru para a tela (reaproveitar o padrão
  do check de linguagem de sinais).

---

## 8. Riscos assumidos

| risco | mitigação |
|---|---|
| Comparação com pares lida como ranking entre prefeituras | Grupo anônimo e apenas sua mediana; nada de lista, nome, valor individual ou posição ordinal |
| Quadrante lido como veredito de culpa | Texto fixo da página: a posição indica onde a ação municipal rende mais, não quem falhou |
| Distribuição de pares desatualiza em ritmo diferente do diagnóstico | Período da distribuição no manifesto; divergência de período além do tolerado → gerador recusa |
| Teto de 10 cartas esconde causa relevante | Bloco "outras causas possíveis" mantém tudo auditável e reversível pela curadoria |
