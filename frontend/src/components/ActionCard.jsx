const ICONS = {
  REFUND: '₹',
  REBOOKING: '↻',
  MEAL_VOUCHER: '☕',
  LOUNGE_ACCESS: '◐',
  HOTEL_ACCOMMODATION: '⌂',
  FARE_DIFFERENCE_WAIVER: '✓'
}

export default function ActionCard({ action }) {
  return (
    <article className="action-card">
      <span className="action-icon" aria-hidden="true">
        {ICONS[action.action] || '✓'}
      </span>
      <div className="action-body">
        <p className="action-label">{action.label}</p>
        <p className="action-detail">{action.detail}</p>
      </div>
    </article>
  )
}
