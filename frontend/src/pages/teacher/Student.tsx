import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { teacherApi, trainingApi } from '../../lib/api'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts'
import { motion } from 'framer-motion'
import clsx from 'clsx'

export default function TeacherStudent() {
  const { studentId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: student, isLoading } = useQuery({
    queryKey: ['studentDetails', studentId],
    queryFn: () => teacherApi.getStudentDetails(studentId!).then(res => res.data),
    enabled: !!studentId,
  })

  const generateMutation = useMutation({
    mutationFn: () => trainingApi.generateReport(studentId!, 'periodic'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['studentDetails', studentId] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full" />
      </div>
    )
  }

  const radarData = Object.entries(student?.ability_map || {}).map(([id, score]) => ({
    name: id.replace('ma-', '能力'),
    score: score as number,
    fullMark: 100,
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 rounded-lg bg-railway-700/50 hover:bg-railway-600/50 transition-colors">
            <svg className="w-5 h-5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{student?.name}</h1>
            <p className="text-text-muted mt-1">{student?.student_no} · {student?.class_name}</p>
          </div>
        </div>
        <button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending} className="railway-button flex items-center gap-2">
          {generateMutation.isPending ? '生成中...' : '生成诊断报告'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <p className="text-text-muted text-sm">入学年份</p>
          <p className="stat-value mt-1">{student?.enrollment_year}</p>
        </div>
        <div className="stat-card">
          <p className="text-text-muted text-sm">实训次数</p>
          <p className="stat-value mt-1">{student?.total_trainings || 0}</p>
        </div>
        <div className="stat-card">
          <p className="text-text-muted text-sm">平均成绩</p>
          <p className="stat-value mt-1">{student?.average_score || 0}</p>
        </div>
        <div className="stat-card">
          <p className="text-text-muted text-sm">毕业达标</p>
          <p className={clsx('stat-value mt-1', student?.graduation_ready ? 'text-status-success' : 'text-status-warning')}>
            {student?.graduation_ready ? '已达标' : '未达标'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="railway-card p-6">
          <h2 className="section-title mb-4">能力雷达图</h2>
          <div className="h-80">
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="rgba(0, 212, 255, 0.2)" />
                  <PolarAngleAxis dataKey="name" tick={{ fill: '#8eb8e5', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#5d7a9c', fontSize: 10 }} />
                  <Radar dataKey="score" stroke="#00d4ff" fill="#00d4ff" fillOpacity={0.3} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-text-muted">暂无能力数据</div>
            )}
          </div>
        </div>

        <div className="railway-card p-6">
          <h2 className="section-title mb-4">最近实训记录</h2>
          <div className="space-y-3">
            {student?.training_history?.length > 0 ? (
              student.training_history.map((record: any) => (
                <div key={record.id} className={clsx('p-4 rounded-lg border', record.passed ? 'bg-status-success/5 border-status-success/20' : 'bg-status-danger/5 border-status-danger/20')}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-text-primary">{record.project_name}</p>
                      <p className="text-xs text-text-muted mt-1">{record.completed_at ? new Date(record.completed_at).toLocaleString('zh-CN') : ''}</p>
                    </div>
                    <div className="text-right">
                      <p className={clsx('text-xl font-mono font-bold', record.passed ? 'text-status-success' : 'text-status-danger')}>{record.score}</p>
                      <span className={clsx('text-xs', record.passed ? 'text-status-success' : 'text-status-danger')}>{record.passed ? '通过' : '未通过'}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-text-muted py-8">暂无实训记录</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
