# Início em contexto limpo — publicação pública RS / PME

Este arquivo acompanha o [plano completo](PLANO_IMPLEMENTACAO_RS_PME.md). O plano foi criado em 7 de setembro de 2026; nenhuma etapa de implementação foi executada durante sua preparação.

## Texto para enviar no novo contexto

> Implemente o plano em `docs/PLANO_IMPLEMENTACAO_RS_PME.md` neste repositório, começando pela primeira etapa ainda pendente e avançando pelas dependências. Antes de editar, leia o plano, `AGENTS.md`, `README.md`, `PRODUCT.md`, `docs/ARQUITETURA.md`, `docs/OPERACAO.md` e `docs/HOSPEDAGEM_MULTIESTADO.md` conforme o escopo.
>
> O objetivo é criar uma segunda experiência pública do RS, orientada ao PME, mantendo a plataforma RS atual e a publicação AL. Usaremos o mesmo repositório e dados oficiais, entradas e navegação isoladas e um futuro projeto Cloudflare Pages com endereço próprio.
>
> Implemente todas as melhorias previstas: publicação dupla; percurso de leitura; panorama dos 19 objetivos; Agenda de Análise Municipal; fichas integradas; síntese na entrada municipal; financiamento transversal; síntese executiva, caderno por objetivo e agenda para discussão exportáveis. Inclua transparência, acessibilidade, impressão, testes e documentação operacional.
>
> A plataforma é limitada a dados públicos. Não crie contas, autenticação, uploads, anexos, importação de arquivos, formulários de contribuição, registros municipais, rascunhos locais, backend ou IA em runtime. O município consulta, filtra e exporta. Não implemente os fluxos de edição e aprovação do PME dos DOCX. Eles são referências de propostas; as restrições deste pedido prevalecem.
>
> Preserve fórmulas, fontes, schemas e metodologia existentes, a identidade por código IBGE textual de sete dígitos, os caminhos públicos e as rotas atuais. A Matriz pode faltar para um município: trate-a como enriquecimento opcional e distinga indisponibilidade de erro de integridade. Não invente resultados, causalidade, elegibilidade de programas ou conclusão do PME.
>
> Verifique o estado Git e preserve alterações preexistentes. Trabalhe em branch/checkout seguro sem trocar a branch de um checkout em uso. Use as skills aplicáveis e ferramentas nativas, com delegação seletiva quando justificada. Registre o avanço e as evidências no plano para permitir novas retomadas. Não considere o trabalho completo após somente a primeira fatia navegável.
>
> Esta execução autoriza a implementação local e suas verificações proporcionais. Não faça commit, push, PR, atualização de fontes/dados, acesso a banco ou publicação externa sem solicitação específica. Builds completos ficam para uma release/preview explicitamente autorizada; use os builds app-only durante o desenvolvimento. Prepare os arquivos e a configuração concreta de publicação para a etapa final. Se alguma ação externa depender de informação ou autorização, continue antes com todas as etapas locais independentes.

## Checklist de entrada

- Localizar o plano e verificar sua tabela de etapas e registro de execução; o estado descrito aqui é o da preparação.
- Executar `git status --short` e identificar o checkout atual sem reset, restore ou stash sobre trabalho alheio.
- Confirmar que as instruções locais aplicáveis foram preservadas se este for um novo checkout.
- Conferir os comandos existentes; os comandos PME listados no plano são propostos até sua implementação.
- Ao concluir uma etapa, registrar arquivos, testes, limitações e próximo passo no plano.

## Arquivos não versionados e outro checkout

Na preparação, o plano e este texto foram criados sem commit. Os três DOCX já estavam em `docs` como arquivos não rastreados e `AGENTS.md` tinha alterações preexistentes. Um worktree criado a partir do Git não inclui esses arquivos/alterações automaticamente.

Para começar sem perder o contexto necessário, abrir a nova conversa na mesma pasta ou transferir explicitamente o plano, este texto e as referências/instruções necessárias para o checkout escolhido. Antes de copiar, confirmar os caminhos absolutos, o estado Git do destino e a existência/hash ou conteúdo de cada arquivo. Copiar apenas quando o destino estiver ausente; reutilizar arquivos idênticos. Diante de conteúdo divergente, interromper a cópia daquele arquivo e reconciliar a origem, preservando o conteúdo existente. Isso não autoriza commit, sobrescrita de trabalho alheio ou limpeza do repositório.
