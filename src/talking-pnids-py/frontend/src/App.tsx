import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import AppPage from './pages/AppPage'
import LoginPage from './pages/LoginPage'

function useAuth() {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('auth') === '1')
  return { authed, login: () => setAuthed(true) }
}

export default function App() {
  const { authed, login } = useAuth()

  if (!authed) {
    return <LoginPage onLogin={login} />
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/app" element={<AppPage />} />
    </Routes>
  )
}
