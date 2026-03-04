import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

interface ClassInfo {
  id: string
  name: string
  student_count: number
}

interface Student {
  id: string
  student_no: string
  name: string
}

export default function TeacherReports() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const initialClassId = searchParams.get('class_id')
  
  const [selectedClass, setSelectedClass] = useState(initialClassId || '')
  const [selectedStudent, setSelectedStudent] = useState('')
  const [generatingAll, setGeneratingAll] = useState(false)
  
  const { data: classes } = useQuery<ClassInfo[]>({
    queryKey: ['teacher-classes'],
    queryFn: async () => {
      const res = await api.get('/api/v1/students/classes')
      return res.data
    },
  })
  
  const { data: students } = useQuery<Student[]>({
    queryKey: ['class-students', selectedClass],
    queryFn: async () => {
      const res = await api.get(`/api/v1/students/classes/${selectedClass}/students`)
      return res.data
    },
    enabled: !!selectedClass,
  })
  
  const generateMutation = useMutation({
    mutationFn: async (studentId: string) => {
      const res = await api.post('/api/v1/reports/generate', {
        student_id: studentId,
        report_type: 'periodic',
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student-reports'] })
    },
  })
  
  const handleBatchGenerate = async () => {
    if (!students) return
    setGeneratingAll(true)
    for (const student of students) {
      await generateMutation.mutateAsync(student.id)
    }
    setGeneratingAll(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-gradient">{t('nav.batch_report')}</h1>
        <p className="text-text-muted mt-1">为班级学生批量生成诊断报告</p>
      </div>
      
      <div className="glass-panel p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">选择班级</label>
            <select
              value={selectedClass}
              onChange={(e) => { setSelectedClass(e.target.value); setSelectedStudent(''); }}
              className="input-field"
            >
              <option value="">选择班级</option>
              {classes?.map(cls => (
                <option key={cls.id} value={cls.id}>{cls.name} ({cls.student_count}人)</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">选择学生</label>
            <select
              value={selectedStudent}
              onChange={(e) => setSelectedStudent(e.target.value)}
              className="input-field"
              disabled={!selectedClass}
            >
              <option value="">选择学生</option>
              {students?.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.student_no})</option>
              ))}
            </select>
          </div>
          
          <div className="flex items-end gap-2">
            <button
              onClick={() => selectedStudent && generateMutation.mutate(selectedStudent)}
              disabled={!selectedStudent || generateMutation.isPending}
              className="btn-secondary flex-1"
            >
              📋 生成报告
            </button>
            <button
              onClick={handleBatchGenerate}
              disabled={!selectedClass || generatingAll}
              className="btn-primary flex-1"
            >
              {generatingAll ? '批量生成中...' : '📑 批量生成'}
            </button>
          </div>
        </div>
      </div>
      
      {selectedClass && !selectedStudent && (
        <div className="glass-panel overflow-hidden">
          <div className="p-4 border-b border-accent-blue/20">
            <h3 className="font-display font-semibold text-accent-cyan">班级学生列表</h3>
          </div>
          <div className="divide-y divide-railway-700/50">
            {students?.map((student, index) => (
              <motion.div
                key={student.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.03 }}
                className="p-4 flex items-center justify-between hover:bg-railway-700/20"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center text-white font-semibold">
                    {student.name[0]}
                  </div>
                  <div>
                    <p className="font-semibold text-text-primary">{student.name}</p>
                    <p className="text-sm text-text-muted">{student.student_no}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedStudent(student.id)}
                  className="btn-secondary !py-2 !px-4 text-sm"
                >
                  查看报告
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}
      
      {!selectedClass && (
        <div className="glass-panel p-12 text-center">
          <div className="text-6xl mb-4">📑</div>
          <h3 className="font-display text-xl font-semibold text-text-primary mb-2">请选择班级</h3>
          <p className="text-text-muted">选择班级后可以为学生生成诊断报告</p>
        </div>
      )}
    </div>
  )
}
