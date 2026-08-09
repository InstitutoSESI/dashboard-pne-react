SELECT
    t1.ano,
    t1.id_municipio,
    t1.municipio,
    t1.populacao_18_29_ensino_fundamental_concluido
FROM censo_populacao_ensino_fundamental_concluido_18_29 t1
WHERE t1.ano IN (2010, 2022)
  AND t1.sigla_uf = :uf;
