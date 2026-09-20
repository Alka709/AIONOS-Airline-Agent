import { useState } from 'react'
import LoginForm from '../components/LoginForm.jsx'
import { verifyBooking } from '../services/api.js'

export default function VerificationPage({ onVerified }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (pnr, email) => {
    setBusy(true)
    setError('')
    try {
      const result = await verifyBooking(pnr, email)
      onVerified({
        pnr: result.booking.pnr,
        sessionToken: result.session_token,
        customer: result.customer,
        booking: result.booking
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="verify-page">
      <div className="boarding-stub">
        <div className="stub-main">
          <p className="stub-eyebrow">Disruption support</p>
          <h1 className="stub-title">Airline Resolution Support</h1>
          <p className="stub-lede">
            Find your booking to talk to support about a cancelled or delayed flight.
          </p>
          <LoginForm onSubmit={handleSubmit} busy={busy} error={error} />
        </div>

        <div className="stub-tear" aria-hidden="true" />

        <aside className="stub-side">
          <div className="stub-side-inner">
            <div className="airline-brand-badge">
              <svg className="airline-plane-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.3c.4-.2.6-.6.5-1.1z"/>
              </svg>
              <span>AIONOS AIRLINES</span>
            </div>

            <div className="stub-side-header">
              <h2 className="stub-side-title">Welcome to AIONOS AIRLINES</h2>
              <p className="stub-side-desc">
                Dedicated passenger assistance and live disruption resolution desk.
              </p>
            </div>

            <div className="stub-feature-list">
              <div className="stub-feature-item">
                <span className="feature-icon">⚡</span>
                <div className="feature-info">
                  <strong>Instant Entitlements</strong>
                  <p>Automatic meal vouchers & transport allowances.</p>
                </div>
              </div>

              <div className="stub-feature-item">
                <span className="feature-icon">🔄</span>
                <div className="feature-info">
                  <strong>Smart Rebooking</strong>
                  <p>Priority alternative flight options matching your route.</p>
                </div>
              </div>

              <div className="stub-feature-item">
                <span className="feature-icon">🛡️</span>
                <div className="feature-info">
                  <strong>Policy Compliance</strong>
                  <p>Full adherence to airline & DGCA passenger rights.</p>
                </div>
              </div>
            </div>

            <div className="stub-side-footer">
              <div className="stub-ticket-class">
                <span className="label">SUPPORT DESK</span>
                <span className="val">LIVE ASSISTANCE</span>
              </div>
              <div className="stub-barcode" aria-hidden="true">
                <span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span />
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  )
}
