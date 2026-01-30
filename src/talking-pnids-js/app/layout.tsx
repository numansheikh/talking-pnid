import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from './contexts/AuthContext'

export const metadata: Metadata = {
  title: 'Talking P&IDs',
  description: 'AI-powered Q&A for Piping & Instrumentation Diagrams',
  icons: {
    icon: '/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
