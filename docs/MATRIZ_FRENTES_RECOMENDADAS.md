# Matriz de Prioridades — frentes recomendadas para avançar

Documento de decisão editorial. Registra a substituição da lógica de **causas
identificadas** pela lógica de **frentes recomendadas para avançar** no piloto de
Nova Santa Rita/RS (IBGE 4313375), decidida em 2026-08-18.

- Antecedente: `docs/MATRIZ_DE_PRIORIDADES.md` (construção da matriz por causas).
- O artefato publicado (`public/data/pne2026-matriz/`) **não muda**: metas,
  indicadores, resultados, severidade e comparação com pares seguem como estão.
  A mudança é inteiramente na camada editorial e de interface da plataforma.

---

## 1. Regra central

> **A orientação oficial define as frentes; os dados municipais ajudam a
> contextualizá-las; a plataforma não declara qual é a causa local.**

Consequências práticas:

1. A unidade de tela deixa de ser "causa posicionada por sinal local" e passa a
   ser **frente recomendada**, derivada das estratégias do PNE 2026–2036, das
   orientações do Novo PAR e dos programas e instrumentos do MEC/FNDE.
2. Nenhum texto afirma que um fator foi comprovado no município.
3. Somem da página: "evidência insuficiente", "não é possível verificar",
   "fica para a oficina", perguntas que dependem de preenchimento da prefeitura,
   e a palavra "causa" em qualquer flexão.
4. Fatores amplos (transporte, clima, gestão, busca ativa) só aparecem quando a
   ligação com o indicador é direta e concreta — ex.: busca ativa entra na meta
   de **acesso 6–17** (a meta é exatamente encontrar quem está fora), não como
   pano de fundo genérico de aprendizagem.
5. Referências legais aparecem em uma linha discreta ao pé de cada frente
   ("Base: PNE 2026–2036 — meta 4.a e estratégia 4.10"), nunca como texto
   normativo corrido.
6. Dados de Nova Santa Rita entram no **caminho correspondente**, apenas quando
   ajudam a escolher o que investigar ou quem precisa agir. Cada meta tem no
   máximo dois caminhos. Sem dado útil, permanece a verificação concreta — nunca
   uma mensagem de ausência.

## 2. O que se mantém do piloto publicado

- As **7 metas prioritárias** com valor, referência, ano e unidade.
- A leitura de severidade ("atenção maior" / "atenção") e a comparação com as 88
  cidades parecidas do RS — tudo vindo do artefato, sem recálculo.
- O bloco recolhido de outras metas abaixo do esperado e o bloco "onde o
  município está bem".
- Os cartões recolhidos por padrão, sem seleção, anotação ou exportação de plano
  na página.

## 3. O que sai

- Lista "O que pode estar segurando" e o detalhe de causa (prova, cautela,
  perguntas de oficina, primeiro passo de verificação).
- Blocos "outras causas possíveis" e "fora do alcance municipal".
- Rótulo de governabilidade por causa ("a prefeitura pode agir" etc.).
- O adaptador de exportação que reaproveitava a planilha do caderno.

## 4. Anatomia dos caminhos

Cada meta apresenta uma única seção, **Caminhos para avançar**:

1. um parágrafo curto que indica o foco da decisão;
2. exatamente dois cartões, cada um ligando um mecanismo plausível a um caminho
   de ação;
3. em cada cartão, no máximo um fato municipal, uma verificação local e um
   resultado esperado;
4. etapas, apoio federal, base legal e aprofundamento no painel ficam recolhidos
   sob demanda.

Essa estrutura adapta a escada de evidência do Vocações — fato observado,
mecanismo plausível e verificação — sem converter associação em explicação
comprovada.

Cada meta apresenta **2 caminhos**, em cartões compactos e sem modal:

1. **Título do caminho** — verbo de ação, concreto.
2. **Contexto essencial** — 1 frase simples sobre o mecanismo que torna o
   caminho relevante. Nunca uma acusação de causa local.
3. **Fato municipal**, quando muda a decisão — com frase de uso e limite.
4. **Antes de agir, confira** — verificação concreta em registros ou escolas.
5. **Resultado esperado** — 1 entrega verificável, visível antes do detalhe;
   não define prazo nem responsável.
6. **Etapas sugeridas** — 2 ou 3 passos práticos extraídos da orientação federal.
7. **Apoio federal** — programas e instrumentos com link oficial quando estável.
8. **Base legal** — linha pequena e muda de cor, com meta e estratégias.
9. **Informações relacionadas no painel** — no máximo um aprofundamento interno,
   preservando o município selecionado.

No desktop, os cartões de uma meta ficam lado a lado, cada um com sua própria
altura; no celular, empilham.

## 5. As frentes do piloto (conteúdo integral em `src/features/matriz/matrizFrentes.ts`)

| meta | frentes |
|---|---|
| 1.a Creche | Conhecer a procura por vaga · Ampliar a oferta com apoio federal |
| 5.a Aprendizagem anos iniciais | Avaliar e recompor as aprendizagens · Apoio pedagógico da secretaria às escolas |
| 11.c Conclusão do médio 18+ | EJA compatível com quem trabalha · EJA integrada à formação profissional |
| 17.a Formação docente | Formar os professores na área em que atuam · Carreira que atraia e fixe professores habilitados |
| 4.a Acesso 6–17 | Encontrar e rematricular quem está fora · Preparar a rede para eventos climáticos |
| 4.b Conclusão do 5º ano na idade | Alfabetizar na idade certa · Acompanhar trajetórias e recompor |
| 19.c Infraestrutura mínima | Acessibilidade dos prédios e salas · Investimento por padrões mínimos |

Programas e instrumentos citados: Novo PAR, Proinfância/Novo PAC, Busca Ativa
Escolar, Compromisso Nacional Criança Alfabetizada, PNLD, Pé-de-Meia, Pacto
Nacional da EJA, Parfor, UAB, Mais Professores para
o Brasil, piso nacional do magistério, PDDE, S2iD/Defesa Civil. Links só quando
a página oficial é estável; caso contrário, o programa aparece nomeado sem link.

## 6. Guarda-corpos testados em código

O check de linguagem da matriz é reescrito para o novo contrato:

- Preserva as 7 situações numéricas, a leitura de pares e os rótulos de
  severidade.
- Toda meta prioritária rende exatamente 2 caminhos; total de 14 no piloto.
- Todo caminho possui exatamente 1 resultado esperado, com uma única frase e
  teto editorial de 160 caracteres, exibido antes do conteúdo expandido.
- Proíbe no HTML renderizado: "causa" (qualquer flexão), "oficina",
  "evidência insuficiente", "não é possível verificar", vocabulários técnicos
  (`factorId`, `measureId`, inferências, `placementRationale`), identificadores
  `F_*` e nomes de medida.
- Dados municipais vêm do artefato da matriz ou da publicação validada de
  Educação; medida sem rótulo e consequência prática não aparece.
- Cada meta tem exatamente dois mecanismos, ligados um a um aos dois caminhos;
  cada cartão termina a análise com uma verificação local concreta.
- A página não oferece seleção, anotação nem exportação de plano de ação.

## 7. Fora de escopo (deliberado)

- Demais municípios: o desenho é validado primeiro no piloto.
- Artefato e camada de pesquisa (`SESI\PNE`): intocados.
- Caderno de hipóteses: segue o plano de deleção já registrado, sem mudanças
  aqui. **Estado em 2026-08-24:** a deleção foi executada — o caderno não existe
  mais na plataforma e o conteúdo permanece recuperável no git
  (`git show 91f061e61:docs/CADERNO_HIPOTESES.md`).
