// Get API base URL from environment, ensuring it ends with /api
let apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
// If a full URL is provided, ensure it ends with /api
if (apiBaseUrl.startsWith('http')) {
  // Remove trailing slash if present
  apiBaseUrl = apiBaseUrl.replace(/\/$/, '')
  // Add /api if not already present
  if (!apiBaseUrl.endsWith('/api')) {
    apiBaseUrl = `${apiBaseUrl}/api`
  }
}
const API_BASE_URL = apiBaseUrl

// Debug: Log the API base URL (only in development or if explicitly enabled)
if (import.meta.env.DEV || import.meta.env.VITE_DEBUG_API) {
  console.log('API Base URL:', API_BASE_URL)
  console.log('VITE_API_BASE_URL env:', import.meta.env.VITE_API_BASE_URL)
}

export interface FileMapping {
  id: string
  pdf: string
  json?: string
  md: string
  name: string
  description: string
  pdfExists: boolean
  jsonExists?: boolean
  mdExists: boolean
}

export interface SessionResponse {
  success: boolean
  message: string
  markdownsLoaded?: number
  sessionId?: string
  error?: string
}

export interface QueryResponse {
  answer: string
  error?: string
}

class ApiService {
  async getFiles(): Promise<{ mappings: FileMapping[] }> {
    const response = await fetch(`${API_BASE_URL}/files`)
    if (!response.ok) {
      throw new Error('Failed to load files')
    }
    return response.json()
  }

  async startSession(): Promise<SessionResponse> {
    const response = await fetch(`${API_BASE_URL}/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to start session')
    }
    
    return response.json()
  }

  async query(
    query: string,
    sessionStarted: boolean,
    selectedMapping: { id: string; pdf: string; md: string } | null
  ): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        sessionStarted,
        selectedMapping,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to process query')
    }

    return response.json()
  }

  getPdfUrl(filename: string): string {
    return `${API_BASE_URL}/pdf/${encodeURIComponent(filename)}`
  }
}

export const apiService = new ApiService()
