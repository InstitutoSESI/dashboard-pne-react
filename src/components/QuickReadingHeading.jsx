import { ScanSearch } from 'lucide-react'

export function QuickReadingHeading() {
  return (
    <span className="indicator-quick-reading__heading">
      <ScanSearch aria-hidden="true" className="indicator-quick-reading__heading-icon" />
      <span>Leitura rápida</span>
    </span>
  )
}
