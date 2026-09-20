import FlightCard from './FlightCard.jsx'

export default function BookingPanel({ booking }) {
  const flights = booking.flights || []

  return (
    <section className="booking-panel" aria-label="Your booking">
      <h2 className="panel-title">Your booking</h2>
      <p className="panel-subtitle">
        {flights.length} {flights.length === 1 ? 'flight' : 'flights'} on booking{' '}
        <span className="mono">{booking.pnr}</span>
      </p>

      <div className="flight-list">
        {flights.map((flight, index) => (
          <FlightCard key={`${flight.flight_number || 'leg'}-${index}`} flight={flight} />
        ))}
      </div>
    </section>
  )
}
