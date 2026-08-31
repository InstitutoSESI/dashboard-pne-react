# Síntese de evidência H2 — Job 4A V7

## Escopo e regra de leitura

Esta síntese não altera `REVIEW_REQUIRED`, não seleciona relações por valor-p e não cria candidata. A matriz contém os 162 modelos efetivamente executados no grão `model_id × fator principal`; os 18 coeficientes de controle adicionais do Job 3 permanecem no artefato-fonte `models.csv.gz`. Todos os modelos H2 usam rede total e localização total sob a lente de localização da escola.

## Respostas às seis perguntas

1. **Relação específica com direção estável.** A relação mais claramente estável por sinal entre as sensibilidades executadas é `students_per_class × dropout_rate_percent` no ensino médio. O coeficiente principal é `0.3161519846625904` ponto percentual de abandono por aluno adicional por turma. O sinal é positivo na janela principal, na janela 2022–2025, após excluir 2020–2021, no lag 1, no diagnóstico sem efeitos fixos e nas dez retiradas de município do Vale. A escolha decorre da estabilidade direcional e da presença em sensibilidades, não do valor-p.

2. **Resultado, condição, etapa e rede.** Resultado: abandono; condição: alunos por turma; etapa: médio; rede: **total**. O Job 3 não estimou essa relação por rede municipal, estadual, privada ou federal; por isso não é possível nomear uma rede responsável a partir do modelo.

3. **Janelas, ponderações e sensibilidades.** Os coeficientes executados foram:

| Execução | Anos | Lag | Coeficiente | Sinal | p bruto | p BH | N |
|---|---|---|---|---|---|---|---|
| MAIN_2019_2025 | 2019-2025 | 0 | 0.316152 | positive | 7.27895e-16 | 1.20055e-14 | 3472 |
| WINDOW_2022_2025 | 2022-2025 | 0 | 0.280104 | positive | 5.06764e-07 | 2.85055e-06 | 1984 |
| EXCLUDE_2020_2021 | 2019;2022-2025 | 0 | 0.255639 | positive | 9.93956e-10 | 6.38972e-09 | 2480 |
| LAG_1 | 2020-2025 | 1 | 0.109375 | positive | 0.00849791 | 0.0179956 | 2976 |
| NO_FE_DIAGNOSTIC | 2019-2025 | 0 | 0.238560 | positive | 3.08112e-15 | 3.96144e-14 | 3472 |

As retiradas individuais dos dez municípios do Vale variam de `0.314896789932715` a `0.317122599711284`. Não houve sensibilidade ponderada para H2, nem modelo específico por rede, localização ou pequeno denominador. Logo, a relação permanece nas janelas e diagnósticos executados, mas **não foi verificada** nas ponderações e cortes de rede pré-registrados.

4. **Decisão além do indicador educacional.** A relação acrescenta uma condição concreta — alunos por turma — à investigação de abandono. Porém o modelo em rede total não permite atribuir monitoramento à rede estadual ou municipal, e o pacote municipal não contém a trajetória local de alunos por turma. O `decision_delta` comprovado continua sendo uma prioridade de investigação conjunta, não uma decisão operacional de rede.

5. **Nova Santa Rita.** O abandono no médio caiu de 4,7% para 3,2% entre 2018 e 2025 (`-1,5 pp`) e a distorção do médio caiu de 43,3% para 24,8% entre 2019 e 2025 (`-18,5 pp`). A relação estadual ajuda apenas a formular a pergunta sobre tamanho de turma; sem a série local da condição e sem rede específica, ela não interpreta factual ou causalmente a mudança municipal.

6. **Passagem integral dos critérios.** Nenhuma relação H2 demonstra simultaneamente estabilidade em todas as sensibilidades pré-registradas, diferenciação de rede, ponderação e fato local da condição. O pacote registra isso sem criar uma candidata “trajetória somente” fora do contrato.

## Limite factual

Os coeficientes são associações ecológicas intramunicipais. Um coeficiente positivo não significa que turmas maiores causaram abandono, nem identifica estudantes, escolas ou redes específicas. A matriz conserva p bruto e BH para auditoria, sem usá-los como critério automático.
