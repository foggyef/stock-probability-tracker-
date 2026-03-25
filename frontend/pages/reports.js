import { useState } from "react"
import useSWR from "swr"
import Link from "next/link"
import GradeBadge from "../components/GradeBadge"
import TeamReportCard from "../components/TeamReportCard"

const fetcher = (url) => fetch(url).then(r => { if (!r.ok) throw new Error("not ready"); return r.json() })

function Stat({ label, value, sub, color }) {
  return (
    <div className="bg-slate-800/50 rounded-lg p-3 text-center">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-lg font-bold ${color || "text-white"}`}>{value ?? "—"}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  )
}

function Section({ title, items, color }) {
  if (!items || items.length === 0) return null
  return (
    <div>
      <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${color}`}>{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-slate-300 flex gap-2">
            <span className={`mt-0.5 flex-shrink-0 ${color}`}>›</span>
            <span>{typeof item === "string" ? item : item.directive || item.hypothesis || JSON.stringify(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Reports() {
  const [selectedDate, setSelectedDate] = useState(null)

  const { data: dates } = useSWR("/api/reports/dates", fetcher)
  const reportUrl = selectedDate ? `/api/reports/${selectedDate}` : "/api/reports/latest"
  const { data: report, error } = useSWR(reportUrl, fetcher, { refreshInterval: 120_000 })

  const r = report
  const ceo = r?.ceo_response
  const research = r?.team_reports?.research
  const discovery = r?.team_reports?.discovery
  const deployment = r?.team_reports?.deployment
  const stats = r?.stats

  const heatBorder = {
    hot:  "border-red-700",
    warm: "border-yellow-700",
    cold: "border-blue-800",
  }

  return (
    <div className="min-h-screen bg-bg text-slate-100">

      {/* Header */}
      <header className="border-b border-border px-6 py-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">
              ← Morning Briefing
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white">CEO Daily Report</h1>
              <p className="text-slate-400 text-sm mt-0.5">Strategy team performance &amp; CEO directives</p>
            </div>
          </div>
          {r && (
            <p className="text-xs text-slate-500">
              Last updated {new Date(r.generated_at).toLocaleString()}
            </p>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">

        {/* Date picker */}
        {dates?.dates?.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-8">
            <button
              onClick={() => setSelectedDate(null)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                !selectedDate ? "bg-blue-600 text-white" : "bg-surface border border-border text-slate-400 hover:text-white"
              }`}
            >
              Latest
            </button>
            {dates.dates.map(d => (
              <button
                key={d}
                onClick={() => setSelectedDate(d)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  selectedDate === d ? "bg-blue-600 text-white" : "bg-surface border border-border text-slate-400 hover:text-white"
                }`}
              >
                {new Date(d + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              </button>
            ))}
          </div>
        )}

        {/* No report yet */}
        {error && (
          <div className="text-center py-24">
            <p className="text-4xl mb-4">📋</p>
            <p className="text-white text-xl font-semibold mb-2">No report yet</p>
            <p className="text-slate-400 text-sm">The strategy team runs every 2 hours. Check back soon.</p>
          </div>
        )}

        {r && (
          <>
            {/* Stats bar */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
              <Stat label="Active Strategy" value={stats?.active_strategy_name || "Default"} />
              <Stat label="Live Win Rate" value={stats?.active_strategy_win_rate ? `${(stats.active_strategy_win_rate * 100).toFixed(1)}%` : "—"} color="text-green-400" />
              <Stat label="Live Sharpe" value={stats?.active_strategy_sharpe?.toFixed(2) || "—"} color="text-blue-400" />
              <Stat label="Total Experiments" value={stats?.total_experiments_all_time ?? "—"} />
              <Stat label="Proven Strategies" value={stats?.total_proven_strategies ?? "—"} color="text-emerald-400" />
            </div>

            {/* CEO Response — the main event */}
            <div className={`bg-surface border-2 ${heatBorder[ceo?.heat] || "border-border"} rounded-2xl p-6 mb-8`}>
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">🤖</span>
                    <h2 className="text-xl font-bold text-white">CEO Report</h2>
                    {ceo?.heat === "hot" && <span className="text-xs bg-red-900/50 text-red-400 border border-red-700 px-2 py-0.5 rounded-full">🔥 Demanding</span>}
                    {ceo?.heat === "warm" && <span className="text-xs bg-yellow-900/50 text-yellow-400 border border-yellow-700 px-2 py-0.5 rounded-full">⚡ Pushing</span>}
                    {ceo?.heat === "cold" && <span className="text-xs bg-blue-900/50 text-blue-400 border border-blue-700 px-2 py-0.5 rounded-full">✓ Satisfied</span>}
                  </div>
                  {ceo?.headline && (
                    <p className="text-lg font-semibold text-slate-200 italic">"{ceo.headline}"</p>
                  )}
                </div>
                <GradeBadge grade={ceo?.grade} />
              </div>

              {ceo?.summary && (
                <p className="text-slate-300 leading-relaxed mb-5 border-l-2 border-slate-600 pl-4">
                  {ceo.summary}
                </p>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <Section title="Commendations" items={ceo?.commendations} color="text-green-400" />
                <Section title="Criticisms" items={ceo?.criticisms} color="text-red-400" />
              </div>

              {ceo?.directives_issued?.length > 0 && (
                <div className="mt-5 pt-5 border-t border-slate-700">
                  <p className="text-xs font-semibold uppercase tracking-wider text-yellow-400 mb-3">Directives Issued</p>
                  <div className="space-y-3">
                    {ceo.directives_issued.map((d, i) => (
                      <div key={i} className="bg-yellow-900/10 border border-yellow-900/40 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <span className="text-xs font-bold text-yellow-500 bg-yellow-900/30 px-1.5 py-0.5 rounded mt-0.5 flex-shrink-0">P{d.priority || i + 1}</span>
                          <div>
                            <p className="text-sm text-yellow-200 font-medium">{d.directive}</p>
                            {d.why && <p className="text-xs text-slate-400 mt-1">Why: {d.why}</p>}
                            {d.success_metric && <p className="text-xs text-slate-500 mt-0.5">Success: {d.success_metric}</p>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {ceo?.outlook && (
                <div className="mt-5 pt-4 border-t border-slate-700">
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Outlook</p>
                  <p className="text-sm text-slate-300">{ceo.outlook}</p>
                </div>
              )}
            </div>

            {/* Team Reports */}
            <h2 className="text-lg font-semibold text-white mb-4">Team Reports</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">

              {/* Research */}
              <TeamReportCard title="Research Agent" icon="🔬" status={research?.status}>
                {research?.summary && (
                  <p className="text-sm text-slate-400 mb-3">{research.summary}</p>
                )}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Hypotheses generated</span>
                    <span className="text-white font-medium">{research?.hypotheses_generated ?? 0}</span>
                  </div>
                  {research?.hypotheses?.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {research.hypotheses.map((h, i) => (
                        <div key={i} className="bg-slate-800/50 rounded p-2">
                          <p className="text-xs text-slate-300">{typeof h === "string" ? h : h.hypothesis}</p>
                          {h.rationale && <p className="text-xs text-slate-500 mt-1">{h.rationale}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                  {research?.new_sources?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-slate-500 mb-1">New sources identified</p>
                      {research.new_sources.map((s, i) => (
                        <span key={i} className="text-xs bg-blue-900/30 text-blue-400 border border-blue-800 px-2 py-0.5 rounded mr-1">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              </TeamReportCard>

              {/* Discovery */}
              <TeamReportCard title="Discovery Agent" icon="🧪" status={discovery?.status}>
                {discovery?.summary && (
                  <p className="text-sm text-slate-400 mb-3">{discovery.summary}</p>
                )}
                {discovery?.hypothesis_tested ? (
                  <div className="space-y-2">
                    <div className="bg-slate-800/50 rounded p-2 mb-2">
                      <p className="text-xs text-slate-400 mb-1">Hypothesis tested</p>
                      <p className="text-xs text-white">{discovery.hypothesis_tested}</p>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Result</span>
                      <span className={`font-bold ${discovery.result === "PASSED" ? "text-green-400" : "text-red-400"}`}>
                        {discovery.result || "—"}
                      </span>
                    </div>
                    {discovery.gate_failed && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-500">Failed at</span>
                        <span className="text-orange-400">{discovery.gate_failed}</span>
                      </div>
                    )}
                    {discovery.gate_passed_count > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-500">Gates passed</span>
                        <span className="text-slate-300">{discovery.gate_passed_count} / 5</span>
                      </div>
                    )}
                    {discovery.metrics?.win_rate && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-500">OOS Win Rate</span>
                        <span className="text-white">{(discovery.metrics.win_rate * 100).toFixed(1)}%</span>
                      </div>
                    )}
                    {discovery.metrics?.sharpe && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-500">Sharpe</span>
                        <span className="text-white">{discovery.metrics.sharpe?.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No experiment run yet today</p>
                )}
              </TeamReportCard>

              {/* Deployment */}
              <TeamReportCard title="Deployment Agent" icon="🚀" status={deployment?.status}>
                {deployment?.summary && (
                  <p className="text-sm text-slate-400 mb-3">{deployment.summary}</p>
                )}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Action</span>
                    <span className={`font-medium ${deployment?.action === "deployed" ? "text-green-400" : "text-slate-400"}`}>
                      {deployment?.action || "No action"}
                    </span>
                  </div>
                  {deployment?.strategy_name && (
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Strategy</span>
                      <span className="text-white text-xs">{deployment.strategy_name}</span>
                    </div>
                  )}
                  {deployment?.win_rate && (
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Win Rate</span>
                      <span className="text-green-400">{(deployment.win_rate * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {deployment?.reason && (
                    <div className="bg-slate-800/50 rounded p-2 mt-2">
                      <p className="text-xs text-slate-400">{deployment.reason}</p>
                    </div>
                  )}
                </div>
              </TeamReportCard>

            </div>

            <p className="text-center text-xs text-slate-600 mt-8">
              Strategy team runs every 2 hours · Reports update automatically
            </p>
          </>
        )}
      </main>
    </div>
  )
}
