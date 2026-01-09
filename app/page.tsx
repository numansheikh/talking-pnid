'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  const [redirecting, setRedirecting] = useState(true)

  useEffect(() => {
    router.push('/app')
    // Add a small delay to ensure router is ready
    const timer = setTimeout(() => {
      setRedirecting(false)
    }, 100)
    return () => clearTimeout(timer)
  }, [router])

  if (redirecting) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontFamily: 'system-ui, sans-serif'
      }}>
        <div>Loading...</div>
      </div>
    )
  }

  return null
}
