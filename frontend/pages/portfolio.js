import { useState, useEffect } from "react"
import Link from "next/link"

function StatusBadge({ position }) {
  const now = new Date()
  const sellBy = new Date(position.sell_by)
  const isOverdue = now > sellBy
  const daysLeft = Math.ceil((sellBy - now) / (1000 * 60 * 60 * 24))

  if (isOverdue) return (
    <span className="text-xs bg-orange-900/40 text-orange-400 border border-orange-700 px-2 py-0.5 rounded-full">
      Overdue — consider selling
    </span>
  )
  if (daysLeft <= 2) return (
    <span className="text-xs bg-yellow-900/40 text-yellow-400 border border-yellow-700 px-2 py-0.5 rounded-full">
      Sell soon — {daysLeft}d left
    </span>
  )
  return (
    <span className="text-xs bg-green-900/40 text-green-400 border border-green-700 px-2 py-0.5 rounded-full">
      Active — {daysLeft}d left
    </span>
  )
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState([])
  const [closed, setClosed] = useState([])

  useEffect(() => {
    setPortfolio(JSON.parse(localStorage.getItem("portfolio") || "[]"))
    setClosed(JSON.parse(localStorage.getItem("portfolio_closed") || "[]"))
  }, [])

  const closePosition = (ticker, outcome) => {
    const pos = portfolio.find(p => p.ticker === ticker)
    if (!pos) return
    const closedEntry = { ...pos, closed_at: new Date().toISOString(), outcome }
    const newClosed = [closedEntry, ...closed]
    const newPortfolio = portfolio.filter(p => p.ticker !== ticker)
    localStorage.setItem("portfolio", JSON.stringify(newPortfolio))
    localStorage.setItem("portfolio_closed", JSON.stringify(newClosed))
    setPortfolio(newPortfolio)
    setClosed(newClosed)
    localStorage.removeItem(`investment_${ticker}`)
  }

  const totalInvested = portfolio.reduce((s, p) => s + p.amount_invested, 0)
  const totalEstProfit = portfolio.reduce((s, p) => s + p.est_profit, 0)
  const totalEstLoss   = portfolio.reduce((s, p) => s + p.est_loss, 0)

  return (
    <div className="min-h-screen bg-bg text-slate-100">

      <header className="border-b border-border px-6 py-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">← Morning Briefing</Link>
            <Link href="/reports" className="text-slate-400 hover:text-white text-sm transition-colors">📋 CEO Report</Link>
            <div>
              <h1 className="text-2xl font-bold text-white">My Portfolio</h1>
              <p className="text-slate-400 text-sm mt-0.5">Active positions & trade history</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">

        {/* Summary stats */}
        {portfolio.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Active Positions</p>
              <p className="text-lg font-bold text-white">{portfolio.length}</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Invested</p>
              <p className="text-lg font-bold text-white">${totalInvested.toLocaleString("en-US", { minimumFractionDigits: 2 })}</p>
            </div>
            <div className="bg-green-900/20 rounded-lg p-3 text-center border border-green-900/40">
              <p className="text-xs text-green-400 mb-1">Est. Total Profit</p>
              <p className="text-lg font-bold text-green-300">+${totalEstProfit.toFixed(2)}</p>
            </div>
            <div className="bg-red-900/20 rounded-lg p-3 text-center border border-red-900/40">
              <p className="text-xs text-red-400 mb-1">Max Total Loss</p>
              <p className="text-lg font-bold text-red-300">-${totalEstLoss.toFixed(2)}</p>
            </div>
          </div>
        )}

        {/* Active positions */}
        <h2 className="text-lg font-semibold text-white mb-4">Active Positions</h2>

        {portfolio.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-slate-700 rounded-xl mb-8">
            <p className="text-3xl mb-3">📭</p>
            <p className="text-white font-semibold mb-1">No active positions</p>
            <p className="text-slate-400 text-sm">Enter an investment amount on a pick card and click <strong>Vested</strong> to track it here.</p>
            <Link href="/" className="inline-block mt-4 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-6 py-2 rounded-lg transition-colors">
              View Today's Picks
            </Link>
          </div>
        ) : (
          <div className="space-y-3 mb-10">
            {portfolio.map(pos => (
              <div key={pos.ticker} className={`bg-surface border rounded-xl p-5 ${pos.signal === "BUY" ? "border-green-800" : "border-red-800"}`}>
                <div className="flex flex-wrap items-start justify-between gap-4">

                  {/* Left — ticker info */}
                  <div className="flex items-start gap-4">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xl font-bold text-white">{pos.ticker}</span>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${pos.signal === "BUY" ? "text-green-400 bg-green-900/30 border-green-700" : "text-red-400 bg-red-900/30 border-red-700"}`}>
                          {pos.signal}
                        </span>
                        <StatusBadge position={pos} />
                      </div>
                      <p className="text-sm text-slate-400 mt-0.5">{pos.company}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Vested {new Date(pos.vested_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                        {pos.hold_info && ` · ${pos.hold_info.label}`}
                      </p>
                    </div>
                  </div>

                  {/* Right — financials */}
                  <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 text-center">
                    <div className="bg-slate-800/50 rounded-lg p-2">
                      <p className="text-xs text-slate-400 mb-1">Invested</p>
                      <p className="text-sm font-semibold text-white">${pos.amount_invested.toLocaleString()}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-2">
                      <p className="text-xs text-slate-400 mb-1">Shares</p>
                      <p className="text-sm font-semibold text-white">{pos.shares}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-2">
                      <p className="text-xs text-slate-400 mb-1">Entry</p>
                      <p className="text-sm font-semibold text-white">${pos.entry_price.toFixed(2)}</p>
                    </div>
                    <div className="bg-green-900/20 border border-green-900/40 rounded-lg p-2">
                      <p className="text-xs text-green-400 mb-1">Target</p>
                      <p className="text-sm font-semibold text-green-300">${pos.target_price.toFixed(2)}</p>
                      <p className="text-xs text-green-500">+${pos.est_profit.toFixed(2)}</p>
                    </div>
                    <div className="bg-red-900/20 border border-red-900/40 rounded-lg p-2">
                      <p className="text-xs text-red-400 mb-1">Stop</p>
                      <p className="text-sm font-semibold text-red-300">${pos.stop_loss.toFixed(2)}</p>
                      <p className="text-xs text-red-500">-${pos.est_loss.toFixed(2)}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-2">
                      <p className="text-xs text-slate-400 mb-1">Sell By</p>
                      <p className="text-sm font-semibold text-white">{pos.sell_by}</p>
                    </div>
                  </div>
                </div>

                {/* Close buttons */}
                <div className="flex gap-2 mt-4 pt-4 border-t border-slate-700">
                  <button
                    onClick={() => closePosition(pos.ticker, "profit")}
                    className="flex-1 bg-green-700 hover:bg-green-600 text-white text-sm font-semibold py-1.5 rounded-lg transition-colors"
                  >
                    Sold for Profit
                  </button>
                  <button
                    onClick={() => closePosition(pos.ticker, "loss")}
                    className="flex-1 bg-red-800 hover:bg-red-700 text-white text-sm font-semibold py-1.5 rounded-lg transition-colors"
                  >
                    Sold at Loss
                  </button>
                  <button
                    onClick={() => closePosition(pos.ticker, "breakeven")}
                    className="flex-1 bg-slate-700 hover:bg-slate-600 text-white text-sm font-semibold py-1.5 rounded-lg transition-colors"
                  >
                    Broke Even
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Closed positions */}
        {closed.length > 0 && (
          <>
            <h2 className="text-lg font-semibold text-white mb-4">Trade History</h2>
            <div className="space-y-2">
              {closed.map((pos, i) => (
                <div key={i} className="bg-slate-800/30 border border-slate-700 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{pos.ticker}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        pos.outcome === "profit" ? "bg-green-900/40 text-green-400 border border-green-700" :
                        pos.outcome === "loss"   ? "bg-red-900/40 text-red-400 border border-red-700" :
                        "bg-slate-700 text-slate-300 border border-slate-600"
                      }`}>
                        {pos.outcome === "profit" ? "Profit" : pos.outcome === "loss" ? "Loss" : "Breakeven"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{pos.company} · Closed {new Date(pos.closed_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex gap-4 text-sm text-center">
                    <div>
                      <p className="text-xs text-slate-500">Invested</p>
                      <p className="font-semibold text-white">${pos.amount_invested.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Est. P/L</p>
                      <p className={`font-semibold ${pos.outcome === "profit" ? "text-green-400" : pos.outcome === "loss" ? "text-red-400" : "text-slate-300"}`}>
                        {pos.outcome === "profit" ? `+$${pos.est_profit.toFixed(2)}` : pos.outcome === "loss" ? `-$${pos.est_loss.toFixed(2)}` : "$0"}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
