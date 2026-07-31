# PNE 2026–2036 — rodada acelerada: AEE, atendimento indígena, infraestrutura e Educação Superior

## Escopo e decisão

A rodada foi executada sem download e sem integração externa. Foram lidos o
ponteiro `current.json`, o contrato canônico, a política editorial, a release
ativa e as materializações já existentes. A release de entrada era
`8378537cbf4aef5e35e89c09550f7802e548d15d33eca8b3fe7fa9a915c84dea`,
com contrato 1.4.0 e política 1.2.0.

Quatro relações foram homologadas como `complementary`. A razão estudantil de
AEE, o composto de infraestrutura mínima, o regime docente e os indicadores
de qualidade da Educação Superior permaneceram fora da release por barreira
metodológica. Nenhuma relação foi promovida a `progress`.

## Matriz de auditoria

| Meta | Indicador possível | Fonte existente | Numerador | Denominador | Territorialidade | Cobertura | Modo recomendado | Risco | Condição para publicação |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10.b | Estudantes efetivamente atendidos pelo AEE | `special_education_materialization.py` e contrato municipal de Educação Especial | Estudantes atendidos pelo AEE | Público estudantil elegível para AEE | Estudante, ano, rede e localização compatíveis | Componentes estudantis compatíveis não materializados | Fora da release | Confundir oferta escolar com atendimento estudantil | Materializar numerador e denominador estudantis no mesmo universo, distinguir zero de ausência e homologar a referência legal |
| 10.b | Escolas elegíveis que oferecem AEE | mesma materialização | Escolas com `QT_MAT_ESP > 0` e `TP_AEE` 1 ou 2 | Escolas com `QT_MAT_ESP > 0` | Município da escola | 497/497 disponíveis | `complementary` | Não mede estudantes atendidos | Publicar com leitura explícita de oferta escolar, sem referência, distância, status ou projeção |
| 9.d | Cobertura estimada da educação escolar indígena de 4 a 17 anos | `indigenous_education_coverage.py`, Censo Escolar e população indígena já materializada do Censo 2022/SIDRA 9970 | Matrículas localizadas de pré-escola, ensino fundamental e ensino médio da oferta indígena, no último ano materializado | População indígena residente de 4 a 17 anos em 2022 | Oferta localizada ÷ população residente | 223 disponíveis; 274 `not_applicable` por denominador zero | `complementary` | Territorialidades distintas e pequenos denominadores; pode ultrapassar 100% | Manter retrato único, preservar valor bruto, mostrar componentes e emitir explicação somente quando o valor superar 100% |
| 19.c | Escolas com a cesta mínima integralmente observada | `school_infrastructure_materialization.py` e contratos municipais de infraestrutura | Escolas `compliant` | Escolas `compliant` + `noncompliant` | Mesma escola | 497 contratos, mas somente marginais públicas por item | Fora da release | Inferência ecológica: marginais de água, energia, esgoto, internet, biblioteca e quadra não identificam presença conjunta na mesma escola; cesta legal não homologada | Versionar a cesta legal, conservar o grão escolar e os estados `compliant`/`noncompliant`/`unknown`, divulgar cobertura e definir referência/prazo |
| 14.c | Concluintes da graduação na oferta localizada | `higher_education_materialization.py`, Censo da Educação Superior materializado | Total observado de concluintes | Não se aplica; contagem absoluta | Localização da oferta do curso | 248 disponíveis; 249 `unavailable` | `complementary` | Oferta localizada não representa residentes | Publicar como contagem descritiva, sem distribuir a meta nacional entre municípios |
| 15.c | Docentes com mestrado ou doutorado nas IES com sede local | mesma materialização | Docentes com mestrado + doutorado | Soma exaustiva de sem graduação, graduação, especialização, mestrado e doutorado | Sede administrativa da IES | 45 disponíveis; 452 `unavailable` | `complementary` | Sede não representa residência e a camada não comprova todos os recortes jurídicos | Publicar somente quando a decomposição por titulação for observada e exaustiva; denominador zero explícito é `not_applicable` |
| 15.c | Docentes em tempo integral | mesma materialização | Docentes em regime integral | Total de docentes no mesmo universo | Sede administrativa da IES | Regime docente ausente da camada publicada | Fora da release | Impossível reconstruir regime sem nova fonte/carga | Materializar regime de trabalho com universo e completude auditáveis |
| 14/15 | IES, campi, polos e qualidade | mesma materialização | Conforme a dimensão | Conforme a dimensão | Sede ou localização da oferta, sem mistura | IES e polos existem como detalhe; campi e qualidade não formam medida homologada | Detalhe existente; nenhum novo card | Excesso de cards e mistura de territorialidades; qualidade ausente | Manter como detalhe até existir correspondência legal e medida municipal reproduzível |

## Fórmulas homologadas

- Meta 10.b:
  `100 × escolas elegíveis que oferecem AEE ÷ escolas com matrículas da Educação Especial`.
- Meta 9.d:
  `100 × matrículas indígenas localizadas de 4 a 17 anos ÷ população indígena residente de 4 a 17 anos em 2022`.
- Meta 14.c:
  `concluintes da graduação na oferta localizada no município`.
- Meta 15.c:
  `100 × (docentes com mestrado + docentes com doutorado) ÷ total docente na decomposição exaustiva por titulação`.

Nas quatro relações, referência, distância, status, classificação e projeção
são proibidos. Zero observado é preservado; ausência não é convertida em
zero. Para a Meta 9.d, denominador zero é `not_applicable` e população ausente
é `unavailable`. Para a taxa interna da Meta 15.c, um marcador explícito de
ausência de IES/denominador zero é `not_applicable`; quando a camada não
distingue ausência de IES de ausência de dados, permanece `unavailable`.

## Cobertura e ausências

| Relação | Disponível | Ausência segura |
| --- | ---: | --- |
| `relation.10.b.aee_oferta_escolas_elegiveis` | 497 | 0 |
| `relation.9.d.educacao_indigena_cobertura_estimada_4_17` | 223 | 274 `denominator_zero` |
| `relation.14.c.superior_concluintes_oferta_local` | 248 | 249 `local_offer_unavailable` |
| `relation.15.c.superior_docentes_mestres_doutores_sede` | 45 | 452 `exhaustive_faculty_education_unavailable` |

Há 14 resultados indígenas acima de 100%; todos foram preservados. A
explicação condicional usa matrículas versus pessoas únicas e possível
deslocamento intermunicipal. Não foi criada série, tendência ou projeção.

## Contrato, política e catálogos

- contrato: versão `1.5.0`;
- hash normalizado do contrato:
  `9b5ba002c2aa4f211958aa40c98da2a4186d07d548db01d1d854102b3a408a40`;
- política editorial: versão `1.3.0`;
- hash normalizado da política:
  `5337c7b6156457de5c7ade3aa46c1bf6a22fb09c605ae35ec5e9e7c5f4d3341f`;
- catálogo V3: 46 indicadores canônicos, incluindo as quatro novas relações;
- catálogo/materialização V2: congelado e não reescrito.

## Staging, determinismo e promoção

Foram gerados dois pacotes completos fora de `public/data`. Para reproduzir a
comparação, use diretórios efêmeros configurados por `--output-dir`, por
exemplo `data_pipeline/export/pne-v3-accelerated-a` e
`data_pipeline/export/pne-v3-accelerated-b`; caminhos locais de uma estação de
trabalho não integram o registro metodológico.

Os 498 arquivos de cada staging — manifesto mais 497 municípios — são
idênticos byte a byte. Identificadores:

- SHA-256 do manifesto de staging:
  `7974b0942b04de3eb5d8cd468e5975b0545e0fe39e758483ed2121058bf7efe4`;
- `generationHash` e release:
  `68134c9254da62d2f04d2a1aea7764bab19bf5748278761ad0179198ff0a529a`;
- hash semântico:
  `c0c60a0c3f5774570b02de0c3fe6a237528e98040ca2ffec4e5ee0efdef8e564`;
- SHA-256 do manifesto da release:
  `9a6b6a26795465e56730dc32520fac98061f42b284425228e705355414361aff`;
- SHA-256 de `current.json`:
  `1996f5b4a1f125a3d09e13f56a60069e2697e2d4d4981d1f2221f14b45b3fb14`.

O comparador preservou 15.114 registros fora do pacote sem nenhuma diferença.
A release adicionou somente 1.013 ocorrências: 497 AEE, 223 indígenas, 248
concluintes e 45 de titulação docente. O promotor criou uma única release
imutável e trocou `current.json` atomicamente.

## Contagens finais

- 497 municípios;
- 16.127 resultados;
- 10.155 `progress` e 5.972 `complementary`;
- 8.663 `advance`, 1.492 `maintain` e 0 `unclassified`;
- 4.466 `essential` e 11.661 `standard`;
- mínimo/máximo municipal de 26/35;
- 515 valores numéricos acima de 100, dos quais 14 pertencem à razão indígena
  e 88 são contagens absolutas de concluintes;
- 961 ocorrências `hidden` excluídas;
- zero duplicidade, arquivo inválido, `NaN` ou `Infinity`.

## Interface, impressão e consumidores técnicos

Os quatro complementos aparecem em cards compactos, com título, valor e ano,
sem semáforo, distância, projeção ou classificação. “Fonte e cálculo” fica
recolhido e apresenta fonte, fórmula e componentes disponíveis. A inspeção em
desktop e no viewport 390 × 844 confirmou ausência de overflow horizontal. O
caso indígena de Benjamin Constant do Sul mostrou 128,2% e a explicação
condicional; Ivoti, com 0%, não exibiu o aviso.

O relatório de impressão contém os quatro resultados sem meta ou distância e
lista Censo Escolar, Censo 2022/SIDRA 9970 e Censo da Educação Superior. O
Relatório Técnico Municipal e o workbook usam seções temáticas, rótulos
humanos, fontes e numerador/denominador materializados quando aplicáveis.

## Preservação

As releases anteriores permanecem presentes e imutáveis:

- `3832c3417fdf969af52cd706240b1a15784c1e0f29391dc0397992c16c828933`;
- `b1780788a3598d6993a02f8180b25ef6d241d31163325b41a9e9b0a7b77e5743`;
- `8378537cbf4aef5e35e89c09550f7802e548d15d33eca8b3fe7fa9a915c84dea`.

A árvore V2 permanece sem diff e com o mesmo tree id Git
`14aa867caa7910813ebcf9007f307d887968d680`. Não houve commit nem push.
