import { describe, expect, it } from 'vitest'
import { canAccess, roleDestinations, roleMenus } from './roleAccess'

describe('role access matrix', () => {
  it('redirects each account to a distinct workspace', () => {
    expect(roleDestinations).toEqual({
      student: '/student',
      teacher: '/teacher',
      admin: '/admin',
    })
  })

  it('keeps student, teacher and admin menus separated', () => {
    expect(roleMenus.student.map((item) => item.label)).toContain('我的成绩')
    expect(roleMenus.student.map((item) => item.label)).not.toContain('系统总览')
    expect(roleMenus.student.map((item) => item.label)).not.toContain('环境检查')
    expect(roleMenus.teacher.map((item) => item.label)).toContain('我的班级')
    expect(roleMenus.teacher.map((item) => item.label)).toContain('环境检查')
    expect(roleMenus.teacher.map((item) => item.label)).not.toContain('基础配置')
    expect(roleMenus.admin.map((item) => item.label)).toContain('基础配置')
  })

  it('allows only explicitly listed roles', () => {
    expect(canAccess('teacher', ['teacher', 'admin'])).toBe(true)
    expect(canAccess('student', ['teacher', 'admin'])).toBe(false)
  })
})
