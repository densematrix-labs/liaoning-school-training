import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../lib/api'

interface ClassInfo {
  id: string
  name: string
  major_name: string
  year: number
  student_count: number
}

export default function TeacherClasses() {
  const { t } = useTranslation()
  
  const { data: classes, isLoading } = useQuery<ClassInfo[]>({
    queryKey: ['teacher-classes'],
    queryFn: async () => {
      const res = await api.get('/api/v1/students/classes')
      return res.data
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
      <div>
        <h1 className="font-display text-2xl font-bold text-gradient">
          {t('teacher.my_classes')}
        </h1>
        <p className="text-text-muted mt-1">管理班级学生和查看成绩汇总</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {classes?.map((cls, index) => (
          <motion.div
            key={cls.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="glass-panel p-6 hover:shadow-glow-sm transition-all"
          >
            <h3 className="font-display text-xl font-semibold text-text-primary mb-2">
              {cls.name}
            </h3>
            <p className="text-sm text-text-muted mb-4">{cls.major_name}</p>
            
            <div className="flex items-center gap-2 mb-4">
              <span className="text-2xl">👥</span>
              <span className="font-mono text-lg text-accent-cyan">{cls.student_count}</span>
              <span className="text-text-muted text-sm">学生</span>
            </div>
            
            <div className="flex gap-2">
              <Link
                to={`/class-scores?class_id=${cls.id}`}
                className="btn-secondary flex-1 text-center !py-2 text-sm"
              >
                📊 查看成绩
              </Link>
              <Link
                to={`/batch-reports?class_id=${cls.id}`}
                className="btn-primary flex-1 text-center !py-2 text-sm"
              >
                📋 生成报告
              </Link>
            </div>
          </motion.div>
        ))}
      </div>
      
      {(!classes || classes.length === 0) && (
        <div className="glass-panel p-12 text-center">
          <div className="text-6xl mb-4">👥</div>
          <h3 className="font-display text-xl font-semibold text-text-primary mb-2">暂无班级</h3>
          <p className="text-text-muted">您目前没有分配班级</p>
        </div>
      )}
    </div>
  )
}
