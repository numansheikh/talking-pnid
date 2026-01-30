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

// Debug mode - can be enabled via VITE_DEBUG_API=true or in development
// Check for both string 'true' and boolean true, and also check if it's not explicitly 'false'
const DEBUG_API = (import.meta.env.VITE_DEBUG_API === 'true' || 
                   import.meta.env.VITE_DEBUG_API === true ||
                   (import.meta.env.VITE_DEBUG_API && import.meta.env.VITE_DEBUG_API !== 'false')) ||
                   import.meta.env.DEV

// Always log API base URL (helpful for debugging production issues)
// Using console.error so it shows up even if console.log is filtered
console.error('═══════════════════════════════════════')
console.error('🔗 API CONFIGURATION DEBUG')
console.error('🔗 API Base URL:', API_BASE_URL)
console.error('🔗 VITE_API_BASE_URL (raw):', import.meta.env.VITE_API_BASE_URL || '(NOT SET - THIS IS THE PROBLEM!)')
console.error('🔗 Will call:', API_BASE_URL + '/files')
console.error('═══════════════════════════════════════')

if (DEBUG_API) {
  console.log('🔍 API Debug Info:')
  console.log('  - API Base URL:', API_BASE_URL)
  console.log('  - VITE_API_BASE_URL env:', import.meta.env.VITE_API_BASE_URL)
  console.log('  - Environment:', import.meta.env.MODE)
  console.log('  - Dev mode:', import.meta.env.DEV)
  console.log('  - DEBUG_API enabled:', true)
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
  private async fetchWithDebug(url: string, options?: RequestInit) {
    if (DEBUG_API) {
      console.log(`🌐 API Request:`, {
        url,
        method: options?.method || 'GET',
        body: options?.body,
      })
    }

    try {
      const response = await fetch(url, options)
      
      if (DEBUG_API) {
        console.log(`📥 API Response:`, {
          url,
          status: response.status,
          statusText: response.statusText,
          ok: response.ok,
        })
      }

      if (!response.ok) {
        const errorText = await response.text()
        if (DEBUG_API) {
          console.error(`❌ API Error:`, {
            url,
            status: response.status,
            error: errorText,
          })
        }
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      return response
    } catch (error) {
      if (DEBUG_API) {
        console.error(`💥 API Request Failed:`, {
          url,
          error: error instanceof Error ? error.message : String(error),
        })
      }
      throw error
    }
  }

  async getFiles(): Promise<{ mappings: FileMapping[] }> {
    const url = `${API_BASE_URL}/files`
    
    // Always log the URL being called (helps debug production issues)
    console.error('🚨 API CALL DEBUG - getFiles URL:', url)
    console.error('🚨 API_BASE_URL value:', API_BASE_URL)
    console.error('🚨 VITE_API_BASE_URL env:', import.meta.env.VITE_API_BASE_URL || 'NOT SET!')
    
    const response = await this.fetchWithDebug(url)
    
    // Check if response is actually JSON
    const contentType = response.headers.get('content-type')
    if (!contentType || !contentType.includes('application/json')) {
      const text = await response.text()
      console.error('❌ Received non-JSON response!')
      console.error('❌ Content-Type:', contentType)
      console.error('❌ Response preview:', text.substring(0, 200))
      throw new Error(`API returned HTML instead of JSON. Check if VITE_API_BASE_URL is set correctly. URL called: ${url}`)
    }
    
    const data = await response.json()
    
    if (DEBUG_API) {
      console.log('📋 Files Response:', data)
    }
    
    return data
  }

  async startSession(): Promise<SessionResponse> {
    const url = `${API_BASE_URL}/session`
    const response = await this.fetchWithDebug(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    
    const data = await response.json()
    
    if (DEBUG_API) {
      console.log('🚀 Session Response:', data)
    }
    
    return data
  }

  async query(
    query: string,
    sessionStarted: boolean,
    selectedMapping: { id: string; pdf: string; md: string } | null
  ): Promise<QueryResponse> {
    const url = `${API_BASE_URL}/query`
    const body = JSON.stringify({
      query,
      sessionStarted,
      selectedMapping,
    })
    
    const response = await this.fetchWithDebug(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    
    const data = await response.json()
    
    if (DEBUG_API) {
      console.log('💬 Query Response:', data)
    }
    
    return data
  }

  getPdfUrl(filename: string): string {
    const url = `${API_BASE_URL}/pdf/${encodeURIComponent(filename)}`
    if (DEBUG_API) {
      console.log('📄 PDF URL:', url)
    }
    return url
  }
}

export const apiService = new ApiService()
