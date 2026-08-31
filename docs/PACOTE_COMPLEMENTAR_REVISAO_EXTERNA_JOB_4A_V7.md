# Pacote complementar para revisão externa — Job 4A V7

## Natureza e escopo

Este pacote interno, compacto e versionável reúne evidência já executada para o julgamento externo final de `H2_TRAJETORIA_PERMANENCIA`, `H3_TRABALHO_JUVENIL_MEDIO` e `A3_OCUPACOES_FORMACAO`, além de auditar o fechamento do portfólio V7. Não aprova candidatas, não altera estados, contrato ou pré-registro, não escreve narrativa pública e não promove dados.

## Entregas

| Entrega | Conteúdo | Dimensão |
|---|---|---|
| [Matriz H2](MATRIZ_EVIDENCIA_H2_JOB_4A_V7.csv) | Uma linha por modelo H2 efetivamente testado, com coeficientes, sensibilidades e limites | 162 linhas × 31 colunas |
| [Síntese H2](SINTESE_EVIDENCIA_H2_JOB_4A_V7.md) | Respostas às seis perguntas de julgamento | documento |
| [Matriz H3](MATRIZ_EVIDENCIA_H3_JOB_4A_V7.csv) | Estoque RAIS separado do contexto de fluxo CAGED, faixas etárias e sensibilidades | 66 linhas × 41 colunas |
| [Síntese H3](SINTESE_EVIDENCIA_H3_JOB_4A_V7.md) | Respostas às seis perguntas de julgamento | documento |
| [Dossiê A3](DOSSIE_A3_OCUPACOES_FORMACAO_JOB_4A_V7.md) | Ocupações, CNAEs, cursos, eixos, municípios e caso de Nova Santa Rita | documento |
| [Matriz A3](MATRIZ_A3_OCUPACOES_FORMACAO_JOB_4A_V7.csv) | Correspondências normativas e cinco cursos não mapeados em linhas próprias | 56 linhas × 29 colunas |
| [Auditoria do pré-registro](AUDITORIA_PRE_REGISTRO_JOB_4A_V7.md) | Comparação literal entre pré-registro, executor e artefatos | documento |
| [Correções C9](CORRECOES_C9_POS_JOB_3_V7.md) | Quatro correções factuais, sem editar o Job 3 | documento |
| [Auditoria do portfólio](AUDITORIA_FECHAMENTO_PORTFOLIO_V7_JOB_4A.md) | Oito combinações H2/H3/A3 e preflight de A4 | documento |

## Fatos decisivos por candidata

### H2_TRAJETORIA_PERMANENCIA

- Relação específica mais estável nas execuções disponíveis: alunos por turma × abandono no ensino médio, rede total. Coeficiente principal `+0,3161519846625904 pp` de abandono por aluno adicional por turma.
- O sinal permanece positivo em 2022–2025, com exclusão de 2020–2021, lag 1, diagnóstico sem efeitos fixos e nas dez retiradas de municípios do Vale; o leave-one-out varia de `+0,314896789932715` a `+0,317122599711284`.
- Não foram executadas ponderação, diferenciação por rede, comparação de localização, tratamento de pequeno denominador nem todas as janelas pré-registradas. O pacote municipal também não contém a trajetória local de alunos por turma.
- O delta factual permanece uma prioridade de investigação conjunta, não uma decisão operacional de rede. Nenhuma relação passa integralmente pelos critérios solicitados.

### H3_TRABALHO_JUVENIL_MEDIO

- Padrão mais estável disponível: estoque RAIS 15–17 × distorção idade-série do ensino médio. O principal é `-1,1326770423912371 pp` por unidade de `log1p(vínculos)`; lag 1 preserva o sinal e lag 2 o inverte.
- O sinal negativo aparece no painel estadual, no Vale, com controle populacional, com ponderação populacional e após excluir 2020–2021. A magnitude `VALE_ONLY` é muito maior (`-5,530660`) em somente dez municípios e 70 observações.
- Em Nova Santa Rita, o estoque RAIS 15–17 passou de 104 para 172, enquanto abandono e distorção do médio caíram. Trata-se de coexistência agregada, sem ligação individual ou causal.
- A evidência sustenta monitoramento territorial conjunto. Não oferece rede, horário, setor do estoque RAIS ou ator operacional específico.

### A3_OCUPACOES_FORMACAO

- Entre os 14 subgrupos cobertos pela ponte, Escriturários cresceram `+5.931` vínculos, Técnicos das ciências físicas/químicas/engenharia `+1.871` e transformação de metais `+1.453`; têxtil/couro/vestuário/artes gráficas recuou `-2.905`. O Job 3 não definiu teste de persistência ano a ano.
- A ponte cobre 39 de 44 cursos e 12.664 de 13.945 matrículas de 2025. As 1.281 não mapeadas estão separadas: Informática 782, Curso Normal/Magistério 491 e oito matrículas nos três cursos/categorias restantes.
- Em Nova Santa Rita, os totais por CNAE fecham em 8.473 vínculos em 2019 e 11.591 em 2025. Caminhoneiro, auxiliar de logística, assistente administrativo, conferente de carga, transporte rodoviário, carga/descarga e comércio aparecem nominalmente; cursos relacionados estão distribuídos no restante do Vale.
- A leitura acrescenta composição e concentração territorial, mas não demonstra trajetória individual, suficiência de oferta, resultado laboral ou necessidade posterior. Cabe ao julgamento externo decidir se isso constitui delta de planejamento além do monitoramento.

## Divergências e lacunas do pré-registro

| Item | Situação documentada |
|---|---|
| H2 2018–2025 e 2019–2019 | `NOT_EXECUTED` |
| H2 rede, pesos, pequeno denominador e conjunto preferido | `NOT_EXECUTED` |
| H2 localização, com/sem INSE e leave-one-out | `DOCUMENTATION_GAP` |
| H3 2019–2019 e 2022–2025 | `NOT_EXECUTED` |
| H3 leave-one-out e contexto setorial/ocupacional do estoque RAIS | `DOCUMENTATION_GAP` |
| H3 CAGED descritivo | `EXECUTED_AS_PREREGISTERED`: o modelo interno era RAIS; nenhum coeficiente CAGED foi criado |
| Falhas de modelo | `model_failures.json` vazio; ausência de execução não foi registrada como falha |

As não execuções não foram convertidas retroativamente em inaplicabilidade. O pré-registro continua congelado.

## Pontos para julgamento pelo GPT-5.6 Pro

1. Se a estabilidade parcial de H2 compensa a ausência de ponderação, rede, série local da condição e partes do espaço pré-registrado.
2. Se H3 possui delta decisório suficiente quando o padrão inverte no lag 2, a sensibilidade regional tem amostra pequena e a recomendação permanece monitoramento conjunto.
3. Se a composição concreta e municipalizada de A3 é uma questão de planejamento suficiente, mesmo sem teste de persistência, fluxo individual ou medida de resultado laboral.
4. Se as divergências do pré-registro afetam a validade de cada candidata e não somente a documentação da execução.
5. Se as correções C9 são incorporadas antes de qualquer redação pública, sem transportar números entre janelas H1 nem agregar sentidos opostos de H4.

## Contagem real do portfólio e gate

Com os estados preservados do julgamento preliminar, H1 e H4 formam **2 histórias únicas** na primeira direção e não há agenda aprovada na segunda. A1 e A2 permanecem redundantes e não devem ser restauradas para preencher quantidade. No melhor cenário hipotético — aprovação de H2, H3 e A3 — o portfólio alcança **4 histórias únicas + 1 agenda única**, não `4+3`. O `PILOT_GATE_11_V7` permanece `BLOQUEADO` nas oito combinações possíveis.

## Preflight factual de A4_MOBILIDADE_COORDENACAO

A4 tem pergunta distinta e fatos suficientes para um futuro laboratório dirigido: em 2022, 33.868 de 229.441 residentes estudantes do Vale estudavam fora do município (`14,7611%`); no médio, 5.812 de 38.516 (`15,0898%`). Em Nova Santa Rita, eram 1.349 de 7.666 no total (`17,5972%`) e 220 de 1.151 no médio (`19,1138%`). A fonte não informa destino, rota, corredor, escola receptora, capacidade ou motivo; por isso A4 ainda não pode orientar fluxos específicos. Mesmo uma futura aprovação levaria o melhor cenário apenas a `4+2`.

## Integridade das fontes congeladas

| Conjunto | Verificação |
|---|---|
| Job 2 | 20/20 payloads conferidos por tamanho e SHA-256 contra o manifest |
| Manifest Job 2 | `28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85` |
| Execution state Job 2 | `fd01f128773367598a1b36d190439029a91af1757bce6c6807cd53ded1869425` |
| Job 3 | 17/17 payloads conferidos por tamanho e SHA-256 contra o manifest |
| Manifest Job 3 | `eb123990bd04a28e8fe4995f8d350e7573cf1a0a74a7cffb3f35d981bb4074ea` |

## Hashes das entregas

| Arquivo | Bytes | SHA-256 |
|---|---:|---|
| `MATRIZ_EVIDENCIA_H2_JOB_4A_V7.csv` | 167974 | `6a9c3bddf31e72ae5ddf8d6ed18ab7f57aa43767b13e0cf59691f41392c62c59` |
| `SINTESE_EVIDENCIA_H2_JOB_4A_V7.md` | 3843 | `62c1f1a334738d62eb720fe9daf44abed0eb8362f57b9070842aed84dcfc7d7a` |
| `MATRIZ_EVIDENCIA_H3_JOB_4A_V7.csv` | 131495 | `8396c84dd173124fb2553f512a5da0e1d9f3b0396901a3aacfd580bd1fc7632e` |
| `SINTESE_EVIDENCIA_H3_JOB_4A_V7.md` | 5289 | `264c8354c24202d253769dc8000ff40c1c151ddfda4d4364dbe93047ffb31b1c` |
| `DOSSIE_A3_OCUPACOES_FORMACAO_JOB_4A_V7.md` | 10017 | `de7ad8cd94ceed9c437b9832fb5beb3e3f151bebc6661fb8a7622f78c14f0560` |
| `MATRIZ_A3_OCUPACOES_FORMACAO_JOB_4A_V7.csv` | 66364 | `75bca0cfd5cf3cde9237525316a0a1a0cd9be840480d04620ae4f16b1b5a7ea5` |
| `AUDITORIA_PRE_REGISTRO_JOB_4A_V7.md` | 6070 | `df9d48b03412cf0491a232be4040f07d7f8093fd768c11707d237df7f2174047` |
| `CORRECOES_C9_POS_JOB_3_V7.md` | 1314 | `6061a3262002e080b2b718fddcd1c57f9916149aead18b63334568189a343820` |
| `AUDITORIA_FECHAMENTO_PORTFOLIO_V7_JOB_4A.md` | 5391 | `4f1005cc6808197fde4fa415194577308f6399b15926c68a5f0add4fd4d61d02` |

O SHA-256 deste próprio documento não é autoembutido, para evitar referência circular; deve ser registrado na entrega da execução.

## Próximo passo permitido

Submeter este pacote ao julgamento externo final pelo GPT-5.6 Pro. Até decisão explícita posterior, não iniciar Job 5, Job 6, A4, interface, narrativa pública ou alteração de contrato/estado.
