import type { MunicipalityId } from '../types/data'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function assertMunicipalityPayloadMatchesRequest(
  payload: unknown,
  requestedMunicipalityId: MunicipalityId,
): void {
  if (!isRecord(payload)) {
    throw new Error(`Payload municipal inválido para o código ${requestedMunicipalityId}.`)
  }
  if (!Object.prototype.hasOwnProperty.call(payload, 'id_municipio')) return

  if (payload.id_municipio !== requestedMunicipalityId) {
    throw new Error(
      `Identidade municipal divergente: solicitado ${requestedMunicipalityId}, recebido ${String(payload.id_municipio)}.`,
    )
  }
}
