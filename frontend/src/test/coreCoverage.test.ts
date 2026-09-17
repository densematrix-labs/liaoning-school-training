import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, getErrorMessage } from '../lib/api'
import { useAuthStore } from '../store/auth'

describe('API authentication helpers', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.getState().logout()
    vi.restoreAllMocks()
  })

  it('normalizes API error payloads', () => {
    expect(getErrorMessage({ response: { data: { detail: '凭据无效' } } })).toBe('凭据无效')
    expect(getErrorMessage({ response: { data: { detail: [{ msg: '用户名必填' }, { msg: '密码必填' }] } } })).toBe('用户名必填；密码必填')
    expect(getErrorMessage({ response: { data: { detail: [] } }, }, '备用提示')).toBe('备用提示')
    expect(getErrorMessage(null)).toBe('请求失败，请稍后重试')
  })

  it('adds persisted tokens and tolerates malformed storage', async () => {
    const requestHandler = (api.interceptors.request as any).handlers[0]
    localStorage.setItem('auth-storage', JSON.stringify({ state: { token: 'persisted-token' } }))
    const config = await requestHandler.fulfilled({ headers: {} })
    expect(config.headers.Authorization).toBe('Bearer persisted-token')
    localStorage.setItem('auth-storage', '{bad json')
    expect(await requestHandler.fulfilled({ headers: {} })).toEqual({ headers: {} })
    await expect(requestHandler.rejected(new Error('request failed'))).rejects.toThrow('request failed')
  })

  it('handles successful and unauthorized responses', async () => {
    const responseHandler = (api.interceptors.response as any).handlers[0]
    expect(responseHandler.fulfilled({ data: 'ok' })).toEqual({ data: 'ok' })
    const remove = vi.spyOn(localStorage, 'removeItem')
    await expect(responseHandler.rejected({ response: { status: 401 } })).rejects.toMatchObject({ response: { status: 401 } })
    expect(remove).toHaveBeenCalledWith('auth-storage')
  })

  it('logs in, fetches the user, logs out and reports authentication failures', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { access_token: 'access', refresh_token: 'refresh' } })
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: { id: 'u1', username: 'student', name: '学生甲', role: 'student' } })
    await useAuthStore.getState().login('student', 'secret')
    expect(post).toHaveBeenCalledWith('/api/v1/auth/login', { username: 'student', password: 'secret' })
    expect(get).toHaveBeenCalledWith('/api/v1/auth/me', { headers: { Authorization: 'Bearer access' } })
    expect(useAuthStore.getState()).toMatchObject({ isAuthenticated: true, token: 'access', user: { name: '学生甲' } })
    useAuthStore.getState().logout()
    expect(useAuthStore.getState()).toMatchObject({ isAuthenticated: false, token: null, user: null })

    post.mockRejectedValueOnce({ response: { data: { detail: '登录失败原因' } } })
    await expect(useAuthStore.getState().login('bad', 'bad')).rejects.toBeTruthy()
    expect(useAuthStore.getState().error).toBe('登录失败原因')
  })

  it('skips user lookup without a token and clears invalid sessions', async () => {
    const get = vi.spyOn(api, 'get')
    await useAuthStore.getState().fetchUser()
    expect(get).not.toHaveBeenCalled()
    useAuthStore.setState({ token: 'expired', isAuthenticated: true })
    get.mockRejectedValueOnce(new Error('expired'))
    await useAuthStore.getState().fetchUser()
    expect(useAuthStore.getState()).toMatchObject({ token: null, user: null, isAuthenticated: false })
  })
})
