export type MunicipalFinanceSchemaVersion = 'municipal-finance-v1';

export type FinancialStage =
  | 'forecast'
  | 'authorized'
  | 'committed'
  | 'transferred'
  | 'received'
  | 'budgeted'
  | 'empenhado'
  | 'liquidado'
  | 'paid'
  | 'balance'
  | 'calculated_indicator'
  | 'not_applicable';

export type AmountNature =
  | 'official_estimate'
  | 'confirmed'
  | 'municipal_declared'
  | 'panel_displayed'
  | 'local_calculation';

export type ProgramFinancialStatus =
  | 'confirmed_beneficiary'
  | 'confirmed_non_beneficiary'
  | 'eligible'
  | 'not_eligible'
  | 'under_analysis'
  | 'selected'
  | 'agreement_signed'
  | 'transferred'
  | 'balance_available'
  | 'not_verified';

export type EvidenceStatus =
  | 'official_nominal'
  | 'official_aggregate'
  | 'municipal_declared'
  | 'panel_only'
  | 'not_verified'
  | 'unavailable';

export type DataQualityLevel = 'high' | 'medium' | 'low' | 'insufficient';

export type ReconciliationStatus =
  | 'not_required'
  | 'pending_source'
  | 'mapping_pending'
  | 'reconciled'
  | 'reconciliation_required'
  | 'source_missing'
  | 'divergent_explained'
  | 'divergent_unexplained'
  | 'divergent'
  | 'unavailable';

export type MunicipalFinanceCoverageStatus =
  | 'complete'
  | 'partial'
  | 'unavailable'
  | 'pending_source'
  | 'mapping_pending'
  | 'source_missing'
  | 'divergent';

export interface MunicipalFinanceCoverageDimension {
  rate: number | null;
  status: MunicipalFinanceCoverageStatus;
  availableSourceIds: readonly string[];
  missingSourceIds: readonly string[];
  reasonCodes: readonly string[];
}

export interface CompactFinancialValue {
  value: number | null;
  unit: 'BRL' | 'percent' | 'count' | 'coefficient' | 'BRL_per_student';
  referenceYear: number;
  financialStage: FinancialStage;
  amountNature: AmountNature;
  sourceId: string;
  nullReasonCode?: string;
}

export interface CompactFinancialAggregate extends CompactFinancialValue {
  coveredSourceIds: readonly string[];
  summationRuleId: string;
}

export type FundebCompositionStatus =
  | 'total'
  | 'included_in_total'
  | 'not_included_in_total'
  | 'composition_not_reconciled';

export interface FundebCompositionMetadata {
  includedInFundebTotal: boolean;
  compositionStatus: FundebCompositionStatus;
  doubleCountingRisk: 'none' | 'high';
  summationAllowed: boolean;
}

export interface CompactDerivedRate extends CompactFinancialValue {
  calculation: {
    formula: string;
    numeratorReferenceIds: readonly string[];
    denominatorReferenceId: string;
    sourceId: string;
    referenceYear: number;
    functionalClassification: '12 - Educação';
  };
}

export interface CompactDerivedDifference extends CompactFinancialValue {
  calculation: {
    formula: string;
    sourceId: string;
    referenceYear: number;
  };
}

export interface MunicipalFinanceExecutionHistoryEntry {
  referenceYear: number;
  sourceId: string;
  committed: CompactFinancialValue;
  liquidated: CompactFinancialValue;
  paid: CompactFinancialValue;
  committedNotLiquidated: CompactDerivedDifference;
  liquidatedNotPaid: CompactDerivedDifference;
  derivedRates: {
    liquidatedToCommittedRate: CompactDerivedRate;
    paidToCommittedRate: CompactDerivedRate;
    paidToLiquidatedRate: CompactDerivedRate;
  };
  stateReference: {
    paidToCommittedRate: CompactDerivedRate;
  };
}

export interface MunicipalFinanceMdeHistoryEntry {
  referenceYear: number;
  rate: CompactFinancialValue;
  marginFromMinimum: CompactDerivedDifference;
}

export interface MunicipalFinanceDocumentV1 {
  schemaVersion: MunicipalFinanceSchemaVersion;
  dataVersion: string;
  methodologyVersion: 'municipal-finance-p5b2b1-v1';
  generatedAt: string;
  municipality: {
    ibgeCode: string;
    name: string;
    slug: string;
    uf: 'RS';
  };
  periods: {
    closedFiscalYear: number;
    annualForecastYear: 2026;
    forecastCutoffDate: string;
    mixesPeriodsInTotals: false;
  };
  dataQuality: {
    level: DataQualityLevel;
    reasonCodes: readonly string[];
    coverageByDimension: {
      confirmedTransfers: MunicipalFinanceCoverageDimension;
      officialForecasts: MunicipalFinanceCoverageDimension;
      programStatuses: MunicipalFinanceCoverageDimension;
      budgetExecution: MunicipalFinanceCoverageDimension;
      constitutionalApplication: MunicipalFinanceCoverageDimension;
      perStudentMetrics: MunicipalFinanceCoverageDimension;
      reconciliation: MunicipalFinanceCoverageDimension;
    };
  };
  summary: {
    confirmedTransfersCoveredBySources: CompactFinancialAggregate;
    officialAnnualForecastsCurrentYear: CompactFinancialAggregate;
    dcaEducationCommitted: CompactFinancialValue;
  };
  amounts: {
    fundebTotalAnnualForecast: CompactFinancialValue & FundebCompositionMetadata;
    fundebVaafAnnualForecast: CompactFinancialValue & FundebCompositionMetadata;
    fundebVaatAnnualForecast: CompactFinancialValue & FundebCompositionMetadata;
    fundebVaarAnnualForecast: CompactFinancialValue & FundebCompositionMetadata;
    qseDistributedClosedYear: CompactFinancialValue;
    qseOfficialEstimateCurrentYear: CompactFinancialValue;
  };
  programStatuses: {
    fundebVaaf: {
      status: ProgramFinancialStatus;
      sourceId: string;
      referenceYear: 2026;
    };
    fundebVaat: {
      status: ProgramFinancialStatus;
      calculationStatus: 'habilitated_for_calculation' | 'not_habilitated_for_calculation' | 'not_verified';
      sourceIds: readonly string[];
      referenceYear: 2026;
    };
    fundebVaar: {
      status: ProgramFinancialStatus;
      sourceIds: readonly string[];
      referenceYear: 2026;
    };
  };
  qse: {
    enrollmentsClosedYear: CompactFinancialValue;
    distributionCoefficientClosedYear: CompactFinancialValue;
    distributionCoefficientCurrentYear: CompactFinancialValue;
    installments: CompactFinancialValue;
  };
  execution: {
    dcaEducation: {
      referenceYear: number;
      functionalClassification: '12 - Educação';
      amountNature: 'municipal_declared';
      sourceId: string;
      committed: CompactFinancialValue;
      liquidated: CompactFinancialValue;
      paid: CompactFinancialValue;
      outstandingNonProcessed: CompactFinancialValue;
      outstandingProcessed: CompactFinancialValue;
      budgeted: CompactFinancialValue;
      currentExpense: CompactFinancialValue;
      capitalExpense: CompactFinancialValue;
      derivedRates: {
        liquidatedToCommittedRate: CompactDerivedRate;
        paidToCommittedRate: CompactDerivedRate;
        paidToLiquidatedRate: CompactDerivedRate;
        outstandingToCommittedRate: CompactDerivedRate;
      };
      history: readonly MunicipalFinanceExecutionHistoryEntry[];
    };
  };
  constitutionalApplication: {
    status: 'reconciled' | 'source_missing' | 'divergent_explained' | 'divergent_unexplained';
    referenceYear: number;
    period: 6;
    stageBasis: 'empenhado';
    mdeAppliedAmount: ConstitutionalReconciledMetric;
    mdeAppliedRate: ConstitutionalReconciledMetric;
    mdeMarginFromMinimum: CompactDerivedDifference;
    mdeRateHistory: readonly MunicipalFinanceMdeHistoryEntry[];
    fundebProfessionalRemunerationRate: ConstitutionalReconciledMetric;
    fundebRevenueReceivedDeclared: CompactFinancialValue;
  };
  reconciliation: {
    status: ReconciliationStatus;
    scope: 'siope_rreo_constitutional_application';
    availableSourceIds: readonly string[];
    pendingSourceIds: readonly string[];
    absoluteDifference: CompactFinancialValue;
    percentageDifference: CompactFinancialValue;
    reasonCodes: readonly string[];
  };
  perStudent: {
    qseDistributedPerEnrollment: CompactDerivedRate;
  };
  educationLinks: readonly {
    indicatorId: string;
    programId: string;
    relationType: 'general_mde' | 'direct_cost_driver' | 'conditional_support' | 'accounting_context';
    municipalStatus: ProgramFinancialStatus;
    financialStage: FinancialStage;
    amountNature: AmountNature;
    evidenceStatus: EvidenceStatus;
    amountReferenceId: string;
  }[];
  educationalScoreIsolation: {
    needScore: null;
    actionabilityScore: null;
    confidenceScore: null;
    priorityScore: null;
    nullReasonCode: 'scores_not_applicable_to_financial_contract';
    changesDecisionSummary: false;
    changesAttentionOrder: false;
  };
  generationMetadata: {
    interfacePublished: false;
    includedInMunicipalIndex: false;
    manualSourcesIntegrated: false;
    lazyLoadOnly: true;
  };
}

export interface ConstitutionalReconciledMetric {
  canonical: CompactFinancialValue;
  siope: CompactFinancialValue;
  rreo: CompactFinancialValue;
  reconciliation: {
    status: 'reconciled' | 'source_missing' | 'divergent_explained' | 'divergent_unexplained';
    sourceIds: readonly string[];
    absoluteDifference: CompactFinancialValue;
    percentageDifference: CompactFinancialValue;
    tolerance: number;
    toleranceUnit: 'BRL' | 'percent';
    toleranceRuleId: string;
    canonicalRuleId: string;
    reasonCodes: readonly string[];
  };
}
