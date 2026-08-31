import { useEffect, useState } from 'react'
import {
  parseVocacoesPneCore,
  parseVocacoesPneSeriesBundle,
  parseVocacoesPneTechnicalBundle,
} from './vocacoesPneUiV2Runtime'
import { parseVocacoesPneJob5K } from './vocacoesPneJob5kRuntime'
import type {
  VocacoesPneLoadedBundle,
  VocacoesPneTechnicalBundle,
} from './vocacoesPneUiV2Types'

type LoadState =
  | { status: 'loading'; data: null; error: null }
  | { status: 'error'; data: null; error: string }
  | { status: 'ready'; data: VocacoesPneLoadedBundle; error: null }

let cachedBundle: VocacoesPneLoadedBundle | null = null
let bundlePromise: Promise<VocacoesPneLoadedBundle> | null = null

export function loadVocacoesPneInternalBundle(): Promise<VocacoesPneLoadedBundle> {
  if (cachedBundle) return Promise.resolve(cachedBundle)
  if (!bundlePromise) {
    bundlePromise = Promise.all([
      import('./generated/vocacoesPneJob5iCore.json'),
      import('./generated/vocacoesPneJob5iSeries.json'),
      import('./generated/vocacoesPneJob5kStories.json'),
    ]).then(([coreModule, seriesModule, insightModule]) => {
      const core = parseVocacoesPneCore(coreModule.default)
      const seriesBundle = parseVocacoesPneSeriesBundle(seriesModule.default)
      const insights = parseVocacoesPneJob5K(insightModule.default)
      if (seriesBundle.series.length !== core.seriesBundle.seriesCount) {
        throw new TypeError('Bundle Job 5I inválido: contagem de séries divergente.')
      }
      if (insights.municipalities.map((item) => item.ibgeCode).join('|') !== core.municipalities.map((item) => item.ibgeCode).join('|')) {
        throw new TypeError('Bundle Job 5K inválido: identidade municipal divergente do Job 5I.')
      }
      cachedBundle = { core, series: seriesBundle.series, insights }
      return cachedBundle
    })
  }
  return bundlePromise
}

export async function loadVocacoesPneTechnicalBundle(): Promise<VocacoesPneTechnicalBundle> {
  const module = await import('./generated/vocacoesPneJob5iTechnical.json')
  return parseVocacoesPneTechnicalBundle(module.default)
}

export function useVocacoesPneInternalBundle(): LoadState {
  const [state, setState] = useState<LoadState>(() => (
    cachedBundle
      ? { status: 'ready', data: cachedBundle, error: null }
      : { status: 'loading', data: null, error: null }
  ))

  useEffect(() => {
    let active = true
    loadVocacoesPneInternalBundle().then(
      (data) => {
        if (active) setState({ status: 'ready', data, error: null })
      },
      (error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            data: null,
            error: error instanceof Error ? error.message : 'Falha ao validar o bundle interno.',
          })
        }
      },
    )
    return () => { active = false }
  }, [])

  return state
}
