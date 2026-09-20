const STATUS_COPY = {
  cancelled: 'Cancelled',
  delayed: 'Delayed',
  unaffected: 'On schedule'
}

export default function FlightCard({ flight }) {
  const status = flight.status || 'unaffected'
  const route = flight.route || {}

  return (
    <article className={`flight-card flight-card--${status}`}>
      <div className="flight-card-head">
        <span className="flight-number mono">
          {flight.flight_number || 'Flight number not issued'}
        </span>
        <span className={`status-pill status-pill--${status}`}>
          {STATUS_COPY[status] || status}
        </span>
      </div>

      <div className="flight-route">
        <span className="city">{route.from}</span>
        <span className="route-line" aria-hidden="true" />
        <span className="city">{route.to}</span>
      </div>

      <dl className="flight-times">
        <div>
          <dt>Date</dt>
          <dd>{flight.date_label || flight.date}</dd>
        </div>
        <div>
          <dt>Scheduled</dt>
          <dd className="mono">{flight.scheduled_departure}</dd>
        </div>
        {flight.new_departure ? (
          <div>
            <dt>New departure</dt>
            <dd className="mono emphasis">{flight.new_departure}</dd>
          </div>
        ) : null}
      </dl>

      {status === 'delayed' && flight.delay_hours ? (
        <p className="flight-note">Delayed by {flight.delay_hours} hours.</p>
      ) : null}
      {status === 'cancelled' && flight.disruption_reason ? (
        <p className="flight-note">Cancelled due to {flight.disruption_reason}.</p>
      ) : null}
    </article>
  )
}
