/**
 * Structural page header shared by the product domains.
 *
 * This primitive owns only the semantic heading anatomy. Domains keep their
 * own controls and supplementary composition in named slots instead of
 * inheriting another domain's component.
 */
/**
 * @param {{
 *   actions?: import('react').ReactNode,
 *   aside?: import('react').ReactNode,
 *   asideClassName?: string,
 *   asideContentClassName?: string,
 *   asideLabel?: string,
 *   actionsClassName?: string,
 *   className?: string,
 *   context?: import('react').ReactNode,
 *   contextClassName?: string,
 *   description?: import('react').ReactNode,
 *   descriptionClassName?: string,
 *   eyebrow?: import('react').ReactNode,
 *   eyebrowClassName?: string,
 *   mainClassName?: string,
 *   title: import('react').ReactNode,
 *   variant?: string,
 * }} props
 */
export function PageHeader({
  actions = null,
  aside = null,
  asideClassName = '',
  asideContentClassName = '',
  asideLabel = undefined,
  actionsClassName = '',
  className = '',
  context = null,
  description = null,
  descriptionClassName = '',
  eyebrow = null,
  eyebrowClassName = '',
  mainClassName = '',
  title,
  variant = 'listing',
  contextClassName = '',
}) {
  const hasSupplementary = aside || actions

  return (
    <header className={`platform-page-header platform-page-header--${variant}${className ? ` ${className}` : ''}`}>
      <div className={`platform-page-header__main${mainClassName ? ` ${mainClassName}` : ''}`}>
        {eyebrow ? <p className={`platform-page-header__eyebrow${eyebrowClassName ? ` ${eyebrowClassName}` : ''}`}>{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p className={`platform-page-header__description${descriptionClassName ? ` ${descriptionClassName}` : ''}`}>{description}</p> : null}
        {context ? <div className={`platform-page-header__context${contextClassName ? ` ${contextClassName}` : ''}`}>{context}</div> : null}
      </div>

      {hasSupplementary ? (
        <aside className={`platform-page-header__aside${asideClassName ? ` ${asideClassName}` : ''}`} aria-label={asideLabel}>
          {aside ? <div className={`platform-page-header__aside-content${asideContentClassName ? ` ${asideContentClassName}` : ''}`}>{aside}</div> : null}
          {actions ? <div className={`platform-page-header__actions${actionsClassName ? ` ${actionsClassName}` : ''}`}>{actions}</div> : null}
        </aside>
      ) : null}
    </header>
  )
}
