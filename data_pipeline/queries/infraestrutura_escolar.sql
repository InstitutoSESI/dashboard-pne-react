WITH censo_total AS (
    SELECT
        c.ano,
        m.municipio,
        SUM(COALESCE(c.qntd_escolas, 0)) AS qntd_escolas,
        SUM(COALESCE(c.escolas_com_internet, 0)) AS escolas_com_internet,
        SUM(COALESCE(c.escolas_com_internet_alunos, 0)) AS escolas_com_internet_alunos,
        SUM(COALESCE(c.escolas_com_internet_administrativo, 0)) AS escolas_com_internet_administrativo,
        SUM(COALESCE(c.escolas_com_internet_aprendizagem, 0)) AS escolas_com_internet_aprendizagem,
        SUM(COALESCE(c.escolas_com_internet_comunidade, 0)) AS escolas_com_internet_comunidade,
        SUM(COALESCE(c.escolas_com_acesso_internet_computador, 0)) AS escolas_com_acesso_internet_computador,
        SUM(COALESCE(c.escolas_com_acesso_internet_disp_pessoais, 0)) AS escolas_com_acesso_internet_disp_pessoais,
        SUM(COALESCE(c.escolas_com_banda_larga, 0)) AS escolas_com_banda_larga,
        SUM(COALESCE(c.escolas_com_rede_local, 0)) AS escolas_com_rede_local,
        SUM(COALESCE(c.escolas_com_rede_local_wireless, 0)) AS escolas_com_rede_local_wireless,
        SUM(COALESCE(c.escolas_com_rede_local_cabo_wireless, 0)) AS escolas_com_rede_local_cabo_wireless,
        SUM(COALESCE(c.escolas_com_educacao_ambiental, 0)) AS escolas_com_educacao_ambiental,
        SUM(COALESCE(c.escolas_com_desktop_aluno, 0)) AS escolas_com_desktop_aluno,
        SUM(COALESCE(c.escolas_com_comp_portatil_aluno, 0)) AS escolas_com_comp_portatil_aluno,
        SUM(COALESCE(c.escolas_com_tablet_aluno, 0)) AS escolas_com_tablet_aluno,
        SUM(COALESCE(c.qt_salas_utilizadas, 0)) AS qt_salas_utilizadas,
        SUM(COALESCE(c.qt_salas_utiliza_climatizadas, 0)) AS qt_salas_utiliza_climatizadas,
        SUM(COALESCE(c.qt_salas_utilizadas_acessiveis, 0)) AS qt_salas_utilizadas_acessiveis
    FROM censo c
    JOIN municipios m
        ON c.id_municipio = m.id_municipio
    WHERE c.sigla_uf = :uf
    GROUP BY
        c.ano,
        m.municipio
),
escolas_publicas AS (
    SELECT
        ce.ano,
        m.municipio,
        COUNT(DISTINCT ce.cod_escola) AS escolas_publicas_total,
        COUNT(
            DISTINCT CASE
                WHEN COALESCE(ce.escolas_com_orgao_conselho_escolar, 0) > 0
                THEN ce.cod_escola
            END
        ) AS escolas_publicas_com_orgao_conselho_escolar,
        COUNT(
            DISTINCT CASE
                WHEN TRIM(ce.tp_proposta_pedagogica::text) IN ('0', '1')
                THEN ce.cod_escola
            END
        ) AS escolas_publicas_com_proposta_pedagogica
    FROM censo_escolas ce
    JOIN municipios m
        ON ce.id_municipio = m.id_municipio
    WHERE ce.dependencia IN ('federal', 'estadual', 'municipal')
      AND COALESCE(ce.mat_basico, 0) >= 1
      AND ce.sigla_uf = :uf
    GROUP BY
        ce.ano,
        m.municipio
)
SELECT
    censo_total.ano,
    censo_total.municipio,
    'total' AS dependencia,
    qntd_escolas,
    COALESCE(escolas_publicas.escolas_publicas_total, 0) AS escolas_publicas_total,
    escolas_com_internet,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_internet / qntd_escolas
        ELSE NULL
    END AS percentual_internet,
    escolas_com_internet_alunos,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_internet_alunos / qntd_escolas
        ELSE NULL
    END AS percentual_internet_alunos,
    escolas_com_internet_administrativo,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_internet_administrativo / qntd_escolas
        ELSE NULL
    END AS percentual_internet_administrativo,
    escolas_com_internet_aprendizagem,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_internet_aprendizagem / qntd_escolas
        ELSE NULL
    END AS percentual_internet_aprendizagem,
    escolas_com_internet_comunidade,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_internet_comunidade / qntd_escolas
        ELSE NULL
    END AS percentual_internet_comunidade,
    escolas_com_acesso_internet_computador,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_acesso_internet_computador / qntd_escolas
        ELSE NULL
    END AS percentual_acesso_internet_computador,
    escolas_com_acesso_internet_disp_pessoais,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_acesso_internet_disp_pessoais / qntd_escolas
        ELSE NULL
    END AS percentual_acesso_internet_disp_pessoais,
    escolas_com_banda_larga,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_banda_larga / qntd_escolas
        ELSE NULL
    END AS percentual_banda_larga,
    escolas_com_rede_local,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_rede_local / qntd_escolas
        ELSE NULL
    END AS percentual_rede_local,
    escolas_com_rede_local_wireless + escolas_com_rede_local_cabo_wireless AS escolas_com_rede_wireless,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * (escolas_com_rede_local_wireless + escolas_com_rede_local_cabo_wireless) / qntd_escolas
        ELSE NULL
    END AS percentual_rede_wireless,
    escolas_com_educacao_ambiental,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_educacao_ambiental / qntd_escolas
        ELSE NULL
    END AS percentual_educacao_ambiental,
    COALESCE(
        escolas_publicas.escolas_publicas_com_orgao_conselho_escolar,
        0
    ) AS escolas_publicas_com_orgao_conselho_escolar,
    CASE WHEN COALESCE(escolas_publicas.escolas_publicas_total, 0) > 0
        THEN 100.0
            * COALESCE(
                escolas_publicas.escolas_publicas_com_orgao_conselho_escolar,
                0
            )
            / escolas_publicas.escolas_publicas_total
        ELSE NULL
    END AS percentual_conselho_escolar,
    COALESCE(
        escolas_publicas.escolas_publicas_com_proposta_pedagogica,
        0
    ) AS escolas_publicas_com_proposta_pedagogica,
    CASE WHEN COALESCE(escolas_publicas.escolas_publicas_total, 0) > 0
        THEN 100.0
            * COALESCE(
                escolas_publicas.escolas_publicas_com_proposta_pedagogica,
                0
            )
            / escolas_publicas.escolas_publicas_total
        ELSE NULL
    END AS percentual_proposta_pedagogica,
    escolas_com_desktop_aluno,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_desktop_aluno / qntd_escolas
        ELSE NULL
    END AS percentual_desktop_aluno,
    escolas_com_comp_portatil_aluno,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_comp_portatil_aluno / qntd_escolas
        ELSE NULL
    END AS percentual_comp_portatil_aluno,
    escolas_com_tablet_aluno,
    CASE WHEN qntd_escolas > 0
        THEN 100.0 * escolas_com_tablet_aluno / qntd_escolas
        ELSE NULL
    END AS percentual_tablet_aluno,
    qt_salas_utilizadas,
    qt_salas_utiliza_climatizadas,
    CASE WHEN qt_salas_utilizadas > 0
        THEN 100.0 * qt_salas_utiliza_climatizadas / qt_salas_utilizadas
        ELSE NULL
    END AS percentual_salas_climatizadas,
    qt_salas_utilizadas_acessiveis,
    CASE WHEN qt_salas_utilizadas > 0
        THEN 100.0 * qt_salas_utilizadas_acessiveis / qt_salas_utilizadas
        ELSE NULL
    END AS percentual_salas_acessiveis
FROM censo_total
LEFT JOIN escolas_publicas
    ON censo_total.ano = escolas_publicas.ano
   AND censo_total.municipio = escolas_publicas.municipio
ORDER BY
    censo_total.ano,
    censo_total.municipio;
