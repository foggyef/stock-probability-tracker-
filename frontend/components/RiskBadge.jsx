const styles = {
  low:    "bg-green-900/50 text-green-400 border border-green-700",
  medium: "bg-yellow-900/50 text-yellow-400 border border-yellow-700",
  high:   "bg-red-900/50 text-red-400 border border-red-700",
}

const labels = {
  low:    "Low Risk",
  medium: "Medium Risk",
  high:   "High Risk",
}

export default function RiskBadge({ level }) {
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded-full ${styles[level] || styles.medium}`}>
      {labels[level] || level}
    </span>
  )
}
