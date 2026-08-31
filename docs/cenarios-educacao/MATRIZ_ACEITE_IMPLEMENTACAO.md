# Matriz de aceite da implementação

| Requisito | Evidência no artefato | Gate automatizado |
| --- | --- | --- |
| Diagnóstico canônico fica em Vocações | diagnosticBridge com rota e IDs | teste de ponte e resolução |
| Nenhuma afirmação diagnóstica longa é repetida | duplicateCount igual a zero e whitelist vazia | comparação NFKC de strings com 80 ou mais caracteres |
| Não existe seção comparativa entre municípios | uma única lente municipal no bundle | assertor, página e busca de termos retirados |
| Quatro futuros têm peso equivalente | four scenarios e equalScenarioWeight verdadeiro | teste de contagem e política |
| Futuros são materialmente distintos | distância Hamming mínima 4 | reprodução independente das distâncias |
| Clima usa registros públicos com teto de inferência | 66 protocolos únicos, 10/10 | teste de deduplicação por município e S2ID |
| Tecnologia usa razão ponderada | 604/734 e 342/734 | recálculo sobre dez details.json |
| Fiscal não soma margens municipais | mínimo, mediana e máximo | recálculo sobre dez financeiro.json reconciliados |
| Regulação não usa proxy inadequado | eligiblePublicEvidenceCount igual a zero | teste da auditoria do proxy |
| Nova Santa Rita é a única lente publicada | código 4313375 | contrato, loader e página |
| PNE permanece normativo | sete metas e quatro avaliações | contrato do bundle e página |
| Dados são públicos e locais | 30 arquivos, networkDownloadUsed falso, databaseUsed falso | digest reproduzido e gate |
| Publicação é determinística | duas materializações idênticas | check de publicação |
| Pacote falha fechado | mutações estruturais e semânticas recusadas | testes de publicação e loader |
| Interface funciona em múltiplos meios | desktop, tablet, mobile e impressão | E2E |
| Revisão externa não vira aprovação | política consultiva explícita | teste de página e documentação |
