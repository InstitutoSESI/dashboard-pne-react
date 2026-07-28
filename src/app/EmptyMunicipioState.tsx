import { MunicipalitySelector } from '../components/MunicipalitySelector'
import type { ComponentType } from 'react'
import type { MunicipioName } from '../types/data'
import type { Navigate } from '../types/navigation'

interface EmptyMunicipioStateProps {
  municipios: MunicipioName[]
  onMunicipioChange: (value: MunicipioName | null) => void
  onNavigate?: Navigate
}

interface MunicipalitySelectorProps {
  municipios: MunicipioName[]
  onChange: (value: MunicipioName | null) => void
  selectedMunicipio: string
  variant: 'hero'
}

const TypedMunicipalitySelector = MunicipalitySelector as ComponentType<MunicipalitySelectorProps>

export function EmptyMunicipioState({ onNavigate, onMunicipioChange, municipios }: EmptyMunicipioStateProps) {
  return (
    <section className="empty-state">
      <div className="empty-state__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 21s7-6.3 7-12a7 7 0 1 0-14 0c0 5.7 7 12 7 12Z" />
          <circle cx="12" cy="9" r="2.4" />
        </svg>
      </div>
      <h1>Selecione um município para continuar</h1>
      <p>
        Os indicadores, rankings e o diagnóstico municipal só são carregados depois da
        seleção. Escolha o município que deseja analisar.
      </p>
      <div className="empty-municipality-selector">
        <TypedMunicipalitySelector
          variant="hero"
          municipios={municipios}
          selectedMunicipio=""
          onChange={onMunicipioChange}
        />
      </div>
      <button type="button" className="primary-button" onClick={() => onNavigate?.('home')}>
        Voltar ao início
      </button>
    </section>
  )
}
