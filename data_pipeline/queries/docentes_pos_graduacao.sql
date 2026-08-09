SELECT
    dp.ano,
    m.municipio,
    'total' AS dependencia,
    dp.docentes_pos_graduacao,
    dp.total_docentes,
    dp.docentes_especializacao,
    dp.docentes_mestrado,
    dp.docentes_doutorado,
    dp.percentual_pos_graduacao
FROM docentes_pos_graduacao dp
JOIN municipios m
    ON dp.id_municipio::text = m.id_municipio
WHERE dp.sigla_uf = :uf
ORDER BY
    dp.ano,
    m.municipio;
