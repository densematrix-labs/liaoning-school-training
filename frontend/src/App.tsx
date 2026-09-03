import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { useAuthStore } from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import StudentHome from './pages/student/Home'
import StudentScores from './pages/student/Scores'
import StudentAbility from './pages/student/Ability'
import StudentReports from './pages/student/Reports'
import EnvironmentCheckPage from './pages/student/EnvCheck'
import TeacherHome from './pages/teacher/Home'
import TeacherClasses from './pages/teacher/Classes'
import TeacherScores from './pages/teacher/Scores'
import TeacherReports from './pages/teacher/Reports'
import AdminHome from './pages/admin/Home'
import AdminConfig from './pages/admin/Config'
import { canAccess, roleDestinations, type Role } from './lib/roleAccess'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function RoleRoute({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuthStore()
  return user && canAccess(user.role, roles) ? <>{children}</> : <Navigate to="/" replace />
}

function RoleIndex() {
  const { user } = useAuthStore()
  return <Navigate to={user ? roleDestinations[user.role] : '/login'} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<RoleIndex />} />

          <Route path="student" element={<RoleRoute roles={['student']}><StudentHome /></RoleRoute>} />
          <Route path="scores" element={<RoleRoute roles={['student']}><StudentScores /></RoleRoute>} />
          <Route path="ability" element={<RoleRoute roles={['student']}><StudentAbility /></RoleRoute>} />
          <Route path="reports" element={<RoleRoute roles={['student']}><StudentReports /></RoleRoute>} />
          <Route path="env-check" element={<RoleRoute roles={['teacher', 'admin']}><EnvironmentCheckPage /></RoleRoute>} />

          <Route path="teacher" element={<RoleRoute roles={['teacher']}><TeacherHome /></RoleRoute>} />
          <Route path="classes" element={<RoleRoute roles={['teacher', 'admin']}><TeacherClasses /></RoleRoute>} />
          <Route path="class-scores" element={<RoleRoute roles={['teacher', 'admin']}><TeacherScores /></RoleRoute>} />
          <Route path="batch-reports" element={<RoleRoute roles={['teacher', 'admin']}><TeacherReports /></RoleRoute>} />

          <Route path="admin" element={<RoleRoute roles={['admin']}><AdminHome /></RoleRoute>} />
          <Route path="admin/config" element={<RoleRoute roles={['admin']}><AdminConfig /></RoleRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
