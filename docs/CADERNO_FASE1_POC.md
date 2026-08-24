# Caderno de hipóteses — prova de conceito da Fase 1 "onde isso aparece" (2026-08-17)

Registro da prova de conceito que valida a viabilidade da Fase 1 da rota
(`docs/CADERNO_BALANCO_E_ROTA.md`): descer os sinais do caderno ao grão **escola**,
começando pelas metas 7 (conectividade), 8 (climatização) e 19 (acessibilidade).
QA interno em área de rascunho; nada publicado foi alterado.

## O que a prova fez

- Leu o microdado bruto do Censo Escolar 2025 (`Tabela_Escola_2025_V2.csv`, uma linha
  por escola, 290 colunas) direto do zip do acervo da pesquisa, em streaming.
- Extraiu as escolas **em atividade** dos mesmos 14 municípios da validação da
  curadoria (`docs/CADERNO_VALIDACAO_AMOSTRA.md`): 2.222 escolas, zero campos
  desconhecidos nas colunas usadas.
- Materializou, por município, a enumeração factual em ordem alfabética, sem ranking:
  - **Meta 19** — escolas sem nenhuma sala acessível (nome, rede, localização, salas
    em uso);
  - **Meta 8** — escolas sem nenhuma sala climatizada;
  - **Meta 7** — escolas que declaram internet sem uso pedagógico.
- Construção mecânica delegada ao Codex (`gpt-5.6-sol/xhigh`) sob spec; execução e
  conferência da revisão. Script: `.tmp/caderno-fase1-poc/poc_onde_aparece.py`;
  saídas em `fase1-poc/` no scratchpad da sessão.

## Resultado decisivo: conciliação exata com o oficial

Para a meta 19, o percentual municipal derivado do grão escola
(100 × Σ salas acessíveis / Σ salas em uso) foi comparado ao indicador oficial
`salas_acessiveis` do release `fadcfff3…` em três recortes de rede.

**A variante "todas as redes" (incluindo privadas), escolas em atividade, reproduziu o
valor oficial com precisão total nos 14 municípios** — ex.: piloto 47,0833…%,
Porto Alegre 28,3185…%, Alegrete 33,4183…%. Recortes público-only e municipal-only
divergem sempre.

Consequências de desenho, agora fixadas por evidência e não por suposição:

1. O escopo do indicador oficial da meta 19 é **todas as redes em atividade** — o
   bloco "onde isso aparece" deve enumerar no mesmo escopo do número publicado, com a
   rede declarada em cada linha, ou o total do bloco contradiz a tela.
2. A cadeia escola → município fecha sem recálculo divergente: a camada por escola
   pode ser gerada pelo mesmo pipeline determinístico, com o municipal publicado
   como **gate de conciliação fail-closed** (se a soma das escolas não reproduzir o
   oficial, o builder para).

## Amostra do produto (piloto, Nova Santa Rita)

- Meta 19: **11 de 28 escolas** sem nenhuma sala acessível (6 municipais, 3
  estaduais, 2 privadas — enumeradas nominalmente no rascunho).
- Meta 8: **2 de 28** sem nenhuma sala climatizada (as duas estaduais).
- Meta 7: **1 de 28** com internet sem uso pedagógico (municipal, rural).

É exatamente a diferença que a rota prometia: de "infraestrutura inadequada" para
"as 11 escolas sem sala acessível são estas, e 6 são da rede municipal".

## O que a Fase 1 completa ainda exige (fora desta prova)

- Decisão de schema (v3): bloco `whereItAppears` por hipótese no `caderno.json`, com
  vocabulário fechado, sem campo ordenável, e a conciliação selada no manifest.
- Extensão do adaptador do Censo Escolar na pesquisa para materializar o grão escola
  (hoje o normalizado agrega por município), com testes.
- Metas 3/4/5 (rendimento por etapa/escola) e 17 (adequação docente por disciplina)
  dependem de outras fontes e das regras de supressão de números pequenos — a regra
  "nunca substituir suprimido por zero" já está exercitada aqui (`unknown` conta em
  linha própria e nunca entra na lista afirmativa).
- UI: bloco recolhido no cartão de causa, enumeração alfabética, sem cor de gravidade.

## Reprodução

```
C:\Users\rnbirck\PROJETOS\SESI\PNE\data_pipeline\.venv\Scripts\python.exe ^
  .tmp\caderno-fase1-poc\poc_onde_aparece.py
```

Escreve somente no scratchpad da sessão (`fase1-poc\`): `escolas.csv`,
`conciliacao.csv` e `ONDE_APARECE.md`.
