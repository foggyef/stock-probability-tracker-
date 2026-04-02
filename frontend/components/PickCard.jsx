import { useState, useEffect } from "react"
import RiskBadge from "./RiskBadge"
import HoldBadge from "./HoldBadge"

function getSellByDate(holdInfo) {
  const today = new Date()
  const ranges = {
    day_trade:  1,
    swing:      7,
    short_term: 21,
    long_term:  90,
  }
  const key = holdInfo?.type || "short_term"
  const days = ranges[key] || 21
  const sell = new Date(today)
  sell.setDate(sell.getDate() + days)
  return sell.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

function ScoreBar({ label, value, color }) {
  // value is -1 to +1, normalize to 0-100% for display
  const pct = Math.round(((value + 1) / 2) * 100)
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{label}</span>
        <span className={`font-medium ${value > 0.1 ? "text-green-400" : value < -0.1 ? "text-red-400" : "text-slate-300"}`}>
          {value > 0.15 ? "+" : ""}{(value * 100).toFixed(0)}
        </span>
      </div>
      <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function PickCard({ pick }) {
  const isBuy = pick.signal === "BUY"
  const storageKey = `investment_${pick.ticker}`

  const [investment, setInvestment] = useState("")

  useEffect(() => {
    const saved = localStorage.getItem(storageKey)
    if (saved) setInvestment(saved)
  }, [storageKey])

  const handleInvestmentChange = (e) => {
    const val = e.target.value
    setInvestment(val)
    if (val) localStorage.setItem(storageKey, val)
    else localStorage.removeItem(storageKey)
  }

  const amount = parseFloat(investment) || 0
  const shares = amount > 0 && pick.entry_price > 0 ? amount / pick.entry_price : 0
  const estProfit = shares * (pick.target_price - pick.entry_price)
  const estLoss   = shares * (pick.entry_price - pick.stop_loss)
  const sellBy    = getSellByDate(pick.hold_info)

  const signalStyle = isBuy
    ? "text-green-400 bg-green-900/30 border-green-700"
    : "text-red-400 bg-red-900/30 border-red-700"

  const borderStyle = isBuy ? "border-green-800" : "border-red-800"
  const confidencePct = Math.round(pick.confidence * 100)
  const profitPct     = Math.round(pick.probability_of_profit * 100)

  return (
    <div className={`bg-surface rounded-xl border ${borderStyle} p-5 flex flex-col gap-4 hover:border-opacity-80 transition-all`}>

      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-2xl font-bold text-white">{pick.ticker}</span>
            <span className={`text-sm font-bold px-2 py-0.5 rounded border ${signalStyle}`}>
              {pick.signal}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-0.5 truncate max-w-[200px]">{pick.company}</p>
        </div>
        <RiskBadge level={pick.risk_level} />
      </div>

      {/* Price info */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-slate-800/50 rounded-lg p-2">
          <p className="text-xs text-slate-400 mb-1">Entry</p>
          <p className="text-sm font-semibold text-white">${pick.entry_price.toFixed(2)}</p>
        </div>
        <div className="bg-green-900/20 rounded-lg p-2 border border-green-900/50">
          <p className="text-xs text-green-400 mb-1">Target</p>
          <p className="text-sm font-semibold text-green-300">
            ${pick.target_price.toFixed(2)}
          </p>
          <p className="text-xs text-green-500">+{pick.potential_gain_pct}%</p>
        </div>
        <div className="bg-red-900/20 rounded-lg p-2 border border-red-900/50">
          <p className="text-xs text-red-400 mb-1">Stop Loss</p>
          <p className="text-sm font-semibold text-red-300">
            ${pick.stop_loss.toFixed(2)}
          </p>
          <p className="text-xs text-red-500">-{pick.stop_loss_pct}%</p>
        </div>
      </div>

      {/* Overall confidence */}
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span className="font-medium text-slate-300">Overall Confidence</span>
          <span className="font-bold text-white text-sm">{confidencePct}%</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${confidencePct}%` }} />
        </div>
      </div>

      {/* Source score breakdown */}
      <div className="space-y-1.5 border-t border-slate-700 pt-3">
        <p className="text-xs text-slate-500 font-medium mb-2">Signal Sources</p>
        <ScoreBar label="Technical Analysis" value={pick.technical_score ?? 0}  color="bg-blue-500" />
        <ScoreBar label="News Sentiment"     value={pick.news_sentiment ?? 0}   color="bg-purple-500" />
        <ScoreBar label="SEC Filings"        value={pick.sec_sentiment ?? 0}    color="bg-yellow-500" />
        <ScoreBar label="Analyst Consensus"  value={pick.analyst_score ?? 0}    color="bg-cyan-500" />
        <ScoreBar label="Earnings/Insider"   value={pick.fundamental_score ?? 0} color="bg-orange-500" />
      </div>

      {/* Probability of profit */}
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Probability of Profit</span>
          <span className="font-medium text-white">{profitPct}%</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${isBuy ? "bg-green-500" : "bg-red-500"}`}
            style={{ width: `${profitPct}%` }}
          />
        </div>
      </div>

      {/* Hold time */}
      <HoldBadge holdInfo={pick.hold_info} />

      {/* Sources used */}
      {pick.sources_used?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {pick.sources_used.map((s, i) => (
            <span key={i} className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Investment calculator */}
      <div className="border-t border-slate-700 pt-3 space-y-2">
        <p className="text-xs text-slate-500 font-medium">My Investment</p>
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-sm">$</span>
          <input
            type="number"
            min="0"
            placeholder="Amount invested"
            value={investment}
            onChange={handleInvestmentChange}
            className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        {amount > 0 && (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="bg-green-900/20 border border-green-900/40 rounded-lg p-2 text-center">
              <p className="text-xs text-green-400 mb-0.5">Est. Profit</p>
              <p className="text-sm font-bold text-green-300">+${estProfit.toFixed(2)}</p>
              <p className="text-xs text-green-500">{shares.toFixed(2)} shares</p>
            </div>
            <div className="bg-red-900/20 border border-red-900/40 rounded-lg p-2 text-center">
              <p className="text-xs text-red-400 mb-0.5">Max Loss</p>
              <p className="text-sm font-bold text-red-300">-${estLoss.toFixed(2)}</p>
              <p className="text-xs text-red-500">if stop hit</p>
            </div>
            <div className="col-span-2 bg-slate-800/50 border border-slate-700 rounded-lg p-2 text-center">
              <p className="text-xs text-slate-400 mb-0.5">Sell By</p>
              <p className="text-sm font-semibold text-white">{sellBy}</p>
            </div>
            <button
              onClick={() => {
                const portfolio = JSON.parse(localStorage.getItem("portfolio") || "[]")
                const existing = portfolio.findIndex(p => p.ticker === pick.ticker)
                const entry = {
                  ticker: pick.ticker,
                  company: pick.company,
                  signal: pick.signal,
                  entry_price: pick.entry_price,
                  target_price: pick.target_price,
                  stop_loss: pick.stop_loss,
                  potential_gain_pct: pick.potential_gain_pct,
                  stop_loss_pct: pick.stop_loss_pct,
                  risk_level: pick.risk_level,
                  hold_info: pick.hold_info,
                  amount_invested: amount,
                  shares: parseFloat(shares.toFixed(4)),
                  est_profit: parseFloat(estProfit.toFixed(2)),
                  est_loss: parseFloat(estLoss.toFixed(2)),
                  sell_by: sellBy,
                  vested_at: new Date().toISOString(),
                }
                if (existing >= 0) portfolio[existing] = entry
                else portfolio.push(entry)
                localStorage.setItem("portfolio", JSON.stringify(portfolio))
                alert(`${pick.ticker} added to your portfolio!`)
              }}
              className="col-span-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold py-2 rounded-lg transition-colors"
            >
              Vested — Add to Portfolio
            </button>
          </div>
        )}
      </div>

      {/* Rationale */}
      <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-700 pt-3">
        {pick.rationale}
      </p>
    </div>
  )
}
