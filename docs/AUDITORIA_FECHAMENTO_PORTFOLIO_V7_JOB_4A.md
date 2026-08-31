# Auditoria de fechamento do portfólio V7 — Job 4A

## Premissas preservadas

H1 e H4 permanecem analiticamente aprovadas, sem alterar o C9 pendente. A1 e A2 permanecem retidas por redundância. H2, H3 e A3 são tratadas apenas como alternativas hipotéticas de aprovação/retenção para contagem; nenhum estado é modificado.

## Oito combinações

| H2 | H3 | A3 | Histórias únicas | Agendas únicas | Redundâncias | Requisitos não atendidos | Nova Santa Rita | PILOT_GATE_11_V7 |
|---|---|---|---|---|---|---|---|---|
| RETAIN | RETAIN | RETAIN | 2 | 0 | A1↔H1; A2↔H3 | faltam 2 história(s) na primeira direção; faltam 3 agenda(s) na segunda direção; trajetória H2 não aprovada; trabalho juvenil H3 não aprovado; A3 obrigatória/bloqueante não aprovada | sem H2, sem H3, sem A3 | BLOQUEADO |
| RETAIN | RETAIN | APPROVE | 2 | 1 | A1↔H1; A2↔H3 | faltam 2 história(s) na primeira direção; faltam 2 agenda(s) na segunda direção; trajetória H2 não aprovada; trabalho juvenil H3 não aprovado | sem H2, sem H3, A3 local | BLOQUEADO |
| RETAIN | APPROVE | RETAIN | 3 | 0 | A1↔H1; A2↔H3 | faltam 1 história(s) na primeira direção; faltam 3 agenda(s) na segunda direção; trajetória H2 não aprovada; A3 obrigatória/bloqueante não aprovada | sem H2, H3 local, sem A3 | BLOQUEADO |
| RETAIN | APPROVE | APPROVE | 3 | 1 | A1↔H1; A2↔H3 | faltam 1 história(s) na primeira direção; faltam 2 agenda(s) na segunda direção; trajetória H2 não aprovada | sem H2, H3 local, A3 local | BLOQUEADO |
| APPROVE | RETAIN | RETAIN | 3 | 0 | A1↔H1; A2↔H3 | faltam 1 história(s) na primeira direção; faltam 3 agenda(s) na segunda direção; trabalho juvenil H3 não aprovado; A3 obrigatória/bloqueante não aprovada | H2 local, sem H3, sem A3 | BLOQUEADO |
| APPROVE | RETAIN | APPROVE | 3 | 1 | A1↔H1; A2↔H3 | faltam 1 história(s) na primeira direção; faltam 2 agenda(s) na segunda direção; trabalho juvenil H3 não aprovado | H2 local, sem H3, A3 local | BLOQUEADO |
| APPROVE | APPROVE | RETAIN | 4 | 0 | A1↔H1; A2↔H3 | faltam 3 agenda(s) na segunda direção; A3 obrigatória/bloqueante não aprovada | H2 local, H3 local, sem A3 | BLOQUEADO |
| APPROVE | APPROVE | APPROVE | 4 | 1 | A1↔H1; A2↔H3 | faltam 2 agenda(s) na segunda direção | H2 local, H3 local, A3 local | BLOQUEADO |

Mesmo no melhor caso — aprovação externa de H2, H3 e A3 — o portfólio chega a **4 histórias únicas + 1 agenda única**, não `4+3`. Restaurar A1 ou A2 apenas para preencher quantidade violaria C11 e a regra de não redundância: A1 repete H1; A2 repete H3. O `PILOT_GATE_11_V7` permanece `BLOQUEADO` em todas as oito combinações, também porque C9, narrativa, interface, testes de release e validação humana ainda não foram concluídos.

## Efeito factual sobre Nova Santa Rita

- H2 acrescentaria abandono/distorção e condições escolares, mas os modelos atuais são de rede total e não contêm a série local da condição.
- H3 acrescentaria estoque/fluxo formal juvenil e trajetória do médio, sem ligação individual.
- A3 acrescentaria composição ocupacional/setorial e distribuição regional de cursos; o zero local não é conclusão.
- Sem uma das candidatas, o respectivo tema deixa de compor as três prioridades municipais elegíveis exigidas pelo Gate 11.

## Preflight factual de A4_MOBILIDADE_COORDENACAO

**Pergunta distinta.** Que decisões educacionais exigem coordenação entre municípios quando residentes estudam fora do município de residência? A pergunta parte de dependência intermunicipal observada, não de demografia/rede (H1), distribuição EJA (H4) ou ocupações/formação (A3).

**Fatos disponíveis.** A fotografia preliminar de 2022 cobre dez municípios e três universos. No Vale, 33.868 de 229.441 residentes estudantes estudavam fora do município (`14,7611%`); no fundamental, 7.507 de 107.060 (`7,0120%`); no médio, 5.812 de 38.516 (`15,0898%`). Em Nova Santa Rita: total 1.349 de 7.666 (`17,5972%`), fundamental 355 de 4.090 (`8,6797%`) e médio 220 de 1.151 (`19,1138%`). A participação estadual comparável do médio era `8,2202%`.

**Limite da ausência de destino.** A fonte não identifica município de destino, rota, corredor, escola receptora, capacidade ou motivo. A4 não pode nomear receptores, propor transporte específico nem combinar mecanicamente mobilidade com vagas/oferta.

**Possível `decision_delta`.** Delimitar etapa e municípios para monitoramento e pactuação intermunicipal, especialmente no médio, preservando que a decisão é coordenação geral e não desenho de fluxo origem–destino.

**Redundância.** A4 é factualmente distinta de H1/H4/A3 por público, lente e métrica. Há sobreposição na palavra “coordenação”, mas não na pergunta nem no fato principal. Ainda assim, sem destino, o delta operacional pode permanecer genérico; C11 precisa ser testado em laboratório próprio.

**Suficiência para laboratório futuro.** Os fatos existentes são suficientes para um futuro laboratório dirigido e pré-registrado de A4, com fotografia 2022, comparações municipal/regional/estadual e limites explícitos. Não são suficientes para aprovação, narrativa pública ou alteração do contrato. Mesmo que A4 fosse futuramente aprovada, o melhor portfólio iria de 4+1 para 4+2; ainda faltaria uma agenda não redundante.
