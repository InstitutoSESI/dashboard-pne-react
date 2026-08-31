# Guia para o executor (GPT sol 5.6 max) — como chegar ao pedido da gestora

**Data:** 2026-08-30
**Público:** modelo executor do protocolo Vocações × PNE (gpt-5.6-sol max)
**Papel deste documento:** orientação de caminho. Ele **não** substitui o
`docs/CONTRATO_PRODUTO_VOCACOES_PNE.md` (contrato analítico V7, 2.0.0) nem o
`docs/arquivo/planos-vocacoes-regiao/PLANO_APROFUNDAMENTO_VOCACOES_PNE.md` — em conflito, o contrato vence.

---

## Atualização de execução — promoção oficial de 2026-08-30

O diagnóstico da seção 2 registra o ponto de partida e deve ser lido como
histórico. A solicitação explícita posterior promoveu para a página oficial
`Vocações da Região` uma leitura agregada observacional construída sobre os
bundles validados dos Jobs 5I e 5K.

O fechamento adotado não força as candidatas que falharam como relações
positivas. A página entrega 4 + 3 leituras centrais e, em Nova Santa Rita, três
conexões complementares. Em cada uma, separa: dados observados, razão substantiva
para a leitura conjunta, alcance efetivamente sustentado, questão de planejamento
e limite. Resultados sem padrão estável continuam visíveis somente como fronteira
útil para impedir atribuição indevida. O contrato executável da promoção está em
`src/features/vocacoes-regiao/generated/vocacoesPneOfficialPromotion.json` e a
decisão em `docs/DECISAO_PROMOCAO_OFICIAL_VOCACOES_PNE.md`.

Não houve nova coleta, acesso a banco nem escrita em `public/data`. O relatório
anterior do Vale do Sinos permanece como fallback local se a identidade, os
hashes ou a cobertura do pacote promovido não forem validados.

---

## 1. O pedido da gestora, em essência

A plataforma deve gerar **duas saídas** cruzando dados educacionais (PNE) com
dados territoriais (Vocações):

1. **PNE → Vocações — "O que o território ajuda a explicar sobre a educação?"**
   Parte de um resultado educacional observado (queda de matrículas, distorção,
   baixa conclusão, permanência) e busca no território fatores associados:
   população, migração de jovens, renda, emprego formal, setores econômicos,
   perfil etário, dinâmica do mercado de trabalho.
2. **Vocações → PNE — "O que o futuro do território exige da educação?"**
   Parte de tendências territoriais (setores que crescem/retraem, mudanças
   demográficas, novas ocupações, perfil de emprego e renda) e pergunta o que
   entra na agenda de planejamento educacional: ensino médio, EJA, educação
   profissional, aprendizagem, abandono/permanência.
3. **Camada transversal — comparação temporal.** Mostrar transformações que
   ocorreram simultaneamente ao longo de ~10–20 anos (demografia × matrículas;
   emprego/renda × permanência; setores × trajetórias formativas).

**Esclarecimento do Renan (importante):** não é obrigatório reproduzir
exatamente os pares que a gestora listou. O critério de sucesso é mostrar
**relações entre indicadores educacionais e indicadores econômicos, sociais e
demográficos** — com dados que sustentem a leitura. A gestora foi explícita em
um limite: a plataforma **não afirma causa**; aponta fatores associados e
hipóteses explicativas.

## 2. Por que ainda não respondemos (diagnóstico honesto)

O que está publicado hoje (piloto Vale do Sinos, contrato 1.5.0,
`src/features/vocacoes-regiao/generated/vocacoesPneValeDoSinos.json`):

- Direção 1: 3 cartões — **todos com núcleo demográfico** (matrículas ×
  população em idade escolar).
- Direção 2: 2 cartões — coortes e deslocamento para estudo. De novo,
  demografia e mobilidade.
- As outras 9 regiões caem no relatório legado, sem as duas saídas.

O resultado lê-se como "menos crianças → menos matrículas", que é quase
tautológico. **A única variável territorial em uso é a própria população.**
Nada de renda, emprego, setores, ocupações, EJA ou formação profissional chegou
à interface. Três causas:

1. os dados dessas frentes não estavam materializados quando o piloto publicou;
2. a metodologia é fail-closed: relação sem mecanismo, cobertura comprovada e
   aprovação humana não publica;
3. a matéria-prima nova (jobs V7 2–5l) já existe internamente, mas nenhuma
   candidata não demográfica foi calculada → julgada → aprovada. O Gate 11
   está **CLOSED** (`data_pipeline/contracts/vocacoes-pne-v7-job5l-final.json`)
   e o job 5M ainda não foi autorizado.

O contrato V7 já corrige o desequilíbrio por regra: 4 histórias + 3 agendas,
**no máximo uma história com núcleo demográfico**, ao menos duas úteis sem
demografia, e `A3` (ocupações × formação) é bloqueante para o Gate 11.

## 3. O que já temos de dados (inventário local)

Regra de ouro: **antes de coletar qualquer coisa, consulte
`C:\Users\rnbirck\projetos\dados\CATALOGO.md`.** Quase tudo já está no Postgres
local (`localhost:5432`). Nunca refazer coleta que já tem coletor no catálogo.
RAIS via BigQuery custa dinheiro — usar as tabelas locais.

### 3.1 Lado educação (Postgres `sesi` + pipeline do repo)

| Tema da gestora | Tabela/fonte local | Período típico |
|---|---|---|
| Matrículas por etapa/rede/faixa | `censo`, `censo_escolas`, `matriculas_faixa_etaria` | 2007–2025 |
| Permanência/abandono/reprovação | `rendimento_escolar` | 2018–2025 |
| Distorção idade-série | `distorcao_idade_serie` | 2019–2025 |
| Proficiência/IDEB | `saeb_ideb`, `saeb_proficiencia`, `saers` | série histórica |
| EJA | `eja_integrada_educacao_profissional`, estoque adulto sem conclusão (Censo 2022, materializado nos jobs V7) | 2014–2025 + foto 2022 |
| Educação profissional | `ept_nivel_medio` + ponte cursos×CBO (`dados/vocacoes-pne-course-cbo-rs-v1-projection.json`) | recente |
| Escolaridade da população | `censo_populacao_*`, `populacao_idade`, `grau_instrucao` (dim) | censos + estimativas |
| Financiamento (contexto) | `siope_fundeb_municipio_dashboard`, `fnde_pnate_municipio_dashboard`, `custo_aluno_etapa_rs` | anual |

### 3.2 Lado território (Postgres `cei` + aquisições V7)

| Tema da gestora | Tabela/fonte local | Período típico |
|---|---|---|
| Emprego formal (estoque) | `rais_vinculos`, `rais_vinculos_cnae`, `rais_vinculos_ocupacao`, `rais_vinculos_2025_sul` | ~2006–2025 |
| Renda do trabalho | `rais_renda`, `faixa_salarial` (dim) | idem |
| Trabalho juvenil | RAIS 15–17 e 18–24 materializada nos jobs V7 (2019–2025) | 2019–2025 |
| Setores que crescem/retraem | `caged_cnae`, `caged_cnae_ocup`, `estoque_emprego*`, `cnae` (dim) | mensal, ~2020–2025 |
| Ocupações/novas ocupações | `rais_vinculos_ocupacao`, `caged_cnae_ocup`, painel ocupacional CBO dos jobs 5g* | 2019–2025 |
| PIB e estrutura produtiva | `pib_mun_rs`, `pib_per_capita_rs`, `comexstat_mun` | ~2002–2022 |
| Demografia/perfil etário | `populacao*`, `populacao_idade`, censos 2010/2022 | 2000–2025 |
| Migração/mobilidade | Censo 2022 deslocamento para estudo/trabalho (job 5gd) | foto 2022 |
| Vulnerabilidade social | `cadastro_unico`, `novo_bolsa_familia` | mensal recente |
| Empresas/empreendedorismo | `cnpj`, `mei` | atual |

### 3.3 Matéria-prima já computada no repo (não publicada)

`src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iCore.json`
(bundle interno v2, contrato 2.0.0-internal-job5i): 187 fatos, 143 variantes,
124 distribuições, 355 evidências ocupacionais, 138 correspondências
curso×ocupação, 13 famílias, registro de fontes e de limites. **A maior parte
do trabalho de dados já está feita; falta transformar em candidatas julgadas e
narrativas publicáveis.**

## 4. As relações que podemos construir (e como)

Cada relação abaixo já tem dado local. A forma canônica de uma candidata:
**fato educacional + fato territorial + janela temporal comum + mecanismo
declarado + leitura associativa** ("ocorrem juntos", "coexistem nos mesmos
municípios"), nunca "X causou Y".

### Direção 1 — o território ajuda a compreender a educação

| Relação | Educação (sesi) | Território (cei/V7) | Leitura possível |
|---|---|---|---|
| **H2** Permanência × condições | `rendimento_escolar`, `distorcao_idade_serie` por rede/etapa | renda RAIS, CadÚnico, setores predominantes | onde abandono/distorção e vulnerabilidade se concentram juntos |
| **H3** Trabalho juvenil × ensino médio | matrícula/abandono EM 2019–2025 | RAIS 15–17/18–24 por setor e município | municípios onde emprego juvenil cresce enquanto a trajetória do EM piora/melhora — mesma agenda |
| **H4** EJA × escolaridade adulta | matrículas EJA localizadas | estoque adulto sem conclusão (Censo 2022) | a oferta está distribuída como o público? (fórmula já aprovada no contrato §7) |
| Renda × trajetória | conclusão/abandono por município | `rais_renda`, `pib_per_capita_rs` | gradiente territorial: trajetória escolar acompanha o nível de renda do território |

### Direção 2 — o futuro do território na agenda da educação

| Relação | Território (cei/V7) | Educação (sesi) | Agenda gerada |
|---|---|---|---|
| **A2** Mudanças no trabalho juvenil | Caged/RAIS juvenil, setores em expansão/retração | trajetória do EM, aprendizagem | o que a coordenação do EM precisa acompanhar |
| **A3** Ocupações × formação (bloqueante do Gate 11) | painel ocupacional CBO, tendências setoriais | `ept_nivel_medio` + ponte cursos×CBO | a oferta de EPT acompanha as ocupações que mudam? que eixos faltam? |
| Setores × trajetórias formativas | `caged_cnae`, `comexstat_mun`, `estoque_emprego` | matrícula EPT por eixo, EJA integrada | setores que crescem sem lastro formativo local |
| **A4** Mobilidade × coordenação | deslocamento para estudo 2022 | oferta de EM por município | decisões que exigem articulação regional (no limite da fotografia) |

### Camada temporal (o "terceiro pedido")

Não é uma saída separada: é **regra de composição dos cartões**. Todo cartão
mostra as duas séries lado a lado na janela comum (ex.: RAIS 2019–2025 ×
rendimento 2018–2025; população 2010–2025 × matrículas 2007–2025) e a frase
pública nomeia a simultaneidade ("no mesmo período em que X, Y"). As séries de
~10–20 anos existem: RAIS/PIB/população cobrem 2002–2025; educação, 2007–2025.

## 5. Regras inegociáveis ao gerar os insights

1. **Associação, não causa** — proibido "explica", "causou", "resultado de".
   Vocabulário permitido: "acompanha", "coexiste", "concentra-se nos mesmos
   municípios", "no mesmo período". A gestora pediu exatamente isso.
2. **Mecanismo antes da relação** — só cruzar pares com mecanismo plausível
   declarado (catálogo M1–M7). Correlação varrida em massa não entra.
3. **Lentes distintas** — população = moradores; matrícula = escolas
   localizadas; vínculo = estabelecimentos. Contraste de lentes não é junção
   de pessoas (os mesmos indivíduos nunca são identificados).
4. **Fail-closed** — candidata sem dado completo, sem cobertura dos 10
   municípios ou reprovada no julgamento é registrada internamente e omitida.
5. **Zero ≠ null ≠ suprimido ≠ não aplicável.**
6. **Nada de score sintético ou ranking.** Sem número futuro inventado; futuro
   = tendência sustentada observada (decisão formal §8 do contrato).
7. **Toda história fecha em decisão**: questão de planejamento + tema/meta PNE
   + responsabilidade institucional (taxonomia §6) + indicadores a acompanhar.

## 6. Caminho recomendado (ordem de execução)

1. **Destravar o julgamento das candidatas não demográficas.** O veredito do
   job 5l foi "analiticamente útil, mas não pronto para o 5M". Resolver as
   pendências apontadas nesse parecer é o passo zero.
2. **Job 5M (ou sucessor): calcular as candidatas do contrato** na ordem de
   impacto sobre o pedido da gestora:
   `A3` (bloqueante) → `H3` → `H2` → `H4` → `A2` → `A4`.
   `H1`/`A1` (demografia) já têm conteúdo publicado — consolidar, não expandir.
3. **Julgar cada candidata** contra o registro obrigatório (§4.3 do contrato):
   fatos, lente, mecanismo, estabilidade, leitura de Nova Santa Rita, limite
   máximo da afirmação. Reprovadas ficam registradas e fora da interface.
4. **Compor as narrativas** (4 histórias + 3 agendas, no máximo 1 demográfica
   na direção 1) com a camada temporal embutida em cada cartão e o bloco
   municipal dinâmico (§5 do contrato).
5. **Gate 11** — validação humana do piloto Vale do Sinos, incluindo a
   reconstrução de Nova Santa Rita (4313375).
6. **Publicar** a narrativa 2.x do Vale do Sinos e só então **replicar o
   compilador para as demais 9 regiões**, região a região, cada uma com seu
   próprio julgamento (a seleção do que aparece é regional, não copiada).

## 7. Critério de aceite final (como saber que respondemos a gestora)

Um leitor da página de uma região deve conseguir apontar, sem ajuda:

- ao menos **3 relações educação × economia/sociedade** (não demográficas) na
  direção 1, cada uma com os dois dados visíveis lado a lado no tempo;
- ao menos **2 agendas de futuro** derivadas de tendências territoriais
  sustentadas, cada uma nomeando temas PNE e responsabilidade;
- em cada cartão, a frase que responde à pergunta da gestora daquela direção
  ("o que do território ajuda a compreender isso?" / "o que isso coloca na
  agenda?") — em linguagem pública, com fontes e períodos declarados;
- nenhuma frase causal, nenhum score, nenhum número futuro inventado.

Se os cartões publicados continuarem majoritariamente demográficos, o pedido
**não** foi atendido — essa é a lacuna exata que este ciclo precisa fechar.
