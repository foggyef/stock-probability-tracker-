const styles = {
  "A+": "bg-emerald-900/60 text-emerald-300 border-emerald-600",
  "A":  "bg-emerald-900/60 text-emerald-300 border-emerald-600",
  "A-": "bg-emerald-900/40 text-emerald-400 border-emerald-700",
  "B+": "bg-green-900/40 text-green-400 border-green-700",
  "B":  "bg-green-900/40 text-green-400 border-green-700",
  "B-": "bg-green-900/30 text-green-500 border-green-800",
  "C+": "bg-yellow-900/40 text-yellow-400 border-yellow-700",
  "C":  "bg-yellow-900/40 text-yellow-400 border-yellow-700",
  "C-": "bg-yellow-900/30 text-yellow-500 border-yellow-800",
  "D":  "bg-orange-900/40 text-orange-400 border-orange-700",
  "F":  "bg-red-900/60 text-red-300 border-red-600",
}

export default function GradeBadge({ grade }) {
  if (!grade) return <span className="text-slate-500 text-sm">Pending</span>
  return (
    <span className={`text-3xl font-black px-4 py-2 rounded-xl border-2 ${styles[grade] || "bg-slate-800 text-slate-300 border-slate-600"}`}>
      {grade}
    </span>
  )
}
