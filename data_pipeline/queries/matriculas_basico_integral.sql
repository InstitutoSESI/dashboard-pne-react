SELECT
    t1.ano,
    t2.municipio,
    'publica' AS dependencia,
    SUM(t1.mat_basico) AS mat_basico,
    SUM(t1.mat_basico_integral) AS mat_basico_integral
FROM censo t1
JOIN municipios t2 ON t1.id_municipio = t2.id_municipio
WHERE t1.dependencia IN ('federal', 'estadual', 'municipal')
  AND t1.sigla_uf = :uf
GROUP BY t1.ano, t2.municipio;
