const statusDot = {
  pending:   "bg-slate-500",
  running:   "bg-yellow-400 animate-pulse",
  completed: "bg-green-400",
  failed:    "bg-red-400",
}

export default function TeamReportCard({ title, icon, status, children }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <h3 className="font-semibold text-white">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${statusDot[status] || statusDot.pending}`} />
          <span className="text-xs text-slate-500 capitalize">{status || "pending"}</span>
        </div>
      </div>
      {children}
    </div>
  )
}
