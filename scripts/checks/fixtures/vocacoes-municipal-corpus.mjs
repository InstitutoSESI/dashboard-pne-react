/*
 * Corpus bilateral da camada municipal (Rodada 5 do V2, sucessora da D11).
 *
 * A guarda `checkMunicipalText` corre sobre a composição e a exposição de cada
 * município. Quatro vetores são próprios desta camada — número futuro municipal,
 * probabilidade atribuída a município, ranking implícito de municípios e
 * causalidade município↔região — e cada um é atacado aqui de várias formas, e
 * exercido também pelo seu par honesto: a negação da mesma frase, que a camada
 * PRECISA poder dizer. Falso positivo sobre a ressalva honesta é defeito tão
 * grave quanto falso negativo (§5.5 do plano herdado).
 */

/** Ataques: cada um DEVE ser recusado por `checkMunicipalText`. */
export const ATTACKS = Object.freeze([
  // Número futuro municipal (ano à frente do de referência).
  ['fut-ano', 'Em 2031, o município terá 1.500 matrículas no ensino médio.'],
  ['fut-ano-split', 'No ano 20 31, o município chega a 900 nascidos vivos.'],
  ['fut-relativo', 'Daqui a cinco anos, o município terá mil nascidos vivos a mais.'],
  ['fut-proximos', 'Nos próximos anos, o município somará 2.000 famílias no cadastro.'],
  ['fut-sem-ano', 'O município alcançará 1.500 matrículas.'],
  ['fut-modal', 'O município deverá alcançar 1.500 matrículas.'],
  ['fut-espera', 'Espera-se que o município alcance 1.500 matrículas.'],
  ['fut-tendencia', 'A tendência aponta 1.500 matrículas para o município.'],
  // Probabilidade atribuída a um município.
  ['prob-pct', 'Este município tem 70% de probabilidade de seguir o cenário de continuidade.'],
  ['prob-chance', 'Há uma chance de o município acompanhar a trajetória do cenário.'],
  ['prob-provavel', 'É provável que o município siga o cenário de modernização.'],
  ['prob-risco', 'O risco de o município perder matrículas neste cenário é alto.'],
  ['prob-tende', 'O município tenderá a acompanhar o cenário de descompasso.'],
  ['prob-possibilidade', 'Há 70% de possibilidade de o município seguir o cenário.'],
  ['prob-plausivel', 'É plausível que o município siga o cenário.'],
  ['prob-modal', 'O município deve seguir este cenário.'],
  ['prob-tendencia', 'A tendência do município é seguir o cenário.'],
  // Ranking implícito de municípios.
  ['rank-mais-exposto', 'Este é o município mais exposto ao cenário da região.'],
  ['rank-menos', 'Entre os vinte e três, é o município menos exposto ao cenário.'],
  ['rank-vulneravel', 'É o município mais vulnerável do cenário de quebra.'],
  ['rank-ordena', 'A camada ordena os municípios por exposição ao cenário.'],
  ['rank-classifica', 'A leitura classifica os municípios por exposição ao horizonte.'],
  ['rank-maior-exposicao', 'Este município concentra a maior exposição da região.'],
  ['rank-primeira-posicao', 'Este município ocupa a primeira posição em exposição.'],
  ['rank-supera', 'A exposição deste município supera a dos demais.'],
  ['rank-grupo', 'O município está no grupo de maior exposição da região.'],
  ['rank-superior', 'Só dois municípios têm exposição superior a esta.'],
  ['rank-elipse', 'É o de maior exposição na região.'],
  // Causalidade município ↔ região.
  ['causa-regiao-explica', 'O resultado do município se explica pela estrutura da região.'],
  ['causa-regiao-determina', 'A região determina o resultado do município neste cenário.'],
  ['causa-municipio-explica', 'O município explica o resultado da região no cenário.'],
  ['causa-municipio-torna', 'A posição do município o torna causa do resultado da região.'],
  ['causa-palavra', 'A baixa participação do município causou a queda observada na região.'],
  ['causa-explica-porque', 'O perfil da região explica por que o município abandona a escola.'],
  ['causa-determina-trajetoria', 'A participação municipal determina a trajetória regional.'],
  ['causa-molda', 'A região molda o desempenho do município.'],
  ['causa-define', 'A estrutura regional define o resultado municipal.'],
  ['causa-responde', 'A composição local responde pelo rumo da região.'],
])

/** Honestos: cada um DEVE passar por `checkMunicipalText`. */
export const HONEST = Object.freeze([
  ['comp-share', 'População de 0 a 14 anos: 2,8% do total da região, com participação acima da mediana dos municípios da região (pessoas de 2022).'],
  ['comp-rate', 'Taxa de abandono no ensino médio: 2,0%, acima da mediana municipal da região (2025).'],
  ['comp-below', 'Nascidos vivos por residência da mãe: 1,1% do total da região, com participação abaixo da mediana dos municípios da região (nascidos vivos de 2024).'],
  ['exp-observado', 'Neste cenário, a posição observada do município na região aparece na composição ao lado.'],
  // As negações honestas dos quatro vetores — a camada precisa poder dizê-las.
  ['neg-projecao', 'Esta camada não atribui número municipal a ano futuro.'],
  ['neg-probabilidade', 'A leitura não atribui probabilidade a um município.'],
  ['neg-ranking', 'A camada não ordena os municípios por exposição.'],
  ['neg-causa', 'A composição do município não explica o resultado da região.'],
  ['neg-regiao-causa', 'A região não explica o resultado do município.'],
  // Composição descritiva, sem gatilho.
  ['desc-mediana', 'A composição observada situa o município ante a mediana dos municípios da região.'],
  ['desc-participacao', 'A participação do município no cadastro social é a parcela dele no total inscrito da região.'],
  // Negações honestas dos novos sinônimos e formas de projeção/ranking.
  ['neg-futuro-sem-ano', 'Não se espera que o município alcance um valor predeterminado.'],
  ['neg-possibilidade', 'Não se atribui possibilidade de o município seguir o cenário.'],
  ['neg-maior-exposicao', 'A camada não afirma que o município concentra a maior exposição.'],
  ['neg-molda', 'A região não molda o desempenho do município nesta leitura.'],
])

/*
 * Furos de classe aberta — ataques que a guarda ainda NÃO fecha, e que ficam
 * declarados como abertos. Fechá-los exigiria semântica, não léxico: a leitura
 * de exposição por sugestão, sem palavra de probabilidade nem de ranking.
 */
export const DECLARED_GAPS = Object.freeze([
  ['gap-sugestao', 'Um ano de quebra pesaria mais aqui do que na maior parte da região.'],
  ['gap-ordem-implicita', 'Poucos municípios reúnem uma composição tão frágil quanto a deste.'],
])
