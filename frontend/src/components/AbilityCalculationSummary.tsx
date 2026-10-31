const format = (value: number) => Number(value.toFixed(4))

export default function AbilityCalculationSummary({ profile }: { profile: any }) {
  const scope = profile?.history_scope
  const rows = profile?.major_ability_calculations
  if (!scope || !rows?.length) return null
  return <section className="railway-card space-y-4 p-5" aria-label="全历史计算范围与六大类汇总">
    <h2 className="section-heading">全历史计算范围与大类汇总</h2>
    <p>学生：{profile.student_name} · {scope.mode}：共 {scope.available_records} 次，实际计入 {scope.selected_records} 次 · 时间：{scope.date_from?.slice(0, 10) || '—'} 至 {scope.date_to?.slice(0, 10) || '—'}</p>
    <p className="text-sm text-text-secondary">项目：{scope.projects?.map((project: any) => `${project.name}（重复策略：${project.repeat_mode === 'all' ? '保留全部' : project.repeat_mode}）`).join('、')} · 时间衰减系数：{scope.decay}</p>
    <p className="text-xs text-text-muted">{scope.note} 步骤权重已体现在得分和满分中；子能力按步骤满分及衰减加权，大类按子能力权重汇总，大类权重用于综合评分。</p>
    <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead><tr className="border-b border-railway-600 text-text-muted"><th className="p-3">大类能力</th><th>子能力与权重</th><th>大类计算过程</th><th>自动达成值</th><th>大类权重</th><th>达标阈值 / 状态</th></tr></thead><tbody>{rows.map((row: any) => <tr className="border-b border-railway-600/40" key={row.id}><td className="p-3 font-medium">{row.name}</td><td>{row.children.map((child: any) => <p key={child.id}>{child.name} · {format(child.percentage)}% × 权重 {format(child.weight)}</p>)}</td><td>({row.children.map((child: any) => `${format(child.percentage)}×${format(child.weight)}`).join(' + ') || '0'}) ÷ {format(row.weight_sum) || '0'}</td><td className="font-mono text-accent-cyan">{row.percentage}%</td><td>{format(row.weight * 100)}%</td><td>{row.threshold}% · {row.percentage >= row.threshold ? '已达标' : '未达标'}</td></tr>)}</tbody></table></div>
    <p className="text-sm text-accent-cyan">综合能力评分：{profile.total_score} · 大类达标：{profile.graduation_ready_count}/{profile.graduation_total_count}</p>
    
  </section>
}
