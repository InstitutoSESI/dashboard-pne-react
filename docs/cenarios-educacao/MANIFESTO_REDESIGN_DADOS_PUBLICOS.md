# Manifesto do redesenho público de Cenários da Educação

## Decisão de produto

A plataforma passa a manter duas funções editoriais separadas:

- Vocações da Região é a camada diagnóstica canônica. Ela apresenta fatos observados, séries, relações, ruralidade, AEE e contexto social registrado.
- Cenários da Educação é a camada prospectiva. Ela apresenta incertezas, configurações alternativas, mecanismos, efeitos distributivos, implicações para Nova Santa Rita, teste de estresse do PNE, opções e sentinelas.

Cenários não republica cartões, sinais ou narrativas diagnósticas. O vínculo entre as duas seções é uma ponte compacta com rota, hashes e IDs de evidência resolvidos.

## O que foi retirado

- narrativa de ponto de partida regional e municipal;
- cartões de evidência já apresentados em Vocações;
- qualquer seção de comparação entre dois municípios;
- matriz PNE ou lente de um segundo município;
- recibo, gate, comandos e materiais operacionais baseados em encontro presencial;
- status que pudesse sugerir aprovação institucional;
- transversais uniformemente marcados como imaturos quando já havia dados públicos locais.

Não foi criado ranking, benchmark, par substituto ou quinto cenário.

## O que permanece

- quatro futuros alternativos, sem probabilidade e com peso equivalente;
- cinco fatores morfológicos;
- seis domínios educacionais integrados a economia, demografia, condições sociais, território, financiamento e governança;
- uma lente municipal explícita para Nova Santa Rita;
- sete metas do PNE no teste de estresse;
- dez opções de decisão e doze sentinelas;
- limites de inferência e distinção entre zero, null, indisponível, suprimido e não aplicável.

## Ponte diagnóstica

O contrato mantém 18 seletores internos para validar as referências usadas pelos cenários. A publicação expõe somente os IDs. Na geração:

1. cada seletor localiza coleção, registro e índice no bundle canônico de Vocações;
2. a disponibilidade e o valor são validados sem copiar a narrativa;
3. cada referência usada em cenário ou lente municipal precisa existir no índice resolvido;
4. referência ausente encerra a geração;
5. o bundle registra contagem total e contagem resolvida.

## Gate de não duplicação

O algoritmo usa:

- normalização Unicode NFKC;
- conversão para minúsculas com locale pt-BR;
- colapso de espaços;
- comparação exata de strings com pelo menos 80 caracteres;
- escopo: transversais, impactos cruzados, cenários, lente municipal, PNE, opções e sentinelas;
- lista de exceções vazia.

A geração falha se uma afirmação longa de Cenários também existir no diagnóstico canônico. O bundle atual registra 0 duplicações.

## Gate de dados públicos

A publicação só passa quando todos os itens abaixo são verdadeiros:

- hashes e tamanhos das fontes válidos;
- 10/10 details.json, 10/10 financeiro.json e 10/10 matrizes PNE;
- identidades municipais textuais preservadas;
- ano e unidade coerentes;
- numeradores e denominadores finitos;
- aplicação em MDE reconciliada;
- protocolo climático deduplicado;
- proxy regulatório excluído do constructo inadequado;
- todas as referências diagnósticas resolvidas;
- quatro cenários e distância morfológica mínima;
- zero probabilidade, ranking ou recomendação automática;
- zero afirmação de aprovação institucional;
- materialização determinística;
- promoção conjunta de bundle e registro somente após validação em staging.

## Fluxo na plataforma

dados públicos locais → validação e digest → transversais → campo morfológico → quatro futuros → lente de Nova Santa Rita → teste do PNE → opções e sentinelas

A página segue a mesma ordem:

1. fronteira com Vocações;
2. incertezas e transversais;
3. quatro futuros;
4. Nova Santa Rita;
5. PNE;
6. opções;
7. sentinelas;
8. método e fontes.

## Regra de aquisição futura

O gerador não acessa rede e não consulta banco. Uma fonte pública adicional só deve ser adquirida se:

1. a pergunta prospectiva exigir um campo não coberto;
2. a ausência local estiver comprovada;
3. a fonte, URL, período, layout, unidade e teto de inferência estiverem documentados;
4. aquisição, normalização, validação, materialização e promoção forem separadas;
5. bruto, manifesto, data de referência, hash e cobertura forem preservados.

Ausência de dado não autoriza download genérico nem coleta sem contrato.

## Estatuto da revisão externa

A revisão independente por outro modelo funciona como segunda opinião técnica. Ela não substitui participação social, decisão de gestão, validação institucional, certificação metodológica ou aprovação de política pública.

## Critérios de aceite

- 4 cenários e distância Hamming mínima 4;
- 10 municípios cobertos pelos três tipos de entrada pública;
- 18/18 referências diagnósticas resolvidas;
- 0 afirmações diagnósticas copiadas;
- 0 duplicações longas;
- 3 transversais sustentados por evidência pública e 1 lacuna explícita;
- somente Nova Santa Rita como lente municipal publicada;
- nenhuma seção comparativa;
- nenhum fluxo operacional dependente de encontro presencial;
- nenhum download, banco ou escrita em public/data;
- testes de publicação, loader, página, E2E, typecheck, lint e check:fast aprovados.
