# Início em contexto limpo — publicação pública RS / PME

Este arquivo acompanha o [plano completo](PLANO_IMPLEMENTACAO_RS_PME.md), com preparação de commit autorizada em 9 de setembro de 2026. O worktree de continuidade é `C:/Users/rnbirck/PROJETOS/DASHBOARDS/PNE-REACT-RS-PME`, branch `codex/rs-pme`, base de implementação `909e858a5`. Consulte `git log -1` para o commit vigente e `git status` para alterações locais. O checkout original `PNE-REACT` permanece em `main` e contém o planejamento anterior, sem esta implementação.

E0–E9 estão concluídas e verificadas localmente; as evidências estão no plano. E10 tem ficha, comandos e gate de paridade prontos, mas não existe projeto Pages provisionado por esta execução. Conta, projeto real, domínio, branch de produção, build de release e deploy dependem de solicitação específica. Não reiniciar a implementação dos recursos já entregues.

## Texto para enviar no novo contexto

> Retome o plano `docs/PLANO_IMPLEMENTACAO_RS_PME.md` no worktree `C:/Users/rnbirck/PROJETOS/DASHBOARDS/PNE-REACT-RS-PME`, branch `codex/rs-pme`. Primeiro leia o estado por etapa e o aceite local registrado no plano, depois confira `AGENTS.md`, README, arquitetura, operação e hospedagem conforme o escopo. Preserve eventuais alterações locais. As melhorias já foram implementadas e o usuário autorizou seu commit em 9 de setembro de 2026; não recomece E1–E9 nem copie arquivos sobre o checkout original.
>
> A próxima etapa externa é E10, cuja preparação concreta está em `config/hosting/rs-pme-pages.json`. Este texto de retomada não autoriza commit, push, PR, build completo, atualização de fontes/dados, banco ou publicação. Quando houver uma solicitação específica, utilize os gates e o procedimento de release/rollback documentados. Preserve as experiências RS atual, RS PME e AL atual, os dados e a identidade municipal por IBGE textual.
>
> A plataforma continua limitada a consulta, filtros e exportação de dados públicos. Não acrescentar autenticação, uploads, anexos, formulários de contribuição, rascunhos, backend ou IA em runtime. Verifique o estado real antes de qualquer nova ação, reutilize evidências ainda válidas e registre somente o que foi efetivamente executado.

## Pedido de implementação executado — histórico

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

- Localizar o worktree de continuidade e consultar a tabela de etapas e o aceite local no plano.
- Executar `git status --short` e identificar o checkout atual sem reset, restore ou stash sobre trabalho alheio.
- Confirmar que as instruções locais aplicáveis foram preservadas se este for um novo checkout.
- Os comandos PME de desenvolvimento, app-only, testes e futura release estão implementados. `test:rs-pme:e2e` pode iniciar seu próprio servidor local; não executar builds completos por rotina.
- Preservar a junction de dependências e os apoios ignorados necessários à reprodução, inclusive o manifesto usado pelo teste existente da Matriz; o plano registra origem e hash.
- Ao concluir uma etapa, registrar arquivos, testes, limitações e próximo passo no plano.

## Arquivos não versionados e outro checkout

Na preparação, o plano e este texto foram criados sem commit. Os três DOCX já estavam em `docs` como arquivos não rastreados e `AGENTS.md` tinha alterações preexistentes. Um worktree criado a partir do Git não inclui esses arquivos/alterações automaticamente.

Para começar sem perder o contexto necessário, abrir a nova conversa na mesma pasta ou transferir explicitamente o plano, este texto e as referências/instruções necessárias para o checkout escolhido. Antes de copiar, confirmar os caminhos absolutos, o estado Git do destino e a existência/hash ou conteúdo de cada arquivo. Copiar apenas quando o destino estiver ausente; reutilizar arquivos idênticos. Diante de conteúdo divergente, interromper a cópia daquele arquivo e reconciliar a origem, preservando o conteúdo existente. Isso não autoriza commit, sobrescrita de trabalho alheio ou limpeza do repositório.
