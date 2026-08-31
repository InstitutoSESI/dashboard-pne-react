# Contrato de produto — Cenários da Educação

## Estatuto

O produto é um modelo exploratório auditado com dados públicos. Não é previsão, ranking, recomendação automática ou posição institucional.

## Escopo

- região: Vale do Sinos;
- cobertura das entradas: dez municípios;
- lente municipal publicada: Nova Santa Rita, código IBGE textual 4313375;
- horizonte: 2036;
- checkpoint: 2030–2031;
- cenários: quatro, com peso equivalente.

## Contrato do bundle

Schema: vocacoes-pne-foresight-v2.

Blocos obrigatórios:

- identidade e política de publicação;
- ponte diagnóstica;
- snapshot de fontes;
- seis domínios;
- cinco fatores;
- quatro transversais;
- matriz de impactos cruzados;
- campo morfológico;
- quatro cenários;
- uma lente municipal;
- teste do PNE;
- dez opções;
- doze sentinelas;
- governança metodológica;
- gate de qualidade.

Blocos proibidos:

- baseline narrativo copiado;
- lista regional de municípios no bundle;
- probabilidades ou ranking;
- segunda lente municipal;
- recomendação automática;
- alegação de aprovação institucional.

## Ponte diagnóstica

A ponte publica rota, descritores de fonte, IDs, contagens e auditoria de não duplicação. Ela não publica valor, cartão, série ou narrativa do diagnóstico.

## Transversais

Cada transversal precisa declarar:

- maturidade;
- classe de evidência;
- disponibilidade;
- período;
- lente;
- cobertura;
- plano de evidência;
- uso nos cenários;
- teto de afirmação;
- lacuna restante;
- referências de fonte.

Maturidades diferentes são esperadas. Cobertura de arquivo não equivale à disponibilidade do constructo.

## Registro

Schema: vocacoes-pne-foresight-registry-v2.

O registro vincula hash e tamanho do bundle, versão de conteúdo, contagens, distância mínima, status do gate, hash do diagnóstico, hash da matriz PNE focal e digest agregado das 30 entradas públicas.

## Falha fechada

Qualquer ausência, divergência de hash, identidade, cobertura, fórmula, referência, distância, status ou duplicação impede a publicação e a exibição do pacote parcial.
