export default function HoldBadge({ holdInfo }) {
  if (!holdInfo) return null
  return (
    <span className="text-xs font-medium px-2 py-1 rounded-full bg-slate-700 text-slate-300 border border-slate-600">
      {holdInfo.icon} {holdInfo.label} · {holdInfo.range}
    </span>
  )
}
