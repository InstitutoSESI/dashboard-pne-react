import { PageHeader } from './PageHeader'

export function PnePageHeader({
  actions,
  asideContent,
  asideLabel,
  context,
  description,
  eyebrow,
  title,
  variant = 'listing',
}) {
  return (
    <PageHeader
      actions={actions}
      actionsClassName="pne-page-header__actions"
      aside={asideContent}
      asideClassName="pne-page-header__aside"
      asideContentClassName="pne-page-header__aside-content"
      asideLabel={asideLabel}
      className="pne-page-header"
      context={context}
      contextClassName="pne-page-header__context"
      description={description}
      descriptionClassName="pne-page-header__description"
      eyebrow={eyebrow}
      eyebrowClassName="pne-page-header__eyebrow"
      mainClassName="pne-page-header__main"
      title={title}
      variant={variant}
    />
  )
}
