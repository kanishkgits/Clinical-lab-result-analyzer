export default function SeverityBadge({ severity }) {
  const icon = severity === "Critical" ? "🚨" : severity === "Warning" ? "⚠️" : "✓";
  return <span className={`badge ${severity.toLowerCase()}`}>{icon} {severity}</span>;
}
