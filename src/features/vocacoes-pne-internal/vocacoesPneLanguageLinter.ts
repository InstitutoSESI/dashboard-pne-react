export interface PrototypeLanguageIssue {
  id: string
  match: string
}

const BLOCKED: ReadonlyArray<{ id: string; pattern: RegExp }> = [
  { id: 'receiver-municipality', pattern: /\bmunicípio receptor\b/iu },
  { id: 'origin-destination-corridor', pattern: /\bcorredor origem[- ]destino\b/iu },
  { id: 'inferred-route', pattern: /\brota inferida\b/iu },
  { id: 'pnate-2026-executed', pattern: /\bPNATE executad[oa] em 2026\b/iu },
  { id: 'apprentice-opportunity', pattern: /\b(?:oportunidade|vaga)s? de aprendiz\b/iu },
  { id: 'dropout-for-work', pattern: /\balunos? abandonam? para trabalhar\b/iu },
  { id: 'courses-missing', pattern: /\bfaltam cursos\b/iu },
  { id: 'course-demand', pattern: /\bdemanda por curso\b/iu },
  { id: 'professional-deficit', pattern: /\bdéficit de profissionais\b/iu },
  { id: 'future-professions', pattern: /\bprofissões do futuro\b/iu },
  { id: 'municipal-ranking', pattern: /\branking municipal\b/iu },
  { id: 'vale-trajectory-rate', pattern: /\btaxa do Vale\b/iu },
  { id: 'causality-jargon', pattern: /\bcausalidade\b/iu },
  { id: 'mobility-overclaim', pattern: /\bmobilidade (?:não )?explica\b/iu },
  { id: 'blanket-no-relation', pattern: /\bnão (?:há|existe) relação\b/iu },
  { id: 'offer-deficit', pattern: /\b(?:déficit|excesso) de oferta\b/iu },
  { id: 'course-need', pattern: /\bnecessidade de cursos?\b/iu },
  { id: 'unmet-demand', pattern: /\bdemanda não atendida\b/iu },
  { id: 'zero-schools-wording', pattern: /\bzero escolas\b/iu },
  { id: 'technical-r-token', pattern: /\bR[1-8]\b/u },
  { id: 'technical-tvd', pattern: /\bTVD\b/u },
  { id: 'technical-rho', pattern: /\brho\b/iu },
  { id: 'technical-bh', pattern: /\bBH\b/u },
  { id: 'technical-fixed-effects', pattern: /\bfixed effects\b/iu },
  { id: 'technical-regression', pattern: /\bregress(?:ão|ion)\b/iu },
  { id: 'technical-shift-share', pattern: /\bshift[- ]share\b/iu },
  { id: 'technical-hhi', pattern: /\bHHI\b/u },
  { id: 'technical-gate', pattern: /\bGate(?: 11)?\b/iu },
  { id: 'technical-schema', pattern: /\bschema\b/iu },
  { id: 'pne-internal-token', pattern: /\bPNE_[0-9]+\b/u },
  { id: 'pme-internal-token', pattern: /\bPME_[A-Za-z0-9_]+\b/u },
]

export function lintVocacoesPnePrototypeText(text: string): PrototypeLanguageIssue[] {
  return BLOCKED.flatMap(({ id, pattern }) => {
    const match = text.match(pattern)?.[0]
    return match ? [{ id, match }] : []
  })
}

export function assertVocacoesPnePrototypeLanguage(texts: readonly string[]) {
  const issues = texts.flatMap((text) => lintVocacoesPnePrototypeText(text))
  if (issues.length > 0) {
    throw new TypeError(`Linguagem bloqueada no protótipo: ${issues.map((item) => item.id).join(', ')}`)
  }
}
