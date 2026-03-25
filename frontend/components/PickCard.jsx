import RiskBadge from "./RiskBadge"
import HoldBadge from "./HoldBadge"

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

      {/* Rationale */}
      <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-700 pt-3">
        {pick.rationale}
      </p>
    </div>
  )
}
