import {
  EducationQuickReading,
  type EducationQuickReadingItem,
} from '../../../components/EducationQuickReading'

interface EducationIndicatorQuickReadingProps {
  cutLabel?: string | null
  description?: string | null
  firstLabel?: string
  text?: string | null
  warning?: string | null
}

export function EducationIndicatorQuickReading({
  cutLabel,
  description,
  firstLabel = 'Evolução observada',
  text,
  warning,
}: EducationIndicatorQuickReadingProps) {
  const items: EducationQuickReadingItem[] = [
    {
      icon: 'trend',
      key: 'trend',
      label: firstLabel,
      text,
      warning,
    },
    {
      icon: 'measure',
      key: 'measure',
      label: 'O que o indicador mede',
      text: description,
    },
    {
      emphasized: true,
      icon: 'cut',
      key: 'cut',
      label: 'Recorte exibido',
      text: cutLabel,
    },
  ]

  return <EducationQuickReading items={items} />
}
