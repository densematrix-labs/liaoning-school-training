import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import StudentScores from './pages/student/Scores'
import StudentAbility from './pages/student/Ability'
import StudentReports from './pages/student/Reports'
import StudentEnvCheck from './pages/student/EnvCheck'
import TeacherClasses from './pages/teacher/Classes'
import TeacherScores from './pages/teacher/Scores'
import TeacherReports from './pages/teacher/Reports'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          {/* Student Routes */}
          <Route index element={<Navigate to="/scores" replace />} />
          <Route path="scores" element={<StudentScores />} />
          <Route path="ability" element={<StudentAbility />} />
          <Route path="reports" element={<StudentReports />} />
          <Route path="env-check" element={<StudentEnvCheck />} />
          
          {/* Teacher Routes */}
          <Route path="classes" element={<TeacherClasses />} />
          <Route path="class-scores" element={<TeacherScores />} />
          <Route path="batch-reports" element={<TeacherReports />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
