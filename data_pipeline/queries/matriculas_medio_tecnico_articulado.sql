WITH censo_por_municipio AS (
    SELECT
        ano,
        id_municipio::text AS id_municipio,
        SUM(mat_medio) AS mat_medio
    FROM censo
    WHERE sigla_uf = :uf
    GROUP BY ano, id_municipio
),
ept_por_municipio AS (
    SELECT
        ano,
        id_municipio::text AS id_municipio,
        SUM(mat_integrado_total) AS mat_integrado_total,
        SUM(mat_concomitante_total) AS mat_concomitante_total,
        SUM(mat_integrado_federal) AS mat_integrado_federal,
        SUM(mat_integrado_estadual) AS mat_integrado_estadual,
        SUM(mat_integrado_municipal) AS mat_integrado_municipal,
        SUM(mat_integrado_privada) AS mat_integrado_privada,
        SUM(mat_concomitante_federal) AS mat_concomitante_federal,
        SUM(mat_concomitante_estadual) AS mat_concomitante_estadual,
        SUM(mat_concomitante_municipal) AS mat_concomitante_municipal,
        SUM(mat_concomitante_privada) AS mat_concomitante_privada
    FROM ept_nivel_medio
    WHERE sigla_uf = :uf
    GROUP BY ano, id_municipio
)
SELECT
    c.ano,
    c.id_municipio,
    m.municipio,
    e.mat_integrado_total,
    e.mat_concomitante_total,
    CASE
        WHEN e.mat_integrado_total IS NULL OR e.mat_concomitante_total IS NULL THEN NULL
        ELSE e.mat_integrado_total + e.mat_concomitante_total
    END AS mat_articulado_total,
    c.mat_medio,
    e.mat_integrado_federal,
    e.mat_integrado_estadual,
    e.mat_integrado_municipal,
    e.mat_integrado_privada,
    e.mat_concomitante_federal,
    e.mat_concomitante_estadual,
    e.mat_concomitante_municipal,
    e.mat_concomitante_privada
FROM censo_por_municipio c
JOIN municipios m ON c.id_municipio = m.id_municipio::text
LEFT JOIN ept_por_municipio e
    ON e.ano = c.ano
    AND e.id_municipio = c.id_municipio;
