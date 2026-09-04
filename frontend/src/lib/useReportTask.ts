import { useEffect, useState } from 'react'
import { createElement } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

export function useReportTask(onCompleted?: (report: any) => void) {
  const queryClient = useQueryClient()
  const [taskId, setTaskId] = useState('')
  const create = useMutation({
    mutationFn: async (payload: { student_id: string; report_type: 'single' | 'periodic'; score_id?: string }) => (await api.post('/api/v1/reports/generate', payload)).data,
    onSuccess: (task) => setTaskId(task.id),
  })
  const task = useQuery({
    queryKey: ['report-task', taskId],
    queryFn: async () => (await api.get(`/api/v1/reports/tasks/${taskId}`)).data,
    enabled: Boolean(taskId),
    refetchInterval: (query) => ['pending', 'running'].includes((query.state.data as any)?.status) ? 800 : false,
  })
  useEffect(() => {
    if (task.data?.status === 'completed' && task.data.report) {
      queryClient.invalidateQueries({ queryKey: ['student-reports'] })
      queryClient.invalidateQueries({ queryKey: ['teacher-student-reports'] })
      onCompleted?.(task.data.report)
    }
  }, [task.data?.status, task.data?.report_id])
  return { create, task: task.data, taskId, clearTask: () => setTaskId('') }
}

export function ReportTaskStatus({ task }: { task: any }) {
  if (!task) return null
  const labels: Record<string, string> = { pending: '已提交', running: '模型分析中', completed: '生成完成', failed: '生成失败' }
  return createElement(
    'div',
    { className: task.status === 'failed' ? 'alert-warning rounded p-4 text-sm' : 'alert-success rounded p-4 text-sm' },
    createElement(
      'div',
      { className: 'flex flex-wrap items-center justify-between gap-2' },
      createElement('span', null, '任务状态：', createElement('strong', null, labels[task.status] || task.status)),
      createElement('span', { className: 'font-mono text-xs' }, task.id),
    ),
    task.error_message ? createElement('p', { className: 'mt-2' }, task.error_message) : null,
  )
}
