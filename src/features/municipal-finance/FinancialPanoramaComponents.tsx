import type { ReactNode } from 'react'
import {
  ArrowLeft,
  ChartColumnIncreasing,
  CreditCard,
  FileText,
  Landmark,
  TrendingUp,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import { PageHeader } from '../../components/PageHeader'
import { FinancialKpiCard } from '../../components/FinancialIndicatorPrimitives'

export type FinancialIconName = 'allocation' | 'budget' | 'fundeb' | 'payment' | 'resources' | 'trend'

export function FinancialCompactHeader({
  backHref,
  description,
}: {
  backHref: string
  description: string
}) {
  return (
    <PageHeader
      actions={(
        <a className="platform-navigation-button financial-page-header__back" href={backHref}>
          <ArrowLeft aria-hidden="true" />
          Voltar à visão geral de financiamento
        </a>
      )}
      className="financial-page-header financial-page-header--panorama"
      description={description}
      eyebrow="Financiamento da educação"
      title="Panorama financeiro"
      variant="listing"
    />
  )
}

export function FinancialMetricCard({
  children,
  icon,
  label,
  meta,
  tone = 'observed',
}: {
  children: ReactNode
  icon: FinancialIconName
  label: string
  meta: string
  tone?: 'forecast' | 'observed'
}) {
  return (
    <FinancialKpiCard
      icon={<FinancialIcon name={icon} />}
      label={label}
      meta={meta}
      tone={tone}
      value={children}
    />
  )
}

export function FinancialDisclosure({
  children,
  label,
  className = '',
}: {
  children: ReactNode
  label: string
  className?: string
}) {
  return (
    <details className={`municipal-finance-disclosure${className ? ` ${className}` : ''}`}>
      <summary>{label}</summary>
      {children}
    </details>
  )
}

export function FinancialIcon({ name }: { name: FinancialIconName }) {
  const icons: Record<FinancialIconName, LucideIcon> = {
    allocation: ChartColumnIncreasing,
    budget: FileText,
    fundeb: Landmark,
    payment: CreditCard,
    resources: UsersRound,
    trend: TrendingUp,
  }
  const Icon = icons[name]
  return <Icon aria-hidden="true" strokeWidth={1.7} />
}
