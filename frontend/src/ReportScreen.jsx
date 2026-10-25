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
  
  export default function ReportScreen({ report, onRetry, onNewTopic }) {
    const counts = report.items.reduce((acc, i) => {
      acc[i.status] = (acc[i.status] || 0) + 1;
      return acc;
    }, {});
    const gaps = report.items.filter((i) => i.status !== "covered");
  
    return (
      <section className="card">
        <h2>Your report: {report.topic_title}</h2>
        <p className="score">{Math.round(report.score)}%</p>
        <p className="hint">
          {ENDED[report.ended_by] || report.ended_by} &middot;{" "}
          {Object.entries(counts).map(([k, v]) => `${v} ${LABEL[k].toLowerCase()}`).join(", ")}
        </p>
  
        {gaps.length > 0 && <h3>Gaps to work on ({gaps.length})</h3>}
        {gaps.length === 0 && <h3>No gaps. Nice explanation.</h3>}
  
        <ul className="items">
          {[...gaps, ...report.items.filter((i) => i.status === "covered")].map((i) => (
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
        <p className="hint">The revision plan and score comparison arrive in Week 3.</p>
      </section>
    );
  }