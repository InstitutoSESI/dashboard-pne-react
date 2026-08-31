# Inventário dos transversais com dados públicos

## Finalidade

Este inventário registra quais variáveis transversais podem entrar em Cenários da Educação sem depender de coleta primária. A regra é local-first: uma aquisição externa só pode ocorrer quando houver uma necessidade metodológica definida e a ausência do dado no computador tiver sido comprovada.

A verificação de 31 de agosto de 2026 encontrou cobertura local suficiente para clima, tecnologia e contexto fiscal nos dez municípios do Vale do Sinos. Para regime de colaboração, as fontes locais foram examinadas, mas não medem o constructo necessário. Por isso, esse transversal permanece como lacuna explícita.

## Entradas locais

| Família | Padrão de arquivo | Cobertura | Uso |
| --- | --- | ---: | --- |
| Infraestrutura escolar | public/data/municipios/<IBGE>/details.json | 10/10 | Série anual e numeradores/denominadores do Censo Escolar |
| Financiamento | public/data/municipios/<IBGE>/financeiro.json | 10/10 | Aplicação constitucional em MDE reconciliada |
| Matriz PNE municipal | public/data/pne2026-matriz/municipios/<IBGE>.json | 10/10 | Registros MIDR e auditoria do proxy MUNIC |

O manifesto interno da publicação cobre 30 arquivos. Seu digest SHA-256 é calculado sobre código IBGE textual, tipo, caminho, hash e tamanho de cada entrada, em ordem canônica. O bundle público divulga apenas o digest agregado, os padrões de caminho e as contagens de cobertura.

## Resultado por transversal

| Transversal | Maturidade | Recorte | Resultado usado | Limite de afirmação |
| --- | --- | --- | --- | --- |
| Eventos climáticos e continuidade | OBSERVED_PUBLIC_SENTINEL | 2014–2025 | 66 protocolos S2ID únicos na região; 10 municípios com registro; 9 protocolos em Nova Santa Rita | Registros públicos de eventos, não dias letivos perdidos, escolas fechadas, estudantes afetados ou efeito educacional |
| Tecnologia e organização do ensino | OBSERVED_SERIES | 2025 | Internet usada na aprendizagem: 604/734 escolas na região (82,2888%) e 27/28 em Nova Santa Rita (96,4286%). Acesso por computador: 342/734 (46,5940%) e 12/28 (42,8571%) | Infraestrutura declarada por escola, não uso, qualidade da conexão, acesso domiciliar ou aprendizagem |
| Restrição fiscal e custo de coordenação | OBSERVED_RECONCILED_CONTEXT | 2025 | Margem municipal sobre o mínimo de MDE: mínimo 0,09 p.p.; mediana 1,505 p.p.; máximo 6,75 p.p.; Nova Santa Rita 0,09 p.p. | Distribuição municipal contábil, não orçamento regional, folga futura ou capacidade garantida de cofinanciamento |
| Regulação e regime de colaboração | EXPLICIT_GAP | revisão das fontes locais vigentes | Zero evidência pública elegível. O indicador MUNIC de ação geral de acessibilidade no transporte foi excluído como proxy | Não comprova pacto educacional, responsabilidades, nível de serviço, cofinanciamento, revisão ou saída |

## Fórmulas e regras

### Tecnologia

A proporção regional é ponderada pelos denominadores:

percentual regional = soma dos numeradores municipais / soma dos denominadores municipais × 100

Não se calcula média simples dos dez percentuais. Denominador zero produz null. O cálculo bruto não é arredondado; o arredondamento ocorre somente na apresentação.

### Contexto fiscal

Para cada município:

margem MDE = taxa reconciliada de aplicação em MDE − 25 pontos percentuais

A leitura regional usa mínimo, mediana e máximo dos dez valores municipais. As margens não são somadas e não representam uma conta regional.

### Clima

A unidade de deduplicação é:

código IBGE textual de sete dígitos + protocoloS2id

Entram apenas registros MIDR com ano entre 2014 e 2025. Medidas diferentes associadas ao mesmo protocolo não geram novos eventos.

### Regulação

A maturidade descreve a disponibilidade do constructo, não a quantidade de arquivos examinados. A cobertura de 10/10 documentos pode coexistir com disponibilidade unavailable quando nenhum indicador mede o pacto educacional regional requerido.

## Lacunas que continuam abertas

- dias letivos perdidos, escolas afetadas, rotas interrompidas e execução de planos de continuidade;
- intensidade de uso tecnológico, qualidade da conexão, competências digitais e acesso domiciliar;
- custos incrementais das opções, compromissos plurianuais e capacidade futura de cofinanciamento;
- instrumentos regionais com responsabilidades, nível de serviço, financiamento, revisão e saída verificáveis.

Essas lacunas entram como perguntas de monitoramento ou hipóteses de cenário. Não são convertidas em zero, fato observado ou estimativa futura.

## Decisão de aquisição

Nenhum download foi necessário nesta revisão. Também não houve consulta a banco. Se uma evolução futura exigir uma das lacunas acima, o fluxo deve primeiro registrar a pergunta, o campo mínimo, a fonte pública candidata, o período, a unidade, o teto de inferência e a prova de ausência local; somente depois uma aquisição pode ser autorizada.
