import { useEffect, useState } from 'react'
import {
  assertCenariosEducacaoBundle,
  assertCenariosEducacaoRegistry,
  type CenariosEducacaoBundle,
} from './cenariosEducacaoContract'

export type CenariosEducacaoBundleState =
  | { status: 'loading'; data: null; error: null }
  | { status: 'error'; data: null; error: string }
  | { status: 'ready'; data: CenariosEducacaoBundle; error: null }

export interface CenariosEducacaoModules {
  readonly bundleRaw: string
  readonly registry: unknown
}

export type CenariosEducacaoModuleLoader = () => Promise<CenariosEducacaoModules>

async function defaultModuleLoader(): Promise<CenariosEducacaoModules> {
  const [bundleModule, registryModule] = await Promise.all([
    import('./generated/cenariosEducacaoValeDoSinos.json?raw'),
    import('./generated/cenariosEducacaoRegistry.json'),
  ])
  return {
    bundleRaw: bundleModule.default,
    registry: registryModule.default,
  }
}

async function sha256Text(value: string): Promise<string> {
  const cryptoApi = globalThis.crypto?.subtle
  if (cryptoApi === undefined) {
    throw new TypeError('Cenários da Educação: Web Crypto indisponível para validar o pacote.')
  }
  const digest = await cryptoApi.digest('SHA-256', new TextEncoder().encode(value))
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function createCenariosEducacaoLoader(
  loadModules: CenariosEducacaoModuleLoader,
): () => Promise<CenariosEducacaoBundle> {
  let cached: CenariosEducacaoBundle | null = null
  let pending: Promise<CenariosEducacaoBundle> | null = null

  return () => {
    if (cached !== null) return Promise.resolve(cached)
    if (pending === null) {
      pending = loadModules().then(async ({ bundleRaw, registry }) => {
        assertCenariosEducacaoRegistry(registry)
        const byteSize = new TextEncoder().encode(bundleRaw).byteLength
        if (byteSize !== registry.bundleByteSize) {
          throw new TypeError('Cenários da Educação: tamanho do bundle diverge do registro.')
        }
        const digest = await sha256Text(bundleRaw)
        if (digest !== registry.bundleSha256) {
          throw new TypeError('Cenários da Educação: hash do bundle diverge do registro.')
        }

        const raw: unknown = JSON.parse(bundleRaw)
        assertCenariosEducacaoBundle(raw)
        if (raw.contentVersion !== registry.contentVersion) {
          throw new TypeError('Cenários da Educação: versão de conteúdo diverge do registro.')
        }
        if (raw.publicationStatus !== registry.publicationStatus) {
          throw new TypeError('Cenários da Educação: status de publicação diverge do registro.')
        }
        if (raw.qualityGate.status !== registry.publicDataValidationStatus) {
          throw new TypeError('Cenários da Educação: gate de dados públicos diverge do registro.')
        }
        if (raw.region.municipalityCount !== registry.regionalMunicipalityCount) {
          throw new TypeError('Cenários da Educação: cobertura regional diverge do registro.')
        }
        if (raw.municipalities[0]?.municipalityIbgeCode !== registry.focalMunicipalityIbgeCode) {
          throw new TypeError('Cenários da Educação: lente municipal diverge do registro.')
        }
        if (raw.morphologicalField.minimumObservedPairwiseHammingDistance !== registry.minimumPairwiseHammingDistance) {
          throw new TypeError('Cenários da Educação: distância morfológica diverge do registro.')
        }
        if (raw.diagnosticBridge.deDuplicationAudit.duplicateCount !== registry.diagnosticDuplicateCount) {
          throw new TypeError('Cenários da Educação: auditoria de não duplicação diverge do registro.')
        }

        const sourceHashChecks = [
          [raw.sourceSnapshot.authoringContract.sha256, registry.authoringContractSha256, 'contrato de autoria'],
          [raw.sourceSnapshot.advancedBundle.sha256, registry.advancedBundleSha256, 'bundle de Vocações'],
          [raw.sourceSnapshot.advancedRegistry.sha256, registry.advancedRegistrySha256, 'registro de Vocações'],
          [raw.sourceSnapshot.focalPneMunicipalMatrix.sha256, registry.focalPneMunicipalMatrixSha256, 'matriz PNE focal'],
          [raw.sourceSnapshot.regionalPublicInputs.sha256, registry.regionalPublicInputsSha256, 'entradas públicas regionais'],
        ] as const
        for (const [sourceHash, registryHash, label] of sourceHashChecks) {
          if (sourceHash !== registryHash) {
            throw new TypeError('Cenários da Educação: hash de ' + label + ' diverge do registro.')
          }
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

export const loadCenariosEducacaoBundle = createCenariosEducacaoLoader(defaultModuleLoader)

export function useCenariosEducacaoBundle(): CenariosEducacaoBundleState {
  const [state, setState] = useState<CenariosEducacaoBundleState>({
    status: 'loading',
    data: null,
    error: null,
  })

  useEffect(() => {
    let active = true
    loadCenariosEducacaoBundle().then(
      (data) => {
        if (active) setState({ status: 'ready', data, error: null })
      },
      (error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            data: null,
            error: error instanceof Error ? error.message : 'Falha ao validar os cenários da educação.',
          })
        }
      },
    )
    return () => { active = false }
  }, [])

  return state
}
