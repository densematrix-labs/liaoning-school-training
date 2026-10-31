export default function ClassAbilityBands({ overview, dateFrom, dateTo }: { overview: any; dateFrom: string; dateTo: string }) {
  const rows = overview.ability_score_bands
  if (!rows?.length) return null
  return <section className="railway-card space-y-4 p-5" aria-label="班级各维能力值分段人数分布">
    <h2 className="section-heading">能力值分段人数分布</h2>
    <p>授权班级：{overview.class_name} · 班级人数：{overview.student_count} 人 · 统计范围：{dateFrom || '全部历史'} 至 {dateTo || '当前'}</p>
    
    <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead><tr className="border-b border-railway-600 text-text-muted"><th className="py-3">能力维度</th>{rows[0].bands.map((band: any) => <th key={band.label} className="p-2">{band.label}</th>)}<th className="p-2">无该维度证据</th><th className="p-2">合计</th></tr></thead><tbody>{rows.map((row: any) => <tr className="border-b border-railway-600/40" key={row.id}><td className="py-4 font-medium">{row.name}</td>{row.bands.map((band: any) => <td key={band.label} className="p-2"><p className="font-mono text-accent-cyan">{band.count} 人</p><div className="mt-1 h-1.5 w-full rounded bg-railway-700"><div className="h-full rounded bg-accent-cyan" style={{width: `${row.student_count ? band.count / row.student_count * 100 : 0}%`}}/></div></td>)}<td className="p-2">{row.missing_evidence_count} 人</td><td className="p-2">{row.bands.reduce((sum: number, band: any) => sum + band.count, 0) + row.missing_evidence_count} 人</td></tr>)}</tbody></table></div>

  </section>
}
