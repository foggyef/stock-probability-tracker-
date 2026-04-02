import { useState } from "react"
import useSWR from "swr"
import Link from "next/link"
import PickCard from "../components/PickCard"
import MacroBanner from "../components/MacroBanner"

const fetcher = (url) => fetch(url).then((r) => {
  if (!r.ok) throw new Error("not ready")
  return r.json()
})

const FILTERS = [
  { id: "all",        label: "All Picks" },
  { id: "BUY",        label: "Buy Only" },
  { id: "SELL",       label: "Sell Only" },
  { id: "low",        label: "Low Risk" },
  { id: "medium",     label: "Medium Risk" },
  { id: "high",       label: "High Risk" },
  { id: "day_trade",  label: "⚡ Day Trade" },
  { id: "swing",      label: "📅 Swing" },
  { id: "short_term", label: "📆 Short Term" },
  { id: "long_term",  label: "📈 Long Term" },
]

export default function Home() {
  const [activeFilter, setActiveFilter] = useState("all")

  const { data, error, isLoading, mutate } = useSWR("/api/briefing/today", fetcher, {
    refreshInterval: 60_000,
    shouldRetryOnError: false,
  })

  const { data: scanStatus } = useSWR("/api/scan/status", fetcher, {
    refreshInterval: 3_000,
  })

  const { data: strategy } = useSWR("/api/strategy", fetcher, {
    refreshInterval: 60_000,
  })

  const picks = data?.picks ?? []

  const filtered = picks.filter((p) => {
    if (activeFilter === "all")        return true
    if (activeFilter === "BUY")        return p.signal === "BUY"
    if (activeFilter === "SELL")       return p.signal === "SELL"
    if (activeFilter === "low")        return p.risk_level === "low"
    if (activeFilter === "medium")     return p.risk_level === "medium"
    if (activeFilter === "high")       return p.risk_level === "high"
    if (activeFilter === "day_trade")  return p.hold_type === "day_trade"
    if (activeFilter === "swing")      return p.hold_type === "swing"
    if (activeFilter === "short_term") return p.hold_type === "short_term"
    if (activeFilter === "long_term")  return p.hold_type === "long_term"
    return true
  })

  const triggerScan = async () => {
    await fetch("/api/briefing/run", { method: "POST" })
    setTimeout(() => mutate(), 8000)
  }

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  })

  return (
    <div className="min-h-screen bg-bg text-slate-100">

      {/* Header */}
      <header className="border-b border-border px-6 py-5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white">Morning Briefing</h1>
            <p className="text-slate-400 text-sm mt-0.5">{today}</p>
          </div>
          <div className="flex gap-2">
            <Link href="/portfolio" className="text-sm bg-slate-800 hover:bg-slate-700 border border-border text-slate-300 hover:text-white px-4 py-2 rounded-lg transition-colors font-medium">
              💼 Portfolio
            </Link>
            <Link href="/reports" className="text-sm bg-slate-800 hover:bg-slate-700 border border-border text-slate-300 hover:text-white px-4 py-2 rounded-lg transition-colors font-medium">
              📋 CEO Report
            </Link>
          </div>
          {data && (
            <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
              <span className="text-green-400 font-medium">{data.summary?.buy_count ?? 0} BUY</span>
              <span className="text-red-400 font-medium">{data.summary?.sell_count ?? 0} SELL</span>
              <span className="text-slate-600">|</span>
              <span>{data.liquid_scanned?.toLocaleString()} stocks scanned</span>
              <span className="text-slate-600">|</span>
              <span>{new Date(data.generated_at).toLocaleTimeString()}</span>
              <button
                onClick={triggerScan}
                className="ml-2 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1.5 rounded-lg transition-colors"
              >
                Refresh Scan
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">

        {/* Active strategy banner */}
        {strategy && (
          <div className={`mb-5 rounded-xl px-5 py-3 flex flex-wrap items-center justify-between gap-3 border ${
            strategy.active_strategy_id === "default"
              ? "bg-slate-800/40 border-slate-700"
              : "bg-blue-900/30 border-blue-600/50"
          }`}>
            <div className="flex items-center gap-3">
              <span className="text-lg">{strategy.active_strategy_id === "default" ? "⚙️" : "🚀"}</span>
              <div>
                <p className="text-sm font-semibold text-white">
                  Active Strategy: <span className={strategy.active_strategy_id === "default" ? "text-slate-400" : "text-blue-300"}>{strategy.active_strategy_name}</span>
                </p>
                <p className="text-xs text-slate-500">
                  {strategy.deployed_at
                    ? `Deployed ${new Date(strategy.deployed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
                    : "Default weights — no proven strategy deployed yet"}
                </p>
              </div>
            </div>
            {strategy.performance?.backtested_win_rate && (
              <div className="flex gap-4 text-center">
                <div>
                  <p className="text-xs text-slate-500">Backtested Win Rate</p>
                  <p className="text-sm font-bold text-green-400">{(strategy.performance.backtested_win_rate * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Sharpe</p>
                  <p className="text-sm font-bold text-blue-400">{strategy.performance.backtested_sharpe?.toFixed(2) ?? "—"}</p>
                </div>
              </div>
            )}
            <Link href="/reports" className="text-xs text-slate-400 hover:text-white transition-colors">
              View CEO Report →
            </Link>
          </div>
        )}

        {/* Live scan progress banner */}
        {scanStatus?.running && (
          <div className="mb-6 bg-blue-900/40 border border-blue-600/50 rounded-xl px-5 py-4 flex items-center gap-4">
            <div className="flex-shrink-0">
              <div className="w-3 h-3 rounded-full bg-blue-400 animate-pulse" />
            </div>
            <div>
              <p className="text-blue-300 font-semibold text-sm">Scan in progress...</p>
              <p className="text-blue-400 text-xs mt-0.5">{scanStatus.step}{scanStatus.progress ? ` — ${scanStatus.progress}` : ""}</p>
            </div>
            <p className="ml-auto text-xs text-blue-500">Refreshes automatically when done</p>
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="text-center py-24 text-slate-400">
            <p className="text-lg">Loading today's briefing...</p>
          </div>
        )}

        {/* Not generated yet */}
        {error && (
          <div className="text-center py-24">
            <p className="text-3xl mb-4">📊</p>
            <p className="text-white text-xl font-semibold mb-2">No briefing yet for today</p>
            <p className="text-slate-400 text-sm mb-2">
              Briefings run automatically at 8:30am ET on weekdays.
            </p>
            <p className="text-slate-500 text-xs mb-8">
              Sources: Yahoo Finance · SEC EDGAR · Finviz · News RSS · VIX/Macro · Analyst Ratings · Earnings · Insider Trades
            </p>
            <button
              onClick={triggerScan}
              className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-3 rounded-lg transition-colors text-lg"
            >
              Generate Now
            </button>
            <p className="text-slate-600 text-xs mt-4">Takes 2–4 minutes to scan all stocks</p>
          </div>
        )}

        {data && (
          <>
            {/* Macro context banner */}
            <MacroBanner macro={data.macro} />

            {/* Data sources used */}
            <div className="flex flex-wrap gap-1.5 mb-6">
              <span className="text-xs text-slate-500 self-center mr-1">Sources:</span>
              {(data.sources || []).map((s, i) => (
                <span key={i} className="text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded border border-slate-700">
                  {s}
                </span>
              ))}
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-2 mb-6">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setActiveFilter(f.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    activeFilter === f.id
                      ? "bg-blue-600 text-white"
                      : "bg-surface border border-border text-slate-400 hover:text-white hover:border-slate-500"
                  }`}
                >
                  {f.label}
                </button>
              ))}
              <span className="ml-auto text-sm text-slate-500 self-center">
                {filtered.length} pick{filtered.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Risk legend */}
            <div className="flex gap-5 text-xs text-slate-500 mb-8 flex-wrap">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                Low Risk
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />
                Medium Risk
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                High Risk
              </span>
              <span className="flex items-center gap-1.5 ml-4">
                <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                Technical
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-purple-500 inline-block" />
                News
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />
                SEC Filings
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-500 inline-block" />
                Analysts
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-orange-500 inline-block" />
                Earnings/Insider
              </span>
            </div>

            {/* Picks grid */}
            {filtered.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filtered.map((pick) => (
                  <PickCard key={pick.ticker} pick={pick} />
                ))}
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500">
                No picks match this filter today.
              </div>
            )}

            <p className="text-center text-xs text-slate-600 mt-12">
              This is not financial advice. Always do your own research before investing.
              Past performance does not guarantee future results.
            </p>
          </>
        )}
      </main>
    </div>
  )
}
