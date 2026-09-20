const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    })
  } catch (networkError) {
    throw new Error('We could not reach support right now. Check your connection and try again.')
  }

  let body = null
  try {
    body = await response.json()
  } catch (parseError) {
    body = null
  }

  if (!response.ok) {
    const detail = body && body.detail ? body.detail : 'Something went wrong. Please try again.'
    const error = new Error(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.')
    error.status = response.status
    throw error
  }

  return body
}

export function verifyBooking(pnr, email) {
  return request('/api/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ pnr, email })
  })
}

export function sendMessage(pnr, message, sessionToken) {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ pnr, message, session_token: sessionToken })
  })
}

export function fetchBooking(pnr, sessionToken) {
  return request(`/api/bookings/${encodeURIComponent(pnr)}?session_token=${encodeURIComponent(sessionToken)}`)
}

export function checkHealth() {
  return request('/health')
}
