import type { ReactNode } from 'react'

export type EducationDomain =
  | 'atendimento'
  | 'trajetoria'
  | 'profissionais'
  | 'infraestrutura'
  | 'modalidades'

type EducationDomainIconSize = 'sm' | 'md' | 'lg'

/*
 * Nenhum destes glifos pode repetir os que ja aparecem na mesma tela: os chips
 * de contexto do cabecalho usam casa, pessoas, relogio, documento e grafico, e
 * o grupo da barra lateral usa capelo. Ver docs/DESIGN.md, "Assinatura".
 */
const DOMAIN_PATHS: Record<EducationDomain, ReactNode> = {
  atendimento: (
    <>
      <path d="M6 10.5a6 6 0 0 1 12 0V19a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2z" />
      <path d="M9.5 10.5a2.5 2.5 0 0 1 5 0" />
      <path d="M6 15.5h12" />
    </>
  ),
  trajetoria: (
    <>
      <circle cx="5" cy="18.5" r="2.3" />
      <circle cx="12" cy="12" r="2.3" />
      <circle cx="19" cy="5.5" r="2.3" />
      <path d="m6.7 16.9 3.6-3.3M13.7 10.4l3.6-3.3" />
    </>
  ),
  profissionais: (
    <>
      <path d="M4 4h16v11H4z" />
      <path d="M8 15v5M16 15v5" />
      <path d="M7.5 8.5h6" />
    </>
  ),
  infraestrutura: (
    <>
      <path d="M3 21h18" />
      <path d="M5 21V4h14v17" />
      <path d="M9 8h1.5M13.5 8h1.5M9 12h1.5M13.5 12h1.5" />
      <path d="M10 21v-4.5h4V21" />
    </>
  ),
  modalidades: (
    <>
      <path d="M8 3.5h11a1.5 1.5 0 0 1 1.5 1.5v11" />
      <path d="M5.5 7h11A1.5 1.5 0 0 1 18 8.5v11" />
      <rect x="3" y="10.5" width="12.5" height="10" rx="1.5" />
    </>
  ),
}

export function EducationDomainIcon({
  domain,
  size = 'md',
}: {
  domain: EducationDomain
  size?: EducationDomainIconSize
}) {
  return (
    <svg
      aria-hidden="true"
      className={`education-domain-icon education-domain-icon--${size}`}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
    >
      {DOMAIN_PATHS[domain]}
    </svg>
  )
}

export function isEducationDomain(value: unknown): value is EducationDomain {
  return typeof value === 'string' && value in DOMAIN_PATHS
}
