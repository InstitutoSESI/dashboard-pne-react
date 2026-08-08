import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import ts from 'typescript';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const publicData = join(repoRoot, 'public', 'data');
const municipalityIndex = JSON.parse(readFileSync(join(publicData, 'municipios_index.json'), 'utf8'));
const municipalities = [...municipalityIndex.municipios].sort((a, b) => a.id_municipio.localeCompare(b.id_municipio));
const contracts = municipalities.map((municipality) => ({
  municipality,
  document: JSON.parse(readFileSync(join(publicData, 'municipios', municipality.id_municipio, 'financeiro.json'), 'utf8')),
}));
const manifest = JSON.parse(readFileSync(join(publicData, 'financeiro', 'manifest.json'), 'utf8'));
const catalogs = JSON.parse(readFileSync(join(publicData, 'financeiro', 'catalogos.json'), 'utf8'));

function objects(value) {
  if (!value || typeof value !== 'object') return [];
  if (Array.isArray(value)) return value.flatMap(objects);
  return [value, ...Object.values(value).flatMap(objects)];
}

function contractByCode(code) {
  return contracts.find(({ municipality }) => municipality.id_municipio === code).document;
}

function calculateContractsHash() {
  const digest = createHash('sha256');
  for (const municipality of municipalities) {
    const bytes = readFileSync(join(publicData, 'municipios', municipality.id_municipio, 'financeiro.json'));
    digest.update(municipality.id_municipio, 'ascii');
    digest.update(bytes);
  }
  return digest.digest('hex');
}

async function loadTypeScriptModule(path) {
  // O módulo é importado isolado via data: URL, onde imports relativos não
  // resolvem. Este teste valida a publicação RS, então o padrão do estado
  // ativo é substituído pelo equivalente RS.
  const source = readFileSync(path, 'utf8').replace(
    /import \{ ACTIVE_MUNICIPALITY_ID_PATTERN \} from '[^']*stateConfig(?:\.js)?';?\r?\n/,
    'const ACTIVE_MUNICIPALITY_ID_PATTERN = /^43\\d{5}$/;\n',
  );
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`);
}

test('1. existem 497 contratos lógicos em caminhos canônicos por código IBGE', () => {
  assert.equal(municipalities.length, 497);
  assert.equal(manifest.logicalContracts, 497);
  assert.equal(manifest.contractFiles, 497);
  const financeFiles = readdirSync(join(publicData, 'municipios'), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .filter((entry) => existsSync(join(publicData, 'municipios', entry.name, 'financeiro.json')));
  assert.equal(financeFiles.length, 497);
});

test('2. não existem aliases físicos por slug', () => {
  municipalities.forEach((municipality) => {
    assert.equal(
      existsSync(join(publicData, 'municipios', municipality.slug, 'financeiro.json')),
      false,
      municipality.slug,
    );
  });
});

test('3. todos os contratos usam o schema versionado esperado', () => {
  contracts.forEach(({ document }) => {
    assert.equal(document.schemaVersion, 'municipal-finance-v1');
    assert.equal(document.dataVersion, manifest.dataVersion);
    assert.match(document.dataVersion, /^p5b2b1-education-analysis-v1-/);
    assert.equal(document.methodologyVersion, 'municipal-finance-p5b2b1-v1');
    assert.match(document.municipality.ibgeCode, /^43\d{5}$/);
  });
});

test('4. todo valor financeiro nulo possui código de razão', () => {
  contracts.forEach(({ document }) => objects(document).forEach((item) => {
    if ('value' in item && item.value === null) assert.ok(item.nullReasonCode, document.municipality.ibgeCode);
    if ('rate' in item && item.rate === null) assert.ok(item.reasonCodes?.length, document.municipality.ibgeCode);
  }));
});

test('5. previsões permanecem separadas de transferências confirmadas', () => {
  contracts.forEach(({ document }) => {
    assert.equal(document.summary.confirmedTransfersCoveredBySources.financialStage, 'transferred');
    assert.equal(document.summary.confirmedTransfersCoveredBySources.amountNature, 'confirmed');
    assert.equal(document.summary.officialAnnualForecastsCurrentYear.financialStage, 'forecast');
    assert.equal(document.summary.officialAnnualForecastsCurrentYear.amountNature, 'official_estimate');
  });
});

test('6. execução DCA não é publicada como receita ou transferência', () => {
  contracts.forEach(({ document }) => {
    assert.match(document.summary.dcaEducationCommitted.sourceId, /^siconfi_dca_function_\d{4}$/);
    assert.equal(document.summary.dcaEducationCommitted.amountNature, 'municipal_declared');
    assert.notEqual(document.summary.dcaEducationCommitted.financialStage, 'transferred');
    assert.notEqual(document.summary.dcaEducationCommitted.financialStage, 'received');
  });
});

test('7. execução realizada e previsões preservam exercícios e naturezas próprias', () => {
  contracts.forEach(({ document }) => {
    assert.equal(document.periods.closedFiscalYear, document.execution.dcaEducation.referenceYear);
    assert.equal(document.periods.annualForecastYear, 2026);
    assert.equal(document.periods.mixesPeriodsInTotals, false);
    assert.equal(document.summary.confirmedTransfersCoveredBySources.referenceYear, 2024);
    assert.equal(document.summary.officialAnnualForecastsCurrentYear.referenceYear, 2026);
    assert.equal(document.summary.dcaEducationCommitted.referenceYear, document.execution.dcaEducation.referenceYear);
    assert.equal(document.execution.dcaEducation.committed.referenceYear, 2025);
    assert.equal(document.execution.dcaEducation.liquidated.referenceYear, 2025);
    assert.equal(document.execution.dcaEducation.paid.referenceYear, 2025);
  });
});

test('8. VAAR previsto nunca é tratado como recebido', () => {
  contracts.forEach(({ document }) => {
    const vaar = document.amounts.fundebVaarAnnualForecast;
    assert.ok(['forecast', 'not_applicable'].includes(vaar.financialStage));
    assert.notEqual(vaar.financialStage, 'received');
    assert.notEqual(vaar.amountNature, 'confirmed');
  });
});

test('9. não beneficiários VAAR permanecem sem valor potencial', () => {
  contracts.forEach(({ document }) => {
    if (document.programStatuses.fundebVaar.status === 'confirmed_non_beneficiary') {
      assert.equal(document.amounts.fundebVaarAnnualForecast.value, null);
      assert.equal(document.amounts.fundebVaarAnnualForecast.nullReasonCode, 'not_applicable_non_beneficiary');
    }
  });
});

test('10. complementações do Fundeb não podem ser somadas novamente ao total', () => {
  contracts.forEach(({ document }) => {
    assert.equal(document.amounts.fundebTotalAnnualForecast.compositionStatus, 'total');
    for (const field of ['fundebVaafAnnualForecast', 'fundebVaatAnnualForecast', 'fundebVaarAnnualForecast']) {
      const component = document.amounts[field];
      assert.equal(component.summationAllowed, false);
      assert.equal(component.doubleCountingRisk, 'high');
      assert.ok(['included_in_total', 'composition_not_reconciled'].includes(component.compositionStatus));
    }
  });
});

test('11. QSE realizada e estimada são registros distintos', () => {
  contracts.forEach(({ document }) => {
    const realized = document.amounts.qseDistributedClosedYear;
    const estimate = document.amounts.qseOfficialEstimateCurrentYear;
    assert.equal(realized.referenceYear, 2024);
    assert.equal(realized.financialStage, 'transferred');
    assert.equal(realized.amountNature, 'confirmed');
    assert.equal(estimate.referenceYear, 2026);
    assert.equal(estimate.financialStage, 'forecast');
    assert.equal(estimate.amountNature, 'official_estimate');
  });
});

test('12. QSE por matrícula usa denominador válido do mesmo ano e fonte', () => {
  contracts.forEach(({ document }) => {
    const metric = document.perStudent.qseDistributedPerEnrollment;
    const numerator = document.amounts.qseDistributedClosedYear;
    const denominator = document.qse.enrollmentsClosedYear;
    assert.equal(metric.referenceYear, numerator.referenceYear);
    assert.equal(metric.referenceYear, denominator.referenceYear);
    assert.equal(metric.sourceId, numerator.sourceId);
    if (denominator.value > 0) {
      assert.ok(Math.abs(metric.value - (numerator.value / denominator.value)) < 0.000001);
    }
  });
});

test('13. todos os estágios da DCA preservam natureza municipal declarada', () => {
  contracts.forEach(({ document }) => {
    const execution = document.execution.dcaEducation;
    for (const field of ['committed', 'liquidated', 'paid', 'outstandingNonProcessed', 'outstandingProcessed']) {
      assert.equal(execution[field].amountNature, 'municipal_declared');
      assert.equal(execution[field].sourceId, execution.sourceId);
      assert.equal(execution[field].referenceYear, execution.referenceYear);
    }
  });
});

test('14. taxas derivadas guardam mesma fonte, ano e função', () => {
  contracts.forEach(({ document }) => Object.values(document.execution.dcaEducation.derivedRates).forEach((metric) => {
    assert.equal(metric.calculation.sourceId, document.execution.dcaEducation.sourceId);
    assert.equal(metric.calculation.referenceYear, document.execution.dcaEducation.referenceYear);
    assert.equal(metric.calculation.functionalClassification, '12 - Educação');
    assert.ok(metric.calculation.numeratorReferenceIds.length > 0);
    assert.ok(metric.calculation.denominatorReferenceId);
  }));
});

test('15. denominador zero produz null com razão explícita', () => {
  const code = [
    "import json,sys",
    "sys.path.insert(0,'data_pipeline')",
    "from src.municipal_finance import derived_rate",
    "print(json.dumps(derived_rate([10],0,'x / y',['x'],'y','siconfi_dca_function_2024',2024)))",
  ].join(';');
  const result = spawnSync('python', ['-c', code], { cwd: repoRoot, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const metric = JSON.parse(result.stdout);
  assert.equal(metric.value, null);
  assert.equal(metric.nullReasonCode, 'zero_denominator');
});

test('16. aplicação constitucional preserva SIOPE, RREO e canônico reconciliado', () => {
  contracts.forEach(({ document }) => {
    assert.equal(document.constitutionalApplication.status, 'reconciled');
    assert.equal(document.constitutionalApplication.period, 6);
    assert.equal(document.constitutionalApplication.stageBasis, 'empenhado');
    for (const key of ['mdeAppliedAmount', 'mdeAppliedRate', 'fundebProfessionalRemunerationRate']) {
      const metric = document.constitutionalApplication[key];
      assert.notEqual(metric.siope.value, null);
      assert.notEqual(metric.rreo.value, null);
      assert.notEqual(metric.canonical.value, null);
      assert.equal(metric.reconciliation.status, 'reconciled');
      assert.equal(metric.siope.referenceYear, metric.rreo.referenceYear);
      assert.equal(metric.siope.referenceYear, metric.canonical.referenceYear);
      assert.equal(metric.siope.sourceId, `fnde_siope_indicators_odata_${metric.siope.referenceYear}_p6`);
      assert.equal(metric.rreo.sourceId, `fnde_siope_rreo_annex8_${metric.rreo.referenceYear}_p6`);
    }
  });
});

test('16.1 aplicação constitucional usa 2025 quando a conciliação é válida e 2024 somente como fallback', () => {
  const distributions = {
    mdeAmount: new Map(),
    mdeRate: new Map(),
    remuneration: new Map(),
    fundebRevenue: new Map(),
  };
  contracts.forEach(({ document }) => {
    const constitutional = document.constitutionalApplication;
    const entries = [
      ['mdeAmount', constitutional.mdeAppliedAmount.canonical],
      ['mdeRate', constitutional.mdeAppliedRate.canonical],
      ['remuneration', constitutional.fundebProfessionalRemunerationRate.canonical],
      ['fundebRevenue', constitutional.fundebRevenueReceivedDeclared],
    ];
    entries.forEach(([key, value]) => {
      distributions[key].set(value.referenceYear, (distributions[key].get(value.referenceYear) ?? 0) + 1);
    });
  });
  assert.deepEqual(Object.fromEntries(distributions.mdeAmount), { 2024: 11, 2025: 486 });
  assert.deepEqual(Object.fromEntries(distributions.mdeRate), { 2024: 10, 2025: 487 });
  assert.deepEqual(Object.fromEntries(distributions.remuneration), { 2024: 13, 2025: 484 });
  assert.deepEqual(Object.fromEntries(distributions.fundebRevenue), { 2024: 6, 2025: 491 });
});

test('17. SIOPE e RREO reconciliam sem alimentar os totais existentes', () => {
  contracts.forEach(({ document }) => {
    assert.deepEqual(document.reconciliation.pendingSourceIds, []);
    assert.equal(document.reconciliation.status, 'reconciled');
    assert.doesNotMatch(JSON.stringify(document.summary), /siope/i);
    assert.doesNotMatch(JSON.stringify(document.amounts), /siope/i);
    assert.doesNotMatch(JSON.stringify(document.summary), /fundebRevenueReceivedDeclared/);
  });
});

test('18. fontes manuais ficam apenas no catálogo e não imputam zero', () => {
  const expectedStatuses = new Set(['manual', 'blocked', 'needs_hardening', 'not_verified', 'unavailable']);
  const catalogStatuses = new Set(catalogs.sources.map((source) => source.status));
  expectedStatuses.forEach((status) => assert.equal(catalogStatuses.has(status), true, status));
  const blockedIds = catalogs.sources
    .filter((source) => expectedStatuses.has(source.status))
    .map((source) => source.sourceId);
  assert.ok(blockedIds.length > 0);
  contracts.forEach(({ document }) => {
    const serialized = JSON.stringify(document);
    blockedIds.forEach((sourceId) => assert.equal(serialized.includes(sourceId), false, sourceId));
  });
});

test('19. contrato educacional permanece sem dependência do financeiro P5-B1', () => {
  const diagnosticTypes = readFileSync(join(repoRoot, 'src', 'features', 'diagnostic', 'diagnosticTypes.ts'), 'utf8');
  assert.doesNotMatch(diagnosticTypes, /municipalFinance|municipal-finance-v1/);
  contracts.forEach(({ document }) => {
    assert.equal(document.educationalScoreIsolation.changesDecisionSummary, false);
    assert.equal(document.educationalScoreIsolation.changesAttentionOrder, false);
  });
});

test('20. priorityScore e demais escores permanecem null', () => {
  contracts.forEach(({ document }) => {
    const isolation = document.educationalScoreIsolation;
    for (const score of ['needScore', 'actionabilityScore', 'confidenceScore', 'priorityScore']) {
      assert.equal(isolation[score], null);
    }
    assert.equal(isolation.nullReasonCode, 'scores_not_applicable_to_financial_contract');
  });
});

test('21. loader lazy mantém cache e estados de loading, ausência, erro e versão', async () => {
  const module = await loadTypeScriptModule(join(repoRoot, 'src', 'data', 'municipalFinance.ts'));
  const fixture = contractByCode('4300109');
  let calls = 0;
  let release;
  const loader = module.createMunicipalFinanceLoader(() => {
    calls += 1;
    return new Promise((resolve) => { release = resolve; });
  });
  assert.equal(calls, 0);
  const pending = loader.load('4300109');
  assert.equal(loader.getState('4300109').status, 'loading');
  release(new Response(JSON.stringify(fixture), { status: 200, headers: { 'content-type': 'application/json' } }));
  assert.equal((await pending).municipality.ibgeCode, '4300109');
  assert.equal(loader.getState('4300109').status, 'ready');
  await loader.load('4300109');
  assert.equal(calls, 1);

  const absent = module.createMunicipalFinanceLoader(async () => new Response('', { status: 404 }));
  await assert.rejects(absent.load('4300109'), { code: 'contract_absent' });
  assert.equal(absent.getState('4300109').status, 'absent');

  const http = module.createMunicipalFinanceLoader(async () => new Response('', { status: 503 }));
  await assert.rejects(http.load('4300109'), { code: 'http_error' });
  assert.equal(http.getState('4300109').status, 'error');

  const incompatible = module.createMunicipalFinanceLoader(async () => new Response(JSON.stringify({ schemaVersion: 'future' }), { status: 200 }));
  await assert.rejects(incompatible.load('4300109'), { code: 'incompatible_version' });
  assert.equal(incompatible.getState('4300109').status, 'incompatible_version');
});

test('22. geração publicada corresponde ao hash determinístico do manifesto', () => {
  assert.equal(calculateContractsHash(), manifest.contractsSha256);
  assert.match(manifest.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.equal(manifest.generatedAt, '2026-07-20T00:00:00-03:00');
});

test('23. financeiro não foi incorporado a nenhum index.json municipal', () => {
  municipalities.forEach((municipality) => {
    const codeIndex = JSON.parse(readFileSync(join(publicData, 'municipios', municipality.id_municipio, 'index.json'), 'utf8'));
    assert.equal(Object.hasOwn(codeIndex, 'financeiro'), false, municipality.id_municipio);
  });
});
