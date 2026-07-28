# Produto

<!-- impeccable:product-schema 1 -->

## Platform

web

## Público

Equipes técnicas e gestoras das Secretarias Municipais de Educação usam o painel para compreender a situação educacional do município, relacioná-la às referências do PNE e definir prioridades. Conselhos, gestores públicos, comunidade escolar e população também podem consultar uma síntese sustentada por fontes oficiais.

## Propósito

Transformar dados públicos educacionais em uma leitura municipal orientada à decisão. O produto explicita resultados, períodos, fontes, limitações e referências sem converter evidência descritiva em julgamento automático ou causalidade não demonstrada.

## Posicionamento

Os portais educacionais existentes tratam cada domínio em separado: matrícula num lugar, orçamento em outro, meta do PNE num terceiro. Este painel concilia PNE, indicadores educacionais, financiamento e diagnóstico **de um mesmo município numa base única**, de modo que gasto por estudante e matrícula por etapa possam ser lidos lado a lado, com o mesmo recorte territorial e a mesma declaração de período e fonte.

A integração é o mecanismo, não a quantidade de indicadores. O que o painel entrega e um agregador de dados não entregaria com verdade é a leitura de um território inteiro sem o usuário precisar reconciliar bases de origens diferentes por conta própria.

## Contexto de operação

- **Consulta em tela pela equipe técnica da Secretaria**, no navegador, como uso cotidiano.
- **Relatório Técnico Municipal impresso ou em PDF**, circulando em papel fora da ferramenta. Existe folha de impressão dedicada (`src/styles/municipal-technical-report-print.css`), e o documento tem 6 capítulos e 19 seções com fonte e período declarados por seção.

O uso impresso é um requisito de produto, não um extra: define o tema claro, a permanência das tabelas com valor exato e a necessidade de que fonte e período apareçam junto ao dado, e não apenas num tooltip.

## Escopo atual

- visão geral municipal e indicadores educacionais;
- ciclos PNE 2014–2024 e 2026–2036;
- metas legais e séries históricas;
- diagnóstico municipal com comparações e qualidade da evidência;
- panorama de financiamento, Fundeb, aplicação em educação, VAAR, PNATE e QSE;
- detalhamento metodológico e fontes na própria interface.

## Evidência disponível

- **Dados publicados dos 497 municípios do Rio Grande do Sul**, versionados em `public/data/` como saída do pipeline em `data_pipeline/`.
- **Fontes oficiais em uso**: INEP (Censo Escolar, Sinopse Estatística, SAEB), IBGE (estimativas populacionais), SIOPE e Siconfi/RREO (financiamento).
- **Estágio real: piloto.** Há secretarias usando ou avaliando, em número limitado. O painel **não** está em uso pela rede completa dos 497 municípios — a cobertura de dados é total, a adoção não é. Trabalhos futuros não devem afirmar adoção ampla, número de usuários, resultados de uso ou depoimentos: nada disso existe registrado.
- Não há depoimento, estudo de caso, benchmark de mercado, política de preço ou compromisso de nível de serviço. Não invente nenhum.

## Princípios

1. Começar pela decisão, mostrando o que merece atenção e qual evidência sustenta a leitura.
2. Separar dado, interpretação e decisão de gestão.
3. Contextualizar valores com unidade, período, fonte e limitações.
4. Preservar zero, ausência, não aplicabilidade e indisponibilidade como estados distintos.
5. Comunicar sem ranking competitivo, alarmismo ou semáforos de julgamento.
6. Usar a mesma base para análise técnica e prestação de contas, variando apenas o nível de detalhe.

## Linguagem e marca

O painel é institucional, analítico e sóbrio. A linguagem deve ser acessível, precisa e conservadora. Termos de situação descrevem a relação entre o dado e uma referência; não atribuem mérito, culpa ou causalidade ao município.

Identidade institucional SESI-RS e FIERGS, com as marcas presentes na barra superior e na assinatura do rodapé.

## Acessibilidade

O objetivo é conformidade WCAG 2.2 AA: navegação por teclado, foco visível, contraste adequado, alvos de interação confortáveis, leitura com zoom e informação que não dependa apenas de cor. Gráficos e controles devem expor nomes acessíveis e estados textuais.
