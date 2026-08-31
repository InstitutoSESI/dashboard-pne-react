# Lacunas reais — V7 Vocações × PNE após o Job 2

## Critério

Este registro separa ausência de evidência de zero observado e impede que o Job 3 transforme materializações analíticas em afirmações mais fortes que as fontes. As lacunas abaixo não bloquearam o Job 2, mas limitam interpretações e produtos futuros.

## Trajetória e condições

| Lacuna | Efeito | Tratamento atual |
|---|---|---|
| Componentes de água potável, biblioteca e quadra indisponíveis no recorte 2025 consumido | Não há taxa regional/estadual válida para essas condições | `null` e contagem municipal zero; nunca zero observado |
| Parte das métricas não possui numerador/denominador reconstituível | Não existe taxa regional agregada defensável | Distribuição municipal, sem média simples |
| Cobertura temporal varia entre tabelas | Comparações sincrônicas podem misturar anos | Período registrado por artefato e por linha |

## Trabalho jovem

| Lacuna | Efeito | Tratamento atual |
|---|---|---|
| CAGED e RAIS não identificam primeiro emprego de forma suficiente | Não é possível afirmar “primeira oportunidade” | Nenhuma claim de primeiro emprego materializada |
| Informalidade e desemprego estão fora das fontes | O painel descreve somente trabalho formal | Unidade e universo explicitados |
| 52 células CAGED hiperfinas têm ajuste negativo | Células muito desagregadas podem refletir correções superiores ao movimento original | Correções preservadas; agregados mensais validados sem admissões/desligamentos negativos |
| Dois arquivos opcionais `FOR` vazios | Ausência de ajuste tardio nesses meses não equivale a ausência de movimentos | Arquivos registrados no inventário; `MOV` presente |
| Tabela `estoque_emprego_faixa_etaria` é estruturalmente defeituosa | Estoques poderiam ser duplicados, conflitantes ou negativos | Fonte proibida por contrato e não usada |

## EJA

| Lacuna | Efeito | Tratamento atual |
|---|---|---|
| Público potencial é residente; matrícula é por escola | Razão não é taxa individual de atendimento | Lente `resident_population_vs_school_location` explícita |
| Público potencial disponível para 2022 | Não sustenta série anual de demanda–oferta | Artefato fixado em 2022 |
| Matrículas não medem capacidade, intenção ou pessoas únicas | Não há conclusão de suficiência | Métrica descritiva e caveat no schema |

## Ocupações e formação

| Lacuna | Efeito | Tratamento atual |
|---|---|---|
| Cinco cursos regionais de 2025, com 1.281 matrículas, não têm ponte | Cobertura curso–CBO é incompleta | Status `unmapped` e participações publicadas no artefato analítico |
| Ponte normativa não mede correspondência empírica | Não há inferência de aderência ou empregabilidade | Limite semântico obrigatório em todas as linhas de cobertura |
| Oferta é por escola e RAIS por trabalho | Não existe trajetória aluno–emprego | Lentes separadas; junção apenas contextual |
| Cursos detalhados disponíveis somente em 2023–2025 | Não há série longa de composição da oferta | Período explícito |

## Demografia, rede e mobilidade

| Lacuna | Efeito | Tratamento atual |
|---|---|---|
| Mobilidade 2022 não informa destino | Não é possível construir rede origem–destino | `destinationAvailable=false` |
| Mobilidade está classificada como preliminar | Resultados exigem cautela | Classe de evidência preservada |
| Cenário mecânico ignora migração, mortalidade, entrada e políticas | Não é previsão de matrícula | `scenarioIsForecast=false` e método explícito |
| Nascimentos terminam em 2024 | Não há observação completa de 2025/2026 | Último ano final registrado |
| População estimada e matrícula usam lentes distintas | Razões não são taxas de cobertura | Lentes preservadas em cada artefato |

## Prioridades antes de claims públicas

1. Só formular claims cujos requisitos de fonte, lente, período e status estejam atendidos no contrato V7.
2. Tratar os cinco cursos regionais não mapeados antes de qualquer leitura ampla de oferta–ocupação.
3. Não publicar “primeiro emprego”, “déficit de vagas”, “curso adequado” ou “previsão de demanda” sem novas fontes e contrato metodológico.
4. Manter água, biblioteca e quadra como indisponíveis até haver componentes oficiais válidos.
5. Submeter qualquer consumo do Job 3 ao manifesto do Job 2 e preservar `public/data` inalterado até autorização própria.
