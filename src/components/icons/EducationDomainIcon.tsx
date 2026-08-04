import {
  Building2,
  Layers3,
  Presentation,
  Route,
  School,
  type LucideIcon,
} from 'lucide-react'

export type EducationDomain =
  | 'atendimento'
  | 'trajetoria'
  | 'profissionais'
  | 'infraestrutura'
  | 'modalidades'

type EducationDomainIconSize = 'sm' | 'md' | 'lg'

const DOMAIN_ICONS: Record<EducationDomain, LucideIcon> = {
  atendimento: School,
  trajetoria: Route,
  profissionais: Presentation,
  infraestrutura: Building2,
  modalidades: Layers3,
}

export function EducationDomainIcon({
  domain,
  size = 'md',
}: {
  domain: EducationDomain
  size?: EducationDomainIconSize
}) {
  const Icon = DOMAIN_ICONS[domain]

  return (
    <Icon
      aria-hidden="true"
      className={`education-domain-icon education-domain-icon--${size}`}
      strokeWidth={1.7}
    />
  )
}

export function isEducationDomain(value: unknown): value is EducationDomain {
  return typeof value === 'string' && value in DOMAIN_ICONS
}
