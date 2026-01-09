'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface FileMapping {
  id: string
  pdf: string
  json: string
  name: string
  description: string
  pdfExists: boolean
  jsonExists: boolean
}

export default function AppPage() {
  const { user, logout } = useAuth()
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sessionStarted, setSessionStarted] = useState(false)
  const [startingSession, setStartingSession] = useState(false)
  const [mappings, setMappings] = useState<FileMapping[]>([])
  const [selectedMapping, setSelectedMapping] = useState<FileMapping | null>(null)
  const [loadingFiles, setLoadingFiles] = useState(true)

  useEffect(() => {
    loadFiles()
  }, [])

  const loadFiles = async () => {
    try {
      const response = await fetch('/api/files')
      const data = await response.json()
      setMappings(data.mappings || [])
    } catch (error) {
      console.error('Failed to load files:', error)
    } finally {
      setLoadingFiles(false)
    }
  }

  const handleFileSelect = (mapping: FileMapping) => {
    console.log('Selecting file mapping:', mapping, 'Current sessionStarted:', sessionStarted)
    setSelectedMapping(mapping)
    // Don't clear messages when switching files - keep session context
    // Ensure session remains started when selecting files
    if (!sessionStarted) {
      console.warn('File selected but session not started - this should not happen')
    }
    // Force session to remain started
    if (sessionStarted) {
      console.log('Session is started, keeping it that way')
    }
  }

  // Extract PID number from doc_id (e.g., "PID-0008" from "100478CP-N-PG-PP01-PR-PID-0008-001")
  const extractPidFromDocId = (docId: string): string | null => {
    const match = docId.match(/PID-(\d{4})/)
    return match ? `PID-${match[1]}` : null
  }

  // Extract PID number from a string (returns the 4-digit number part)
  const extractPidNumber = (str: string): string | null => {
    const match = str.match(/PID-(\d{4})/)
    return match ? match[1] : null // Returns "0008", "0006", etc.
  }

  // Find mapping by doc_id
  const findMappingByDocId = (docId: string): FileMapping | null => {
    const pidNumber = extractPidNumber(docId.trim())
    if (!pidNumber) return null
    
    // Find mapping where PDF filename contains the same PID number
    return mappings.find(m => {
      const pdfPidNumber = extractPidNumber(m.pdf)
      return pdfPidNumber === pidNumber
    }) || null
  }

  // Process message content to replace doc_id references with clickable links
  const processMessageContent = (content: string): string => {
    const processedIds = new Set<string>()
    let processed = content
    
    // Pattern 1: [doc_id:100478CP-N-PG-PP01-PR-PID-0006-001] (preferred format from LLM)
    processed = processed.replace(/\[doc_id:([^\]]+)\]/gi, (match, docId) => {
      const mapping = findMappingByDocId(docId.trim())
      if (mapping && !processedIds.has(docId)) {
        const pid = extractPidFromDocId(docId.trim()) || docId.trim()
        processedIds.add(docId)
        return `[${pid}](pid:${mapping.id})`
      }
      return match
    })
    
    // Pattern 2: [PID-0006] or [PID-006] (shorthand format)
    processed = processed.replace(/\[PID-(\d{3,4})\]/gi, (match, pidNum) => {
      // Pad with leading zeros if needed (e.g., "6" -> "0006", "006" -> "0006")
      const paddedPidNum = pidNum.padStart(4, '0')
      const pid = `PID-${paddedPidNum}`
      
      // Find mapping by PID number
      const mapping = mappings.find(m => {
        const pdfPidNumber = extractPidNumber(m.pdf)
        return pdfPidNumber === paddedPidNum
      })
      
      if (mapping && !processedIds.has(paddedPidNum)) {
        processedIds.add(paddedPidNum)
        return `[${pid}](pid:${mapping.id})`
      }
      return match
    })
    
    // Pattern 3: Legacy patterns (fallback for older responses)
    // Schema "100478CP-N-PG-PP01-PR-PID-0006-001": 
    processed = processed.replace(/Schema\s+"(100478CP-N-PG-PP01-PR-PID-\d{4}-\d{3})":/gi, (match, docId) => {
      if (processedIds.has(docId)) return match
      const mapping = findMappingByDocId(docId.trim())
      if (mapping) {
        const pid = extractPidFromDocId(docId.trim()) || docId.trim()
        processedIds.add(docId)
        return `Schema [${pid}](pid:${mapping.id}):`
      }
      return match
    })
    
    // Pattern 4: (doc_id: ...) format
    processed = processed.replace(/\(doc_id:\s*(100478CP-N-PG-PP01-PR-PID-\d{4}-\d{3})\)/gi, (match, docId) => {
      if (processedIds.has(docId)) return match
      const mapping = findMappingByDocId(docId.trim())
      if (mapping) {
        const pid = extractPidFromDocId(docId.trim()) || docId.trim()
        processedIds.add(docId)
        return `[${pid}](pid:${mapping.id})`
      }
      return match
    })
    
    // Pattern 5: Quoted doc IDs (fallback)
    processed = processed.replace(/"(\b100478CP-N-PG-PP01-PR-PID-\d{4}-\d{3}\b)"/gi, (match, docId) => {
      if (processedIds.has(docId)) return match
      const mapping = findMappingByDocId(docId.trim())
      if (mapping) {
        const pid = extractPidFromDocId(docId.trim()) || docId.trim()
        processedIds.add(docId)
        return `[${pid}](pid:${mapping.id})`
      }
      return match
    })
    
    return processed
  }

  // Handle click on PID links
  const handlePidLinkClick = (e: React.MouseEvent<HTMLButtonElement | HTMLAnchorElement>, href: string) => {
    // Prevent all default behaviors
    e.preventDefault()
    e.stopPropagation()
    
    // Prevent any form submission or navigation
    if (e.nativeEvent) {
      e.nativeEvent.preventDefault()
      e.nativeEvent.stopPropagation()
      e.nativeEvent.stopImmediatePropagation()
    }
    
    console.log('=== PID LINK CLICKED ===')
    console.log('Href:', href)
    console.log('Session started:', sessionStarted)
    console.log('Mappings count:', mappings.length)
    console.log('Mappings:', mappings.map(m => ({ id: m.id, name: m.name })))
    
    if (!href || !href.startsWith('pid:')) {
      console.error('Invalid href format:', href)
      return false
    }
    
    const mappingId = href.replace('pid:', '')
    console.log('Looking for mapping with ID:', mappingId)
    
    if (mappings.length === 0) {
      console.error('No mappings loaded!')
      return false
    }
    
    const mapping = mappings.find(m => m.id === mappingId)
    
    if (!mapping) {
      console.error('Mapping not found!', {
        requestedId: mappingId,
        availableIds: mappings.map(m => m.id)
      })
      return false
    }
    
    console.log('Found mapping:', mapping)
    console.log('Current selectedMapping:', selectedMapping?.id)
    
    // Directly set the mapping without setTimeout to avoid state issues
    setSelectedMapping(mapping)
    
    // Scroll the mapping into view
    requestAnimationFrame(() => {
      const sidebarItem = document.querySelector(`[data-mapping-id="${mapping.id}"]`)
      if (sidebarItem) {
        sidebarItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    })
    
    return false
  }

  const handleStartSession = async () => {
    setStartingSession(true)
    setMessages([]) // Clear any previous messages
    try {
      console.log('Starting session...')
      const response = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })

      console.log('Session response status:', response.status, response.ok)

      const data = await response.json().catch((parseError) => {
        console.error('Failed to parse response:', parseError)
        return { error: 'Failed to parse response' }
      })
      
      console.log('Session response data:', data)

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to start session`)
      }

      if (data.success) {
        console.log('Session started successfully, schemas loaded:', data.schemasLoaded)
        setSessionStarted(true)
        const initMessage: Message = {
          role: 'assistant',
          content: data.message || 'Session started. Ready to assist with plant operations and P&ID analysis.',
        }
        setMessages([initMessage])
      } else {
        throw new Error(data.error || 'Failed to start session')
      }
    } catch (error: any) {
      console.error('Session start error:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to start session. Please check the console for details and try again.'}`,
      }
      setMessages([errorMessage])
      setSessionStarted(false) // Ensure session state is reset on error
    } finally {
      setStartingSession(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading || !sessionStarted) return

    const userMessage: Message = { role: 'user', content: query }
    setMessages((prev) => [...prev, userMessage])
    setQuery('')
    setLoading(true)

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query,
          sessionStarted,
          selectedMapping: selectedMapping ? {
            id: selectedMapping.id,
            pdf: selectedMapping.pdf,
            json: selectedMapping.json
          } : null
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to process query')
      }
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer || data.error || 'Error: No answer received',
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to process query'}`,
      }
      setMessages((prev) => [...prev, errorMessage])
      console.error('Query error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      {/* Top Navigation */}
      <div className="top-nav">
        <div className="nav-brand">Talking P&IDs</div>
        {user && (
          <div className="nav-user">
            <span className="user-email">{user.email}</span>
            <button onClick={() => logout()} className="logout-button">
              Logout
            </button>
          </div>
        )}
      </div>

      <div className="panels-container">
        {/* Left Sidebar - 20% */}
        <div className="left-sidebar">
          <div className="sidebar-header">Files</div>
          <div className="sidebar-content">
            {loadingFiles ? (
              <div className="empty-state">Loading files...</div>
            ) : mappings.length === 0 ? (
              <div className="empty-state">No files found</div>
            ) : (
                  mappings.map((mapping) => (
                    <div
                      key={mapping.id}
                      data-mapping-id={mapping.id}
                      className={`sidebar-item ${selectedMapping?.id === mapping.id ? 'active' : ''}`}
                      onClick={() => handleFileSelect(mapping)}
                      title={mapping.description}
                    >
                  <span className="sidebar-icon">📄</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                    <span>{mapping.name}</span>
                    <span style={{ fontSize: '11px', opacity: 0.6 }}>
                      {!mapping.pdfExists || !mapping.jsonExists ? '⚠ ' : ''}
                      PDF + JSON
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Center Context Panel - 50% */}
        <div className="center-panel">
          <div className="main-header">
            <div className="main-title">Context</div>
          </div>
          <div className="center-panel-content">
            {/* PDF Viewer - 80% height */}
            <div className="pdf-viewer-container">
              {selectedMapping ? (
                selectedMapping.pdfExists ? (
                  <iframe
                    src={`/api/pdf/${encodeURIComponent(selectedMapping.pdf)}`}
                    className="pdf-viewer"
                    title={`PDF: ${selectedMapping.pdf}`}
                  />
                ) : (
                  <div className="empty-state">
                    <p>PDF file not found: {selectedMapping.pdf}</p>
                  </div>
                )
              ) : (
                <div className="empty-state">
                  <p>Select a file from the left panel to view PDF</p>
                </div>
              )}
            </div>

            {/* Details Panel - 20% height max */}
            <div className="details-panel-container">
              <div className="sidebar-header">Details</div>
              <div className="details-panel-content">
                {selectedMapping ? (
                  <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div>
                      <strong style={{ color: '#1a1a1a', fontSize: '14px' }}>{selectedMapping.name}</strong>
                      <div style={{ marginTop: '4px', fontSize: '12px', color: '#6b7280' }}>
                        {selectedMapping.description}
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>📄</span>
                        <span style={{ color: '#374151' }}>{selectedMapping.pdf}</span>
                        {!selectedMapping.pdfExists && (
                          <span style={{ fontSize: '11px', color: '#dc2626' }}>(Missing)</span>
                        )}
                      </div>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>📋</span>
                        <span style={{ color: '#374151' }}>{selectedMapping.json}</span>
                        {!selectedMapping.jsonExists && (
                          <span style={{ fontSize: '11px', color: '#dc2626' }}>(Missing)</span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    Select a file to view details
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Chat Panel - 30% */}
        <div className="right-sidebar">
          <div className="main-header">
            <div className="main-title">Chat</div>
          </div>
          <div className="main-content">
            <div className="chat-messages">
              {messages.length === 0 ? (
                <div className="empty-state">
                  <p>{sessionStarted ? 'Start a conversation about plant operations and P&IDs...' : 'Click "Start Session" to begin analyzing plant data and P&IDs'}</p>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={index} className={`message ${message.role}`}>
                    <div className="message-content">
                      {message.role === 'assistant' ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            a: ({ node, href, children, ...props }) => {
                              console.log('ReactMarkdown <a> component rendered:', { href, children: children?.toString() })
                              
                              if (href && href.startsWith('pid:')) {
                                const mappingId = href.replace('pid:', '')
                                console.log('Creating PID link span for mapping:', mappingId)
                                
                                const handleClick = (e: React.MouseEvent) => {
                                  console.log('=== PID LINK CLICKED ===', { mappingId, href })
                                  e.preventDefault()
                                  e.stopPropagation()
                                  
                                  console.log('Current mappings:', mappings.length)
                                  console.log('Current sessionStarted:', sessionStarted)
                                  
                                  const mapping = mappings.find(m => m.id === mappingId)
                                  console.log('Found mapping:', mapping)
                                  
                                  if (mapping) {
                                    console.log('Setting selected mapping to:', mapping.id)
                                    setSelectedMapping(mapping)
                                    
                                    requestAnimationFrame(() => {
                                      const sidebarItem = document.querySelector(`[data-mapping-id="${mapping.id}"]`)
                                      if (sidebarItem) {
                                        sidebarItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                                      }
                                    })
                                  } else {
                                    console.error('Mapping not found!', { mappingId, availableIds: mappings.map(m => m.id) })
                                  }
                                }
                                
                                return (
                                  <span
                                    role="button"
                                    tabIndex={0}
                                    onClick={handleClick}
                                    onMouseDown={(e) => {
                                      console.log('MouseDown on PID link')
                                      e.preventDefault()
                                    }}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault()
                                        e.stopPropagation()
                                        const mapping = mappings.find(m => m.id === mappingId)
                                        if (mapping) {
                                          setSelectedMapping(mapping)
                                        }
                                      }
                                    }}
                                    className="pid-link"
                                    style={{
                                      cursor: 'pointer',
                                      userSelect: 'none',
                                    }}
                                  >
                                    {children}
                                  </span>
                                )
                              }
                              return (
                                <a href={href} {...props}>
                                  {children}
                                </a>
                              )
                            },
                          }}
                        >
                          {(() => {
                            const processed = processMessageContent(message.content)
                            console.log('Processed message content:', processed)
                            console.log('Original message content:', message.content)
                            console.log('Contains pid: links?', processed.includes('pid:'))
                            return processed
                          })()}
                        </ReactMarkdown>
                      ) : (
                        message.content
                      )}
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="message assistant">
                  <div className="message-content">Processing...</div>
                </div>
              )}
            </div>
            <div className="chat-input-container">
              {!sessionStarted ? (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px' }}>
                  <button
                    onClick={handleStartSession}
                    className="start-session-button"
                    disabled={startingSession}
                  >
                    {startingSession ? 'Starting Session...' : 'Start Session'}
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="chat-input-form">
                  <textarea
                    className="chat-input"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask about plant operations, P&IDs, troubleshooting..."
                    rows={1}
                    disabled={loading}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSubmit(e)
                      }
                    }}
                  />
                  <button
                    type="submit"
                    className="send-button"
                    disabled={loading || !query.trim()}
                  >
                    Send
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
