import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'

interface User {
  id: string
  username: string
  name: string
  role: 'student' | 'teacher' | 'admin'
  student_id?: string
  student_no?: string
  class_name?: string
  major_name?: string
  classes?: Array<{ id: string; name: string }>
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      
      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await api.post('/api/v1/auth/login', {
            username,
            password,
          })
          
          const { access_token, refresh_token } = response.data
          
          set({
            token: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
          
          // Fetch user info
          await get().fetchUser()
          
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.detail || '登录失败',
          })
          throw error
        }
      },
      
      logout: () => {
        set({
          token: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
          error: null,
        })
      },
      
      fetchUser: async () => {
        const { token } = get()
        if (!token) return
        
        try {
          const response = await api.get('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${token}` },
          })
          
          set({ user: response.data })
        } catch (error) {
          set({ isAuthenticated: false, token: null, user: null })
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
