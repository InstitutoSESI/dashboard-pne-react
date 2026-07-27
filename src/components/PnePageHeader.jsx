export function PnePageHeader({
  actions,
  asideContent,
  asideLabel,
  context,
  description,
  eyebrow,
  title,
  variant = '',
}) {
  const hasAside = asideContent || actions
  const variantClassName = variant
    ? ` platform-page-header platform-page-header--${variant}`
    : ''

  return (
    <header className={`pne-page-header${variantClassName}`}>
      <div className="pne-page-header__main">
        <p className="pne-page-header__eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {description ? <p className="pne-page-header__description">{description}</p> : null}
        {context ? <div className="pne-page-header__context">{context}</div> : null}
      </div>

      {hasAside ? (
        <aside className="pne-page-header__aside" aria-label={asideLabel}>
          {asideContent ? <div className="pne-page-header__aside-content">{asideContent}</div> : null}
          {actions ? <div className="pne-page-header__actions">{actions}</div> : null}
        </aside>
      ) : null}
    </header>
  )
}
