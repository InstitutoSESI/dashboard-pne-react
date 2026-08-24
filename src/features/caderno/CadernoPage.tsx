import { useCallback, useEffect, useMemo, useState } from 'react'
import { ContentState } from '../../components/ContentState'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { CadernoGoalDetail } from './components/CadernoGoalDetail.js'
import { CadernoGoalIndex } from './components/CadernoGoalIndex.js'
import { CADERNO_ALL_SECTION_KEYS, countGoalCauses, plural } from './cadernoVocabulary.js'
import {
  cadernoFrontKey,
  getBrowserCadernoStorage,
  persistCadernoFronts,
  restoreCadernoFronts,
} from '../../domain/cadernoFrontsStorage.js'
import { useMunicipioCaderno } from '../../hooks/useMunicipioCaderno'
import { useMunicipioDiagnostic } from '../../hooks/useMunicipioDiagnostic'
import type { CadernoDocument } from './cadernoTypes'
import type { Pne2026DiagnosticResultViewModel } from '../diagnostic/diagnosticTypes'
import '../../styles/caderno-page.css'

/*
 * Caderno de hipóteses — PNE 2026.
 *
 * A página lê o artefato publicado e não decide nada: a ordem das metas, das
 * seções e das hipóteses é a do caderno, não existe escore nem classificação
 * relativa, e a seleção de frentes é decisão municipal guardada só no
 * navegador até a exportação explícita para a oficina.
 */

function countCauses(caderno: CadernoDocument): number {
  return caderno.goals.reduce((total, goal) => total + countGoalCauses(goal), 0)
}

const MONTHS = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

/** "2026-08-14" -> "14 de agosto de 2026", sem depender de fuso. */
function formatReferenceDate(reference: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(reference)
  if (!match) return reference
  const [, year, month, day] = match
  return `${Number(day)} de ${MONTHS[Number(month) - 1] ?? month} de ${year}`
}

export function CadernoPage({
  municipalityId,
  selectedMunicipio,
}: {
  municipalityId: string | null
  selectedMunicipio: string | null
}) {
  const { data, error, loading } = useMunicipioCaderno(municipalityId)
  const { data: diagnostic } = useMunicipioDiagnostic(municipalityId)
  const caderno = data?.caderno ?? null

  /*
   * Resultados oficiais do PNE 2026–2036, indexados por meta legal × indicador.
   *
   * O número da meta que o caderno exibe é o MESMO publicado no diagnóstico
   * municipal — o caderno não recalcula indicador. A camada de pesquisa segue
   * respondendo pelas causas; o resultado observado vem daqui.
   */
  const resultsByRelation = useMemo(() => {
    const index = new Map<string, Pne2026DiagnosticResultViewModel>()
    for (const goal of diagnostic?.pne2026PublicDiagnostic?.goals ?? []) {
      for (const result of goal.results) {
        index.set(`${result.goalId}|${result.indicatorId}`, result)
      }
    }
    return index
  }, [diagnostic])
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null)
  const [selectedKeys, setSelectedKeys] = useState<ReadonlySet<string>>(() => new Set())
  const [exportState, setExportState] = useState<'idle' | 'working' | 'failed'>('idle')

  const scope = useMemo(
    () => (caderno
      ? { municipalityIbge7: caderno.municipality.ibge7, referenceDate: caderno.referenceDate }
      : null),
    [caderno],
  )

  useEffect(() => {
    setSelectedGoalId(null)
    setExportState('idle')
    setSelectedKeys(scope ? new Set(restoreCadernoFronts(getBrowserCadernoStorage(), scope)) : new Set())
  }, [scope])

  const toggleFront = useCallback((goalId: string, factorId: string) => {
    if (!scope) return
    const key = cadernoFrontKey(goalId, factorId)
    const next = new Set(selectedKeys)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    persistCadernoFronts(getBrowserCadernoStorage(), scope, [...next])
    setSelectedKeys(next)
  }, [scope, selectedKeys])

  const exportWorkbook = useCallback(async () => {
    if (!caderno) return
    setExportState('working')
    try {
      const { downloadCadernoDecisionXlsx } = await import('./cadernoDecisionXlsx.js')
      await downloadCadernoDecisionXlsx(caderno, [...selectedKeys])
      setExportState('idle')
    } catch {
      setExportState('failed')
    }
  }, [caderno, selectedKeys])

  if (loading) {
    return <LoadingState message={`Carregando o caderno de hipóteses de ${selectedMunicipio ?? 'seu município'}…`} />
  }

  if (error || !caderno) {
    return (
      <ContentState kind="empty">
        <strong>O caderno de hipóteses ainda não está disponível para este município.</strong>
        <p>Estamos publicando o caderno município a município. Enquanto isso, o diagnóstico municipal continua disponível.</p>
      </ContentState>
    )
  }

  const causeCount = countCauses(caderno)
  const activeGoal = caderno.goals.find((goal) => goal.goalId === selectedGoalId) ?? caderno.goals[0]
  const planCounts = new Map(caderno.goals.map((goal) => [
    goal.goalId,
    CADERNO_ALL_SECTION_KEYS.reduce(
      (total, key) => total + goal.hypotheses[key].filter(
        (hypothesis) => selectedKeys.has(cadernoFrontKey(goal.goalId, hypothesis.factorId)),
      ).length,
      0,
    ),
  ]))

  return (
    <div className="page-stack caderno-page">
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={`${caderno.municipality.name}/${caderno.municipality.uf}`}
        description="O que os dados públicos mostram e o que a teoria sugere sobre cada meta, para orientar a conversa municipal sobre as frentes de trabalho."
        eyebrow="Planejamento municipal"
        title="Caderno de hipóteses — PNE 2026–2036"
        variant="editorial"
      />

      <section aria-labelledby="caderno-aviso" className="caderno-notice">
        <h2 className="caderno-notice__title" id="caderno-aviso">Como usar este caderno</h2>
        <p className="caderno-notice__text">Para cada meta, este caderno mostra o resultado do município e as possíveis causas desse resultado. Ele não decide nem prioriza: escolher as frentes de trabalho é decisão do município.</p>
        <p className="caderno-notice__meta">
          {plural(caderno.goals.length, 'meta', 'metas')} ·{' '}
          {plural(causeCount, 'possível causa', 'possíveis causas')} · atualizado em{' '}
          {formatReferenceDate(caderno.referenceDate)}
        </p>
      </section>

      <section aria-labelledby="caderno-frentes" className="caderno-toolbar">
        <div>
          <h2 className="caderno-toolbar__title" id="caderno-frentes">Frentes escolhidas pelo município</h2>
          <p className="caderno-toolbar__text">
            <strong>{plural(selectedKeys.size, 'frente selecionada', 'frentes selecionadas')}</strong>.
            A escolha fica guardada apenas neste navegador.
          </p>
        </div>
        <div className="caderno-toolbar__actions">
          <button
            className="pne-diagnostic-action pne-diagnostic-action--primary"
            disabled={selectedKeys.size === 0 || exportState === 'working'}
            onClick={() => { void exportWorkbook() }}
            type="button"
          >
            {exportState === 'working' ? 'Gerando planilha…' : 'Exportar frentes para a oficina'}
          </button>
          {exportState === 'failed' ? (
            <p className="caderno-toolbar__text" role="alert">
              Não foi possível gerar a planilha agora. Tente novamente.
            </p>
          ) : null}
        </div>
      </section>

      <div className="caderno-workspace">
        <CadernoGoalIndex
          goals={caderno.goals}
          onSelect={setSelectedGoalId}
          planCounts={planCounts}
          selectedGoalId={activeGoal.goalId}
        />
        <CadernoGoalDetail
          goal={activeGoal}
          key={activeGoal.goalId}
          onToggleFront={(factorId) => toggleFront(activeGoal.goalId, factorId)}
          resultsByRelation={resultsByRelation}
          selectedKeys={selectedKeys}
        />
      </div>
    </div>
  )
}
