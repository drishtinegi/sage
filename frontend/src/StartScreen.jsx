import { useEffect, useState } from "react";
import { api } from "./api";

export default function StartScreen({ onStarted, onOpenReport }) {
  const [topics, setTopics] = useState([]);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [showNotes, setShowNotes] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.history().then(setHistory).catch(() => {});
  }, []);

  useEffect(() => {
    api.listTopics().then(setTopics).catch((e) => setError(e.message));
  }, []);

  async function start(chosenTitle, chosenNotes) {
    setLoading(true);
    setError("");
    try {
      const topic = await api.createTopic(chosenTitle, chosenNotes);
      const s = await api.createSession(topic.id);
      onStarted({ ...s, topic_id: topic.id });
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  }

  function submit(e) {
    e.preventDefault();
    start(title.trim(), showNotes ? notes.trim() : "");
  }

  return (
    <section className="card">
      <h2>Pick a topic</h2>

      {topics.length > 0 && (
        <div className="chips">
          {topics.map((t) => (
            <button
              key={t.id}
              className="chip"
              disabled={loading}
              onClick={() => start(t.title, "")}
            >
              {t.title}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={submit}>
        <label className="label">Or type any topic</label>
        <input
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Binary search trees"
          disabled={loading}
        />
        <label className="check">
          <input
            type="checkbox"
            checked={showNotes}
            onChange={(e) => setShowNotes(e.target.checked)}
            disabled={loading}
          />
          I want to paste my own notes
        </label>
        {showNotes && (
          <textarea
            className="input"
            rows={7}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Paste your notes here. The checkpoints will come only from them."
            disabled={loading}
          />
        )}
        <button className="btn" disabled={loading || title.trim().length < 2}>
          {loading ? "Preparing your session..." : "Start"}
        </button>
      </form>

      {loading && (
        <p className="hint">New topics can take up to 30 seconds. Saved topics start at once.</p>
      )}
      {error && <p className="error">{error}</p>}

      {history.length > 0 && (
        <>
          <h3>Your past attempts</h3>
          <ul className="history">
            {history.map((h) => (
              <li key={h.session_id}>
                <button className="link" onClick={() => onOpenReport(h).catch((e) => setError(e.message))}>
                  {h.topic_title}, attempt {h.attempt}
                </button>
                <span className="hint">
                  {" "}{Math.round(h.score)}%
                  {h.ended_at ? ` · ${new Date(h.ended_at + "Z").toLocaleDateString()}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}