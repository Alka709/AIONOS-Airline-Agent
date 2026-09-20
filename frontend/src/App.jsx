import { useState } from 'react'
import VerificationPage from './pages/VerificationPage.jsx'
import ChatPage from './pages/ChatPage.jsx'

/**
 * The verified session lives only in memory. Reloading the page returns the
 * traveller to verification, so the chat is never reachable without a matching
 * booking reference and email.
 */
export default function App() {
  const [session, setSession] = useState(null)

  if (!session) {
    return <VerificationPage onVerified={setSession} />
  }

  return <ChatPage session={session} onSignOut={() => setSession(null)} />
}
