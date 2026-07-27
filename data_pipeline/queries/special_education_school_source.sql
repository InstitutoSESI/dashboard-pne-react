SELECT *
FROM censo_educacao_especial_escolas
WHERE situacao_funcionamento = 1
  AND ano BETWEEN 2014 AND 2025
ORDER BY ano, id_municipio, cod_escola
