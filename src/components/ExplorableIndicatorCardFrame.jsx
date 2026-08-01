import { InteractionChevron } from './InteractionChevron'
import { Sparkline } from './Sparkline'
import { StatusBadge } from './StatusBadge'

export function ExplorableIndicatorCardFrame({
  buttonRef,
  classContract,
  disabled = false,
  isSelected = false,
  onSelect,
  viewModel,
}) {
  const {
    anatomy,
    ariaLabel,
    contextLabel,
    description,
    featureMeta,
    footer,
    hideContext = false,
    hideSparkline = false,
    hideStatus = false,
    hideSupport = false,
    insight,
    layout,
    leadingIcon,
    metaLine,
    metadata,
    modifier,
    modifierExtras,
    sparklineSeries,
    status,
    support,
    title,
    value,
    variant,
  } = viewModel
  const isUniform = layout === 'uniform'
  const isEditorialCard = anatomy === 'education' || anatomy === 'financial'
  const usesEducationReference = isEditorialCard && !isUniform
  const statusTone = status?.tone ?? 'default'
  const valueLength = Array.from(String(value?.display ?? '')).length
  const denseValueLength = anatomy === 'financial' ? 11 : 9
  const valueScaleClass = isEditorialCard
    ? valueLength >= denseValueLength
      ? ' indicator-card-shell__value-row--dense'
      : valueLength >= 6
        ? ' indicator-card-shell__value-row--compact'
        : ''
    : ''
  const variantClass = variant ? ` ${classContract.root}--${variant}` : ''
  const modifiers = [
    ...(Array.isArray(modifier) ? modifier : modifier ? [modifier] : []),
    ...(Array.isArray(modifierExtras) ? modifierExtras : modifierExtras ? [modifierExtras] : []),
  ]
  const modifierClass = modifiers.map((name) => ` ${classContract.root}--${name}`).join('')
  const anatomyClass = anatomy ? ` indicator-card-shell--${anatomy}` : ''
  const referenceClass = usesEducationReference ? ' indicator-card-shell--education-reference' : ''
  const directionClass = isEditorialCard && status?.direction ? ` indicator-card-shell--direction-${status.direction}` : ''
  const uniformClass = isUniform ? ' indicator-card-shell--uniform' : ''
  const className = `${classContract.root} indicator-card-shell${anatomyClass}${referenceClass} indicator-card-shell--${statusTone}${directionClass}${uniformClass} interaction-card--explorable ${classContract.statusModifier(statusTone)}${variantClass}${modifierClass}${isSelected ? ' is-selected' : ''}`

  return (
    <button
      className={className}
      ref={buttonRef}
      type="button"
      onClick={onSelect}
      aria-label={ariaLabel}
      aria-pressed={isSelected}
      disabled={disabled}
      title={title}
    >
      {isUniform ? (
        <>
          <span className={`${classContract.topline} indicator-card-shell__topline`}>
            {!hideContext ? <span className={`${classContract.context} indicator-card-shell__context`}>{contextLabel}</span> : null}
            {!hideStatus && status?.label ? (
              <StatusBadge marker={status.marker} status={status.label} tone={statusTone} />
            ) : null}
          </span>
          <span className={`${classContract.title} indicator-card-shell__title`}>{title}</span>
          <span className={`${classContract.valueRow} indicator-card-shell__value-row${valueScaleClass}`}>
            <strong>{value.display}</strong>
            {value.metaLabel ? <span>{value.metaLabel}</span> : null}
          </span>
          {metaLine ? (
            <span className="indicator-card-shell__metaline">
              <strong>{metaLine.year}</strong>
              {metaLine.change ? <span>{metaLine.change}</span> : null}
            </span>
          ) : null}
          <span className={`${classContract.footer} indicator-card-shell__footer indicator-card-shell__footer--uniform`}>
            <span className="indicator-card-shell__footer-action">{footer.actionLabel}</span>
            <span className="indicator-card-shell__action" aria-hidden="true"><InteractionChevron /></span>
          </span>
        </>
      ) : (
      <>
      {leadingIcon ? (
        <span className="indicator-card-shell__leading-icon" aria-hidden="true">
          {leadingIcon}
        </span>
      ) : null}

      <span className={`${classContract.topline} indicator-card-shell__topline`}>
        {!hideContext ? <span className={`${classContract.context} indicator-card-shell__context`}>{contextLabel}</span> : null}
        {!hideStatus && status?.label ? (
          <StatusBadge
            marker={isEditorialCard ? status.marker : undefined}
            status={status.label}
            tone={statusTone}
          />
        ) : null}
      </span>

      <span className={`${classContract.title} indicator-card-shell__title`}>{title}</span>
      <span className={`${classContract.description} indicator-card-shell__description`}>{description}</span>

      {isEditorialCard ? (
        <>
          <span className={`${classContract.valueRow} indicator-card-shell__value-row${valueScaleClass}`}>
            <strong>{value.display}</strong>
            {value.metaLabel ? <span>{value.metaLabel}</span> : null}
          </span>

          <span className={`${classContract.metadata} indicator-card-shell__metadata`}>
            <span className={`${classContract.metadataItem} indicator-card-shell__metadata-item`}>
              <span className={`${classContract.metadataLabel} indicator-card-shell__metadata-label`}>{metadata.yearLabel ?? 'Ano'}</span>
              <strong className={`${classContract.metadataValue} indicator-card-shell__metadata-value`}>{metadata.year}</strong>
            </span>
            {metadata.variation ? (
              <span className={`${classContract.metadataItem} indicator-card-shell__metadata-item`}>
                <span className={`${classContract.metadataLabel} indicator-card-shell__metadata-label`}>{metadata.variation.label}</span>
                <strong className={`${classContract.metadataValue} indicator-card-shell__metadata-value indicator-card-shell__metadata-value--variation`}>{metadata.variation.value}</strong>
              </span>
            ) : null}
          </span>

          {featureMeta ? (
            <span className="indicator-card-shell__feature-meta">
              {featureMeta.map((item) => (
                <span className="indicator-card-shell__feature-meta-item" key={`${item.label}-${item.value}`}>
                  {item.valueFirst ? (
                    <>
                      <strong>{item.value}</strong>
                      {item.label ? <span>{item.label}</span> : null}
                    </>
                  ) : (
                    <>
                      {item.label ? <span>{item.label}</span> : null}
                      <strong>{item.value}</strong>
                    </>
                  )}
                </span>
              ))}
            </span>
          ) : null}

          <span className={`${classContract.divider} indicator-card-shell__divider`} aria-hidden="true" />

          <span className={`${classContract.insight} indicator-card-shell__insight`}>
            <span className={`${classContract.insightItem} indicator-card-shell__insight-item`}>
              {usesEducationReference ? (
                <>
                  {insight.marker ? (
                    <span className="indicator-card-shell__insight-marker" aria-hidden="true">
                      {insight.direction === 'up' ? (
                        <svg viewBox="0 0 24 24" focusable="false">
                          <path d="m4 16 5-5 4 4 7-7M15 8h5v5" />
                        </svg>
                      ) : insight.direction === 'down' ? (
                        <svg viewBox="0 0 24 24" focusable="false">
                          <path d="m4 8 5 5 4-4 7 7M15 16h5v-5" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" focusable="false">
                          <path d="M4 12h16M16 8l4 4-4 4" />
                        </svg>
                      )}
                    </span>
                  ) : null}
                  <span className="indicator-card-shell__insight-copy">
                    {isEditorialCard ? (
                      <span className={`${classContract.insightLabel} indicator-card-shell__insight-label`}>{insight.label ?? 'Leitura'}</span>
                    ) : null}
                    <strong className={`${classContract.insightValue} indicator-card-shell__insight-value`}>{insight.emphasis ?? insight.reading}</strong>
                    {insight.context ? <span>{insight.context}</span> : null}
                  </span>
                </>
              ) : (
                <>
                  <span className={`${classContract.insightLabel} indicator-card-shell__insight-label`}>Leitura</span>
                  <strong className={`${classContract.insightValue} indicator-card-shell__insight-value`}>{insight.reading}</strong>
                </>
              )}
            </span>
            {insight.period ? (
              <span className={`${classContract.insightItem} indicator-card-shell__insight-item`}>
                <span className={`${classContract.insightLabel} indicator-card-shell__insight-label`}>Período</span>
                <strong className={`${classContract.insightValue} indicator-card-shell__insight-value`}>{insight.period}</strong>
              </span>
            ) : null}
          </span>
        </>
      ) : (
        <>
          <span className={`${classContract.valueRow} indicator-card-shell__value-row`}>
            <strong>{value.display}</strong>
            <span>{value.metaLabel}</span>
          </span>

          {!hideSupport && support ? (
            <span className={`${classContract.support} indicator-card-shell__support`}>
              <span>{support.label}</span>
              <strong>{support.value}</strong>
            </span>
          ) : null}

          {!hideSparkline ? <Sparkline series={sparklineSeries} classNames={classContract.sparkline} /> : null}
        </>
      )}

      <span className={`${classContract.footer} indicator-card-shell__footer`}>
        {footer.primary ? (
          <span title={footer.primary}>
            {footer.icon === 'history' ? (
              <svg className="indicator-card-shell__footer-icon" viewBox="0 0 24 24" focusable="false" aria-hidden="true">
                <path d="M5 19V12M12 19V5M19 19V9" />
              </svg>
            ) : null}
            {footer.primary}
          </span>
        ) : null}
        {footer.secondary ? <span title={footer.secondary}>{footer.secondary}</span> : null}
        {footer.actionLabel ? (
          <span
            className={`${classContract.action ?? 'indicator-card-shell__action'} indicator-card-shell__action`}
            aria-hidden="true"
            title={footer.actionLabel}
          >
            <InteractionChevron />
          </span>
        ) : (
          <InteractionChevron />
        )}
      </span>
      </>
      )}
    </button>
  )
}
