import { useEffect, useState } from "react";
import { api } from "./api";

const LABEL = {
  covered: "Covered",
  partial: "Partly covered",
  missing: "Missing",
  wrong: "Wrong",
};

const ENDED = {
  "student tapped finish": "You tapped Finish",
  "all items covered": "Everything was covered",
  "turn cap": "The turn limit was reached",
};

function RevisionPlan({ sessionId }) {
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    setError("");
    api.getPlan(sessionId)
      .then(setPlan)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [sessionId]);

  if (loading) return <p className="hint">Preparing your revision plan...</p>;
  if (error)
    return (
      <p className="error">
        {error} <button className="link" onClick={load}>Try again</button>
      </p>
    );

  return (
    <div className="plan">
      <p>{plan.summary}</p>

      {plan.misconceptions.length > 0 && (
        <>
          <h3>Ideas to double-check</h3>
          <ul className="miscs">
            {plan.misconceptions.map((m, i) => (
              <li key={i}>
                <strong>{m.belief}</strong>
                <p className="quote">You said: "{m.evidence}"</p>
              </li>
            ))}
          </ul>
        </>
      )}

      {plan.steps.length > 0 && (
        <>
          <h3>Your revision plan</h3>
          <ol className="steps">
            {plan.steps.map((s) => (
              <li key={s.position} className={`step ${s.status}`}>
                <div className="item-head">
                  <span className={`tag ${s.status}`}>{LABEL[s.status]}</span>
                  <span className="hint">{s.kind}</span>
                </div>
                <p className="item-text">{s.text}</p>
                <p className="note">{s.why}</p>
                <p className="practice"><strong>Try this:</strong> {s.practice_prompt}</p>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}

export default function ReportScreen({ report, onRetry, onNewTopic }) {
  const counts = report.items.reduce((acc, i) => {
    acc[i.status] = (acc[i.status] || 0) + 1;
    return acc;
  }, {});
  const gaps = report.items.filter((i) => i.status !== "covered");
  const covered = report.items.filter((i) => i.status === "covered");

  return (
    <section className="card">
      <h2>Your report: {report.topic_title}</h2>
      <p className="score">{Math.round(report.score)}%</p>
      {report.attempt > 1 && report.previous_score != null && (() => {
        const d = Math.round(report.score) - Math.round(report.previous_score);
        return (
          <p className="compare">
            Attempt {report.attempt}: {d > 0 ? `up ${d} points` : d < 0 ? `down ${-d} points` : "same score"} from{" "}
            {Math.round(report.previous_score)}%
            {report.fixed.length > 0 && `, ${report.fixed.length} gap${report.fixed.length > 1 ? "s" : ""} closed`}
          </p>
        );
      })()}
      <p className="hint">
        {ENDED[report.ended_by] || report.ended_by} &middot;{" "}
        {Object.entries(counts).map(([k, v]) => `${v} ${LABEL[k].toLowerCase()}`).join(", ")}
      </p>

      <RevisionPlan sessionId={report.session_id} />

      <h3>Item by item</h3>
      <ul className="items">
        {[...gaps, ...covered].map((i) => (
          <li key={i.position} className={`item ${i.status}`}>
            <div className="item-head">
              <span className={`tag ${i.status}`}>{LABEL[i.status]}</span>
              <span className="hint">importance {i.weight} of 3</span>
            </div>
            <p className="item-text">{i.text}</p>
            {i.evidence && <p className="quote">You said: "{i.evidence}"</p>}
            {i.note && <p className="note">{i.note}</p>}
          </li>
        ))}
      </ul>

      <div className="row">
        <button className="btn" onClick={onRetry}>Retry this topic</button>
        <button className="btn secondary" onClick={onNewTopic}>Choose another topic</button>
      </div>
      
    </section>
  );
}