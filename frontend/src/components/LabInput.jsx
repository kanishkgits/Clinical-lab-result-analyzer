import { useState } from "react";

const defaultRows = [
  { test_name: "Ferritin", value: "28.9", unit: "ug/L" },
  { test_name: "Glycated Hemoglobin (HbA1c)", value: "5.0", unit: "%" },
  { test_name: "Total IgE", value: "1.73", unit: "KU/L" },
  { test_name: "Insulin", value: "9.42", unit: "mU/L" },
  { test_name: "Free T4", value: "1.14", unit: "ng/dL" },
];

export default function LabInput({ onAnalyze, onCsv, loading }) {
  const [rows, setRows] = useState(defaultRows);

  function update(index, field, value) {
    setRows((current) => current.map((row, i) => i === index ? { ...row, [field]: value } : row));
  }

  function addRow() {
    setRows((current) => [...current, { test_name: "", value: "", unit: "" }]);
  }

  function removeRow(index) {
    setRows((current) => current.filter((_, i) => i !== index));
  }

  function submit(e) {
    e.preventDefault();
    const labs = rows.map((row) => ({
      test_name: row.test_name.trim(),
      value: Number(row.value),
      unit: row.unit.trim(),
    }));
    onAnalyze(labs);
  }

  return (
    <form onSubmit={submit}>
      <div className="input-header">
        <div>
          <h2>Enter laboratory results</h2>
          <p>Provide test name, numerical value and unit, or upload a CSV.</p>
        </div>
        <label className="upload">
          Upload CSV
          <input type="file" accept=".csv,text/csv" onChange={(e) => e.target.files[0] && onCsv(e.target.files[0])} />
        </label>
      </div>

      <div className="table-wrap">
        <table>
          <thead><tr><th>Test name</th><th>Result</th><th>Unit</th><th></th></tr></thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td><input value={row.test_name} onChange={(e) => update(index, "test_name", e.target.value)} placeholder="e.g. Ferritin" /></td>
                <td><input type="number" step="any" value={row.value} onChange={(e) => update(index, "value", e.target.value)} /></td>
                <td><input value={row.unit} onChange={(e) => update(index, "unit", e.target.value)} placeholder="e.g. ug/L" /></td>
                <td><button type="button" className="icon-button" onClick={() => removeRow(index)}>×</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="actions">
        <button type="button" className="secondary" onClick={addRow}>+ Add test</button>
        <button type="submit" className="primary" disabled={loading}>{loading ? "Analyzing…" : "Analyze results"}</button>
      </div>
    </form>
  );
}
