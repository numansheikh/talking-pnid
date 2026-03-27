import { useState, FormEvent } from 'react'

const VALID_USER = 'pnid'
const VALID_PASS = 'pakistan'

export default function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (username === VALID_USER && password === VALID_PASS) {
      sessionStorage.setItem('auth', '1')
      onLogin()
    } else {
      setError('Invalid username or password')
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#fffbf7',
    }}>
      <div style={{
        background: '#fff',
        border: '1px solid #fed7aa',
        borderRadius: '12px',
        padding: '40px',
        width: '340px',
        boxShadow: '0 4px 24px rgba(249,115,22,0.08)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <img src="/logo.svg" alt="Talking P&IDs" style={{ width: '48px', height: '48px', marginBottom: '12px' }} />
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#1c1917' }}>Talking P&IDs</div>
          <div style={{ fontSize: '13px', color: '#78716c', marginTop: '4px' }}>Sign in to continue</div>
        </div>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#57534e', marginBottom: '6px' }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={e => { setUsername(e.target.value); setError('') }}
              autoFocus
              style={{
                width: '100%',
                padding: '9px 12px',
                border: '1px solid #e7d5c0',
                borderRadius: '7px',
                fontSize: '14px',
                outline: 'none',
                boxSizing: 'border-box',
                background: '#fafafa',
              }}
            />
          </div>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#57534e', marginBottom: '6px' }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => { setPassword(e.target.value); setError('') }}
              style={{
                width: '100%',
                padding: '9px 12px',
                border: '1px solid #e7d5c0',
                borderRadius: '7px',
                fontSize: '14px',
                outline: 'none',
                boxSizing: 'border-box',
                background: '#fafafa',
              }}
            />
          </div>
          {error && (
            <div style={{ fontSize: '13px', color: '#dc2626', marginBottom: '14px', textAlign: 'center' }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            style={{
              width: '100%',
              padding: '10px',
              background: 'linear-gradient(135deg, #fb923c, #f97316)',
              color: '#fff',
              border: 'none',
              borderRadius: '7px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  )
}
