# Plano de integração de foresight à plataforma PNE

## Objetivo

Integrar quatro cenários educacionais regionais à plataforma sem duplicar o diagnóstico de Vocações e sem depender de coleta primária. A educação é tratada em interação com demografia, economia e trabalho, condições sociais, território, tecnologia, clima, financiamento e governança.

## Arquitetura-alvo

1. Vocações produz o diagnóstico canônico.
2. O contrato de Cenários referencia evidências diagnósticas por ID.
3. O gerador valida as referências e não copia os textos.
4. Dados públicos locais amadurecem os transversais.
5. Cinco fatores formam o campo morfológico.
6. Quatro configurações com distância mínima geram futuros alternativos.
7. Cada futuro recebe seis domínios, quatro efeitos distributivos e uma lente de Nova Santa Rita.
8. As metas fixas do PNE são testadas sob condições de execução distintas.
9. Opções e sentinelas permitem agir e revisar sem escolher um futuro vencedor.
10. Bundle e registro são gerados em staging, validados e promovidos juntos.

## Etapas implementadas

### Etapa 1 — Fronteira editorial

Concluída.

- retirado o baseline regional e municipal da publicação;
- criada ponte para Vocações com 18 IDs resolvidos;
- implementado gate de strings longas, com zero exceções;
- retirado qualquer módulo comparativo entre municípios.

### Etapa 2 — Transversais públicos

Concluída.

- clima: protocolos MIDR deduplicados;
- tecnologia: razões ponderadas de infraestrutura escolar;
- fiscal: distribuição de margens MDE reconciliadas;
- regulação: proxy inadequado excluído e lacuna preservada;
- cobertura de 10/10 municípios nos três tipos de entrada.

### Etapa 3 — Produto e interface

Concluída no código.

- página reorganizada pela sequência fronteira → forças → futuros → Nova Santa Rita → PNE → opções → sentinelas → método;
- limites de inferência exibidos em cada transversal;
- método e hashes visíveis;
- somente uma lente municipal publicada.

### Etapa 4 — Gates permanentes

O encerramento exige:

- geração e check determinísticos;
- teste de fórmulas independente do gerador;
- teste de digest das 30 entradas;
- teste de não duplicação;
- teste de contrato e loader fail-closed;
- teste de página e E2E em desktop, tablet, mobile e impressão;
- typecheck, lint, check:fast e diff check;
- segunda opinião final pelo Fable, tratada como consultiva.

## Evolução com dados públicos

Prioridades futuras, sem aquisição automática:

1. continuidade educacional: dias perdidos, escolas e rotas afetadas;
2. tecnologia: uso, qualidade, competências e acesso domiciliar;
3. custo das opções: recorrência, compromisso plurianual e saída;
4. colaboração: instrumentos, responsabilidades, nível de serviço, cofinanciamento e revisão.

Para avançar em qualquer item, primeiro é necessário provar que o campo não existe localmente. Só então se documenta fonte pública candidata, período, unidade, teto de inferência, preservação do bruto e fluxo transacional.

## Critério de sucesso

A integração é bem-sucedida quando a plataforma consegue responder:

- quais combinações de mudanças podem pressionar a educação;
- por quais mecanismos econômicos, demográficos, sociais e territoriais;
- quem pode ganhar ou perder em cada futuro;
- como Nova Santa Rita fica exposta;
- quais metas do PNE são favorecidas ou pressionadas;
- quais ações são robustas, contingentes ou reversíveis;
- quais sinais mudariam a decisão;
- qual dado sustenta cada afirmação e qual afirmação o dado não sustenta.
