import { useState, useEffect, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchFiles, startSession, sendQuery, getPdfUrl, type FileMapping, type QuerySources } from '../utils/api'

type SourceMode = 'graph' | 'rag' | 'both'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: QuerySources
}

export default function AppPage() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sessionStarted, setSessionStarted] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [mappings, setMappings] = useState<FileMapping[]>([])
  const [selectedMapping, setSelectedMapping] = useState<FileMapping | null>(null)
  const [sourceMode, setSourceMode] = useState<SourceMode>('both')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  // Load files and auto-start session on mount
  useEffect(() => {
    const init = async () => {
      try {
        const data = await fetchFiles()
        const loadedMappings = data.mappings || []
        setMappings(loadedMappings)
        if (loadedMappings.length > 0) setSelectedMapping(loadedMappings[0])
      } catch (error: any) {
        setMessages([{
          role: 'assistant',
          content: `**Backend not reachable.** Make sure the server is running on port 8050.\n\nError: ${error.message}`
        }])
        return
      }

      try {
        const session = await startSession()
        if (session.success) {
          setSessionStarted(true)
          setSessionId(session.sessionId || null)
          setMessages([{ role: 'assistant', content: session.message || 'Ready. Select a diagram and ask a question.' }])
        }
      } catch (error: any) {
        setMessages([{ role: 'assistant', content: `Session error: ${error.message}` }])
      }
    }
    init()
  }, [])

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Intercept PID links in chat (global capture)
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const pidLink = (e.target as HTMLElement).closest('[data-pid-link]') as HTMLElement
      if (pidLink) {
        e.preventDefault(); e.stopPropagation()
        const id = pidLink.getAttribute('data-pid-link')
        const mapping = mappings.find(m => m.id === id)
        if (mapping) setSelectedMapping(mapping)
        return
      }
      const link = (e.target as HTMLElement).closest('a[href^="#pid-"]') as HTMLAnchorElement
      if (link) {
        e.preventDefault(); e.stopPropagation()
        const id = link.getAttribute('href')?.replace('#pid-', '')
        const mapping = mappings.find(m => m.id === id)
        if (mapping) setSelectedMapping(mapping)
      }
    }
    document.addEventListener('click', handleClick, true)
    return () => document.removeEventListener('click', handleClick, true)
  }, [mappings])

  const extractPidNumber = (str: string | null | undefined) => str?.match(/PID-(\d{3,4})/)?.[1] ?? null

  const processMessageContent = (content: string): string => {
    const seen = new Set<string>()
    let out = content

    out = out.replace(/\[doc_id:([^\]]+)\]/gi, (match, docId) => {
      const pid = docId.match(/PID-(\d{4})/)?.[1]
      if (!pid) return match
      const mapping = mappings.find(m => extractPidNumber(m.pdf) === pid)
      if (mapping && !seen.has(pid)) { seen.add(pid); return `[PID-${pid}](#pid-${mapping.id})` }
      return match
    })

    out = out.replace(/\[PID-(\d{3,4})\]/gi, (match, num) => {
      const padded = num.padStart(4, '0')
      const mapping = mappings.find(m => extractPidNumber(m.pdf) === padded)
      if (mapping && !seen.has(padded)) { seen.add(padded); return `[PID-${padded}](#pid-${mapping.id})` }
      return match
    })

    out = out.replace(/\bPID-(\d{3,4})\b/gi, (match, num) => {
      if (seen.has(`p${num}`)) return match
      const padded = num.padStart(4, '0')
      const mapping = mappings.find(m => extractPidNumber(m.pdf) === padded)
      if (mapping) { seen.add(`p${num}`); return `[PID-${padded}](#pid-${mapping.id})` }
      return match
    })

    return out
  }

  const handlePidClick = useCallback((id: string) => (e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation()
    const mapping = mappings.find(m => m.id === id)
    if (mapping) setSelectedMapping(mapping)
  }, [mappings])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading || !sessionStarted) return

    const userMsg: Message = { role: 'user', content: query }
    setMessages(prev => [...prev, userMsg])
    setQuery('')
    setLoading(true)

    try {
      const sourcesParam = sourceMode === 'graph' ? ['graph'] : sourceMode === 'rag' ? ['rag'] : ['graph', 'rag']
      abortRef.current = new AbortController()
      const data = await sendQuery({
        query,
        sessionStarted,
        selectedMapping: selectedMapping ? { id: selectedMapping.id, pdf: selectedMapping.pdf, md: selectedMapping.md } : null,
        sessionId,
        sources: sourcesParam,
      }, abortRef.current.signal)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || data.error || 'No answer received',
        sources: data.sources,
      }])
    } catch (error: any) {
      if (error.name === 'AbortError') return
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${error.message}` }])
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
  }

  const handleCopy = useCallback((content: string, index: number) => {
    const done = () => { setCopiedIndex(index); setTimeout(() => setCopiedIndex(null), 2000) }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(content).then(done).catch(() => {
        // Fallback for non-secure contexts
        const el = document.createElement('textarea')
        el.value = content
        document.body.appendChild(el)
        el.select()
        document.execCommand('copy')
        document.body.removeChild(el)
        done()
      })
    } else {
      const el = document.createElement('textarea')
      el.value = content
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      done()
    }
  }, [])

  const handleEdit = useCallback((content: string, index: number) => {
    setQuery(content)
    setMessages(prev => prev.slice(0, index))
    setTimeout(() => textareaRef.current?.focus(), 50)
  }, [])

  const sourceModeLabel = (mode: SourceMode) => ({ graph: 'Diagram Analysis', rag: 'Engineering Notes', both: 'Full Picture' }[mode])

  return (
    <div className="app-container">
      {/* Top Nav */}
      <div className="top-nav">
        <div className="nav-brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <img src="/logo.svg" alt="Talking P&IDs" style={{ height: '28px', width: 'auto' }} />
          Talking P&IDs
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#6b7280' }}>
          {selectedMapping && <span>{selectedMapping.name}</span>}
        </div>
      </div>

      <div className="panels-container">
        {/* Left Sidebar — P&ID list */}
        <div className="left-sidebar">
          <div className="sidebar-header">Diagrams</div>
          <div className="sidebar-content">
            {mappings.length === 0 ? (
              <div className="empty-state">Loading…</div>
            ) : (
              mappings.map(mapping => (
                <div
                  key={mapping.id}
                  data-mapping-id={mapping.id}
                  className={`sidebar-item ${selectedMapping?.id === mapping.id ? 'active' : ''}`}
                  onClick={() => setSelectedMapping(mapping)}
                  title={mapping.description}
                >
                  <span className="sidebar-icon">{mapping.id === 'supergraph' ? '🔗' : '📐'}</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                    <span>{mapping.name}</span>
                    <span style={{ fontSize: '11px', opacity: 0.55 }}>{mapping.description}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Center — PDF Viewer */}
        <div className="center-panel">
          <div className="main-header">
            <div className="main-title">{selectedMapping?.name ?? 'Select a diagram'}</div>
          </div>
          <div className="center-panel-content">
            <div className="pdf-viewer-container">
              {selectedMapping?.id === 'supergraph' ? (
                <div className="empty-state" style={{ textAlign: 'left', padding: '24px', maxWidth: '480px', margin: '0 auto' }}>
                  <p style={{ fontWeight: 600, fontSize: '15px', marginBottom: '8px' }}>All P&IDs — Overview</p>
                  <p style={{ color: '#6b7280', fontSize: '13px', marginBottom: '16px' }}>
                    Querying across the full supergraph: PID-006, PID-007, and PID-008 combined.
                    Ask cross-diagram questions such as:
                  </p>
                  <ul style={{ color: '#374151', fontSize: '13px', lineHeight: '1.8', paddingLeft: '20px' }}>
                    <li>How does the Scraper Launcher connect to the Fuel Gas KO Drum?</li>
                    <li>List all pressure safety valves across all diagrams</li>
                    <li>What are all the spec breaks between systems?</li>
                    <li>Trace the fuel gas flow from DS-3 to PP01-362-V001</li>
                  </ul>
                </div>
              ) : selectedMapping?.pdfExists ? (
                <iframe
                  src={getPdfUrl(selectedMapping.pdf)}
                  className="pdf-viewer"
                  title={selectedMapping.pdf}
                />
              ) : (
                <div className="empty-state">
                  <p>{selectedMapping ? `PDF not found: ${selectedMapping.pdf}` : 'Select a diagram to view'}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right — Chat */}
        <div className="right-sidebar">
          <div className="main-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div className="main-title">Chat</div>
            {/* Source selector */}
            <div style={{ display: 'flex', gap: '4px' }}>
              {(['graph', 'rag', 'both'] as SourceMode[]).map(mode => (
                <button
                  key={mode}
                  onClick={() => setSourceMode(mode)}
                  style={{
                    fontSize: '11px',
                    padding: '3px 8px',
                    borderRadius: '12px',
                    border: '1px solid',
                    cursor: 'pointer',
                    borderColor: sourceMode === mode ? '#f97316' : '#d1d5db',
                    background: sourceMode === mode ? '#f97316' : 'transparent',
                    color: sourceMode === mode ? '#fff' : '#6b7280',
                    fontWeight: sourceMode === mode ? 600 : 400,
                  }}
                >
                  {mode === 'graph' ? 'Diagram' : mode === 'rag' ? 'Notes' : 'Both'}
                </button>
              ))}
            </div>
          </div>

          <div className="main-content">
            <div className="chat-messages">
              {messages.length === 0 ? (
                <div className="empty-state">
                  <p>Select a diagram and ask a question.</p>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={index} className={`message ${message.role}`}>
                    <div className="message-content">
                      {message.role === 'assistant' ? (
                        <>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '4px' }}>
                            <button
                              onClick={() => handleCopy(message.content, index)}
                              title="Copy to clipboard"
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                fontSize: '11px', color: copiedIndex === index ? '#16a34a' : '#9ca3af',
                                padding: '2px 6px', borderRadius: '4px',
                                transition: 'color 0.2s',
                              }}
                            >
                              {copiedIndex === index ? '✓ copied' : '⎘ copy'}
                            </button>
                          </div>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              table: ({ children }) => (
                                <div className="table-wrap">
                                  <table>{children}</table>
                                </div>
                              ),
                              a: ({ href, children, ...props }) => {
                                if (href?.startsWith('#pid-')) {
                                  const id = href.replace('#pid-', '')
                                  return (
                                    <span
                                      role="button"
                                      tabIndex={0}
                                      className="pid-link"
                                      data-pid-link={id}
                                      onClick={handlePidClick(id)}
                                      style={{ cursor: 'pointer', textDecoration: 'underline', color: '#f97316' }}
                                    >
                                      {children}
                                    </span>
                                  )
                                }
                                return <a href={href} {...props} target="_blank" rel="noopener noreferrer">{children}</a>
                              },
                            }}
                          >
                            {processMessageContent(message.content)}
                          </ReactMarkdown>

                          {/* Source callout */}
                          {message.sources && (
                            <div style={{
                              marginTop: '8px',
                              padding: '6px 10px',
                              borderRadius: '6px',
                              background: '#f3f4f6',
                              fontSize: '11px',
                              color: '#6b7280',
                              display: 'flex',
                              flexWrap: 'wrap',
                              gap: '6px',
                              alignItems: 'center',
                            }}>
                              <span style={{ fontWeight: 600, color: '#374151' }}>
                                {message.sources.mode === 'graph' ? '📐 Diagram Analysis' :
                                 message.sources.mode === 'reasoning+graph' ? '📐 Diagram Analysis' :
                                 '📄 Markdown'}
                              </span>
                              {message.sources.tools_called && message.sources.tools_called.length > 0 && (
                                <span>· tools: {message.sources.tools_called.join(', ')}</span>
                              )}
                              {message.sources.graph_nodes && message.sources.graph_nodes.length > 0 && (
                                <span>· nodes: {message.sources.graph_nodes.slice(0, 5).join(', ')}{message.sources.graph_nodes.length > 5 ? ` +${message.sources.graph_nodes.length - 5}` : ''}</span>
                              )}
                              {message.sources.rag_chunks && message.sources.rag_chunks.length > 0 && (
                                <span>· 📝 {message.sources.rag_chunks.map(c => c.replace('.docx', '')).join(', ')}</span>
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        <>
                          {message.content}
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                            <button
                              onClick={() => handleEdit(message.content, index)}
                              title="Edit message"
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                fontSize: '11px', color: 'rgba(255,255,255,0.75)',
                                padding: '2px 6px', borderRadius: '4px',
                              }}
                            >
                              ✎ edit
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="message assistant">
                  <div className="message-content" style={{ color: '#9ca3af', fontStyle: 'italic' }}>Thinking…</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-container">
              <form onSubmit={handleSubmit} className="chat-input-form">
                <textarea
                  ref={textareaRef}
                  className="chat-input"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder={sessionStarted ? `Ask about ${selectedMapping?.name ?? 'this diagram'}…` : 'Initialising…'}
                  rows={1}
                  disabled={loading || !sessionStarted}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) }
                  }}
                />
                {loading ? (
                  <button
                    type="button"
                    onClick={handleStop}
                    className="send-button"
                    style={{ background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', boxShadow: '0 4px 6px -1px rgba(239,68,68,0.25)' }}
                  >
                    ■
                  </button>
                ) : (
                  <button type="submit" className="send-button" disabled={!query.trim() || !sessionStarted}>
                    →
                  </button>
                )}
              </form>
              <div style={{ textAlign: 'right', fontSize: '10px', color: '#9ca3af', padding: '2px 4px 0' }}>
                {sourceModeLabel(sourceMode)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
