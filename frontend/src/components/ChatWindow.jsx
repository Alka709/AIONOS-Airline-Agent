import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble.jsx'

export default function ChatWindow({ messages, onSend, busy, error, customerName }) {
  const [draft, setDraft] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  const submit = (event) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text || busy) return
    setDraft('')
    onSend(text)
  }

  return (
    <section className="chat" aria-label="Chat with resolution support">
      <div className="chat-head">
        <h2 className="panel-title">Resolution support</h2>
        <p className="panel-subtitle">
          Verified chat for {customerName}. Replies use your booking and our published policy only.
        </p>
      </div>

      <div className="chat-log">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p>Tell us what you need help with.</p>
            <p className="chat-empty-hint">
              Rebooking, refunds, delay support, or a question about any flight on this booking.
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} message={message} />
          ))
        )}

        {busy ? (
          <div className="message-row message-row--agent">
            <div className="bubble bubble--agent bubble--typing" aria-live="polite">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        ) : null}

        <div ref={endRef} />
      </div>

      {error ? (
        <p className="chat-error" role="alert">
          {error}
        </p>
      ) : null}

      <form className="composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="composer-input">
          Your message
        </label>
        <textarea
          id="composer-input"
          className="composer-input"
          rows={2}
          value={draft}
          placeholder="Type your message"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) submit(event)
          }}
        />
        <button className="button button--primary" type="submit" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
