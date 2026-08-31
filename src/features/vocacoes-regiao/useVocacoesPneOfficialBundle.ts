import { useEffect, useState } from 'react'
import {
  loadVocacoesPneInternalBundle,
} from '../vocacoes-pne-internal/useVocacoesPneInternalBundle'
import type { VocacoesPneLoadedBundle } from '../vocacoes-pne-internal/vocacoesPneUiV2Types'
import { assertVocacoesPneOfficialBundle } from './vocacoesPneOfficialPromotion'

type OfficialBundleState =
  | { status: 'idle'; data: null; error: null }
  | { status: 'loading'; data: null; error: null }
  | { status: 'error'; data: null; error: string }
  | { status: 'ready'; data: VocacoesPneLoadedBundle; error: null }

let publicBundle: VocacoesPneLoadedBundle | null = null
let publicBundlePromise: Promise<VocacoesPneLoadedBundle> | null = null

export function loadVocacoesPneOfficialBundle(): Promise<VocacoesPneLoadedBundle> {
  if (publicBundle) return Promise.resolve(publicBundle)
  if (!publicBundlePromise) {
    publicBundlePromise = loadVocacoesPneInternalBundle().then((bundle) => {
      assertVocacoesPneOfficialBundle(bundle)
      publicBundle = bundle
      return bundle
    })
  }
  return publicBundlePromise
}

export function useVocacoesPneOfficialBundle(enabled: boolean): OfficialBundleState {
  const [state, setState] = useState<OfficialBundleState>(() => {
    if (!enabled) return { status: 'idle', data: null, error: null }
    if (publicBundle) return { status: 'ready', data: publicBundle, error: null }
    return { status: 'loading', data: null, error: null }
  })

  useEffect(() => {
    let active = true
    if (!enabled) {
      setState({ status: 'idle', data: null, error: null })
      return () => { active = false }
    }
    if (publicBundle) {
      setState({ status: 'ready', data: publicBundle, error: null })
      return () => { active = false }
    }
    setState({ status: 'loading', data: null, error: null })
    loadVocacoesPneOfficialBundle().then(
      (data) => {
        if (active) setState({ status: 'ready', data, error: null })
      },
      (error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            data: null,
            error: error instanceof Error ? error.message : 'Falha ao validar a leitura integrada oficial.',
          })
        }
      },
    )
    return () => { active = false }
  }, [enabled])

  return state
}
