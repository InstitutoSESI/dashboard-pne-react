import { isMissing } from '../utils/educationFormatters'
import { ContentState } from './ContentState'

export function EducationTable({ columns, rows, emptyMessage = 'Sem dados disponíveis.', caption = 'Dados educacionais', className = '' }) {
  if (!rows || rows.length === 0) {
    return (
      <ContentState as="p" kind="empty" className="education-table-empty platform-data-state">
        {emptyMessage}
      </ContentState>
    )
  }

  return (
    <div className={`education-table-wrap platform-data-table-region${className ? ` ${className}` : ''}`} role="region" aria-label={`${caption}. Role horizontalmente para consultar todas as colunas quando necessário.`} tabIndex={0}>
      <table className="education-table platform-data-table">
        <caption className="u-sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((col) => {
              const isNumeric = col.numeric ?? rows.some((row) => typeof row[col.key] === 'number')
              const className = [col.className, isNumeric ? 'platform-data-cell--numeric' : ''].filter(Boolean).join(' ')
              return <th key={col.key} scope="col" className={className}>{col.label}</th>
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => {
                const raw = row[col.key]
                const missing = isMissing(raw)
                const isNumeric = col.numeric ?? rows.some((candidate) => typeof candidate[col.key] === 'number')
                const className = [
                  col.className,
                  isNumeric ? 'platform-data-cell--numeric' : '',
                  missing ? 'platform-data-cell--missing' : '',
                ].filter(Boolean).join(' ')
                const display = missing
                  ? <span className="platform-data-missing" aria-label="Dado não disponível" title="Dado não disponível">—</span>
                  : col.format ? col.format(raw) : String(raw)
                return col.rowHeader
                  ? <th key={col.key} scope="row" className={className}>{display}</th>
                  : <td key={col.key} className={className}>{display}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
