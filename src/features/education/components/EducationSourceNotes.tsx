import { DataSourceNote } from '../../../components/DataSourceNote.jsx'
import { MethodNote } from '../../../components/MethodNote.jsx'
import { getDataSourceParts } from '../../../utils/dataSourceNotes.js'

interface EducationSourceIndicator {
  description?: unknown
  key?: unknown
  label?: unknown
  tema?: unknown
  themeKey?: unknown
  themeLabel?: unknown
}

export type EducationDataSourceContext = Record<string, unknown>

export function dataSourceContextForEducation(
  indicator?: EducationSourceIndicator | null,
  extra: EducationDataSourceContext = {},
): EducationDataSourceContext {
  return {
    block: 'educacao',
    description: indicator?.description,
    indicatorKey: indicator?.key,
    indicatorName: indicator?.label,
    section: indicator?.themeLabel,
    themeKey: indicator?.themeKey ?? indicator?.tema,
    title: indicator?.label,
    ...extra,
  }
}

export function EducationSourceNotes({ context }: { context: EducationDataSourceContext }) {
  const { methodology, source } = getDataSourceParts(context)

  return (
    <>
      {source ? <DataSourceNote context={undefined} source={source} /> : null}
      {methodology ? (
        <MethodNote className="data-source-note">Nota metodológica: {methodology}</MethodNote>
      ) : null}
    </>
  )
}
