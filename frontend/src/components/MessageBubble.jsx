import ActionCard from './ActionCard.jsx'
import EscalationBanner from './EscalationBanner.jsx'

export default function MessageBubble({ message }) {
  const isCustomer = message.role === 'customer'

  return (
    <div className={`message-row message-row--${isCustomer ? 'customer' : 'agent'}`}>
      <div className={`bubble bubble--${isCustomer ? 'customer' : 'agent'}`}>
        {!isCustomer ? <p className="bubble-sender">Resolution support</p> : null}
        <p className="bubble-text">{message.content}</p>
      </div>

      {!isCustomer && message.actions && message.actions.length > 0 ? (
        <div className="action-list">
          {message.actions.map((action, idx) => (
            <ActionCard key={`${action.action}-${idx}`} action={action} />
          ))}
        </div>
      ) : null}

      {!isCustomer ? <EscalationBanner escalation={message.escalation} /> : null}
    </div>
  )
}
