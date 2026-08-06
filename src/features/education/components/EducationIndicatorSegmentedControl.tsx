import type { ReactNode } from 'react'
import { SegmentedControl } from '../../../components/SegmentedControl.jsx'

interface EducationIndicatorSegmentedOption {
  key: string
  label: ReactNode
}

interface EducationIndicatorSegmentedControlProps {
  ariaLabel: string
  onSelect: (key: string) => void
  options: readonly EducationIndicatorSegmentedOption[]
  scrollable?: boolean
  selectedKey: string
}

export function IndicatorSegmentedControl({
  options,
  selectedKey,
  onSelect,
  ariaLabel,
  scrollable = false,
}: EducationIndicatorSegmentedControlProps) {
  return (
    <SegmentedControl
      ariaLabel={ariaLabel}
      className={`indicator-stage-segmented platform-segmented-control${scrollable ? ' platform-segmented-control--scrollable' : ''}`}
      optionClassName="indicator-stage-segmented__button platform-segmented-option"
      onSelect={onSelect}
      options={options.map(({ key, label }) => ({ key, label }))}
      selectedKey={selectedKey}
    />
  )
}
