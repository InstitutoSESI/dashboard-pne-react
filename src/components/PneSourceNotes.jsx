import { getDataSourceParts } from '../utils/dataSourceNotes'
import { DataSourceNote } from './DataSourceNote'
import { DisclosureChevron } from './DisclosureChevron'
import { MethodNote } from './MethodNote'

export function PneSourceNotes({ compact = false, context, includeMethodology = true, label = 'Fonte e cálculo' }) {
  const { methodology, source } = getDataSourceParts(context)

  if (!source && !(includeMethodology && methodology)) return null

  return (
    <>
      <details className={`platform-support-disclosure chart-methodology-disclosure${compact ? ' chart-methodology-disclosure--compact' : ''}`}>
        <summary className="platform-support-disclosure__summary">
          <span>{label}</span>
          <DisclosureChevron />
        </summary>
        <SourceNotesBody
          includeMethodology={includeMethodology}
          methodology={methodology}
          source={source}
        />
      </details>
      <section
        aria-hidden="true"
        className="pne-source-notes-print"
      >
        <h3>Fonte e cálculo</h3>
        <SourceNotesBody
          includeMethodology={includeMethodology}
          methodology={methodology}
          source={source}
        />
      </section>
    </>
  )
}

function SourceNotesBody({ includeMethodology, methodology, source }) {
  return (
    <div className="platform-support-disclosure__body">
      {source ? <DataSourceNote source={source} /> : null}
      {includeMethodology && methodology ? (
        <MethodNote className="data-source-note">Nota metodológica: {methodology}</MethodNote>
      ) : null}
    </div>
  )
}
