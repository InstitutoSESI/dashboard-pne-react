# MAPA DE LACUNAS ANALÍTICAS PÓS-JOB 5F — V7

## Escopo

Este mapa separa prontidão de evidência, custo de processamento e bloqueio metodológico. Não altera vereditos congelados, não aprova histórias e não autoriza aquisição de fonte, publicação ou Job 6.

## 1. Relações que já podem ser construídas

Estas frentes têm dados materializados e resultado exploratório suficiente para protótipo analítico interno, sempre com as limitações registradas na matriz:

- demografia × matrículas por etapa (`D1_DEMOGRAFIA_MATRICULAS_ETAPA`);
- demografia × escolas × turmas (`D1_DEMOGRAFIA_ESCOLAS_TURMAS`);
- coortes e pressão mecânica futura (`D1_COORTES_DEMANDA_FUTURA_MECANICA`, `D1_COORTES_TRANSICOES_ETAPAS`, `D2_COORTES_INDICADORES_PNE`);
- trajetória municipal oficial descritiva (`D1_FAMILIA_RENDIMENTO_MUNICIPAL`, `D1_MATRICULA_RENDIMENTO_OFICIAL`, `D1_MATRICULA_DISTORCAO_OFICIAL`, `D1_DISTORCAO_PERSISTENCIA_DESCRITIVA`);
- alunos por turma e adequação docente como contexto exploratório (`D1_TRAJETORIA_ALUNOS_TURMA`, `D1_TRAJETORIA_ADEQUACAO_DOCENTE`);
- conectividade e INSE como contexto descritivo (`D1_TRAJETORIA_CONECTIVIDADE`, `D1_TRAJETORIA_INFRAESTRUTURA`, `D1_TRAJETORIA_INSE`);
- público adulto × EJA fundamental/médio e séries históricas (`D1_EJA_FUNDAMENTAL_PUBLICO_ADULTO`, `D1_EJA_MEDIO_PUBLICO_ADULTO`, `D1_EJA_FUNDAMENTAL_HISTORICA`, `D1_EJA_MEDIO_HISTORICA`);
- EJA integrada à educação profissional (`D1_EJA_EDUCACAO_PROFISSIONAL`);
- EPT dentro da rede e concentração territorial (`D1_MATRICULA_EPT_REDE`, `D2_CONCENTRACAO_TRABALHO_FORMACAO`, `D2_EPT_TENDENCIA_TRABALHO`);
- mobilidade educacional por etapa e associações ecológicas exploratórias (`D1_MOBILIDADE_POR_ETAPA`, `D1_MOBILIDADE_ESTRUTURA_OFERTA`, `D1_MOBILIDADE_CRESCIMENTO_DEMOGRAFICO`, `D1_MOBILIDADE_TRAJETORIA`);
- trabalho jovem, aprendizagem e escolaridade dos vínculos (`D2_TRABALHO_JUVENIL_ENSINO_MEDIO`, `D2_APRENDIZES_JOVENS_EDUCACAO`, `D2_COORTES_JOVENS_TRABALHO`, `D2_ESCOLARIDADE_JOVENS_TRABALHADORES`);
- ocupações em crescimento/retração e ponte normativa CBO–CNCT (`D2_OCUPACOES_CRESCIMENTO_FORMACAO`, `D2_CBO_CNCT_PONTE`);
- Caged juvenil como leitura descritiva de fluxo (`D2_CAGED_JUVENIL_TRAJETORIA`, `D2_CAGED_OCUPACOES_EMERGENTES`).

Mesmo neste grupo, “pode ser construída” não significa “aprovada para publicação”. A matriz preserva `PROMISING_NEEDS_MORE_TESTING` e `DESCRIPTIVE_ONLY` quando o uso precisa ser mais restrito.

## 2. Relações que precisam de novo processamento

As fontes já existem no projeto, mas faltou integrar, recortar ou validar o universo `total_all_dependencies`:

| Relação | Processamento necessário | Ganho esperado |
|---|---|---|
| Nascimentos × educação infantil | Defasar nascimentos, população por idade e matrícula por município/etapa | Antecipar mudanças de pressão sobre creche e pré-escola |
| Demografia × docentes | Materializar docentes da rede total por etapa e ano | Dimensionar força de trabalho junto da demanda |
| Docentes × turmas × jornada | Integrar docentes, turmas, HAD e matrículas | Distinguir expansão física de reorganização pedagógica |
| Trajetória × horas-aula/tempo integral | Produzir séries totais e alinhar períodos | Contextualizar permanência e jornada |
| Trajetória × esforço/regularidade docente | Integrar IED e IRD no grão municipal total | Completar o perfil docente além da adequação |
| Escolaridade adulta 2010→2022 × EJA | Materializar os dois censos no mesmo contrato | Mostrar mudança estrutural do público adulto |
| Vulnerabilidade × EJA/trajetória | Integrar CadÚnico sem microvinculação | Orientar busca ativa e equidade |
| Educação especial/AEE × território | Validar população, matrícula e oferta compatíveis | Tornar visível a agenda de inclusão |
| Educação rural × demografia | Integrar localização rural, matrículas e população | Avaliar alcance territorial e reorganização |
| Diagnósticos/comparadores PNE | Extrair recorte dirigido sem republicar 499 detalhes | Ligar histórias a metas e alertas municipais |
| Aprendizes × ocupações/eixos | Consolidar Caged aprendiz por CBO/CNAE e ponte auditável | Identificar oportunidades de aprendizagem protegida |
| Setores × cursos/eixos | Consolidar painel CNAE total e regras setor–eixo | Formular agenda formativa territorial |
| Shift-share econômico × educação | Executar decomposição com bases e períodos comuns | Separar efeito estrutural e diferencial municipal |
| Escolaridade adulta × estrutura ocupacional | Integrar RAIS adulta e Censo | Relacionar elevação de escolaridade e perfil de postos sem inferir causalidade |
| Público adulto/EJA × trabalho | Integrar RAIS adulta em painel separado | Contextualizar EJA e inclusão produtiva |
| Transporte/PNATE × mobilidade | Materializar PNATE e alinhar com mobilidade 2022 | Qualificar perguntas de acesso e governança |
| Finanças × condições de oferta | Integrar finanças com defasagens e controles descritivos | Contextualizar capacidade, sem atribuir efeito causal |

## 3. Relações que exigem nova fonte pública

| Lacuna | Fonte/componente necessário | Relações afetadas | Potencial de produto |
|---|---|---|---|
| Destino da mobilidade educacional | Matriz origem–destino por município, etapa e ano | `D2_DESTINOS_MOBILIDADE_EDUCACIONAL`, `D1_MOBILIDADE_ESTRUTURA_OFERTA`, `D2_MOBILIDADE_EPT` | **Muito alto:** transforma uma taxa de saída em rede territorial concreta de fluxos |
| Componentes exatos das taxas de trajetória | Numeradores e denominadores oficiais no grão aceito | `D2_TAXA_REGIONAL_TRAJETORIA_EXATA` | **Muito alto:** permite recomposição regional legítima e estabilidade verificável |
| Matriz residência–trabalho por idade/escolaridade | Origem residencial e destino do estabelecimento | `D2_OD_RESIDENCIA_TRABALHO` | **Alto:** separa emprego local de trajetórias pendulares dos residentes |
| Cenários demográficos municipais validados | Projeções com mortalidade, fecundidade e migração | `D2_CENARIOS_TERRITORIAIS_PNE` | **Alto:** substitui pressão mecânica por cenários auditáveis, sem prometer previsão certa |
| Migração municipal anual por idade | Fluxos origem–destino ou componentes demográficos | `D2_NASCIMENTOS_MIGRACAO_OFERTA` | **Alto:** explica divergências entre nascimentos, coortes residentes e matrículas |
| Origem residencial dos estudantes de EPT | Origem–destino específica da educação profissional | `D2_MOBILIDADE_EPT` | **Alto:** mede acesso regional à oferta concentrada |

As duas maiores oportunidades de ganho imediato são a matriz origem–destino educacional por etapa e os componentes exatos das taxas do Inep. A primeira mudaria a capacidade de planejar cooperação regional; a segunda permitiria uma leitura regional de trajetória metodologicamente legítima.

## 4. Relações bloqueadas metodologicamente

- **Causalidade condições→trajetória (`D2_CAUSAL_CONDICOES_TRAJETORIA`):** não há contrafactual nem desenho causal; correlação ecológica não resolve o problema.
- **Dependência administrativa como explicação de desempenho (`D2_DEPENDENCIA_ADMINISTRATIVA_DESEMPENHO`):** proibida pela regra canônica; dependência serve apenas a reconstrução, disponibilidade, proveniência e QA.
- **Transição individual escola→trabalho (`D2_TRANSICAO_INDIVIDUAL_ESCOLA_TRABALHO`):** não há vinculação individual autorizada; agregados com lentes diferentes não identificam trajetórias pessoais.
- **Taxa regional de trajetória sem componentes (`D2_TAXA_REGIONAL_TRAJETORIA_EXATA`):** retrocálculo, média simples, ponderação inventada e recomposição aproximada continuam proibidos.
- **Previsão de matrícula a partir da coorte (`D2_PREVISAO_MATRICULA_POR_COORTE`):** a formulação preditiva foi rejeitada; somente pressão mecânica transparente pode ser usada com os dados atuais.
- **Adequação ocupação–curso:** a ponte CBO–CNCT não autoriza dizer que a oferta é adequada, suficiente ou causada pelo mercado.

## 5. Relações potencialmente valiosas, mas ainda não testadas de forma suficiente

Este grupo possui pergunta substantiva e fonte identificada, mas requer execução ou robustez adicional antes de qualquer protótipo:

- docentes, turmas, jornada, esforço e regularidade;
- nascimentos e educação infantil com defasagens;
- escolaridade adulta 2010→2022, EJA e trabalho;
- educação especial, ruralidade e vulnerabilidade;
- aprendizes por ocupação/setor e eixos formativos;
- painel setorial, shift-share e tendências da EPT;
- finanças, PNATE e capacidade de coordenação;
- comparadores PNE por indicador e município;
- associações mobilidade×demografia/oferta/ trajetória, que hoje têm apenas `n=10` e um ano de mobilidade;
- trabalho juvenil×trajetória, cujos sinais históricos foram instáveis;
- infraestrutura além de conectividade, devido a indisponibilidades do recorte atual.

## 6. Lacunas que não devem ser “resolvidas” por aproximação

- não usar dependência administrativa como estrato;
- não calcular taxa regional de trajetória por média municipal;
- não inferir destino a partir da origem da mobilidade;
- não equiparar vínculos RAIS/Caged a estudantes ou residentes;
- não transformar zero de matrícula EPT/EJA integrada em ausência de acesso;
- não recodificar escolaridade RAIS sem dicionário oficial versionado;
- não tornar o cenário mecânico uma previsão;
- não somar correspondências muitos-para-muitos CBO–CNCT.

## 7. Encaminhamento

Este mapa serve ao julgamento externo do GPT-5.6 Pro. Nenhuma fonte adicional deve ser adquirida e nenhum novo processamento amplo deve começar antes de o revisor indicar quais lacunas justificam testes adicionais.
