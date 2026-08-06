import type { ReactNode } from 'react'
import {
  QuickReadingList,
  type QuickReadingItem,
} from './QuickReadingList'

const EM = '\u2014'

interface FinancialQuickReadingIndicator {
  currentYear?: number | string | null
  initialYear?: number | string | null
  quickReading?: ReactNode
}

interface FinancialQuickReadingMetadata {
  measures?: ReactNode
}

interface FinancialQuickReadingGuide {
  oQueMede?: ReactNode
}

export interface FinancialQuickReadingProps {
  description?: ReactNode
  indicator?: FinancialQuickReadingIndicator | null
  metadata?: FinancialQuickReadingMetadata | null
  readingGuide?: FinancialQuickReadingGuide | null
  text?: ReactNode
}

export function buildFinancialQuickReadingItems({
  description,
  indicator,
  metadata,
  readingGuide,
  text,
}: FinancialQuickReadingProps): QuickReadingItem[] {
  const period = indicator?.initialYear && indicator?.currentYear
    ? `${indicator.initialYear} a ${indicator.currentYear}`
    : indicator?.currentYear
      ? String(indicator.currentYear)
      : EM

  return [
    {
      icon: 'trend',
      key: 'trend',
      label: 'Evolução observada',
      text: text ?? indicator?.quickReading,
    },
    {
      icon: 'measure',
      key: 'measure',
      label: 'O que o indicador mede',
      text: readingGuide?.oQueMede ?? metadata?.measures ?? description,
    },
    {
      emphasized: true,
      icon: 'cut',
      key: 'cut',
      label: 'Recorte exibido',
      text: period,
    },
  ]
}

export function FinancialQuickReading(props: FinancialQuickReadingProps) {
  return (
    <QuickReadingList
      ariaLabel="Leitura rápida do indicador"
      className="financial-quick-reading"
      items={buildFinancialQuickReadingItems(props)}
    />
  )
}
