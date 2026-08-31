# Cenários da Educação

Esta pasta documenta a camada prospectiva integrada à plataforma PNE para o Vale do Sinos, com lente municipal em Nova Santa Rita.

A separação editorial é obrigatória:

- Vocações da Região mantém o diagnóstico factual;
- Cenários da Educação usa referências ao diagnóstico para construir quatro futuros alternativos, impactos, opções e sentinelas;
- a página não apresenta comparação entre municípios;
- o fluxo usa somente dados públicos e locais;
- revisão externa é consultiva e não representa aprovação institucional.

## Documentos canônicos

- MANIFESTO_REDESIGN_DADOS_PUBLICOS.md: fronteira editorial, arquitetura, gates e critérios de aceite;
- INVENTARIO_TRANSVERSAIS_DADOS_PUBLICOS.md: fontes, fórmulas, resultados e lacunas;
- PLANO_IMPLEMENTACAO.md: integração técnica e evolução;
- CONTRATO_PRODUTO.md: contrato público do bundle e da página;
- MATRIZ_ACEITE_IMPLEMENTACAO.md: rastreabilidade entre requisito e teste;
- GLOSSARIO.md: vocabulário metodológico.

## Operação

Gerar e promover bundle e registro:

    npm run generate:cenarios-educacao

Conferir determinismo e aderência aos arquivos promovidos:

    npm run check:cenarios-educacao

Executar a suíte do domínio:

    npm run test:cenarios-educacao
    npm run test:cenarios-educacao:e2e

O gerador lê 30 arquivos públicos já locais, o bundle avançado de Vocações, os registros canônicos e o contrato de autoria. Ele não acessa rede, não consulta banco e não escreve em public/data.
