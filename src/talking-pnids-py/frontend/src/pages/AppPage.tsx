import { useState, useEffect, useCallback } from 'react'
// import { useAuth } from '../contexts/AuthContext'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchFiles, startSession, sendQuery, getPdfUrl, type FileMapping } from '../utils/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function AppPage() {
  // Login disabled for now
  // const { user, logout } = useAuth()
  const user = { email: 'user@example.com', name: 'User' }
  const logout = () => {}
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sessionStarted, setSessionStarted] = useState(false)
  const [startingSession, setStartingSession] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [mappings, setMappings] = useState<FileMapping[]>([])
  const [selectedMapping, setSelectedMapping] = useState<FileMapping | null>(null)
  const [loadingFiles, setLoadingFiles] = useState(true)

  useEffect(() => {
    loadFiles()
  }, [])

  // Global click handler to intercept PID links before navigation
  useEffect(() => {
    const handleGlobalClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      
      // Check if clicked element or its parent has data-pid-link attribute (for HTML spans)
      const pidLink = target.closest('[data-pid-link]') as HTMLElement
      if (pidLink) {
        e.preventDefault()
        e.stopPropagation()
        e.stopImmediatePropagation()
        
        const mappingId = pidLink.getAttribute('data-pid-link')
        if (mappingId) {
          const mapping = mappings.find(m => m.id === mappingId)
          if (mapping) {
            setSelectedMapping(mapping)
            requestAnimationFrame(() => {
              const sidebarItem = document.querySelector(`[data-mapping-id="${mapping.id}"]`)
              if (sidebarItem) {
                sidebarItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
              }
            })
          } else {
            console.error('Global handler: Mapping not found for ID:', mappingId, 'Available IDs:', mappings.map(m => m.id))
          }
        }
        return false
      }
      
      // Also check for any link with href starting with pid: or #pid- (for markdown links)
      const link = target.closest('a[href^="pid:"], a[href^="#pid-"]') as HTMLAnchorElement
      if (link) {
        e.preventDefault()
        e.stopPropagation()
        e.stopImmediatePropagation()
        
        const href = link.getAttribute('href')
        if (href) {
          const mappingId = href.replace(/^(pid:?\/?\/?|#pid-)/, '')
          const mapping = mappings.find(m => m.id === mappingId)
          if (mapping) {
            setSelectedMapping(mapping)
            requestAnimationFrame(() => {
              const sidebarItem = document.querySelector(`[data-mapping-id="${mapping.id}"]`)
              if (sidebarItem) {
                sidebarItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
              }
            })
          }
        }
        return false
      }
    }

    // Use capture phase to catch events early
    document.addEventListener('click', handleGlobalClick, true)
    
    return () => {
      document.removeEventListener('click', handleGlobalClick, true)
    }
  }, [mappings])

  const loadFiles = async () => {
    try {
      const data = await fetchFiles()
      setMappings(data.mappings || [])
    } catch (error) {
      console.error('Failed to load files:', error)
    } finally {
      setLoadingFiles(false)
    }
  }

  const handleFileSelect = (mapping: FileMapping) => {
    setSelectedMapping(mapping)
    if (!sessionStarted) {
      console.warn('File selected but session not started - this should not happen')
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
        return `[${pid}](#pid-${mapping.id})`
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
        return `[${pid}](#pid-${mapping.id})`
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
        return `[${pid}](#pid-${mapping.id})`
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
        return `[${pid}](#pid-${mapping.id})`
      }
      return match
    })
    
    // Pattern 6: Plain PID-XXXX text (without brackets) - must be at word boundaries
    // Use markdown link format but with code formatting to prevent autolinking
    processed = processed.replace(/\bPID-(\d{3,4})\b/gi, (match, pidNum) => {
      // Skip if already processed or if it's part of a markdown link
      if (processedIds.has(`plain-${pidNum}`)) return match
      if (match.includes('](') || match.includes('[') || match.includes('`')) return match
      
      // Pad with leading zeros if needed
      const paddedPidNum = pidNum.padStart(4, '0')
      const pid = `PID-${paddedPidNum}`
      
      // Find mapping by PID number
      const mapping = mappings.find(m => {
        const pdfPidNumber = extractPidNumber(m.pdf)
        return pdfPidNumber === paddedPidNum
      })
      
      if (mapping) {
        processedIds.add(`plain-${pidNum}`)
        // Use hash-based format that ReactMarkdown will parse as a link
        // Our handler will intercept it
        return `[${pid}](#pid-${mapping.id})`
      }
      return match
    })
    
    return processed
  }

  // Handle click on PID links - wrapped in useCallback for stability
  const handlePidLinkClick = useCallback((mappingId: string) => {
    return (e: React.MouseEvent) => {
      // Prevent ALL default behaviors and propagation
      e.preventDefault()
      e.stopPropagation()
      if (e.nativeEvent) {
        e.nativeEvent.preventDefault()
        e.nativeEvent.stopPropagation()
        if (e.nativeEvent.stopImmediatePropagation) {
          e.nativeEvent.stopImmediatePropagation()
        }
      }
      
      if (mappings.length === 0) {
        console.error('No mappings loaded!')
        return
      }
      
      const mapping = mappings.find(m => m.id === mappingId)
      
      if (!mapping) {
        console.error('Mapping not found!', {
          requestedId: mappingId,
          availableIds: mappings.map(m => m.id)
        })
        return
      }
      
      // Set the selected mapping
      setSelectedMapping(mapping)
      
      // Scroll the mapping into view in the sidebar
      requestAnimationFrame(() => {
        const sidebarItem = document.querySelector(`[data-mapping-id="${mapping.id}"]`)
        if (sidebarItem) {
          sidebarItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      })
    }
  }, [mappings, setSelectedMapping])

  const handleStartSession = async () => {
    setStartingSession(true)
    setMessages([]) // Clear any previous messages
    try {
      const data = await startSession()

      if (data.success) {
        setSessionStarted(true)
        setSessionId(data.sessionId || null)
        const initMessage: Message = {
          role: 'assistant',
          content: data.message || 'Session started. Ready to assist with plant operations and P&ID analysis.',
        }
        setMessages([initMessage])
      } else {
        throw new Error('Failed to start session')
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
      const data = await sendQuery({
        query,
        sessionStarted,
        selectedMapping: selectedMapping ? {
          id: selectedMapping.id,
          pdf: selectedMapping.pdf,
          md: selectedMapping.md
        } : null,
        sessionId: sessionId
      })
      
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
                      {!mapping.pdfExists || !mapping.mdExists ? '⚠ ' : ''}
                      PDF + MD
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
                    src={getPdfUrl(selectedMapping.pdf)}
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
                        <span style={{ color: '#374151' }}>{selectedMapping.md}</span>
                        {!selectedMapping.mdExists && (
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
            <div 
              className="chat-messages"
              onClick={(e) => {
                // Prevent any link navigation in chat messages
                const target = e.target as HTMLElement
                if (target.tagName === 'A' && target.getAttribute('href')?.startsWith('pid:')) {
                  e.preventDefault()
                  e.stopPropagation()
                }
              }}
            >
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
                          rehypePlugins={[]}
                          components={{
                            // Handle HTML spans with data-pid-link
                            span: ({ node, className, ...props }: any) => {
                              if (className === 'pid-link' && props['data-pid-link']) {
                                const mappingId = props['data-pid-link']
                                const clickHandler = handlePidLinkClick(mappingId)
                                return (
                                  <span
                                    {...props}
                                    className="pid-link"
                                    onClick={clickHandler}
                                    onMouseDown={(e) => {
                                      e.preventDefault()
                                      e.stopPropagation()
                                    }}
                                    style={{
                                      cursor: 'pointer',
                                      userSelect: 'none',
                                      display: 'inline-flex',
                                    }}
                                  />
                                )
                              }
                              return <span {...props} />
                            },
                            a: ({ node, href, children, ...props }) => {
                              // Handle PID links - check for both pid: and #pid- formats
                              if (href && (href.startsWith('pid:') || href.startsWith('pid://') || href.startsWith('#pid-'))) {
                                const mappingId = href.replace(/^(pid:?\/?\/?|#pid-)/, '')
                                const clickHandler = handlePidLinkClick(mappingId)
                                
                                // Return span instead of anchor to prevent any URL resolution
                                return (
                                  <span
                                    role="button"
                                    tabIndex={0}
                                    onClick={clickHandler}
                                    onMouseDown={(e) => {
                                      e.preventDefault()
                                      e.stopPropagation()
                                    }}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault()
                                        e.stopPropagation()
                                        clickHandler(e as any)
                                      }
                                    }}
                                    className="pid-link"
                                    style={{
                                      cursor: 'pointer',
                                      userSelect: 'none',
                                      display: 'inline-flex',
                                      textDecoration: 'none',
                                    }}
                                    data-pid-link={mappingId}
                                    data-href={href}
                                  >
                                    {children}
                                  </span>
                                )
                              }
                              // For regular links, ensure they open in new tab
                              return (
                                <a href={href} {...props} target="_blank" rel="noopener noreferrer" onClick={(e) => {
                                  // Only prevent default if it's a relative link that might cause navigation
                                  if (href && !href.startsWith('http') && !href.startsWith('mailto:') && !href.startsWith('#')) {
                                    e.preventDefault()
                                  }
                                }}>
                                  {children}
                                </a>
                              )
                            },
                          }}
                        >
                          {processMessageContent(message.content)}
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
