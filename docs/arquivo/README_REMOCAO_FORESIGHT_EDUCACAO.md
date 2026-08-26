# Arquivo morto — Cenários da educação municipal (`foresight-educacao`)

**Removido da plataforma em 2026-08-25**, na Rodada 1 do plano
`docs/PLANO_VOCACOES_REGIAO_V2.md` (execução da decisão **D11** do
`docs/PLANO_VOCACOES_REGIAO_V1.md`).

## O que foi removido

O produto `foresight-educacao` — os *Cenários da educação municipal* — saiu por
inteiro do repositório: página, loader, hook, domínio de publicação, contrato e
dados públicos (`public/data/foresight-educacao/`), gerador, quatro suítes de
teste, `tsconfig` próprio, folha de estilo, quatro scripts do `package.json`, o
item de menu, a rota e o registro de publicação do piloto. Não é despromoção nem
arquivamento do produto — é remoção.

## Por que estes dois documentos ficam aqui

`BRIEFING_FORESIGHT_EDUCACAO_MUNICIPAL.md` e
`FORESIGHT_EDUCACAO_INTEGRACAO_PLATAFORMA_V0_4_0_RC4.md` são o briefing original
e o gabarito de publicação do produto. Foram **movidos para cá, não apagados do
histórico**, porque registram a metodologia e a decisão de integração que
antecederam a remoção. O histórico de git preserva o restante.

## O que substitui

A decisão D11 define a sucessora: **não** o cenário regional sozinho, e sim uma
camada nova — os cenários da região acrescidos de como cada município dela
contribui para o cenário e é afetado por ele. Essa camada é trabalho da Rodada 5
do V2; a camada de pesquisa municipal (`SESI\PNE\foresight\`) permanece fora
deste repositório e será inventariada lá para decidir reuso.

## O que não mudou

O produto regional que fica no ar — **Vocações da Região** — não depende mais do
municipal. Os três pontos de acoplamento (o teste da D3 lia o `schema.json`
municipal; o `schema.json` regional citava a família municipal em `distinctFrom`;
o gerador escrevia esse nome) foram portados antes da remoção, e a decisão D3
passou a ser declarada como **regra única** da família regional no contrato
público `vocacoes-regiao-2.2.0`.
