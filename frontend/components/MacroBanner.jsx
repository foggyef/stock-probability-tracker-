export default function MacroBanner({ macro }) {
  if (!macro) return null

  const regimeColor = {
    bull:     "text-green-400",
    bear:     "text-red-400",
    volatile: "text-yellow-400",
    neutral:  "text-slate-400",
  }

  const vixColor = macro.vix < 20 ? "text-green-400" : macro.vix < 30 ? "text-yellow-400" : "text-red-400"

  return (
    <div className="bg-surface border border-border rounded-xl p-4 mb-6">
      <p className="text-xs text-slate-500 font-medium mb-3 uppercase tracking-wider">Market Context</p>
      <div className="flex flex-wrap gap-6 text-sm">

        <div>
          <p className="text-xs text-slate-500 mb-1">Market Regime</p>
          <p className={`font-semibold capitalize ${regimeColor[macro.market_regime] || "text-slate-300"}`}>
            {macro.market_regime}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-500 mb-1">VIX (Fear Index)</p>
          <p className={`font-semibold ${vixColor}`}>
            {macro.vix?.toFixed(1)} — <span className="font-normal text-slate-400">{macro.vix_interpretation}</span>
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-500 mb-1">S&P 500 (5-day)</p>
          <p className={`font-semibold ${(macro.spy_5d_return ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
            {macro.spy_5d_return != null ? `${macro.spy_5d_return > 0 ? "+" : ""}${macro.spy_5d_return}%` : "—"}
          </p>
        </div>

        {macro.sectors && Object.keys(macro.sectors).length > 0 && (
          <div>
            <p className="text-xs text-slate-500 mb-1">Best Sector (5d)</p>
            <p className="font-semibold text-green-400">
              {Object.entries(macro.sectors).sort((a, b) => b[1] - a[1])[0]?.[0]}
              {" "}
              <span className="text-xs text-green-500">
                +{Object.entries(macro.sectors).sort((a, b) => b[1] - a[1])[0]?.[1].toFixed(1)}%
              </span>
            </p>
          </div>
        )}

      </div>
    </div>
  )
}
