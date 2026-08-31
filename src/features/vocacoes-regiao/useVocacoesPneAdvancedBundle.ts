import { useEffect, useState } from 'react'
import {
  assertVocacoesPneAdvancedBundle,
  assertVocacoesPneAdvancedRegistry,
  type VocacoesPneAdvancedBundle,
} from './vocacoesPneAdvancedContract'

export type VocacoesPneAdvancedBundleState =
  | { status: 'idle'; data: null; error: null }
  | { status: 'loading'; data: null; error: null }
  | { status: 'error'; data: null; error: string }
  | { status: 'ready'; data: VocacoesPneAdvancedBundle; error: null }

export interface VocacoesPneAdvancedModules {
  readonly bundleRaw: string
  readonly registry: unknown
}

export type VocacoesPneAdvancedModuleLoader = () => Promise<VocacoesPneAdvancedModules>

async function defaultModuleLoader(): Promise<VocacoesPneAdvancedModules> {
  const [bundleModule, registryModule] = await Promise.all([
    import('./generated/vocacoesPneAdvancedInsightsValeDoSinos.json?raw'),
    import('./generated/vocacoesPneAdvancedInsightsRegistry.json'),
  ])
  return {
    bundleRaw: bundleModule.default,
    registry: registryModule.default,
  }
}

async function sha256Text(value: string): Promise<string> {
  const cryptoApi = globalThis.crypto?.subtle
  if (cryptoApi === undefined) throw new TypeError('Web Crypto indisponível para validar o pacote avançado.')
  const digest = await cryptoApi.digest('SHA-256', new TextEncoder().encode(value))
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function createVocacoesPneAdvancedLoader(
  loadModules: VocacoesPneAdvancedModuleLoader,
): () => Promise<VocacoesPneAdvancedBundle> {
  let cached: VocacoesPneAdvancedBundle | null = null
  let pending: Promise<VocacoesPneAdvancedBundle> | null = null
  return () => {
    if (cached !== null) return Promise.resolve(cached)
    if (pending === null) {
      pending = loadModules().then(async ({ bundleRaw, registry }) => {
        assertVocacoesPneAdvancedRegistry(registry)
        const byteSize = new TextEncoder().encode(bundleRaw).byteLength
        if (byteSize !== registry.bundleByteSize) {
          throw new TypeError('Leitura avançada: tamanho do bundle diverge do registro.')
        }
        const digest = await sha256Text(bundleRaw)
        if (digest !== registry.bundleSha256) {
          throw new TypeError('Leitura avançada: hash do bundle diverge do registro.')
        }
        const raw: unknown = JSON.parse(bundleRaw)
        assertVocacoesPneAdvancedBundle(raw)
        if (raw.contentVersion !== registry.contentVersion) {
          throw new TypeError('Leitura avançada: versão de conteúdo diverge do registro.')
        }
        cached = raw
        return raw
      }).catch((error: unknown) => {
        pending = null
        throw error
      })
    }
    return pending
  }
}

export const loadVocacoesPneAdvancedBundle = createVocacoesPneAdvancedLoader(defaultModuleLoader)

export function useVocacoesPneAdvancedBundle(enabled: boolean): VocacoesPneAdvancedBundleState {
  const [state, setState] = useState<VocacoesPneAdvancedBundleState>(() => (
    enabled
      ? { status: 'loading', data: null, error: null }
      : { status: 'idle', data: null, error: null }
  ))

  useEffect(() => {
    let active = true
    if (!enabled) {
      setState({ status: 'idle', data: null, error: null })
      return () => { active = false }
    }
    setState({ status: 'loading', data: null, error: null })
    loadVocacoesPneAdvancedBundle().then(
      (data) => {
        if (active) setState({ status: 'ready', data, error: null })
      },
      (error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            data: null,
            error: error instanceof Error ? error.message : 'Falha ao validar a leitura avançada.',
          })
        }
      },
    )
    return () => { active = false }
  }, [enabled])

  return state
}
