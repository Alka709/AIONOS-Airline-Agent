export default function EscalationBanner({ escalation }) {
  if (!escalation || !escalation.required) return null

  return (
    <aside className="escalation-banner" role="status">
      <p className="escalation-title">Passed to a human agent</p>
      <p className="escalation-text">
        {escalation.reason || 'Your request requires support from a human agent.'}
      </p>
      {escalation.ticket_id ? (
        <p className="escalation-ticket mono">Case {escalation.ticket_id}</p>
      ) : null}
    </aside>
  )
}
