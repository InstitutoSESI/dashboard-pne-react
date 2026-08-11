import type { MunicipalFinanceDocumentV1 } from '../features/diagnostic/municipalFinanceTypes';
import { ACTIVE_MUNICIPALITY_ID_PATTERN } from '../config/stateConfig.js';

export const MUNICIPAL_FINANCE_SCHEMA_VERSION = 'municipal-finance-v1' as const;

export type MunicipalFinanceLoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'absent'
  | 'incompatible_version'
  | 'error';

export type MunicipalFinanceLoadErrorCode =
  | 'invalid_identifier'
  | 'contract_absent'
  | 'http_error'
  | 'invalid_contract'
  | 'incompatible_version';

export interface MunicipalFinanceLoadState {
  status: MunicipalFinanceLoadStatus;
  data: MunicipalFinanceDocumentV1 | null;
  error: MunicipalFinanceLoadError | null;
}

export interface MunicipalFinanceSourceCatalogEntry {
  sourceId: string;
  name?: string;
  url?: string;
  agency?: string;
  referenceYear?: number;
  referenceYears?: readonly number[];
  stateCodes?: readonly string[];
  methodologyUrl?: string;
  resultsUrl?: string;
  status: string;
  reasonCode?: string;
}

export interface MunicipalFinanceCatalog {
  schemaVersion: string;
  dataVersion: string;
  sources: readonly MunicipalFinanceSourceCatalogEntry[];
  reasonMessages: Readonly<Record<string, string>>;
  summationRules: Readonly<Record<string, string>>;
}

export class MunicipalFinanceLoadError extends Error {
  readonly code: MunicipalFinanceLoadErrorCode;
  readonly httpStatus: number | null;

  constructor(code: MunicipalFinanceLoadErrorCode, message: string, httpStatus: number | null = null) {
    super(message);
    this.name = 'MunicipalFinanceLoadError';
    this.code = code;
    this.httpStatus = httpStatus;
  }
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

let catalogRequest: Promise<MunicipalFinanceCatalog> | null = null;

const idleState = (): MunicipalFinanceLoadState => ({ status: 'idle', data: null, error: null });

export const normalizeMunicipalFinanceIdentifier = (identifier: string): string => {
  const normalized = identifier.trim().toLowerCase();
  if (!ACTIVE_MUNICIPALITY_ID_PATTERN.test(normalized)) {
    throw new MunicipalFinanceLoadError('invalid_identifier', `Identificador municipal inválido: ${identifier}`);
  }
  return normalized;
};

export const resolveMunicipalFinancePath = (identifier: string): string =>
  `/data/municipios/${normalizeMunicipalFinanceIdentifier(identifier)}/financeiro.json`;

export const loadMunicipalFinanceCatalog = (
  fetchImpl: FetchLike = fetch,
): Promise<MunicipalFinanceCatalog> => {
  if (catalogRequest) return catalogRequest;

  catalogRequest = (async () => {
    const response = await fetchImpl('/data/financeiro/catalogos.json');
    if (!response.ok) {
      throw new MunicipalFinanceLoadError(
        'http_error',
        `Falha HTTP ao carregar o catálogo financeiro: ${response.status}.`,
        response.status,
      );
    }
    const payload = await response.json() as Partial<MunicipalFinanceCatalog>;
    if (
      payload.schemaVersion !== MUNICIPAL_FINANCE_SCHEMA_VERSION
      || !Array.isArray(payload.sources)
      || !payload.reasonMessages
      || !payload.summationRules
    ) {
      throw new MunicipalFinanceLoadError('invalid_contract', 'O catálogo financeiro é incompatível.');
    }
    return payload as MunicipalFinanceCatalog;
  })().catch((error) => {
    catalogRequest = null;
    throw error;
  });

  return catalogRequest;
};

export const createMunicipalFinanceLoader = (fetchImpl: FetchLike = fetch) => {
  const cache = new Map<string, Promise<MunicipalFinanceDocumentV1>>();
  const states = new Map<string, MunicipalFinanceLoadState>();

  const getState = (identifier: string): MunicipalFinanceLoadState => {
    const key = normalizeMunicipalFinanceIdentifier(identifier);
    return states.get(key) ?? idleState();
  };

  const clear = (identifier?: string): void => {
    if (identifier === undefined) {
      cache.clear();
      states.clear();
      return;
    }
    const key = normalizeMunicipalFinanceIdentifier(identifier);
    cache.delete(key);
    states.delete(key);
  };

  const load = (
    identifier: string,
    options: { force?: boolean } = {},
  ): Promise<MunicipalFinanceDocumentV1> => {
    const key = normalizeMunicipalFinanceIdentifier(identifier);
    if (!options.force) {
      const cached = cache.get(key);
      if (cached) return cached;
    }

    states.set(key, { status: 'loading', data: null, error: null });
    const request = (async () => {
      try {
        const response = await fetchImpl(resolveMunicipalFinancePath(key));
        if (response.status === 404) {
          throw new MunicipalFinanceLoadError('contract_absent', 'Contrato financeiro municipal ausente.', 404);
        }
        if (!response.ok) {
          throw new MunicipalFinanceLoadError(
            'http_error',
            `Falha HTTP ao carregar o contrato financeiro: ${response.status}.`,
            response.status,
          );
        }

        let payload: unknown;
        try {
          payload = await response.json();
        } catch {
          throw new MunicipalFinanceLoadError('invalid_contract', 'O contrato financeiro não contém JSON válido.');
        }
        if (!payload || typeof payload !== 'object' || !('schemaVersion' in payload)) {
          throw new MunicipalFinanceLoadError('invalid_contract', 'O contrato financeiro não possui versão de schema.');
        }
        if (payload.schemaVersion !== MUNICIPAL_FINANCE_SCHEMA_VERSION) {
          throw new MunicipalFinanceLoadError(
            'incompatible_version',
            `Versão financeira incompatível: ${String(payload.schemaVersion)}.`,
          );
        }

        const document = payload as MunicipalFinanceDocumentV1;
        states.set(key, { status: 'ready', data: document, error: null });
        return document;
      } catch (error) {
        const normalizedError = error instanceof MunicipalFinanceLoadError
          ? error
          : new MunicipalFinanceLoadError('http_error', 'Falha inesperada ao carregar o contrato financeiro.');
        cache.delete(key);
        states.set(key, {
          status: normalizedError.code === 'contract_absent'
            ? 'absent'
            : normalizedError.code === 'incompatible_version'
              ? 'incompatible_version'
              : 'error',
          data: null,
          error: normalizedError,
        });
        throw normalizedError;
      }
    })();

    cache.set(key, request);
    return request;
  };

  return { load, getState, clear };
};

export const municipalFinanceLoader = createMunicipalFinanceLoader();
