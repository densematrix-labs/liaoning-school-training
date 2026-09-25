import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

type AbilityItem = {
  ability_id?: string
  name?: string
  ability_name?: string
  score?: number
  average?: number
  avg?: number
  threshold?: number
}

export default function AbilityRadar({
  items,
  title = '能力雷达图',
  description = '能力均值与毕业达标线对比',
  compact = false,
}: {
  items: AbilityItem[]
  title?: string
  description?: string
  compact?: boolean
}) {
  const data = (items || []).map((item) => ({
    id: item.ability_id || item.name || item.ability_name,
    name: item.name || item.ability_name || '能力维度',
    value: Number(item.score ?? item.average ?? item.avg ?? 0),
    threshold: Number(item.threshold ?? 60),
    fullMark: 100,
  }))
  const readyCount = data.filter((item) => item.value >= item.threshold).length

  return (
    <section className="railway-card ability-radar-panel overflow-hidden">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-railway-600/50 px-5 py-4">
        <div>
          <p className="eyebrow">COMPETENCY PROFILE</p>
          <h2 className="section-heading">{title}</h2>
          <p className="mt-1 text-xs text-text-muted">{description}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl text-accent-cyan">{readyCount}/{data.length}</p>
          <p className="text-[10px] text-text-muted">达标维度</p>
        </div>
      </header>
      {data.length ? (
        <>
          <div className={compact ? 'h-64 px-2 py-3' : 'h-80 px-3 py-4'}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={data} outerRadius={compact ? '64%' : '70%'}>
                <PolarGrid stroke="rgba(0, 212, 255, 0.24)" />
                <PolarAngleAxis dataKey="name" tick={{ fill: '#b8d7f5', fontSize: compact ? 10 : 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#5d7a9c', fontSize: 9 }} tickCount={5} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0d1525', border: '1px solid rgba(0, 212, 255, 0.4)', borderRadius: 8 }}
                  labelStyle={{ color: '#e8f4ff' }}
                />
                <Radar name="当前能力" dataKey="value" stroke="#00fff2" fill="#00d4ff" fillOpacity={0.3} strokeWidth={2.5} />
                <Radar name="毕业达标线" dataKey="threshold" stroke="#ffaa00" fill="#ffaa00" fillOpacity={0.04} strokeDasharray="5 5" strokeWidth={1.5} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid gap-px border-t border-railway-600/50 bg-railway-600/40 sm:grid-cols-2">
            {data.map((item) => (
              <div key={item.id} className="flex items-center justify-between bg-railway-800/95 px-4 py-2 text-xs">
                <span className="truncate text-text-secondary">{item.name}</span>
                <span className={item.value >= item.threshold ? 'font-mono text-status-success' : 'font-mono text-status-warning'}>
                  {item.value} / {item.threshold}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex h-64 items-center justify-center text-sm text-text-muted">选择学生后查看能力雷达图</div>
      )}
    </section>
  )
}
