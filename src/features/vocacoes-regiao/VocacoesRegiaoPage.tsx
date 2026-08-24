import { LoadingState } from '../../components/LoadingState'
import { useVocacoesRegiao } from '../../hooks/useVocacoesRegiao'
import { ForesightScenarioReport } from '../foresight/ForesightScenarioReport'

/*
 * Vocações da Região.
 *
 * A página resolve o pacote da região a que o município pertence e entrega a
 * leitura ao mesmo relatório de cenários usado no escopo municipal — o corpo
 * do relatório lê apenas `document.*`, então a transposição não pede nenhuma
 * ramificação de renderização.
 *
 * Enquanto a camada de pesquisa não publicar o contrato de origem, o manifesto
 * fica vazio, a rota não é alcançável e esta página não é montada. Ela não
 * inventa cenário regional nem reaproveita o pacote de um município.
 */
export function VocacoesRegiaoPage({
  municipalityId,
}: {
  municipalityId: string | null
}) {
  const { data, loading } = useVocacoesRegiao(municipalityId)

  if (loading) {
    return <LoadingState message="Carregando as vocações da região…" />
  }

  /*
   * Quem decide a visibilidade é o roteador, a partir do manifesto. Chegar
   * aqui sem pacote significa falha de integridade, e nesse caso não há o que
   * apresentar.
   */
  if (!data) return null

  const { document } = data

  return (
    <ForesightScenarioReport
      context={`Região ${document.region.name}/${document.region.uf}`}
      document={document}
    />
  )
}
