import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const mutationSuccess = vi.fn()
const authHarness = vi.hoisted(() => ({
  state: {} as any,
  setState(update: any) { this.state = { ...this.state, ...update } },
}))

vi.mock('../store/auth', () => ({
  useAuthStore: Object.assign(() => authHarness.state, { setState: (update: any) => authHarness.setState(update) }),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('recharts', async () => {
  const React = await import('react')
  const Box = ({ children }: { children?: React.ReactNode }) => React.createElement('div', null, children)
  return { RadarChart: Box, PolarGrid: Box, PolarAngleAxis: Box, PolarRadiusAxis: Box, Radar: Box, BarChart: Box, Bar: Box, XAxis: Box, YAxis: Box, Tooltip: Box, ResponsiveContainer: Box, AreaChart: Box, Area: Box, CartesianGrid: Box, Cell: Box, LineChart: Box, Line: Box }
})

vi.mock('framer-motion', async () => {
  const React = await import('react')
  const Box = React.forwardRef(({ children }: any, ref: any) => React.createElement('div', { ref }, children))
  return { motion: new Proxy({}, { get: () => Box }), AnimatePresence: Box }
})

const dashboard = {
  realtime: { active_students: 12, today_trainings: 30, average_score: 86, pass_rate: 92 },
  class_ranking: [1, 2, 3, 4].map((rank) => ({ class_id: `c${rank}`, class_name: `${rank}班`, average_score: 90 - rank, training_count: 20 + rank, rank })),
  ability_distribution: [1, 2, 3, 4, 5, 6].map((index) => ({ ability_id: `a${index}`, ability_name: `能力维度${index}`, avg: 70 + index, distribution: [1, 2] })),
  trend: [1, 2, 3, 4, 5, 6, 7].map((index) => ({ date: `2026-09-0${index}`, training_count: index, average_score: 70 + index, pass_rate: 80 })),
  lab_status: [
    { lab_id: 'l1', lab_name: '实训室1', status: 'available', current_students: 0, capacity: 30 },
    { lab_id: 'l2', lab_name: '实训室2', status: 'in_use', current_students: 12, capacity: 30 },
    { lab_id: 'l3', lab_name: '实训室3', status: 'maintenance', current_students: 0, capacity: 30 },
  ],
  updated_at: '2026-09-17T08:00:00',
}

const ability = {
  total_score: 82,
  strongest_ability: '安全意识',
  weakest_ability: '规范操作',
  graduation_ready: false,
  updated_at: '2026-09-17T08:00:00',
  radar_data: [1, 2, 3, 4, 5].map((index) => ({ ability_id: `a${index}`, name: `能力${index}`, score: 60 + index, threshold: 70, weight: .2 })),
  weak_abilities: [{ name: '规范操作', score: 61 }],
  improvement_suggestions: ['加强步骤训练'],
  sub_ability_details: [{ id: 's1', major_ability_id: 'a1', name: '步骤执行', score: 60, weight: 1, evidence: [{ score_id: 'score-1', step_id: 'step-1', project_name: '实训项目', source_record_id: 'SRC-1', step_name: '步骤一', passed: false, score: 5, max_score: 10 }] }],
}

const scoreList = { total: 1, average_score: 80, scores: [{ id: 'score-1', student_id: 'student-1', student_name: '学生甲', project_id: 'project-1', project_name: '实训项目', total_score: 80, max_score: 100, percentage: 80, calculated_at: '2026-09-17T08:00:00' }] }
const report = { id: 'report-1', report_type: 'single', score_id: 'score-1', title: '诊断报告', content: '# 诊断\n改进建议', generated_at: '2026-09-17T08:00:00' }
const environmentResult = { id: 'check-1', lab_name: '实训室1', total_score: 88, final_score: 25, summary: '整体规范', reviewed_summary: '人工确认规范', review_status: 'confirmed', review_note: '已确认', reviewer_name: '教师甲', reviewed_at: '2026-09-17T08:00:00', checked_at: '2026-09-17T08:00:00', uploaded_image_url: '/current.jpg', reference_image_url: '/reference.jpg', details: { surface_cleanliness: { score: 25, max_score: 30, issues: ['少量遗留物'] } }, reviewed_details: { surface_cleanliness: { score: 25, max_score: 30, issues: ['少量遗留物'], comment: '已核对' } }, suggestions: ['清理台面'], reviewed_suggestions: ['清理台面'], reviewed_suggestions_comment: '建议已落实' }

function queryData(key: readonly unknown[]) {
  const name = String(key[0])
  const values: Record<string, any> = {
    dashboard,
    'student-home-scores': scoreList,
    'student-home-ability': ability,
    studentAbility: ability,
    studentAbilityTrend: { abilities: [{ id: 'a1', name: '能力1' }], points: [{ date: '2026-09-17T08:00:00', abilities: { a1: 70 } }] },
    'score-projects': [{ id: 'project-1', name: '实训项目' }],
    'student-scores': scoreList,
    'score-detail': { student_name: '学生甲', class_name: '机车一班', project_name: '实训项目', total_score: 80, max_score: 100, source_record_id: 'SRC-1', source_completed_at: '2026-09-17T08:00:00', steps_total: 80, reconciliation_ok: true, details: [{ step_id: 'step-1', step_name: '步骤一', source_status: '未通过', passed: false, score: 5, max_score: 10, applied_rule: { passed_score: 10, failed_score: 5, rule_version: 2 }, related_ability_names: ['规范操作'], reason: '步骤遗漏' }] },
    'student-reports': [report],
    'student-report-scores': scoreList,
    'my-environment-results': [environmentResult],
    'teacher-home-classes': [{ id: 'class-1', name: '机车一班', major_name: '铁道机车', student_count: 35 }],
    'teacher-classes': [{ id: 'class-1', name: '机车一班', student_count: 35 }],
    'class-overview': { student_count: 35, completed_students: 30, training_count: 100, average_score: 82, graduation_ready_count: 20, score_distribution: [{ label: '80-89', count: 10 }], ability_distribution: [{ name: '规范操作', average: 75 }], common_weak_abilities: [{ name: '规范操作', student_count: 5 }], students: [{ id: 'student-1', name: '学生甲', student_no: '2023001', training_count: 3, average_score: 82, graduation_ready: false }] },
    'student-comprehensive': { student: { name: '学生甲', class_name: '机车一班', student_no: '2023001' }, score_summary: scoreList, ability, environment_checks: [environmentResult], reports: [report] },
    'class-students': [{ id: 'student-1', name: '学生甲' }],
    'class-scores': scoreList,
    'class-summary': { student_count: 35, average_score: 82, pass_rate: 90 },
    'teacher-report-scores': scoreList,
    'teacher-student-reports': [report],
    'environment-classes': [{ id: 'class-1', name: '机车一班' }],
    'environment-students': [{ id: 'student-1', name: '学生甲' }],
    'environment-labs': [{ id: 'lab-1', name: '实训室1', reference_image_url: '/reference.jpg' }],
    'environment-scores': scoreList,
    'environment-history': [environmentResult],
    'environment-task': { id: 'task-1', status: 'completed', result: environmentResult },
    'admin-overview': { students: 140, classes: 4, scores: 1000, abilities: 6, labs: 4, reports: 20, database: 'SQLite', sync_status: '正常' },
    'admin-abilities': [{ id: 'a1', name: '规范操作', graduation_threshold: .7, sub_abilities: [{ id: 's1', name: '步骤执行', weight: 1 }] }],
    'admin-labs': [{ id: 'lab-1', name: '实训室1', reference_image_url: '/reference.jpg' }],
    'admin-projects': [{ id: 'project-1', name: '实训项目', steps: [{ id: 'step-1', name: '步骤一', score: 100, failed_score: 0 }], ability_mapping: { 'step-1': ['s1'] }, sample_scores: [{ id: 'score-1', student_id: 'student-1', total_score: 80 }] }],
    'admin-access': { role_scopes: [{ role: 'student', label: '学生', scope: '本人' }], teachers: [{ id: 'teacher-1', name: '教师甲', username: 'T1' }], classes: [{ id: 'class-1', name: '机车一班', year: 2023, teacher_id: 'teacher-1', teacher_name: '教师甲' }] },
    'admin-sync-history': [{ id: 'sync-1', started_at: '2026-09-17T08:00:00', read_count: 1000, success_count: 990, skipped_count: 5, error_count: 5, status: 'completed' }],
    'operations-status': { application: { status: 'healthy' }, database: { status: 'healthy' }, sync: { status: 'completed' }, ai: { status: 'configured' } },
    'sync-schedule': { enabled: true, frequency_hours: 24, hour: 2 },
    backups: [{ id: 'backup-1' }],
    'audit-logs': [{ id: 'log-1', created_at: '2026-09-17T08:00:00', actor_name: '管理员', action: 'update', object_type: 'project', result: 'success' }],
  }
  return values[name]
}

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn((options: any) => ({ data: queryData(options.queryKey), isLoading: false, error: null, refetch: vi.fn() })),
  useMutation: vi.fn((options: any) => ({ mutate: vi.fn((payload) => { mutationSuccess(payload); options?.onSuccess?.({ id: 'task-1', status: 'completed', result: environmentResult, message: '成功', rule_version: 2, max_score: 100, recalculated_count: 1, sample: { before_total: 80, after_total: 90, rule_version: 2 } }) }), isPending: false, error: null, data: null })),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  QueryClient: class {},
  QueryClientProvider: ({ children }: any) => children,
}))

import Dashboard from '../pages/Dashboard'
import Login from '../pages/Login'
import StudentHome from '../pages/student/Home'
import StudentScores from '../pages/student/Scores'
import StudentAbility from '../pages/student/Ability'
import StudentReports from '../pages/student/Reports'
import StudentEnvironmentResults from '../pages/student/EnvironmentResults'
import EnvironmentCheckPage from '../pages/student/EnvCheck'
import TeacherHome from '../pages/teacher/Home'
import TeacherClasses from '../pages/teacher/Classes'
import TeacherScores from '../pages/teacher/Scores'
import TeacherReports from '../pages/teacher/Reports'
import AdminHome from '../pages/admin/Home'
import AdminConfig from '../pages/admin/Config'
import Layout from '../components/Layout'
import ScoreEvidenceModal from '../components/ScoreEvidenceModal'
import { useAuthStore } from '../store/auth'
import App from '../App'
import { api } from '../lib/api'

function renderPage(node: React.ReactNode, route = '/') {
  window.history.pushState({}, '', route)
  return render(<MemoryRouter initialEntries={[route]}>{node}</MemoryRouter>)
}

describe('all role workspaces render populated acceptance states', () => {
  beforeEach(() => {
    useAuthStore.setState({ isAuthenticated: true, token: 'token', refreshToken: 'refresh', user: { id: 'student-user', username: '2023001', name: '学生甲', role: 'student', student_id: 'student-1', class_name: '机车一班' }, isLoading: false, error: null, login: vi.fn(async () => undefined), logout: vi.fn() })
    globalThis.WebSocket = class { onmessage: any; onerror: any; close() {} } as any
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  })
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders public and student pages with populated data', async () => {
    const apiGet = vi.spyOn(api, 'get').mockResolvedValue({ data: new Blob(['report']) } as any)
    const pages = [<Dashboard />, <StudentHome />, <StudentScores />, <StudentAbility />, <StudentReports />, <StudentEnvironmentResults />]
    for (const page of pages) { renderPage(page); expect(document.body.textContent?.length).toBeGreaterThan(20); cleanup() }
    const evidence = renderPage(<ScoreEvidenceModal scoreId="score-1" onClose={vi.fn()} />)
    expect(evidence.container.querySelector('.alert-success')).toHaveTextContent('核对一致')
    cleanup()
    renderPage(<StudentReports />)
    fireEvent.click(screen.getAllByText('诊断报告')[1])
    fireEvent.click(screen.getByText('下载 Word'))
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith('/api/v1/reports/report-1/download.doc', { responseType: 'blob' }))
  })

  it('renders teacher workflows and drills into populated records', () => {
    useAuthStore.setState({ user: { id: 'teacher-1', username: 'T1', name: '教师甲', role: 'teacher' } as any })
    const pages = [<TeacherHome />, <TeacherClasses />, <TeacherScores />, <TeacherReports />, <EnvironmentCheckPage />]
    for (const page of pages) { renderPage(page); expect(document.body.textContent?.length).toBeGreaterThan(20); cleanup() }
    renderPage(<TeacherClasses />)
    fireEvent.change(screen.getByLabelText('授权班级'), { target: { value: 'class-1' } })
    fireEvent.click(screen.getByText('学生甲'))
    expect(screen.getByText('STUDENT COMPREHENSIVE DETAIL')).toBeInTheDocument()
    cleanup()
    renderPage(<TeacherReports />)
    expect(screen.getByLabelText('生成报告类型')).toBeInTheDocument()
    expect(screen.queryByLabelText('筛选历史报告类型')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('授权班级'), { target: { value: 'class-1' } })
    fireEvent.change(screen.getByLabelText('学生'), { target: { value: 'student-1' } })
    expect(screen.getByLabelText('筛选历史报告类型')).toBeInTheDocument()
    cleanup()
    renderPage(<EnvironmentCheckPage />)
    expect(screen.queryByText('__suggestions__')).not.toBeInTheDocument()
    expect(screen.getByDisplayValue('已核对')).toBeInTheDocument()
    expect(screen.getByDisplayValue('建议已落实')).toBeInTheDocument()
  })

  it('renders administrator configuration and operations', () => {
    useAuthStore.setState({ user: { id: 'admin-1', username: 'A1', name: '管理员', role: 'admin' } as any })
    renderPage(<AdminHome />)
    cleanup()
    renderPage(<AdminConfig />)
    fireEvent.click(screen.getByText('保存同步计划'))
    fireEvent.click(screen.getByText('立即生成数据库备份'))
    fireEvent.click(screen.getByText('执行一次 Mock 同步'))
    expect(mutationSuccess).toHaveBeenCalled()
  })

  it('renders layout and submits a demo login', async () => {
    renderPage(<Layout />)
    cleanup()
    useAuthStore.setState({ isAuthenticated: false, user: null })
    renderPage(<Login />, '/login')
    fireEvent.click(screen.getByRole('button', { name: '学生' }))
    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    await waitFor(() => expect(authHarness.state.login).toHaveBeenCalledWith('2023010101', '123456'))
  })

  it('routes authenticated and unauthenticated users through the application shell', () => {
    window.history.pushState({}, '', '/student')
    render(<App />)
    expect(document.body.textContent).toContain('学习概览')
    expect(document.body.textContent).toContain('能力看板')
    expect(document.body.textContent).toContain('查看你的强项、弱项，以及是否达到毕业标准')
    cleanup()
    window.history.pushState({}, '', '/')
    render(<App />)
    expect(window.location.pathname).toBe('/student')
    cleanup()
    useAuthStore.setState({ isAuthenticated: false, user: null })
    window.history.pushState({}, '', '/admin')
    render(<App />)
    expect(window.location.pathname).toBe('/login')
  })
})
