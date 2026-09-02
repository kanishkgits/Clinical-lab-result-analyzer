import SeverityBadge from "./SeverityBadge";

export default function ResultsDisplay({ results }) {
  return (
    <section className="results">
      <div className="results-title">
        <div><h2>Analysis results</h2><p>Critical results are routed first, followed by warnings and normal results.</p></div>
      </div>

      {results.map((item, index) => (
        <article className={`result-card ${item.severity.toLowerCase()}`} key={`${item.test_name}-${index}`}>
          <div className="result-top">
            <div>
              <h3>{item.test_name}</h3>
              <div className="value"><strong>{item.value}</strong> {item.unit}</div>
            </div>
            <SeverityBadge severity={item.severity} />
          </div>

          <div className="range">
            <span>Reference range</span>
            <strong>{item.reference_range} {item.unit}</strong>
          </div>

          <div className="explain">
            <h4>Why was this flagged?</h4>
            <p>{item.reason}</p>
            <h4>AI explanation</h4>
            <p>{item.explanation}</p>
            <h4>Suggested next step</h4>
            <p>{item.recommended_followup}</p>
          </div>

          <small>{item.disclaimer}</small>
        </article>
      ))}
    </section>
  );
}
