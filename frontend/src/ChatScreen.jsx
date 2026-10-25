import { useEffect, useRef, useState } from "react";
import { api } from "./api";

export default function ChatScreen({ session, onReport }) {
  const [messages, setMessages] = useState([{ role: "beginner", text: session.opening }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [turn, setTurn] = useState(0);
  const [error, setError] = useState("");
  const [failedText, setFailedText] = useState(null);
  const [ended, setEnded] = useState(false);
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text, isResend = false) {
    setError("");
    setFailedText(null);
    setLoading(true);
    if (!isResend) setMessages((m) => [...m, { role: "student", text }]);
    try {
      const d = await api.sendTurn(session.session_id, text);
      setMessages((m) => [...m, { role: "beginner", text: d.beginner }]);
      setTurn(d.turn);
      if (d.ended) setEnded(true);
    } catch (e) {
      setError(e.message);
      if (e.status !== 409) setFailedText(text);
      if (e.status === 409) setEnded(true);
    } finally {
      setLoading(false);
    }
  }

  function submit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading || ended) return;
    setInput("");
    send(text);
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) submit(e);
  }

  async function openReport() {
    setLoading(true);
    setError("");
    try {
      const r = ended ? await api.getReport(session.session_id) : await api.finish(session.session_id);
      onReport(r);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  }

  return (
    <section className="card chat">
      <div className="chat-top">
        <strong>{session.topic_title}</strong>
        <span className="hint">Turn {turn} of {session.turn_cap}</span>
      </div>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <span className="who">{m.role === "student" ? "You" : "Beginner"}</span>
            {m.text}
          </div>
        ))}
        {loading && <div className="bubble beginner typing">Beginner is thinking...</div>}
        <div ref={bottom} />
      </div>

      {error && (
        <p className="error">
          {error}{" "}
          {failedText && (
            <button className="link" onClick={() => send(failedText, true)} disabled={loading}>
              Resend
            </button>
          )}
        </p>
      )}

      {ended ? (
        <button className="btn" onClick={openReport} disabled={loading}>
          See your report
        </button>
      ) : (
        <form onSubmit={submit} className="composer">
          <textarea
            className="input"
            rows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Explain it in your own words. Enter to send, Shift+Enter for a new line."
            disabled={loading}
          />
          <div className="row">
            <button className="btn" disabled={loading || !input.trim()}>Send</button>
            <button
              type="button"
              className="btn secondary"
              onClick={openReport}
              disabled={loading || turn === 0}
              title={turn === 0 ? "Explain the topic first" : ""}
            >
              Finish and see report
            </button>
          </div>
        </form>
      )}
    </section>
  );
}