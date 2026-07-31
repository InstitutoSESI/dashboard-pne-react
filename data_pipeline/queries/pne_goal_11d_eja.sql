-- Relação 11.d: matrículas EJA de 18 anos ou mais por população residente
-- de 18 anos ou mais sem Educação Básica concluída. A origem territorial é
-- deliberadamente mista e deve permanecer visível na apresentação.
SELECT
    eja.ano,
    eja.id_municipio,
    eja.matriculas_eja_18_mais AS numerator_value,
    censo.populacao_18_mais_sem_basica_concluida AS denominator_value,
    100.0 * eja.matriculas_eja_18_mais
        / NULLIF(censo.populacao_18_mais_sem_basica_concluida, 0) AS value
FROM pne_eja_18_mais eja
JOIN pne_censo_2022_sem_basica_concluida censo
    ON censo.id_municipio = eja.id_municipio;
