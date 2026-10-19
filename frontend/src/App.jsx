import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL;

export default function App() {
  const [apiStatus, setApiStatus] = useState("checking...");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [showNotes, setShowNotes] = useState(false);
  const [loading, setLoading] = useState(false);
  const [topic, setTopic] = useState(null);
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(null);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => setApiStatus(`API ${d.status}, DB ${d.db}`))
      .catch(() => setApiStatus("API unreachable"));
  }, []);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setTopic(null);
    const start = Date.now();
    try {
      const res = await fetch(`${API}/topics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, notes: showNotes ? notes : null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = Array.isArray(body.detail)
          ? "Please check your input."
          : body.detail || "Something went wrong.";
        throw new Error(detail);
      }
      setTopic(await res.json());
      setSeconds(((Date.now() - start) / 1000).toFixed(1));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: "40px auto", padding: "0 16px", fontFamily: "system-ui, sans-serif" }}>
      <h1>Explain-Back</h1>
      <p style={{ color: "#666" }}>{apiStatus}</p>
      <p>Pick a topic, then explain it to a curious beginner.</p>

      <form onSubmit={submit}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Recursion, Pointers in C, Process scheduling"
          style={{ width: "100%", padding: 10, fontSize: 16, boxSizing: "border-box" }}
          disabled={loading}
        />
        <label style={{ display: "block", margin: "12px 0" }}>
          <input
            type="checkbox"
            checked={showNotes}
            onChange={(e) => setShowNotes(e.target.checked)}
            disabled={loading}
          />{" "}
          I want to paste my own notes
        </label>
        {showNotes && (
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Paste your notes here"
            rows={8}
            style={{ width: "100%", padding: 10, fontSize: 14, boxSizing: "border-box" }}
            disabled={loading}
          />
        )}
        <button
          type="submit"
          disabled={loading || title.trim().length < 2}
          style={{ marginTop: 12, padding: "10px 20px", fontSize: 16 }}
        >
          {loading ? "Preparing your session..." : "Start"}
        </button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {topic && (
        <section style={{ marginTop: 24, padding: 16, border: "1px solid #ccc", borderRadius: 8 }}>
          <h2 style={{ marginTop: 0 }}>Session ready: {topic.title}</h2>
          <p>
            {topic.rubric_count} hidden checkpoints prepared in {seconds}s. You will see
            them in your report after you finish.
          </p>
          <button disabled title="Coming in Week 2">Begin explaining (Week 2)</button>
        </section>
      )}
    </main>
  );
}