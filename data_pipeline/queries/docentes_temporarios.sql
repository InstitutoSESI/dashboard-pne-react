SELECT
    dt.ano,
    m.municipio,
    CASE
        WHEN LOWER(TRIM(dt.dependencia)) IN ('publica', 'pÃºblica') THEN 'publica'
        ELSE LOWER(TRIM(dt.dependencia))
    END AS dependencia,
    dt.docentes_temporarios,
    dt.total_docentes,
    dt.percentual_temporarios
FROM docentes_temporarios dt
JOIN municipios m
    ON dt.id_municipio::text = m.id_municipio
WHERE LOWER(TRIM(dt.dependencia)) IN (
    'publica',
    'pÃºblica',
    'federal',
    'estadual',
    'municipal'
)
  AND dt.sigla_uf = :uf
ORDER BY
    dt.ano,
    m.municipio,
    dependencia;
