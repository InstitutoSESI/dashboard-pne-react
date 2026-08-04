import { MapPin } from 'lucide-react'
import { MunicipalitySelector } from '../components/MunicipalitySelector'
import type { MunicipalityId, MunicipalityRef } from '../types/data'
import type { Navigate } from '../types/navigation'

interface EmptyMunicipioStateProps {
  municipalities: MunicipalityRef[]
  onMunicipalityChange: (value: MunicipalityId | null) => void
  onNavigate?: Navigate
}

export function EmptyMunicipioState({
  onNavigate,
  onMunicipalityChange,
  municipalities,
}: EmptyMunicipioStateProps) {
  return (
    <section className="empty-state">
      <div className="empty-state__icon" aria-hidden="true">
        <MapPin strokeWidth={1.7} />
      </div>
      <h1>Selecione um município para continuar</h1>
      <p>
        Os indicadores, rankings e o diagnóstico municipal só são carregados depois da
        seleção. Escolha o município que deseja analisar.
      </p>
      <div className="empty-municipality-selector">
        <MunicipalitySelector
          variant="hero"
          municipalities={municipalities}
          selectedMunicipalityId={null}
          onChange={onMunicipalityChange}
        />
      </div>
      <button type="button" className="primary-button" onClick={() => onNavigate?.('home')}>
        Voltar ao início
      </button>
    </section>
  )
}
