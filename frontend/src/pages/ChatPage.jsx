import { useState } from 'react'
import BookingPanel from '../components/BookingPanel.jsx'
import ChatWindow from '../components/ChatWindow.jsx'
import CustomerHeader from '../components/CustomerHeader.jsx'
import { sendMessage } from '../services/api.js'

export default function ChatPage({ session, onSignOut }) {
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleSend = async (text) => {
    setMessages((current) => [...current, { role: 'customer', content: text }])
    setBusy(true)
    setError('')

    try {
      const reply = await sendMessage(session.pnr, text, session.sessionToken)
      setMessages((current) => [
        ...current,
        {
          role: 'agent',
          content: reply.message,
          actions: reply.actions || [],
          escalation: reply.escalation
        }
      ])
    } catch (err) {
      setError(err.message)
      if (err.status === 401) onSignOut()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="chat-page">
      <CustomerHeader customer={session.customer} pnr={session.pnr} onSignOut={onSignOut} />

      <main className="chat-layout">
        <BookingPanel booking={session.booking} />
        <ChatWindow
          messages={messages}
          onSend={handleSend}
          busy={busy}
          error={error}
          customerName={session.customer.name.split(' ')[0]}
        />
      </main>
    </div>
  )
}
