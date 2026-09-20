import { useState } from 'react'

export default function LoginForm({ onSubmit, busy, error }) {
  const [pnr, setPnr] = useState('')
  const [email, setEmail] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
    if (busy) return
    onSubmit(pnr.trim(), email.trim())
  }

  return (
    <form className="login-form" onSubmit={handleSubmit} noValidate>
      <label className="field">
        <span className="field-label">Booking reference</span>
        <input
          className="field-input field-input--code"
          value={pnr}
          onChange={(event) => setPnr(event.target.value.toUpperCase())}
          placeholder="SK4821X"
          autoComplete="off"
          spellCheck="false"
          maxLength={12}
          required
        />
      </label>

      <label className="field">
        <span className="field-label">Email on the booking</span>
        <input
          className="field-input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="name@example.com"
          autoComplete="email"
          required
        />
      </label>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <button className="button button--primary" type="submit" disabled={busy || !pnr || !email}>
        {busy ? 'Checking booking…' : 'Continue'}
      </button>

      <p className="form-note">
        Both details must match the booking. We will not confirm either one on its own.
      </p>
    </form>
  )
}
