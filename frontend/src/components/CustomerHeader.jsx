export default function CustomerHeader({ customer, pnr, onSignOut }) {
  const history = customer.travel_history || {}
  const complaint = history.previous_complaint

  return (
    <header className="customer-header">
      <div className="customer-header-top">
        <div>
          <p className="customer-header-eyebrow">Signed in as</p>
          <h1 className="customer-name">{customer.name}</h1>
        </div>
        <button className="button button--ghost" type="button" onClick={onSignOut}>
          Sign out
        </button>
      </div>

      <dl className="customer-facts">
        <div className="customer-fact">
          <dt>Booking reference</dt>
          <dd className="mono">{pnr}</dd>
        </div>
        <div className="customer-fact">
          <dt>Loyalty tier</dt>
          <dd>
            <span className={`tier tier--${customer.loyalty_tier.toLowerCase()}`}>
              {customer.loyalty_tier}
            </span>
          </dd>
        </div>
        <div className="customer-fact">
          <dt>Flights in 12 months</dt>
          <dd>{history.flights_last_12_months}</dd>
        </div>
        <div className="customer-fact">
          <dt>Previous complaints</dt>
          <dd>
            {history.prior_complaints}
            {complaint ? ` — ${complaint.type}, resolved with ${complaint.resolution}` : ''}
          </dd>
        </div>
      </dl>
    </header>
  )
}
