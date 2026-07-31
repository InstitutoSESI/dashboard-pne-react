/*
 * Dominio do eixo Y para escalas limitadas (percentual, IDEB, INSE).
 *
 * O painel usava dominio fixo (0-100 para todo percentual). Isso desperdicava
 * 60-75% da area de plotagem quando a serie vivia entre 88% e 100%: a linha
 * virava um traco colado no topo e a leitura se perdia.
 *
 * O oposto -- ajustar o eixo colado nos dados -- seria pior: transformaria uma
 * variacao de 2 p.p. numa escalada dramatica, e o produto se propoe a descrever
 * sem alarmar (PRODUCT.md, principio 5).
 *
 * A regra aqui fica no meio: usa a area disponivel, mas impoe um VAO MINIMO
 * VISIVEL por tipo de escala. Uma serie que varia 2 p.p. continua ocupando
 * 2/20 da altura, e nao a altura inteira.
 *
 * A referencia normativa (meta) entra no calculo sempre que existir, para que
 * a linha de meta nunca caia fora do grafico.
 */

export const MIN_VISIBLE_SPAN = Object.freeze({
  ideb: 2,
  inse: 2,
  percent: 20,
})

export const SCALE_HARD_MAX = Object.freeze({
  ideb: 10,
  inse: 10,
  percent: 100,
})

export function niceStep(value) {
  if (!Number.isFinite(value) || value <= 0) return 1
  const power = 10 ** Math.floor(Math.log10(value))
  const normalized = value / power
  const multiplier = normalized <= 1
    ? 1
    : normalized <= 2
      ? 2
      : normalized <= 2.5
        ? 2.5
        : normalized <= 5
          ? 5
          : 10
  return multiplier * power
}

/**
 * @param {number[]} values valores da serie (e da meta, quando houver)
 * @param {'percent'|'ideb'|'inse'} scaleType
 * @param {{allowPercentOverflow?: boolean}} options
 */
export function getBoundedDomain(values, scaleType, options = {}) {
  const usable = values.filter((value) => Number.isFinite(value))
  if (!usable.length) return { max: SCALE_HARD_MAX[scaleType] ?? 100, min: 0 }

  const hardMax = SCALE_HARD_MAX[scaleType] ?? 100
  const minSpan = MIN_VISIBLE_SPAN[scaleType] ?? hardMax / 5
  const minVal = Math.min(...usable)
  const maxVal = Math.max(...usable)
  const allowPercentOverflow = options.allowPercentOverflow ?? true
  const upperBound = (
    scaleType === 'percent'
    && allowPercentOverflow
    && maxVal > hardMax
  )
    ? Number.POSITIVE_INFINITY
    : hardMax

  const padding = Math.max((maxVal - minVal) * 0.25, minSpan * 0.2)
  let low = minVal - padding
  let high = maxVal + padding

  if (high - low < minSpan) {
    const grow = (minSpan - (high - low)) / 2
    low -= grow
    high += grow
  }

  // Zero permanece visivel quando a serie se aproxima dele: uma cobertura de
  // 3% precisa mostrar que esta perto do chao, nao flutuando no meio do eixo.
  low = minVal <= minSpan * 0.5 ? 0 : Math.max(0, low)
  high = Math.min(upperBound, high)
  if (high - low < minSpan) low = Math.max(0, high - minSpan)

  const step = niceStep((high - low) / 4)
  return {
    max: Math.min(upperBound, Math.ceil(high / step) * step),
    min: Math.max(0, Math.floor(low / step) * step),
  }
}
