SELECT
    t1.ano,
    t2.municipio,
    SUM(t1.mat_basico_15_17) AS mat_basico_15_17
FROM censo t1
JOIN municipios t2 ON t1.id_municipio = t2.id_municipio
WHERE t1.sigla_uf = :uf
GROUP BY t1.ano, t2.municipio;
