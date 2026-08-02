# Pesquisa do pipeline

Esta área reúne experimentos e auditorias metodológicas que não fazem parte da publicação automática da plataforma. Ela está separada de `data_pipeline/src` e `data_pipeline/scripts`, que continuam sendo a área operacional de produção.

## Fronteira com a produção

- experimentos não alteram contratos, cálculos ou dados publicados;
- auditorias bloqueadas preservam evidência sobre fontes que ainda não podem ser publicadas;
- código de produção não pode importar `research`;
- código de pesquisa pode reutilizar funções de `data_pipeline/src`;
- nenhum comando desta área é executado por `npm run update:data`, pelo build ou pelos materializadores operacionais;
- resultados experimentais devem ser gravados em `data_pipeline/export`, que é ignorado pelo Git, e nunca em `public/data`.

Os snapshots metodológicos de `director_selection` e `inec_connectivity` permanecem em `data_pipeline/data/pne_macro_sources`. Eles só podem ser atualizados por execução humana explícita das auditorias correspondentes, após revisão das fontes.

## Execução explícita

Experimento de projeção educacional:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/research/projections/run_education_attendance_projection_experiment.py `
  --output-dir data_pipeline/export/education_attendance_projection_experiment
```

Auditoria do critério de seleção de diretores:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/research/audits/audit_pne_director_selection.py `
  --csv CAMINHO_PARA_O_CSV `
  --dictionary CAMINHO_PARA_O_DICIONARIO_XLSX
```

Auditoria de conectividade INEC/ENEC com a nota técnica já obtida:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/research/audits/audit_pne_inec_connectivity.py `
  --note-file CAMINHO_PARA_A_NOTA_TECNICA_PDF
```

Use `--help` em qualquer comando para consultar os argumentos sem abrir banco, acessar a rede, executar o experimento ou escrever arquivos.

A pesquisa reutiliza as dependências de runtime declaradas no
`data_pipeline/pyproject.toml`; não há um ambiente ou grupo `research`
separado. Sincronize o lock antes da execução com `npm run python:sync`.

## Promoção de resultados

Um resultado de pesquisa não se torna produção por movimentação ou cópia de artefatos. A promoção exige implementação separada na área operacional, revisão metodológica e testes dos contratos de produção.
