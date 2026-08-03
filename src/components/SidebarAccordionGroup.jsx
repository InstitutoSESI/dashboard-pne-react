export function SidebarAccordionGroup({
  activeItemKey,
  icon: Icon,
  id,
  isOpen,
  items,
  label,
  onNavigate,
  onToggle,
}) {
  const panelId = `sidebar-${id}-items`

  return (
    <section className={`nav-group nav-group--${id}${isOpen ? ' is-open' : ''}`}>
      <button
        aria-controls={panelId}
        aria-expanded={isOpen}
        className="nav-item nav-item--group"
        type="button"
        onClick={() => onToggle(id)}
      >
        <span className="nav-item__icon" aria-hidden="true">
          <Icon />
        </span>
        <span className="nav-item__label">{label}</span>
        <ChevronIcon className="nav-item__chevron" />
      </button>

      <div
        aria-label={`Subitens de ${label}`}
        className="nav-subitems"
        hidden={!isOpen}
        id={panelId}
      >
        <ul>
          {items.map((item) => {
            const isCurrent = item.key === activeItemKey
            const ItemIcon = item.icon

            return (
              <li key={item.key}>
                <a
                  aria-current={isCurrent ? 'page' : undefined}
                  className={isCurrent ? 'nav-subitem is-active' : 'nav-subitem'}
                  href={`#${item.target}`}
                  onClick={(event) => {
                    event.preventDefault()
                    onNavigate(item.target)
                  }}
                >
                  {ItemIcon ? (
                    <span className="nav-subitem__icon" aria-hidden="true">
                      <ItemIcon />
                    </span>
                  ) : null}
                  <span>{item.label}</span>
                </a>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}

function ChevronIcon({ className = '' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path d="m8 10 4 4 4-4" />
    </svg>
  )
}
