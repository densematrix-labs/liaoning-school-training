import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function TeacherClasses() {
  const [classId, setClassId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [studentId, setStudentId] = useState('')
  const classes = useQuery({ queryKey: ['teacher-classes'], queryFn: async () => (await api.get('/api/v1/students/classes')).data })
  const overview = useQuery({
    queryKey: ['class-overview', classId, dateFrom, dateTo],
    queryFn: async () => (await api.get(`/api/v1/students/classes/${classId}/overview`, { params: { date_from: dateFrom || undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined } })).data,
    enabled: Boolean(classId),
  })
  const detail = useQuery({ queryKey: ['student-comprehensive', studentId], queryFn: async () => (await api.get(`/api/v1/students/${studentId}/comprehensive`)).data, enabled: Boolean(studentId) })

  return <div className="space-y-6">
    <header><p className="eyebrow">AUTHORIZED CLASS OVERVIEW</p><h1 className="page-title">班级实训概览</h1><p className="mt-2 text-sm text-text-muted">从班级汇总下钻至学生成绩、能力、环境检查和诊断报告</p></header>
    <section className="railway-card grid gap-4 p-5 md:grid-cols-3">
      <Field label="授权班级"><select className="input-field" value={classId} onChange={(e) => { setClassId(e.target.value); setStudentId('') }}><option value="">请选择班级</option>{classes.data?.map((item: any) => <option key={item.id} value={item.id}>{item.name}（{item.student_count}人）</option>)}</select></Field>
      <Field label="统计开始"><input className="input-field" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></Field>
      <Field label="统计结束"><input className="input-field" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></Field>
    </section>
    {!classId && <section className="railway-card p-12 text-center text-text-muted">选择班级后查看成绩分布、能力分布与毕业达标情况</section>}
    {overview.data && <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"><Metric label="学生" value={overview.data.student_count} unit="人" /><Metric label="有实训记录" value={overview.data.completed_students} unit="人" /><Metric label="实训记录" value={overview.data.training_count} unit="次" /><Metric label="平均成绩" value={overview.data.average_score} unit="分" /><Metric label="毕业达标" value={overview.data.graduation_ready_count} unit="人" /></div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Distribution title="成绩分布" items={overview.data.score_distribution.map((item: any) => ({ label: item.label, value: item.count }))} suffix="条" />
        <Distribution title="能力分布" items={overview.data.ability_distribution.map((item: any) => ({ label: item.name, value: item.average }))} suffix="分" max={100} />
      </div>
      <section className="railway-card p-5"><p className="eyebrow">COMMON WEAK SIGNALS</p><h2 className="section-heading">共性薄弱能力</h2><div className="mt-4 grid gap-3 md:grid-cols-3">{overview.data.common_weak_abilities.map((item: any) => <div key={item.name} className="rounded border border-status-warning/30 bg-status-warning/5 p-4"><p className="text-text-primary">{item.name}</p><p className="mt-2 font-mono text-xl text-status-warning">{item.student_count} 人未达标</p></div>)}</div></section>
      <section className="railway-card overflow-hidden"><div className="border-b border-railway-600/50 p-5"><p className="eyebrow">STUDENT DRILLDOWN</p><h2 className="section-heading">学生列表与完成情况</h2></div><div className="divide-y divide-railway-600/50">{overview.data.students.map((item: any) => <button key={item.id} onClick={() => setStudentId(item.id)} className="grid w-full gap-3 p-4 text-left hover:bg-railway-700/40 sm:grid-cols-[1.3fr_auto_auto_auto] sm:items-center"><div><p className="font-semibold text-text-primary">{item.name}</p><p className="text-xs text-text-muted">{item.student_no}</p></div><span className="text-text-secondary">{item.training_count} 次实训</span><span className="font-mono text-accent-cyan">均分 {item.average_score}</span><span className={item.graduation_ready ? 'text-status-success' : 'text-status-warning'}>{item.graduation_ready ? '毕业能力达标' : '能力提升中'} →</span></button>)}</div></section>
    </>}
    {studentId && <StudentDetail data={detail.data} loading={detail.isLoading} onClose={() => setStudentId('')} />}
  </div>
}

function StudentDetail({ data, loading, onClose }: { data: any; loading: boolean; onClose: () => void }) {
  return <div className="fixed inset-0 z-[80] flex items-center justify-center bg-railway-900/90 p-3 backdrop-blur" onClick={onClose}><section className="glass-panel-bright max-h-[92vh] w-full max-w-5xl overflow-y-auto" onClick={(e) => e.stopPropagation()}><header className="sticky top-0 z-10 flex justify-between border-b border-railway-600/50 bg-railway-800/95 p-5"><div><p className="eyebrow">STUDENT COMPREHENSIVE DETAIL</p><h2 className="section-heading">{data?.student?.name || '学生综合详情'}</h2><p className="mt-1 text-xs text-text-muted">{data?.student?.class_name} · {data?.student?.student_no}</p></div><button className="railway-button" onClick={onClose}>关闭</button></header>{loading ? <p className="p-8 text-text-muted">正在汇总学生数据…</p> : data && <div className="space-y-6 p-5"><div className="grid gap-3 sm:grid-cols-4"><Metric label="实训次数" value={data.score_summary.total} /><Metric label="平均成绩" value={data.score_summary.average_score || 0} /><Metric label="综合能力" value={data.ability?.total_score || 0} /><Metric label="环境检查" value={data.environment_checks.length} /></div><section><h3 className="section-heading">能力概况</h3><div className="mt-3 grid gap-2 md:grid-cols-3">{data.ability?.radar_data.map((item: any) => <div key={item.ability_id} className="rounded border border-railway-600/60 p-3"><p className="text-sm text-text-secondary">{item.name}</p><p className="font-mono text-xl text-accent-cyan">{item.score} / 阈值 {item.threshold}</p></div>)}</div></section><section><h3 className="section-heading">历史成绩</h3><div className="mt-3 space-y-2">{data.score_summary.scores.slice(0, 8).map((item: any) => <div key={item.id} className="flex justify-between rounded bg-railway-800/60 p-3 text-sm"><span>{item.project_name}</span><span className="text-accent-cyan">{item.percentage} 分</span></div>)}</div></section><div className="grid gap-4 md:grid-cols-2"><Metric label="诊断报告" value={data.reports.length} unit="份" /><Metric label="环境检查记录" value={data.environment_checks.length} unit="条" /></div></div>}</section></div>
}

function Distribution({ title, items, suffix, max }: { title: string; items: Array<{ label: string; value: number }>; suffix: string; max?: number }) { const peak = max || Math.max(...items.map((item) => item.value), 1); return <section className="railway-card p-5"><h2 className="section-heading">{title}</h2><div className="mt-5 space-y-3">{items.map((item) => <div key={item.label} className="grid grid-cols-[90px_1fr_55px] items-center gap-3 text-sm"><span className="truncate text-text-secondary">{item.label}</span><div className="h-2 overflow-hidden rounded bg-railway-700"><div className="h-full bg-accent-blue" style={{ width: `${Math.min(100, item.value / peak * 100)}%` }} /></div><span className="text-right font-mono text-accent-cyan">{item.value}{suffix}</span></div>)}</div></section> }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="text-sm text-text-secondary"><span className="mb-2 block">{label}</span>{children}</label> }
function Metric({ label, value, unit }: { label: string; value: string | number; unit?: string }) { return <div className="metric-strip"><p>{label}</p><strong className="text-accent-cyan">{value}</strong>{unit && <span>{unit}</span>}</div> }
