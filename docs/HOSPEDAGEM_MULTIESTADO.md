# Hospedagem separada de RS, AL e PME RS

O mesmo repositório produz sites estáticos independentes. Cada projeto executa
um comando que fixa UF e experiência e materializa somente a raiz de dados
declarada pelo perfil selecionado.

| Produto | Situação de hospedagem | Comando de build | Saída | Dados |
| --- | --- | --- | --- | --- |
| RS atual | perfil existente | `npm run build:cloudflare:rs` | `dist` | raiz pública do RS |
| AL atual | perfil existente | `npm run build:cloudflare:al` | `dist` | raiz pública própria de AL |
| PME RS | preparação, ainda sem projeto externo | `npm run build:cloudflare:rs-pme` | `dist` | mesma raiz pública do RS |

## Preparação do projeto PME RS

Esta é uma ficha para criação posterior, não uma declaração de que o projeto já
existe. O nome proposto é `painel-sesi-rs-pme`. O repositório a conectar é
`https://github.com/rnbirck/dashboard-pne-react.git`; a referência local
registrada é `codex/rs-pme`, sem push implícito. A raiz do projeto é `.` e o build fixa
`RS/pme` pela CLI: `npm run build:cloudflare:rs-pme`, com diretório de saída
`dist`.

Conta, ID do projeto, domínio, branch de produção e ID de deploy permanecem
pendentes de autorização e estão nulos na ficha versionada
[`config/hosting/rs-pme-pages.json`](../config/hosting/rs-pme-pages.json). Ela
não é lida por Cloudflare Pages e não cria, configura ou publica um projeto.

Não defina `PLATFORM_STATE` no painel para substituir o comando: a CLI já fixa
o perfil. A aplicação navega por hash, portanto `index.html` precisa continuar
como fallback da SPA. O build não acessa banco, não consulta rede, não atualiza
fontes e não promove `public/data`.

## Validação antes de uma autorização de deploy PME

Em desenvolvimento, use `npm run dev:rs` em `http://127.0.0.1:5187`,
`npm run dev:al` em `http://127.0.0.1:5188` e `npm run dev:rs-pme` em
`http://127.0.0.1:5189`. Os builds app-only vão para `dist/app-only` (RS atual)
e `dist/app-only-rs-pme` (PME); eles não servem para publicação.

No aceite local, execute os testes PME unitários e E2E:

```powershell
npm run test:rs-pme
npm run test:rs-pme:e2e
```

O teste E2E reutiliza `http://127.0.0.1:5189` ou inicia um servidor local. A variável
`PME_E2E_BASE_URL` permite indicar outro endereço local. Depois da autorização de
release, construa as saídas completas em sequência e valide a paridade de dados:

```powershell
npm run build:rs
npm run build:rs-pme
npm run build:al
node scripts/checks/rs-experience-data-parity.mjs dist/rs/data dist/rs-pme/data
```

Não execute a checagem de paridade sem esses dois diretórios. O build de release
é explícito e continua sendo `npm run build:cloudflare:rs-pme`.
Os previews locais de releases existentes usam `preview:rs` (4187), `preview:al`
(4188) e `preview:rs-pme` (4189). Nenhum desses comandos publica externamente.

No smoke test autorizado, confira o perfil PME, seleção municipal, diagnóstico,
ausência e erro da Matriz, série pública como contexto, condições financeiras,
impressão/PDF do navegador e exportação XLSX de oito planilhas. Guarde commit,
manifests e ID de deploy. Rollback reverte somente o projeto PME para um deploy
PME anterior conhecido; não altera RS atual, AL ou dados publicados.

## Garantias de isolamento

- RS atual e PME RS usam a mesma raiz `/data`, mas builds e projetos distintos.
- AL usa sua raiz pública própria e não recebe fallback de RS.
- `config/publications/rs.json` declara `public/data`; a publicação AL declara
  `state-publications/al/data`, ambas com analytics completo.
- O build rejeita códigos, nomes, slugs, contagens ou diretórios municipais que
  não coincidam com o registro canônico selecionado. A raiz AL não contém
  identidade municipal `43xxxxx`.
- Os pipelines recebem a UF explicitamente e permanecem fail-closed; a
  hospedagem não inventa nem replica dados de outro estado.
- A experiência PME não tem backend, login, armazenamento ou IA.
- O panorama PME preserva 19 objetivos e 73 metas. Matriz, diagnóstico e séries
  mantêm seus estados e versões por domínio; ausência e erro não são confundidos.
- Séries brutas apenas contextualizam a observação diagnóstica. Condições
  financeiras não comprovam elegibilidade, vigência, saldo ou repasse.
- PDFs são produzidos pelo navegador; o XLSX possui oito planilhas e preserva
  fontes e versões dos domínios de origem.

## Fim de linha e fixtures

`.gitattributes` fixa `LF` para JSONs contratuais e fixtures de Vocações. Em
checkout Windows, isso evita mudar hashes por conversão de fim de linha; o
conteúdo versionado permanece o mesmo no Git.
