SELECT
    infra.ano,
    infra.id_municipio,
    municipios.municipio,
    infra.cod_escola,
    infra.situacao_funcionamento,
    infra.tp_dependencia,
    infra.tp_localizacao,
    infra.in_agua_potavel,
    infra.in_energia_inexistente,
    infra.in_internet,
    infra.in_biblioteca_sala_leitura,
    infra.in_quadra_esportes,
    infra.in_esgoto_rede_publica
FROM vw_educacao_infraestrutura_escolar_ativa infra
JOIN municipios
    ON municipios.id_municipio::text = infra.id_municipio::text
WHERE infra.ano = 2025
ORDER BY infra.id_municipio, infra.cod_escola;
