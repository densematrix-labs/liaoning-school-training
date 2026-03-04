import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { api } from '../../lib/api'
import { useAuthStore } from '../../store/auth'

interface Report {
  id: string
  student_id: string
  student_name: string
  report_type: string
  title: string
  content: string
  generated_at: string
}

function ReportCard({ 
  report, 
  index,
  onView 
}: { 
  report: Report
  index: number
  onView: (report: Report) => void 
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="glass-panel p-5 cursor-pointer hover:shadow-glow-sm transition-all duration-300 group"
      onClick={() => onView(report)}
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-display text-lg font-semibold text-text-primary group-hover:text-accent-cyan transition-colors">
            {report.title}
          </h3>
          <p className="text-sm text-text-muted mt-1">
            {new Date(report.generated_at).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>
        
        <span className={`px-3 py-1 rounded-full text-xs font-semibold
          ${report.report_type === 'single' 
            ? 'bg-accent-blue/20 text-accent-cyan' 
            : 'bg-accent-cyan/20 text-accent-cyan'}`}
        >
          {report.report_type === 'single' ? '单次诊断' : '阶段报告'}
        </span>
      </div>
      
      {/* Preview */}
      <p className="text-text-muted text-sm mt-3 line-clamp-2">
        {report.content.slice(0, 100)}...
      </p>
      
      <div className="mt-4 text-sm text-accent-blue group-hover:text-accent-cyan transition-colors">
        点击查看详情 →
      </div>
    </motion.div>
  )
}

function ReportModal({ 
  report, 
  onClose 
}: { 
  report: Report
  onClose: () => void 
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-railway-900/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        className="glass-panel-bright w-full max-w-3xl max-h-[80vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-accent-blue/20">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-bold text-gradient">
                {report.title}
              </h2>
              <p className="text-sm text-text-muted mt-1">
                生成时间: {new Date(report.generated_at).toLocaleString('zh-CN')}
              </p>
            </div>
            <button
              onClick={onClose}
              className="w-10 h-10 rounded-lg bg-railway-700 hover:bg-railway-600 flex items-center justify-center transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-100px)]">
          <article className="prose prose-invert prose-cyan max-w-none">
            <ReactMarkdown
              components={{
                h2: ({ children }) => (
                  <h2 className="font-display text-lg font-semibold text-accent-cyan mt-6 mb-3 pb-2 border-b border-accent-blue/20">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="font-display text-base font-semibold text-text-primary mt-4 mb-2">
                    {children}
                  </h3>
                ),
                p: ({ children }) => (
                  <p className="text-text-secondary leading-relaxed mb-3">
                    {children}
                  </p>
                ),
                ul: ({ children }) => (
                  <ul className="space-y-2 my-3">
                    {children}
                  </ul>
                ),
                li: ({ children }) => (
                  <li className="flex items-start gap-2 text-text-secondary">
                    <span className="text-accent-cyan mt-1">•</span>
                    <span>{children}</span>
                  </li>
                ),
                strong: ({ children }) => (
                  <strong className="text-accent-cyan font-semibold">{children}</strong>
                ),
              }}
            >
              {report.content}
            </ReactMarkdown>
          </article>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function StudentReports() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)
  
  const { data: reports, isLoading } = useQuery<Report[]>({
    queryKey: ['student-reports'],
    queryFn: async () => {
      const res = await api.get('/api/v1/reports/')
      return res.data
    },
  })
  
  const generateMutation = useMutation({
    mutationFn: async (reportType: string) => {
      const res = await api.post('/api/v1/reports/generate', {
        student_id: user?.student_id,
        report_type: reportType,
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student-reports'] })
    },
  })
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-4 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gradient">
            {t('nav.reports')}
          </h1>
          <p className="text-text-muted mt-1">
            查看 AI 生成的个性化诊断报告
          </p>
        </div>
        
        {/* Generate buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => generateMutation.mutate('single')}
            disabled={generateMutation.isPending}
            className="btn-secondary flex items-center gap-2"
          >
            {generateMutation.isPending ? (
              <div className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
            ) : (
              <span>📋</span>
            )}
            生成单次报告
          </button>
          <button
            onClick={() => generateMutation.mutate('periodic')}
            disabled={generateMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {generateMutation.isPending ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <span>📊</span>
            )}
            生成阶段报告
          </button>
        </div>
      </div>
      
      {/* Report list */}
      <div className="grid gap-4">
        {reports?.map((report, index) => (
          <ReportCard
            key={report.id}
            report={report}
            index={index}
            onView={setSelectedReport}
          />
        ))}
      </div>
      
      {/* Empty state */}
      {(!reports || reports.length === 0) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-panel p-12 text-center"
        >
          <div className="text-6xl mb-4">📋</div>
          <h3 className="font-display text-xl font-semibold text-text-primary mb-2">
            暂无诊断报告
          </h3>
          <p className="text-text-muted mb-6">
            点击上方按钮生成你的第一份 AI 诊断报告
          </p>
        </motion.div>
      )}
      
      {/* Report modal */}
      {selectedReport && (
        <ReportModal
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
        />
      )}
    </div>
  )
}
