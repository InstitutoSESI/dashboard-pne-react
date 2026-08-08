WITH totais AS (
    SELECT
        ano,
        id_municipio::bigint AS id_municipio,
        SUM(pop_estimada) FILTER (WHERE idade >= 18) AS populacao_18_mais_total
    FROM populacao_idade
    WHERE ano IN (2010, 2022)
      AND sigla_uf = :uf
    GROUP BY ano, id_municipio
)
SELECT
    t1.ano,
    t1.id_municipio,
    t1.municipio,
    t1.populacao_18_mais_ensino_fundamental_concluido,
    t2.populacao_18_mais_total,
    100.0 * t1.populacao_18_mais_ensino_fundamental_concluido / NULLIF(t2.populacao_18_mais_total, 0) AS percentual_18_mais_ensino_fundamental_concluido
FROM censo_populacao_ensino_fundamental_concluido_18_mais t1
LEFT JOIN totais t2
    ON t2.ano = t1.ano
   AND t2.id_municipio = t1.id_municipio
WHERE t1.ano IN (2010, 2022);
