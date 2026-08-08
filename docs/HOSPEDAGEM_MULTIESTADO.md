# Hospedagem separada de RS e AL

O mesmo repositório produz dois sites independentes. Cada projeto de hospedagem
executa um comando que fixa a UF e copia somente a raiz de dados declarada no
manifesto correspondente.

| Projeto | Comando de build | Diretório de saída | Cobertura |
| --- | --- | --- | --- |
| RS | `npm run build:cloudflare:rs` | `dist` | PNE, Educação e Financeiro completos |
| AL | `npm run build:cloudflare:al` | `dist` | cadastro oficial dos 102 municípios e Educação; PNE e Financiamento indisponíveis |

## Cloudflare Pages

Crie dois projetos Pages apontando para o mesmo repositório e para a mesma
branch de produção. Configure em cada projeto o comando e o diretório da tabela
acima. Associe um domínio diferente a cada projeto, por exemplo um endereço para
RS e outro para AL.

Não é necessário definir `PLATFORM_STATE` no painel quando os comandos
`build:cloudflare:*` são usados: eles já fixam a UF de forma explícita. O build
não acessa banco, não consulta rede e não atualiza fontes. Ele apenas valida o
perfil versionado e empacota os ativos correspondentes.

A aplicação navega por hash (`#home`, `#pne2026`), então o documento solicitado
ao servidor continua sendo `index.html`. Não adicione um `404.html` que possa
alterar esse comportamento de SPA.

## Validação local antes do deploy

```powershell
npm run test:state-publication
npm run test:multistate-hosting
npm run build:rs
npm run build:al
```

Os builds locais ficam em `dist/rs` e `dist/al`. Para inspecioná-los:

```powershell
npm run preview:rs
npm run preview:al
```

Durante desenvolvimento, use `npm run dev:rs` em
`http://127.0.0.1:5187` e `npm run dev:al` em
`http://127.0.0.1:5188`.

## Garantias de isolamento

- `config/publications/rs.json` aponta para `public/data` e exige analytics
  completo.
- `config/publications/al.json` aponta para `state-publications/al/data` e
  declara `partial` com somente `educacao` habilitada.
- O build rejeita códigos, nomes, slugs, contagens ou diretórios municipais que
  não coincidam com o registro canônico selecionado.
- A raiz AL contém o catálogo canônico, Educação básica, Superior e Especial.
  Não contém PNE, Financiamento nem qualquer identidade municipal 43xxxxx.
- O pipeline educacional aceita RS e AL com filtro explícito de UF. Os produtos
  ainda não publicados permanecem fail-closed; a hospedagem não inventa nem
  replica dados do RS.
