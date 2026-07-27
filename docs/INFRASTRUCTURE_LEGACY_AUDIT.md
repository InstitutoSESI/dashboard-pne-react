# Auditoria de compatibilidade da infraestrutura escolar

Referência: ETAPA INFRA-3.

## Fonte canônica já adotada

Os seis indicadores de infraestrutura de 2025, seus oito recortes, os cinco novos cards, o card de Internet e o Bloco C do relatório municipal consomem `school-infrastructure-v2`. O frontend apenas seleciona e formata os resultados materializados.

## Consumidores legados mantidos nesta etapa

- `src/features/education/components/EducationIndicatorDetailView.tsx`: usa `resumo_ultimo_ano`, `series`, `grupos`, `por_rede` e `por_localizacao` para os blocos históricos já existentes de ambiente escolar, conectividade e rede/dispositivos. Esses blocos aparecem depois do novo agrupamento canônico, como exigido pela INFRA-3.
- `src/features/education/educationViewModels.ts`: `buildInfrastructureMetricExplore` continua alimentando os recortes dos indicadores complementares legados de conectividade e equipamentos que não pertencem ao contrato dos seis indicadores.
- `src/features/education/educationViewModels.ts`: `buildRedeInfraExplore` e os campos exploratórios legados continuam disponíveis para compatibilidade do panorama existente.
- `src/utils/dataSourceNotes.js`, `src/utils/pneDisplayRules.js`, `src/pages/PneLegalGoalsPage.jsx`, `src/data/pne2026LegalGoalIndicatorMap.js`, `src/data/pne2026IndicatorGoalRefs.js`, `src/data/thematicGroups.js` e `src/data/diagnostic/indicatorCatalog.json`: mantêm `salas_climatizadas` e `salas_acessiveis`, indicadores PNE que não fazem parte do contrato canônico desta etapa.
- `src/data/educationIndicatorCatalog.js`: o `seriesPath` legado de `rede-infraestrutura` permanece como metadado de compatibilidade; o valor público de Internet em 2025 vem do contrato canônico.

## Candidatos para uma futura INFRA-4

Após criar contratos canônicos próprios para conectividade, equipamentos, climatização e acessibilidade, a INFRA-4 poderá:

1. substituir os acessos a `infraestrutura.resumo_ultimo_ano`, `infraestrutura.series`, `infraestrutura.grupos`, `infraestrutura.por_rede` e `infraestrutura.por_localizacao`;
2. remover `buildInfrastructureMetricExplore` e `buildRedeInfraExplore` quando nenhum indicador complementar depender deles;
3. remover o `seriesPath` legado de `rede-infraestrutura`;
4. retirar do documento municipal as propriedades legadas somente depois de uma nova busca de consumidores e de testes equivalentes de histórico e recortes.

Nenhuma dessas propriedades foi removida na INFRA-3.
