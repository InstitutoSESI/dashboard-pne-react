import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { PropsWithChildren } from 'react'
import { ACTIVE_STATE_CONFIG, type StateConfig } from '../config/stateConfig'
import {
  findMunicipalityById,
  indexMunicipalitiesById,
} from '../domain/municipalityRegistry'
import {
  getBrowserMunicipalityStorage,
  persistMunicipalitySelection,
  restoreMunicipalitySelection,
} from '../domain/municipalityStorage'
import type { MunicipalityId, MunicipalityRef } from '../types/data'

export interface MunicipalityContextValue {
  activeState: StateConfig
  selectedMunicipalityId: MunicipalityId | null
  selectedMunicipality: MunicipalityRef | null
  setSelectedMunicipalityId: (value: MunicipalityId | null) => void
  selectionReady: boolean
}

interface MunicipalityProviderProps extends PropsWithChildren {
  activeState?: StateConfig
  municipalities: MunicipalityRef[]
}

const FALLBACK_MUNICIPALITY_CONTEXT: MunicipalityContextValue = {
  activeState: ACTIVE_STATE_CONFIG,
  selectedMunicipalityId: null,
  selectedMunicipality: null,
  setSelectedMunicipalityId: () => {},
  selectionReady: false,
}

const MunicipalityContext = createContext<MunicipalityContextValue | undefined>(undefined)

export function MunicipalityProvider({
  activeState = ACTIVE_STATE_CONFIG,
  children,
  municipalities,
}: MunicipalityProviderProps) {
  const [selectedMunicipalityId, setSelectedMunicipalityIdState] =
    useState<MunicipalityId | null>(null)
  const [selectionReady, setSelectionReady] = useState(false)
  const hydratedStateCodeRef = useRef<string | null>(null)
  const municipalitiesById = useMemo(
    () => indexMunicipalitiesById(municipalities),
    [municipalities],
  )
  const selectedMunicipality = useMemo(
    () => findMunicipalityById(municipalitiesById, selectedMunicipalityId),
    [municipalitiesById, selectedMunicipalityId],
  )

  useLayoutEffect(() => {
    if (municipalities.length === 0) return
    if (hydratedStateCodeRef.current === activeState.stateCode) return

    const restored = restoreMunicipalitySelection(
      getBrowserMunicipalityStorage(),
      municipalities,
      activeState,
    )
    hydratedStateCodeRef.current = activeState.stateCode
    setSelectedMunicipalityIdState(restored.municipalityId)
    setSelectionReady(true)
  }, [activeState, municipalities])

  useLayoutEffect(() => {
    if (!selectionReady || municipalities.length === 0 || !selectedMunicipalityId) return
    if (municipalitiesById.has(selectedMunicipalityId)) return

    setSelectedMunicipalityIdState(null)
    persistMunicipalitySelection(
      getBrowserMunicipalityStorage(),
      municipalities,
      activeState,
      null,
    )
  }, [activeState, municipalities, municipalitiesById, selectedMunicipalityId, selectionReady])

  const setSelectedMunicipalityId = useCallback((value: MunicipalityId | null) => {
    if (value !== null && !municipalitiesById.has(value)) return

    setSelectedMunicipalityIdState(value)
    persistMunicipalitySelection(
      getBrowserMunicipalityStorage(),
      municipalities,
      activeState,
      value,
    )
  }, [activeState, municipalities, municipalitiesById])

  return (
    <MunicipalityContext.Provider
      value={{
        activeState,
        selectedMunicipalityId,
        selectedMunicipality,
        setSelectedMunicipalityId,
        selectionReady,
      }}
    >
      {children}
    </MunicipalityContext.Provider>
  )
}

export function useMunicipality(): MunicipalityContextValue {
  const municipality = useContext(MunicipalityContext)
  if (!municipality) {
    if (import.meta.env.DEV) {
      throw new Error('useMunicipality deve ser usado dentro de MunicipalityProvider.')
    }
    return FALLBACK_MUNICIPALITY_CONTEXT
  }
  return municipality
}
