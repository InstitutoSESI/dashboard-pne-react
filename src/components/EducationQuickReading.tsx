import {
  QuickReadingList,
  type QuickReadingIcon,
  type QuickReadingItem,
  type QuickReadingListProps,
} from './QuickReadingList'

export type EducationQuickReadingIcon = QuickReadingIcon
export type EducationQuickReadingItem = QuickReadingItem

interface EducationQuickReadingProps extends Omit<QuickReadingListProps, 'className'> {
  className?: string
}

export function EducationQuickReading({
  className = '',
  ...props
}: EducationQuickReadingProps) {
  const domainClassName = `education-quick-reading${className ? ` ${className}` : ''}`
  return <QuickReadingList {...props} className={domainClassName} />
}
