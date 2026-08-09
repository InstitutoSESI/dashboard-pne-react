SELECT
    t1.ano,
    t1.id_municipio,
    m.municipio,
    t1.mat_eja_total,
    t1.mat_eja_fundamental_total,
    t1.mat_eja_fundamental_federal,
    t1.mat_eja_fundamental_estadual,
    t1.mat_eja_fundamental_municipal,
    t1.mat_eja_fundamental_privada,
    t1.mat_eja_medio_total,
    t1.mat_eja_medio_federal,
    t1.mat_eja_medio_estadual,
    t1.mat_eja_medio_municipal,
    t1.mat_eja_medio_privada,
    t1.mat_eja_curso_tecnico_integrada,
    t1.mat_eja_curso_tecnico_integrada_federal,
    t1.mat_eja_curso_tecnico_integrada_estadual,
    t1.mat_eja_curso_tecnico_integrada_municipal,
    t1.mat_eja_curso_tecnico_integrada_publica,
    t1.mat_eja_curso_tecnico_integrada_privada,
    t1.mat_eja_fic_integrado_fundamental,
    t1.mat_eja_fic_integrado_fundamental_federal,
    t1.mat_eja_fic_integrado_fundamental_estadual,
    t1.mat_eja_fic_integrado_fundamental_municipal,
    t1.mat_eja_fic_integrado_fundamental_publica,
    t1.mat_eja_fic_integrado_fundamental_privada,
    t1.mat_eja_fic_integrado_medio,
    t1.mat_eja_fic_integrado_medio_federal,
    t1.mat_eja_fic_integrado_medio_estadual,
    t1.mat_eja_fic_integrado_medio_municipal,
    t1.mat_eja_fic_integrado_medio_publica,
    t1.mat_eja_fic_integrado_medio_privada,
    t1.mat_eja_integrada_educacao_profissional,
    t1.mat_eja_integrada_educacao_profissional_federal,
    t1.mat_eja_integrada_educacao_profissional_estadual,
    t1.mat_eja_integrada_educacao_profissional_municipal,
    t1.mat_eja_integrada_educacao_profissional_publica,
    t1.mat_eja_integrada_educacao_profissional_privada,
    CASE
      WHEN t1.mat_eja_curso_tecnico_integrada IS NULL
        OR t1.mat_eja_fic_integrado_fundamental IS NULL
        OR t1.mat_eja_fic_integrado_medio IS NULL
      THEN NULL
      ELSE t1.mat_eja_curso_tecnico_integrada
        + t1.mat_eja_fic_integrado_fundamental
        + t1.mat_eja_fic_integrado_medio
    END AS mat_eja_integrada_educacao_profissional_calculada,
    CASE
      WHEN t1.mat_eja_fundamental_total IS NULL
        OR t1.mat_eja_medio_total IS NULL
      THEN NULL
      ELSE t1.mat_eja_fundamental_total + t1.mat_eja_medio_total
    END AS mat_eja_denominador_calculado,
    CASE
      WHEN t1.mat_eja_fundamental_total IS NULL
        OR t1.mat_eja_medio_total IS NULL
        OR t1.mat_eja_fundamental_total + t1.mat_eja_medio_total = 0
        OR t1.mat_eja_curso_tecnico_integrada IS NULL
        OR t1.mat_eja_fic_integrado_fundamental IS NULL
        OR t1.mat_eja_fic_integrado_medio IS NULL
      THEN NULL
      ELSE 100.0 * (
        t1.mat_eja_curso_tecnico_integrada
        + t1.mat_eja_fic_integrado_fundamental
        + t1.mat_eja_fic_integrado_medio
      ) / (t1.mat_eja_fundamental_total + t1.mat_eja_medio_total)
    END AS percentual_eja_integrada_educacao_profissional_calculado,
    t1.percentual_eja_integrada_educacao_profissional
FROM eja_integrada_educacao_profissional t1
JOIN municipios m
  ON m.id_municipio::text = t1.id_municipio::text
WHERE t1.ano BETWEEN 2014 AND 2025
  AND t1.sigla_uf = :uf;
