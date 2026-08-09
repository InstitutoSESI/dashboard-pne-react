SELECT
    t1.ano,
    t1.id_municipio,
    t1.municipio,
    t1.populacao_15_17_ensino_medio_ou_basica_completa,
    t1.populacao_15_17_total,
    t1.percentual_15_17_ensino_medio_ou_basica_completa
FROM censo_populacao_ensino_medio_15_17 t1
WHERE t1.ano IN (2010, 2022)
  AND t1.sigla_uf = :uf;
