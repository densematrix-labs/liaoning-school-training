export type Role = 'student' | 'teacher' | 'admin'

export const roleDestinations: Record<Role, string> = {
  student: '/student',
  teacher: '/teacher',
  admin: '/admin',
}

export const roleMenus: Record<Role, Array<{ to: string; label: string; icon: string }>> = {
  student: [
    { to: '/student', label: '学习概览', icon: '◉' },
    { to: '/scores', label: '我的成绩', icon: '▥' },
    { to: '/ability', label: '能力图谱', icon: '⌁' },
    { to: '/reports', label: '诊断报告', icon: '▤' },
    { to: '/env-check', label: '环境检查', icon: '▣' },
  ],
  teacher: [
    { to: '/teacher', label: '教学工作台', icon: '◉' },
    { to: '/classes', label: '我的班级', icon: '▦' },
    { to: '/class-scores', label: '成绩总览', icon: '▥' },
    { to: '/batch-reports', label: '学生诊断', icon: '▤' },
  ],
  admin: [
    { to: '/admin', label: '系统总览', icon: '◉' },
    { to: '/classes', label: '全校班级', icon: '▦' },
    { to: '/class-scores', label: '全校成绩', icon: '▥' },
    { to: '/batch-reports', label: '报告中心', icon: '▤' },
    { to: '/admin/config', label: '基础配置', icon: '⚙' },
  ],
}

export function canAccess(role: Role, allowedRoles: Role[]) {
  return allowedRoles.includes(role)
}
