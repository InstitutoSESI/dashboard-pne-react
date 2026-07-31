SELECT
    t15.ano,
    t15.id_municipio::bigint AS id_municipio,
    t15.municipio,
    (
        t15.populacao_15_17_ensino_medio_ou_basica_completa
        + t18.populacao_18_mais_fundamental_concluido
    ) AS populacao_15_mais_ensino_fundamental_concluido,
    (
        t15.populacao_15_17_total
        + t18.populacao_18_mais_total
    ) AS populacao_15_mais_total,
    100.0 * (
        t15.populacao_15_17_ensino_medio_ou_basica_completa
        + t18.populacao_18_mais_fundamental_concluido
    ) / NULLIF(
        t15.populacao_15_17_total
        + t18.populacao_18_mais_total,
        0
    ) AS percentual_15_mais_ensino_fundamental_concluido
FROM pne2026_goal_11b_15_17_snapshot t15
JOIN pne2026_censo_10061_municipal_components t18
  ON t18.ano = t15.ano
 AND t18.id_municipio = t15.id_municipio
WHERE t15.ano = 2022
  AND t15.status_valor = 'available'
  AND t18.status_valor = 'available';
