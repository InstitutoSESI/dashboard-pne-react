import { InstitutionalLogo } from './InstitutionalLogo'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'

export function InstitutionalTopBarSignature() {
  return (
    <div className="institutional-top-signature" aria-label="Marcas institucionais">
      <InstitutionalLogo alt={`SESI-${ACTIVE_STATE_CONFIG.stateCode}`} src="/brands/SESI.png" />
      {ACTIVE_STATE_CONFIG.stateCode === 'RS' ? (
        <InstitutionalLogo alt="FIERGS" src="/brands/FIERGS.png" />
      ) : null}
    </div>
  )
}
