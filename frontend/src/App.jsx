import { useState } from "react";
import Papa from "papaparse";
import LabInput from "./components/LabInput";
import ResultsDisplay from "./components/ResultsDisplay";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function analyzeLabs(labs) {
    setLoading(true);
    setError("");
    setResults([]);
    setSummary(null);

    try {
      const response = await fetch(`${API_URL}/analyze_labs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ labs }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Analysis failed");

      setResults(data.results);
      setSummary(data.summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleCsv(file) {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: ({ data, errors }) => {
        if (errors.length) {
          setError("Could not parse the CSV file.");
          return;
        }

        const labs = data.map((row) => ({
          test_name: row.Test_Name || row.test_name,
          value: Number(row.Result ?? row.value),
          unit: row.Unit || row.unit,
          date: row.Date || row.date || null,
        }));

        if (labs.some((x) => !x.test_name || !Number.isFinite(x.value) || !x.unit)) {
          setError("CSV must contain Test_Name, Result and Unit columns with valid values.");
          return;
        }
        analyzeLabs(labs);
      },
    });
  }

  return (
    <main className="page">
      <header className="hero">
        <div>
          <span className="eyebrow">GENAI + FULL-STACK</span>
          <h1>Clinical Lab Results Analyzer</h1>
          <p>
            Explainable laboratory-result analysis using deterministic reference-range
            classification, MCP agent routing, and Gemini-generated explanations.
          </p>
        </div>
        <div className="pipeline">
          <span>Classify</span><b>→</b><span>Route</span><b>→</b><span>Explain</span>
        </div>
      </header>

      <section className="card">
        <LabInput onAnalyze={analyzeLabs} onCsv={handleCsv} loading={loading} />
      </section>

      {error && <div className="error">{error}</div>}

      {summary && (
        <section className="summary-grid">
          <div className="summary critical"><strong>{summary.critical}</strong><span>Critical</span></div>
          <div className="summary warning"><strong>{summary.warning}</strong><span>Warning</span></div>
          <div className="summary normal"><strong>{summary.normal}</strong><span>Normal</span></div>
        </section>
      )}

      {results.length > 0 && <ResultsDisplay results={results} />}

      <footer>
        <strong>Important:</strong> This demo provides decision-support explanations only. It does not diagnose conditions or replace professional medical advice.
      </footer>
    </main>
  );
}
