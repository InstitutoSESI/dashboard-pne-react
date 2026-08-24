import { LoadingState } from '../../components/LoadingState'
import { useForesightEducacao } from '../../hooks/useForesightEducacao'
import { ForesightScenarioReport } from './ForesightScenarioReport'
import type { ForesightDocument } from './foresightTypes'

/*
 * Cenários da educação municipal.
 *
 * A página resolve o pacote do município e entrega a leitura ao relatório
 * compartilhado. A rota só é alcançável quando o manifesto declara o município
 * publicado; esta página nunca é montada em vazio.
 */
export function ForesightEducacaoPage({
  municipalityId,
  selectedMunicipio,
}: {
  municipalityId: string | null
  selectedMunicipio: string | null
}) {
  const { data, loading } = useForesightEducacao(municipalityId)
  const document: ForesightDocument | null = data?.document ?? null

  if (loading) {
    return <LoadingState message={`Carregando os cenários da educação de ${selectedMunicipio ?? 'seu município'}…`} />
  }

  /*
   * Sem pacote válido a página não se monta: quem decide a visibilidade é o
   * roteador, a partir do manifesto. Chegar aqui sem documento significa falha
   * de integridade, e nesse caso não há o que apresentar.
   */
  if (!document) return null

  return (
    <ForesightScenarioReport
      context={`${document.municipality.name}/${document.municipality.uf}`}
      document={document}
    />
  )
}
