SELECT
    t1.ano,
    t2.municipio,
    SUM(t1.pop_estimada) AS pop_4_5
FROM populacao_idade t1
JOIN municipios t2 ON t1.id_municipio = t2.id_municipio
WHERE t1.idade >= 4 AND t1.idade <= 5
  AND t1.sigla_uf = :uf
GROUP BY t1.ano, t2.municipio;
