import { Routes, Route, Navigate } from 'react-router-dom'
// import { useAuth } from './contexts/AuthContext'
// import LoginPage from './pages/LoginPage'
// import SignupPage from './pages/SignupPage'
import AppPage from './pages/AppPage'

// Login disabled - all routes are public for now
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/app" element={<AppPage />} />
      {/* Login routes disabled for now */}
      {/* <Route path="/login" element={<LoginPage />} /> */}
      {/* <Route path="/signup" element={<SignupPage />} /> */}
    </Routes>
  )
}
