# Backlog consolidado — Vocações da Região (triagem V2)

Origem: Rodada 0 do `docs/PLANO_VOCACOES_REGIAO_V2.md` (§5, tarefa 4). Consolida
**100% dos itens B1–B45** nomeados nos relatórios das Rodadas 0–10 do V1
(`.tmp/vocacoes-regiao/rodada-*/RELATORIO_RODADA_*.md`, seções de Backlog).
Cada item recebe **um destino**: rodada deste plano, fechado no V1, descartado com
motivo, ou fora de escopo declarado.

Data: 2026-08-25.

## Legenda de destino
- **Rnn** — endereçado à Rodada nn do V2 (tarefa/aceite onde o item é tratado).
- **Fechado V1** — já resolvido em uma rodada do V1 (rodada indicada).
- **Coberto pelo protocolo** — resolvido pela mudança de processo (v3 §4.3), não é dívida de produto.
- **Descartado** — sem entregável afetado / limpeza de sistema; motivo declarado.
- **Fora de escopo declarado** — pertence a outra camada (pesquisa/metodologia) fora do V2; não será fechado por este plano.

## Tabela de triagem

| # | Item (resumo) | Estado no fim do V1 | Destino V2 | Justificativa |
|---|---|---|---|---|
| B1 | Sem série educacional no pacote, associações ficam sem `seriesKey` | resolvido em parte na R4 (matrículas) | **R2** (resíduo) | R4/V1 adicionou séries de estoque; o fluxo escolar (distorção, abandono) que falta é a lacuna L3 → adquirido na R2. |
| B2 | Dupla redação das limitações das séries herdadas da R2 | aberto (camada de pesquisa) | **R2** | R2 reacquire séries e estende o builder; a duplicação config×pacote se resolve ao consolidar as `limitations` na porta do builder. |
| B3 | Diretório sem permissão na área de staging da R3 | aberto, sem impacto na origem | **Descartado** | Resíduo de sandbox em `.tmp/` arquivado; limpeza de sistema, fora do plano. |
| B4 | Quatro construções causais de classe aberta passam pelas guardas | aberto e sem instrumento | **R4** | Família da guarda de linguagem; a guarda nova da R4 (corpus bilateral) declara este furo como conhecido no aceite. Ver B21/B36. |
| B5 | Falso positivo da guarda sobre negação com escopo de oração | **FECHADO na R5** | **Fechado V1 (R5)** | Verificação de escopo subiu para a guarda da plataforma. |
| B6 | Contrato guarda uma janela só por par temporal defasado | aberto (2.1.0 foi aditivo) | **R3** | R3 recura os pares temporais por região; a janela defasada entra ao reescrever o cardápio de pares. |
| B7 | Documento de origem do foresight municipal sumiu do disco (reprova test:foresight) | aberto (única reprovação herdada) | **R1** | D11 remove o produto municipal e suas 4 suítes; a reprovação desaparece com a remoção. |
| B8 | Performance da página (450+ KB, produto inteiro) não medida | agravado, não fechado | **R7** | Varredura final; medição/acessibilidade entram na entrega. Ver B44. |
| B9 | Contrato não varre texto livre atrás de ano futuro (camada de publicação) | parcialmente endereçado | **R4** | A fronteira "tema da meta × meta com número" da R4 e sua guarda nova cobrem o texto livre da ponte; furo geral declarado. |
| B10 | Falta a ponta do emprego formal municipal (trajetórias) | decidido (D1-c), não resolvido | **R5** | Camada municipal avalia reuso da pesquisa aposentada; se o insumo não existir, vira limitação declarada. |
| B11 | Dimensão «Instituições e dinâmica sociocultural» com zero série | confirmado e usado | **Fora de escopo declarado** | Ficha de cobertura da camada da metodologia; não é dado da plataforma. |
| B12 | Validador da metodologia sem estado «instanciado, não executado» | superado na R8 (camada) | **Fora de escopo declarado** | Proposta à camada da metodologia, fora do V2. |
| B13 | Séries de PIB param em 2021 (mistura instantes no contraste) | contornado e declarado | **R7** | Política de cadência/expiração da governança sinaliza a defasagem; nenhum V2 amplia a série de PIB. |
| B14 | Plugin de consulta reporta `running` para processo morto | aberto (defeito do plugin) | **Coberto pelo protocolo** | Rotina de vivacidade v3 §4.3 (vigia o log da task, relança job morto). Ver B23. |
| B15 | Atribuição de cada série à melhor dimensão sem instrumento | aberto (camada) | **Fora de escopo declarado** | Ficha de cobertura da metodologia. |
| B16 | Frase de trajetória descreve direção, não intensidade | parcialmente endereçado | **R7** | Revisão editorial (L9) trata legibilidade; a intensidade sem número é limitação por desenho, declarada. |
| B17 | Verificação `teto` aceita linha sem nível declarado | aberto (metodologia) | **Fora de escopo declarado** | Arquivo da camada da metodologia. |
| B18 | Linha `TE01` declara `validado` com limitações/lacunas | aberto (metodologia) | **Fora de escopo declarado** | Camada da metodologia. |
| B19 | Intercambialidade byte-idêntica não basta | **FECHADO na R8** | **Fechado V1 (R8)** | Virou mecanismo dos marcadores exclusivos, provado por teste cego. |
| B20 | Prosa pode afirmar direção sobre série não ancorada | **FECHADO na R8** | **Fechado V1 (R8)** | `probe --so prosa_ancorada` com injeção; virou regra do contrato na R9. |
| B21 | Causalidade em forma modal passa pelas listas do contrato | aberto e sem instrumento | **R4** | Mesma família de B4/B36; a guarda nova da R4 declara o furo conhecido. |
| B22 | Composição da alegação proibida com o abridor é obrigação da página | **FECHADO na R9** | **Fechado V1 (R9)** | `probe_r9 --so proibicao` + teste com injeções. |
| B23 | B14 reapareceu (duas ocorrências) | agravado | **Coberto pelo protocolo** | Idem B14 — vivacidade v3 §4.3. |
| B24 | Probes dependem de qual `python` resolve (jsonschema) | contornado, não resolvido | **R2** | R2 volta a rodar o validador de pesquisa; os scripts passam a declarar o interpretador exigido. |
| B25 | Classificação de pares cobre 8 de 69 | aberto (morfologia) | **R6** | Gate de transferibilidade revisita a caixa morfológica. |
| B26 | A caixa morfológica não elimina nada | aberto | **R6** | Nomeado no aceite do gate da R6 (resolver ou aceitar com registro). L8. |
| B27 | Teste cego discriminou por número, não por prosa | aberto (barato) | **R6** | R6 faz o teste cego com os números retirados dos textos. |
| B28 | Três critérios normativos sem série que os acompanhe | aberto | **R6** | Sinais de acompanhamento do normativo na expansão de cenários. |
| B29 | Menor distância morfológica é 2 de 5 fatores | aberto | **R6** | Revisto no gate de transferibilidade/morfologia da R6. |
| B30 | Hipótese do quadro docente (H03) sem estado na caixa | aberto | **R6** | Estado morfológico revisto na expansão. |
| B31 | Remoção de nome por string não confere descrição indireta | aberto | **R6** | Robustez do teste cego na expansão. |
| B32 | Esqueletos derrubados 6/6 e correções não reauditadas | aberto | **R6** | Reauditoria adversarial dos esqueletos na expansão (gate por lote). |
| B33 | Afirmação comparativa sem dígito não tem lastro conferível | pré-condição da expansão | **R6** | Guarda de prosa ancorada estendida à expansão de cenários. |
| B34 | Parser não recalcula `contentVersion` | aberto | **R4** | R4 mexe no contrato (2.3.0); a integridade do parser é revisitada na rodada de contrato (nota: WebCrypto recusado na R0/V1, `declared` mantido). |
| B35 | Verificação de nome de outra região só pega ≥2 palavras | pré-condição da expansão | **R6** | Agrava com 8 regiões novas de nome de palavra única; tratado na expansão. |
| B36 | Guarda de contradição de estatuto é lexical | risco central da expansão | **R6** | Mesma família de B4/B21; endereçado no gate narrativo da R6. |
| B37 | `MANIFESTO_ORIGEM.json` inventaria a área de trabalho da Fase B | aberto (camada) | **Fora de escopo declarado** | Decisão da camada de pesquisa. |
| B38 | R9 diz «24 itens», checklist tem 25 | defeito de prosa | **Descartado** | Relatório encerrado; sem entregável afetado. |
| B39 | Sem política de obsolescência | insumo de decisão | **R7** | Governança: cadência, responsável, regra de expiração (D13/L8). |
| B40 | Sem canal de contestação territorial | insumo de decisão | **R7** | Governança: canal de contestação (D13/L8). |
| B41 | Reificação do recorte regional | insumo de decisão | **R7** | Limitação declarada no documento de entrega à gestão. |
| B42 | Legitimidade do normativo sem participação | insumo de decisão | **R7** | Limitação declarada na entrega/governança (L8). |
| B43 | Descoberta fora da navegação (estatuto na página+metadados) | insumo de decisão | **R7** | Revisão editorial: estatuto na própria página e nos metadados. |
| B44 | Acessibilidade não medida | insumo de decisão | **R7** | Varredura final de entrega (com B8). |
| B45 | Coerência temporal entre produtos (anos-base) | insumo de decisão | **R7** | Sinalização de anos-base na entrega; a ponte PNE (R4) também relaciona produtos. |

## Contagem de cobertura

- Total de itens triados: **45** (B1–B45) — 100% dos nomeados no V1.
- Fechados no V1: B5, B19, B20, B22 (4).
- Cobertos pelo protocolo v3 §4.3: B14, B23 (2).
- Descartados com motivo: B3, B38 (2).
- Fora de escopo declarado: B11, B12, B15, B17, B18, B37 (6).
- Endereçados a rodadas do V2: **31**.
  - R1: B7
  - R2: B1, B2, B24
  - R3: B6
  - R4: B4, B9, B21, B34
  - R5: B10
  - R6: B25, B26, B27, B28, B29, B30, B31, B32, B33, B35, B36
  - R7: B8, B13, B16, B39, B40, B41, B42, B43, B44, B45
