SELECT
    t1.ano,
    t1.id_municipio,
    t1.municipio,
    t1.total_15_mais,
    t1.alfabetizadas_15_mais,
    t1.taxa_alfabetizacao_15_mais
FROM censo_populacao_alfabetizacao t1
WHERE t1.ano IN (2010, 2022)
  AND t1.sigla_uf = :uf;
