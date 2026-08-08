import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'

export function SidebarInstitutionalSignature({ compact = false }) {
  return (
    <div className={`sidebar-institutional-signature${compact ? ' sidebar-institutional-signature--compact' : ''}`}>
      <p>Observatório da Educação — SESI-{ACTIVE_STATE_CONFIG.stateCode}</p>
    </div>
  )
}
