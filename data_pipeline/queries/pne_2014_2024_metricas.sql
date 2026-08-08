WITH municipios_base AS (
    SELECT
        id_municipio::text AS id_municipio,
        municipio
    FROM municipios
),
censo_total AS (
    SELECT
        c.ano,
        c.id_municipio::text AS id_municipio,
        SUM(COALESCE(c.mat_infantil_creche, 0)) AS mat_infantil_creche,
        SUM(COALESCE(c.mat_infantil_pre, 0)) AS mat_infantil_pre,
        SUM(COALESCE(c.mat_basico_6_10, 0) + COALESCE(c.mat_basico_11_14, 0) + COALESCE(c.mat_basico_15_17, 0)) AS mat_basico_6_17,
        SUM(COALESCE(c.mat_basico_15_17, 0)) AS mat_basico_15_17,
        SUM(COALESCE(c.mat_medio, 0)) AS mat_medio,
        SUM(COALESCE(c.mat_medio_ct, 0)) AS mat_profissional_tecnico,
        SUM(COALESCE(c.mat_fundamental_anos_iniciais, 0)) AS mat_fundamental_anos_iniciais,
        SUM(COALESCE(c.mat_fundamental_anos_finais, 0)) AS mat_fundamental_anos_finais
    FROM censo c
    GROUP BY 1, 2
),
censo_publica AS (
    SELECT
        c.ano,
        c.id_municipio::text AS id_municipio,
        SUM(COALESCE(c.mat_basico, 0)) AS mat_basico,
        SUM(COALESCE(c.mat_basico_integral, 0)) AS mat_basico_integral,
        SUM(COALESCE(c.mat_medio_ct, 0)) AS mat_profissional_tecnico
    FROM censo c
    WHERE c.dependencia IN ('federal', 'estadual', 'municipal')
    GROUP BY 1, 2
),
pop_0_3 AS (
    SELECT
        p.ano,
        p.id_municipio::text AS id_municipio,
        SUM(COALESCE(p.pop_estimada, 0)) AS pop_0_3
    FROM populacao_idade p
    WHERE p.idade <= 3
      AND p.sigla_uf = :uf
    GROUP BY 1, 2
),
pop_4_5 AS (
    SELECT
        p.ano,
        p.id_municipio::text AS id_municipio,
        SUM(COALESCE(p.pop_estimada, 0)) AS pop_4_5
    FROM populacao_idade p
    WHERE p.idade BETWEEN 4 AND 5
      AND p.sigla_uf = :uf
    GROUP BY 1, 2
),
pop_6_17 AS (
    SELECT
        p.ano,
        p.id_municipio::text AS id_municipio,
        SUM(COALESCE(p.pop_estimada, 0)) AS pop_6_17
    FROM populacao_idade p
    WHERE p.idade BETWEEN 6 AND 17
      AND p.sigla_uf = :uf
    GROUP BY 1, 2
),
pop_15_17 AS (
    SELECT
        p.ano,
        p.id_municipio::text AS id_municipio,
        SUM(COALESCE(p.pop_estimada, 0)) AS pop_15_17
    FROM populacao_idade p
    WHERE p.idade BETWEEN 15 AND 17
      AND p.sigla_uf = :uf
    GROUP BY 1, 2
),
creche AS (
    SELECT
        c.ano,
        m.municipio,
        'creche' AS indicador,
        100.0 * c.mat_infantil_creche::double precision / NULLIF(p.pop_0_3::double precision, 0) AS valor
    FROM censo_total c
    JOIN pop_0_3 p
      ON p.ano = c.ano
     AND p.id_municipio = c.id_municipio
    JOIN municipios_base m
      ON m.id_municipio = c.id_municipio
),
pre_escola AS (
    SELECT
        c.ano,
        m.municipio,
        'pre_escola' AS indicador,
        100.0 * c.mat_infantil_pre::double precision / NULLIF(p.pop_4_5::double precision, 0) AS valor
    FROM censo_total c
    JOIN pop_4_5 p
      ON p.ano = c.ano
     AND p.id_municipio = c.id_municipio
    JOIN municipios_base m
      ON m.id_municipio = c.id_municipio
),
basico_6_17 AS (
    SELECT
        c.ano,
        m.municipio,
        'basico_6_17' AS indicador,
        100.0 * c.mat_basico_6_17::double precision / NULLIF(p.pop_6_17::double precision, 0) AS valor
    FROM censo_total c
    JOIN pop_6_17 p
      ON p.ano = c.ano
     AND p.id_municipio = c.id_municipio
    JOIN municipios_base m
      ON m.id_municipio = c.id_municipio
),
basico_15_17 AS (
    SELECT
        c.ano,
        m.municipio,
        'basico_15_17' AS indicador,
        100.0 * c.mat_basico_15_17::double precision / NULLIF(p.pop_15_17::double precision, 0) AS valor
    FROM censo_total c
    JOIN pop_15_17 p
      ON p.ano = c.ano
     AND p.id_municipio = c.id_municipio
    JOIN municipios_base m
      ON m.id_municipio = c.id_municipio
),
basico_integral AS (
    SELECT
        c.ano,
        m.municipio,
        'basico_integral' AS indicador,
        100.0 * c.mat_basico_integral::double precision / NULLIF(c.mat_basico::double precision, 0) AS valor
    FROM censo_publica c
    JOIN municipios_base m
      ON m.id_municipio = c.id_municipio
),
escolas_integral AS (
    SELECT
        e.ano,
        e.municipio,
        'escolas_integral' AS indicador,
        e.perc_escolas_publicas_com_integral::double precision AS valor
    FROM (
        SELECT
            ce.ano,
            m.municipio,
            ROUND(
                COUNT(
                    DISTINCT CASE
                        WHEN ce.mat_basico >= 1
                         AND 100.0 * COALESCE(ce.mat_basico_integral, 0) / NULLIF(ce.mat_basico, 0) >= 25.0
                        THEN ce.cod_escola
                    END
                )
                * 100.0
                / NULLIF(COUNT(DISTINCT CASE WHEN ce.mat_basico >= 1 THEN ce.cod_escola END), 0),
                1
            ) AS perc_escolas_publicas_com_integral
        FROM censo_escolas ce
        JOIN municipios_base m
          ON m.id_municipio = ce.id_municipio::text
        WHERE ce.dependencia IN ('federal', 'estadual', 'municipal')
        GROUP BY 1, 2
    ) e
),
eja_integrada_educacao_profissional_percentual AS (
    SELECT
        e.ano,
        m.municipio,
        'eja_integrada_educacao_profissional_percentual' AS indicador,
        100.0 * (
            e.mat_eja_curso_tecnico_integrada
            + e.mat_eja_fic_integrado_fundamental
            + e.mat_eja_fic_integrado_medio
        ) / NULLIF(
            e.mat_eja_fundamental_total + e.mat_eja_medio_total,
            0
        )::double precision AS valor
    FROM eja_integrada_educacao_profissional e
    JOIN municipios_base m
      ON m.id_municipio = e.id_municipio::text
    WHERE e.ano BETWEEN 2014 AND 2024
),
medio_tecnico AS (
    SELECT
        e.ano,
        m.municipio,
        'medio_tecnico' AS indicador,
        e.mat_ept_nivel_medio_publica::double precision AS valor
    FROM ept_nivel_medio e
    JOIN municipios_base m
      ON m.id_municipio = e.id_municipio::text
    WHERE e.ano >= 2013
),
aee AS (
    SELECT
        a.ano,
        m.municipio,
        'aee' AS indicador,
        CASE
            WHEN COALESCE(a.total_turmas_educacao_especial, 0) = 0 THEN NULL
            ELSE 100.0 * a.quantidade_aee::double precision / a.total_turmas_educacao_especial::double precision
        END AS valor
    FROM atendimento_educacional_especializado a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
),
alfabetizacao AS (
    SELECT
        a.ano,
        m.municipio,
        'alfabetizacao' AS indicador,
        a.taxa_alfabetizacao::double precision AS valor
    FROM alfabetizacao a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    WHERE a.ano <= 2024
      AND LOWER(TRIM(a.dependencia)) = 'municipal'
      AND (
          SELECT COUNT(*)
          FROM alfabetizacao duplicada
          WHERE duplicada.ano = a.ano
            AND duplicada.id_municipio::text = a.id_municipio::text
            AND LOWER(TRIM(duplicada.dependencia)) = 'municipal'
      ) = 1
),
alfabetizacao_pop_15_mais AS (
    SELECT
        a.ano,
        m.municipio,
        'alfabetizacao_pop_15_mais' AS indicador,
        AVG(a.taxa_alfabetizacao_15_mais::double precision) AS valor
    FROM censo_populacao_alfabetizacao a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    GROUP BY 1, 2, 3
),
ensino_medio_ou_basica_completa_pop_15_17 AS (
    SELECT
        a.ano,
        m.municipio,
        'ensino_medio_ou_basica_completa_pop_15_17' AS indicador,
        AVG(a.percentual_15_17_ensino_medio_ou_basica_completa::double precision) AS valor
    FROM censo_populacao_ensino_medio_15_17 a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    GROUP BY 1, 2, 3
),
ensino_fundamental_ou_completo_pop_6_14 AS (
    SELECT
        a.ano,
        m.municipio,
        'ensino_fundamental_ou_completo_pop_6_14' AS indicador,
        AVG(a.percentual_6_14_ensino_fundamental_ou_completo::double precision) AS valor
    FROM censo_populacao_ensino_fundamental_6_14 a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    GROUP BY 1, 2, 3
),
escolaridade_media_18_29 AS (
    SELECT
        a.ano,
        m.municipio,
        'escolaridade_media_18_29' AS indicador,
        AVG(a.escolaridade_media_18_29::double precision) AS valor
    FROM censo_populacao_escolaridade_media_18_29 a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    GROUP BY 1, 2, 3
),
razao_escolaridade_racial_18_29 AS (
    SELECT
        a.ano,
        m.municipio,
        'razao_escolaridade_racial_18_29' AS indicador,
        AVG(a.razao_percentual_escolaridade_negros_nao_negros_18_29::double precision) AS valor
    FROM censo_populacao_escolaridade_media_18_29_racial a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    GROUP BY 1, 2, 3
),
ideb AS (
    SELECT
        s.ano,
        m.municipio,
        CASE s.categoria
            WHEN 'anos_iniciais' THEN 'ideb_anos_iniciais'
            WHEN 'anos_finais' THEN 'ideb_anos_finais'
            WHEN 'ensino_medio' THEN 'ideb_ensino_medio'
        END AS indicador,
        s.valor::double precision AS valor
    FROM saeb_ideb s
    JOIN municipios_base m
      ON m.id_municipio = s.id_municipio::text
    WHERE s.indicador = 'ideb'
      AND s.rede = 'Pública'
      AND s.categoria IN ('anos_iniciais', 'anos_finais', 'ensino_medio')
),
saeb_matematica AS (
    SELECT
        sp.ano,
        m.municipio,
        CASE sp.etapa_codigo
            WHEN 5 THEN 'saeb_anos_iniciais'
            WHEN 9 THEN 'saeb_anos_finais'
            WHEN 12 THEN 'saeb_ensino_medio'
        END AS indicador,
        SUM(
            CASE
                WHEN (sp.etapa_codigo = 5 AND sp.nivel >= 3)
                  OR (sp.etapa_codigo = 9 AND sp.nivel >= 2)
                  OR (sp.etapa_codigo = 12 AND sp.nivel >= 3)
                THEN sp.valor
                ELSE 0
            END
        )::double precision AS valor
    FROM saeb_proficiencia sp
    JOIN municipios_base m
      ON m.id_municipio = sp.id_municipio::text
    WHERE sp.tipo_indicador = 'nivel'
      AND sp.materia = 'matematica'
      AND sp.dependencia = 'total'
      AND sp.localizacao = 'total'
      AND sp.etapa_codigo IN (5, 9, 12)
    GROUP BY 1, 2, 3
),
distorcao_total AS (
    SELECT
        CAST(d.ano AS integer) AS ano,
        d.id_municipio::text AS id_municipio,
        m.municipio,
        CASE d.categoria
            WHEN 'taxa_distorcao_fundamental_anos_iniciais' THEN 'idade_regular_quinto'
            WHEN 'taxa_distorcao_fundamental_anos_finais' THEN 'idade_regular_nono'
            WHEN 'taxa_distorcao_medio' THEN 'idade_regular_medio'
        END AS indicador,
        CAST(d.valor AS double precision) AS taxa_distorcao
    FROM distorcao_idade_serie d
    JOIN municipios_base m
      ON m.id_municipio = d.id_municipio::text
    WHERE LOWER(TRIM(d.dependencia)) = 'total'
      AND d.categoria IN (
          'taxa_distorcao_fundamental_anos_iniciais',
          'taxa_distorcao_fundamental_anos_finais',
          'taxa_distorcao_medio'
      )
),
idade_regular AS (
    SELECT
        d.ano,
        d.municipio,
        d.indicador,
        CASE
            WHEN d.indicador = 'idade_regular_quinto' AND COALESCE(c.mat_fundamental_anos_iniciais, 0) <= 0 THEN NULL
            WHEN d.indicador = 'idade_regular_nono' AND COALESCE(c.mat_fundamental_anos_finais, 0) <= 0 THEN NULL
            WHEN d.indicador = 'idade_regular_medio' AND COALESCE(c.mat_medio, 0) <= 0 THEN NULL
            ELSE GREATEST(0.0, LEAST(100.0, 100.0 - d.taxa_distorcao))
        END AS valor
    FROM distorcao_total d
    LEFT JOIN censo_total c
      ON c.ano = d.ano
     AND c.id_municipio = d.id_municipio
),
adequacao AS (
    SELECT
        a.ano,
        m.municipio,
        CASE a.etapa
            WHEN 'anos_iniciais' THEN 'adequacao_ai'
            WHEN 'anos_finais' THEN 'adequacao_af'
            WHEN 'ensino_medio' THEN 'adequacao_em'
        END AS indicador,
        AVG(a.percentual_adequacao::double precision) AS valor
    FROM adequacao_docente a
    JOIN municipios_base m
      ON m.id_municipio = a.id_municipio::text
    WHERE a.dependencia = 'total'
      AND a.etapa IN ('anos_iniciais', 'anos_finais', 'ensino_medio')
    GROUP BY 1, 2, 3
),
pos_graduacao AS (
    SELECT
        d.ano,
        m.municipio,
        'pos_graduacao' AS indicador,
        AVG(d.percentual_pos_graduacao::double precision) AS valor
    FROM docentes_pos_graduacao d
    JOIN municipios_base m
      ON m.id_municipio = d.id_municipio::text
    GROUP BY 1, 2, 3
),
temporarios AS (
    SELECT
        d.ano,
        m.municipio,
        'temporarios' AS indicador,
        AVG(d.percentual_temporarios::double precision) AS valor
    FROM docentes_temporarios d
    JOIN municipios_base m
      ON m.id_municipio = d.id_municipio::text
    WHERE d.dependencia = 'publica'
    GROUP BY 1, 2, 3
)
SELECT ano, municipio, indicador, valor
FROM creche
UNION ALL
SELECT ano, municipio, indicador, valor
FROM pre_escola
UNION ALL
SELECT ano, municipio, indicador, valor
FROM basico_6_17
UNION ALL
SELECT ano, municipio, indicador, valor
FROM basico_15_17
UNION ALL
SELECT ano, municipio, indicador, valor
FROM basico_integral
UNION ALL
SELECT ano, municipio, indicador, valor
FROM escolas_integral
UNION ALL
SELECT ano, municipio, indicador, valor
FROM eja_integrada_educacao_profissional_percentual
UNION ALL
SELECT ano, municipio, indicador, valor
FROM medio_tecnico
UNION ALL
SELECT ano, municipio, indicador, valor
FROM aee
UNION ALL
SELECT ano, municipio, indicador, valor
FROM alfabetizacao
UNION ALL
SELECT ano, municipio, indicador, valor
FROM alfabetizacao_pop_15_mais
UNION ALL
SELECT ano, municipio, indicador, valor
FROM ensino_medio_ou_basica_completa_pop_15_17
UNION ALL
SELECT ano, municipio, indicador, valor
FROM ensino_fundamental_ou_completo_pop_6_14
UNION ALL
SELECT ano, municipio, indicador, valor
FROM escolaridade_media_18_29
UNION ALL
SELECT ano, municipio, indicador, valor
FROM razao_escolaridade_racial_18_29
UNION ALL
SELECT ano, municipio, indicador, valor
FROM ideb
UNION ALL
SELECT ano, municipio, indicador, valor
FROM saeb_matematica
UNION ALL
SELECT ano, municipio, indicador, valor
FROM idade_regular
UNION ALL
SELECT ano, municipio, indicador, valor
FROM adequacao
UNION ALL
SELECT ano, municipio, indicador, valor
FROM pos_graduacao
UNION ALL
SELECT ano, municipio, indicador, valor
FROM temporarios;
