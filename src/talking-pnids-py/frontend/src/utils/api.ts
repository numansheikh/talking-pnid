// Get API base URL from environment variable, default to relative path for local dev
// If a full URL is provided, ensure it ends with /api
let apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
if (apiBaseUrl.startsWith('http')) {
  // Remove trailing slash if present
  apiBaseUrl = apiBaseUrl.replace(/\/$/, '')
  // Add /api if not already present
  if (!apiBaseUrl.endsWith('/api')) {
    apiBaseUrl = `${apiBaseUrl}/api`
  }
}
const API_BASE_URL = apiBaseUrl

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

export interface FilesResponse {
  mappings: FileMapping[]
  availablePdfs: string[]
  availableJsons: string[]
  availableMds: string[]
}

export interface SessionResponse {
  success: boolean
  message: string
  markdownsLoaded: number
  sessionId: string
}

export interface QueryRequest {
  query: string
  sessionStarted: boolean
  selectedMapping: {
    id: string
    pdf: string
    md: string
  } | null
  sessionId?: string | null
}

export interface QueryResponse {
  answer: string
  error?: string
}

export async function fetchFiles(): Promise<FilesResponse> {
  const response = await fetch(`${API_BASE_URL}/files`)
  if (!response.ok) {
    throw new Error('Failed to load files')
  }
  return response.json()
}

export async function startSession(): Promise<SessionResponse> {
  const response = await fetch(`${API_BASE_URL}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ error: 'Failed to start session' }))
    throw new Error(data.error || `HTTP ${response.status}: Failed to start session`)
  }
  return response.json()
}

export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ error: 'Failed to process query' }))
    throw new Error(data.error || 'Failed to process query')
  }
  return response.json()
}

export function getPdfUrl(filename: string): string {
  return `${API_BASE_URL}/pdf/${encodeURIComponent(filename)}`
}
