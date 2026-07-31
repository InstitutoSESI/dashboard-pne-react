WITH observacoes_municipais AS (
    SELECT
        t1.ano,
        t1.id_municipio,
        t1.taxa_alfabetizacao,
        COUNT(*) OVER (
            PARTITION BY t1.ano, t1.id_municipio, LOWER(TRIM(t1.dependencia))
        ) AS quantidade_no_grao
    FROM alfabetizacao t1
    WHERE LOWER(TRIM(t1.dependencia)) = 'municipal'
)
SELECT
    fonte.ano,
    fonte.id_municipio::text AS id_municipio,
    municipio.municipio,
    'municipal' AS rede,
    'municipal' AS dependencia,
    fonte.taxa_alfabetizacao,
    'inep_avaliacao_alfabetizacao_crianca_alfabetizada' AS source_id,
    NULL::text AS arquivo_origem,
    NULL::date AS data_atualizacao
FROM observacoes_municipais fonte
JOIN municipios municipio
    ON fonte.id_municipio = municipio.id_municipio
WHERE fonte.quantidade_no_grao = 1;
