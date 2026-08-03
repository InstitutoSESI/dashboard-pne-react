import type { ReactNode } from 'react'

/*
 * Glifos de orientacao (wayfinding) para os subitens de PNE e Financiamento.
 * Diferente do selo de dominio da Educacao (EducationDomainIcon), que carrega
 * identidade e reaparece no eyebrow do cabecalho, estes vivem so na barra
 * lateral: dao a cada aba uma silhueta reconhecivel a 16px. Cada glifo nasce do
 * vocabulario da propria aba -- balanca para metas legais, onibus para o PNATE.
 *
 * Convencao compartilhada com os selos: viewBox 24x24, traco 1,7, sem fill.
 * Nenhum repete o icone do grupo na mesma tela (PNE = alvo; Financiamento =
 * barras) nem os itens globais (casa, documento).
 */
export type NavGlyphName =
  | 'pne-overview'
  | 'pne-legal-goals'
  | 'pne2014'
  | 'pne2026'
  | 'diagnostico'
  | 'financeiros'
  | 'financeiros-panorama'
  | 'financeiros-aplicacao-recursos'
  | 'financeiros-fundeb'
  | 'financeiros-vaar'
  | 'financeiros-pnate'
  | 'visao-geral'
  | 'panorama'
  | 'educacao-superior'
  | 'demanda'
  | 'metodologia'

type NavGlyphSize = 'sm' | 'md'

const GLYPH_PATHS: Record<NavGlyphName, ReactNode> = {
  // Livro aberto -- a leitura introdutoria "o que e o PNE".
  'pne-overview': (
    <>
      <path d="M12 6.5C10 5 6.5 4.5 4 5v13c2.5-.5 6 0 8 1.5" />
      <path d="M12 6.5C14 5 17.5 4.5 20 5v13c-2.5-.5-6 0-8 1.5" />
      <path d="M12 6.5v13" />
    </>
  ),
  // Balanca -- as metas legais / referencia normativa.
  'pne-legal-goals': (
    <>
      <path d="M12 4.5v15" />
      <path d="M8.5 19.5h7" />
      <path d="M4.5 8h15" />
      <path d="M4.5 8 3 11.5h3z" />
      <path d="M19.5 8 18 11.5h3z" />
    </>
  ),
  // Calendario com marca -- o ciclo 2014-2024 ja concluido.
  pne2014: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M4 9.5h16" />
      <path d="M8.5 3.5v3M15.5 3.5v3" />
      <path d="m9 15 2 2 4-4" />
    </>
  ),
  // Bandeira -- o ciclo 2026-2036, a meta adiante.
  pne2026: (
    <>
      <path d="M6 3.5v17" />
      <path d="M6 4.5h11l-2.5 3.5L17 11.5H6" />
    </>
  ),
  // Lupa sobre barras -- o diagnostico, a leitura analitica do municipio.
  diagnostico: (
    <>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m19.5 19.5-4.2-4.2" />
      <path d="M8.5 11.5v-1M10.5 11.5v-3M12.5 11.5v-2" />
    </>
  ),
  // Grade -- a visao geral, o quadro de todas as areas.
  financeiros: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="1.2" />
      <rect x="13" y="4" width="7" height="7" rx="1.2" />
      <rect x="4" y="13" width="7" height="7" rx="1.2" />
      <rect x="13" y="13" width="7" height="7" rx="1.2" />
    </>
  ),
  // Area sob a curva -- o panorama, a sintese ampla.
  'financeiros-panorama': (
    <>
      <path d="M4 20V15l4-4 3 2 4-6 5 5v8z" />
      <path d="M4 20h16" />
    </>
  ),
  // Cedula -- a aplicacao e execucao dos recursos.
  'financeiros-aplicacao-recursos': (
    <>
      <rect x="3" y="7" width="18" height="10" rx="1.5" />
      <circle cx="12" cy="12" r="2.3" />
      <path d="M6 9.5v5M18 9.5v5" />
    </>
  ),
  // Pilha de moedas -- o fundo redistribuido (FUNDEB).
  'financeiros-fundeb': (
    <>
      <ellipse cx="12" cy="7" rx="6" ry="2.3" />
      <path d="M6 7v4c0 1.3 2.7 2.3 6 2.3s6-1 6-2.3V7" />
      <path d="M6 11v4c0 1.3 2.7 2.3 6 2.3s6-1 6-2.3v-4" />
    </>
  ),
  // Moeda com adicao -- a complementacao (VAAR).
  'financeiros-vaar': (
    <>
      <circle cx="10.5" cy="13.5" r="6.5" />
      <path d="M8 13.5h5M10.5 11v5" />
      <circle cx="18.5" cy="6.5" r="3.2" />
      <path d="M18.5 5v3M17 6.5h3" />
    </>
  ),
  // Onibus -- o transporte escolar rural (PNATE).
  'financeiros-pnate': (
    <>
      <rect x="3" y="6" width="18" height="9" rx="2" />
      <path d="M3 10.5h18" />
      <path d="M12 10.5V15" />
      <circle cx="8" cy="17" r="1.6" />
      <circle cx="16" cy="17" r="1.6" />
    </>
  ),
  // Bussola -- a visao geral, o ponto de partida para orientar a leitura.
  'visao-geral': (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.5 15.5 3.5-8 3.5 8-3.5-2z" />
    </>
  ),
  // Barra segmentada -- a composicao das matriculas (Panorama educacional).
  panorama: (
    <>
      <rect x="3" y="9" width="18" height="6" rx="1.5" />
      <path d="M10 9v6M15 9v6" />
    </>
  ),
  // Instituicao com colunas -- a Educacao Superior.
  'educacao-superior': (
    <>
      <path d="M4 9 12 4l8 5" />
      <path d="M5 9h14" />
      <path d="M7 9v8M12 9v8M17 9v8" />
      <path d="M4 20h16" />
    </>
  ),
  // Setas divergentes -- os cenarios (trajetorias futuras) de atendimento.
  demanda: (
    <>
      <path d="M4 12h6" />
      <path d="m10 12 8-5" />
      <path d="M18 7h-3.2M18 7v3.2" />
      <path d="m10 12 8 5" />
      <path d="M18 17h-3.2M18 17v-3.2" />
    </>
  ),
  // Prancheta -- a metodologia e as fontes documentadas.
  metodologia: (
    <>
      <rect x="5" y="5" width="14" height="16" rx="2" />
      <rect x="9.5" y="2.5" width="5" height="3" rx="1" />
      <path d="M8.5 10h7M8.5 13.5h7M8.5 17h4" />
    </>
  ),
}

export function NavGlyphIcon({
  name,
  size = 'sm',
}: {
  name: NavGlyphName
  size?: NavGlyphSize
}) {
  return (
    <svg
      aria-hidden="true"
      className={`nav-glyph nav-glyph--${size}`}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
    >
      {GLYPH_PATHS[name]}
    </svg>
  )
}

export function isNavGlyphName(value: unknown): value is NavGlyphName {
  return typeof value === 'string' && value in GLYPH_PATHS
}
