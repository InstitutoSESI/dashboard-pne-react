import type { PmeEditorialPath } from './pmeTypes'

export function PmeEditorialPaths({ paths }: { paths: PmeEditorialPath[] }) {
  if (!paths.length) return <p className="pme-note">Não há instrumentos associados a esta seleção. Outras possibilidades de financiamento podem ser consultadas nos canais oficiais.</p>
  return <div className="pme-editorial-paths">{paths.map((path) => {
    const hasRequirements = Boolean(path.knownConditions?.length || path.evidenceRequired?.length)
    const hasBothLists = Boolean(path.knownConditions?.length && path.evidenceRequired?.length)
    return <article className={`pme-editorial-path${hasRequirements ? hasBothLists ? ' pme-editorial-path--three-columns' : '' : ' pme-editorial-path--simple'}`} key={path.id}>
    <div className="pme-editorial-path__summary"><h3>{path.title}</h3><p>{path.relationReason}</p>
      {path.officialUrl && <p><a href={path.officialUrl}>Referência oficial do instrumento</a></p>}
    </div>
    {!!path.knownConditions?.length && <div className="pme-editorial-path__requirements"><h4>Condições de acesso</h4><ul>{path.knownConditions.map((condition) => <li key={condition}>{condition}</li>)}</ul></div>}
    {!!path.evidenceRequired?.length && <div className="pme-editorial-path__requirements"><h4>Informações a conferir</h4><ul>{path.evidenceRequired.map((condition) => <li key={condition}>{condition}</li>)}</ul></div>}
  </article>})}<p className="pme-editorial-paths__caution">Consulte as condições de acesso nas fontes oficiais e, antes de planejar a utilização, confirme as regras atuais, a elegibilidade e os recursos disponíveis para o município.</p></div>
}
