/*
 * Guarda de linguagem pública dos Cenários da educação municipal.
 *
 * A camada de pesquisa entrega o texto já aprovado; esta guarda existe para
 * impedir que qualquer identificador interno, enum de pipeline ou número
 * futuro chegue à tela. Ela é usada pelo gerador (que falha fechado antes de
 * publicar), pelo loader (que recusa o pacote em runtime) e pelos testes.
 *
 * Duas classes de texto convivem na página:
 *
 * - `evidence`: a prosa aprovada na camada de pesquisa. Só pode citar anos já
 *   observados, porque descreve séries históricas.
 * - `framing`: a moldura editorial da página (título, introdução, notas de
 *   horizonte). Pode citar 2031 e 2036 — o estado futuro e o fim da varredura —
 *   e nenhum outro número, porque a metodologia não projeta valor algum.
 */

/** Último ano observado nas séries publicadas. */
export const LAST_OBSERVED_YEAR = 2026
/** Ano do estado futuro descrito qualitativamente. */
export const HORIZON_STATE_YEAR = 2031
/** Último ano da varredura de sinais. */
export const HORIZON_SCAN_YEAR = 2036

const YEAR_PATTERN = /\b(1[89]\d{2}|20\d{2})\b/g
const NUMBER_PATTERN = /\d+(?:[.,]\d+)?/g
const DIACRITICS_PATTERN = /[̀-ͯ]/g

/*
 * Padrões estruturais: qualquer um deles é identificador de pipeline, nunca
 * português corrente. Cada entrada guarda o motivo para o erro ser legível.
 */
const STRUCTURAL_PATTERNS = Object.freeze([
  { code: 'scenario_id', pattern: /\bC[1-9]\d?\b/, reason: 'identificador interno de cenário' },
  { code: 'factor_id', pattern: /\bF0[1-9]\b/, reason: 'identificador interno de fator' },
  { code: 'combination_id', pattern: /\bMC-\d+/i, reason: 'identificador interno de combinação' },
  { code: 'relation_id', pattern: /\bRP-\d+/i, reason: 'identificador interno de relação' },
  { code: 'evidence_id', pattern: /\bEV-[A-Z0-9-]+/, reason: 'identificador interno de evidência' },
  { code: 'assertion_id', pattern: /\b(?:NAR|TRJ|SHR)-\d+/, reason: 'identificador interno de afirmação' },
  { code: 'fingerprint', pattern: /\b[a-f0-9]{32,}\b/i, reason: 'fingerprint ou hash' },
  { code: 'json_pointer', pattern: /(?:^|\s)#?(?:\/[A-Za-z0-9_]+){2,}/, reason: 'ponteiro de documento' },
  { code: 'dotted_path', pattern: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\b/, reason: 'caminho de nó interno' },
  { code: 'camel_case', pattern: /\b[a-z]+[A-Z][A-Za-z]*\b/, reason: 'identificador camelCase' },
  { code: 'snake_case', pattern: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/, reason: 'identificador snake_case' },
  { code: 'version_tag', pattern: /\bv\d+\.\d+\.\d+(?:-rc\d+)?\b/i, reason: 'versão de contrato' },
  { code: 'hash_label', pattern: /\bsha-?256\b/i, reason: 'rótulo de hash' },
])

/*
 * Enums internos, vocabulário de pipeline e mensagens de indisponibilidade.
 * Nenhum deles pode aparecer, em nenhuma construção. A busca é por palavra
 * inteira e sem acento, para não depender de como o texto acentua.
 */
const FORBIDDEN_TERMS = Object.freeze([
  'not located',
  'not materialized',
  'not evaluated',
  'scenarios generated',
  'selection robust',
  'selection unstable',
  'insufficient',
  'fail closed',
  'falha fechada',
  'pipeline',
  'staging',
  'gate',
  'gates',
  'schema',
  'fingerprint',
  'validador',
  'validadores',
  'runner',
  'orquestrador',
  'artefato',
  'artefatos',
  'artifact',
  'commit',
  'payload',
  'endpoint',
  'parser',
  'loader',
  'json',
  'markdown',
  'dados nao materializados',
  'dados insuficientes',
  'erro ao carregar',
  'em breve',
  'indisponivel',
  'melhor cenario',
  'pior cenario',
  'cenario ideal',
  'cenario otimista',
  'cenario pessimista',
  'mais provavel',
  'menos provavel',
  'futuro provavel',
])

/*
 * Termos que a página só pode usar para negar. "Estes cenários não são
 * previsões" é exatamente a ressalva que a metodologia exige; "a previsão para
 * o município" é a afirmação que ela proíbe. A diferença é a negação na mesma
 * frase, antes do termo — a mesma leitura que o controle negativo da camada de
 * pesquisa usa.
 */
const NEGATION_ONLY_TERMS = Object.freeze([
  'previsao',
  'previsoes',
  'projecao',
  'projecoes',
  'probabilidade',
  'probabilidades',
  'ranking',
  'score',
  'pontuacao',
])

const NEGATION_MARKER = /(?:^|[^a-z0-9_])(?:nao|nem|sem|jamais|nenhum|nenhuma)(?:$|[^a-z0-9_])/

/** Remove acentos e baixa a caixa, preservando as fronteiras de palavra. */
export function foldForSearch(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(DIACRITICS_PATTERN, '')
    .toLocaleLowerCase('pt-BR')
}

function escapeForRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function findYears(text) {
  return [...String(text ?? '').matchAll(YEAR_PATTERN)].map((match) => Number(match[1]))
}

/**
 * Lista as violações de um texto. Lista vazia significa publicável.
 *
 * @param {unknown} text
 * @param {{ kind?: 'evidence' | 'framing', label?: string }} [options]
 * @returns {{ code: string, match: string, reason: string }[]}
 */
export function findPublicLanguageViolations(text, { kind = 'evidence', label = 'texto' } = {}) {
  const value = String(text ?? '')
  const violations = []

  for (const { code, pattern, reason } of STRUCTURAL_PATTERNS) {
    const match = pattern.exec(value)
    if (match) violations.push({ code, match: match[0].trim(), reason: `${label}: ${reason}` })
  }

  const folded = foldForSearch(value)
  for (const term of FORBIDDEN_TERMS) {
    const boundary = new RegExp(`(?:^|[^a-z0-9_])${escapeForRegExp(foldForSearch(term))}(?:$|[^a-z0-9_])`)
    if (boundary.test(folded)) {
      violations.push({ code: 'forbidden_term', match: term, reason: `${label}: termo proibido na camada pública` })
    }
  }
  for (const term of NEGATION_ONLY_TERMS) {
    const needle = escapeForRegExp(foldForSearch(term))
    for (const sentence of folded.split(/(?<=[.;!?])\s+/)) {
      const boundary = new RegExp(`(?:^|[^a-z0-9_])${needle}(?:$|[^a-z0-9_])`)
      const found = boundary.exec(sentence)
      if (!found) continue
      if (NEGATION_MARKER.test(sentence.slice(0, found.index + 1))) continue
      violations.push({
        code: 'unnegated_claim_term',
        match: term,
        reason: `${label}: termo só admitido em negação explícita`,
      })
    }
  }

  const years = findYears(value)
  if (kind === 'evidence') {
    for (const year of years) {
      if (year > LAST_OBSERVED_YEAR) {
        violations.push({
          code: 'future_year',
          match: String(year),
          reason: `${label}: ano futuro em texto de evidência histórica`,
        })
      }
    }
    return violations
  }

  for (const year of years) {
    if (year !== HORIZON_STATE_YEAR && year !== HORIZON_SCAN_YEAR) {
      violations.push({
        code: 'unexpected_year',
        match: String(year),
        reason: `${label}: ano fora do horizonte declarado`,
      })
    }
  }
  for (const match of value.matchAll(NUMBER_PATTERN)) {
    const number = Number(match[0].replace(',', '.'))
    if (number === HORIZON_STATE_YEAR || number === HORIZON_SCAN_YEAR) continue
    violations.push({
      code: 'framing_number',
      match: match[0],
      reason: `${label}: número fora do horizonte em texto editorial`,
    })
  }

  return violations
}

/**
 * Recusa uma projeção numérica futura: um número atribuído a um ano posterior
 * ao último ano observado, dentro da mesma frase.
 */
export function findFutureNumericProjection(text, { label = 'texto' } = {}) {
  const violations = []

  for (const sentence of String(text ?? '').split(/(?<=[.;!?])\s+/)) {
    const futureYears = findYears(sentence).filter((year) => year > LAST_OBSERVED_YEAR)
    if (futureYears.length === 0) continue
    const carriesOtherNumber = [...sentence.matchAll(NUMBER_PATTERN)]
      .map((match) => Number(match[0].replace(',', '.')))
      .some((number) => Number.isFinite(number) && !futureYears.includes(number))
    if (carriesOtherNumber) {
      violations.push({
        code: 'future_numeric_projection',
        match: sentence.trim(),
        reason: `${label}: número associado a ano futuro`,
      })
    }
  }

  return violations
}

/** Lança quando o texto não é publicável; devolve o próprio texto quando é. */
export function assertPublicText(text, options = {}) {
  const violations = [
    ...findPublicLanguageViolations(text, options),
    ...findFutureNumericProjection(text, options),
  ]
  if (violations.length > 0) {
    const detail = violations
      .map((violation) => `${violation.reason} ("${violation.match}")`)
      .join('; ')
    throw new Error(`Linguagem pública recusada — ${detail}`)
  }
  return text
}
