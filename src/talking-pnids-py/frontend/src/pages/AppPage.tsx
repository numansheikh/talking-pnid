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

  const extractPidNumber = (str: string) => str.match(/PID-(\d{3,4})/)?.[1] ?? null

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
      const data = await sendQuery({
        query,
        sessionStarted,
        selectedMapping: selectedMapping ? { id: selectedMapping.id, pdf: selectedMapping.pdf, md: selectedMapping.md } : null,
        sessionId,
        sources: sourcesParam,
      })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || data.error || 'No answer received',
        sources: data.sources,
      }])
    } catch (error: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${error.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const sourceModeLabel = (mode: SourceMode) => ({ graph: 'Diagram Analysis', rag: 'Engineering Notes', both: 'Full Picture' }[mode])

  return (
    <div className="app-container">
      {/* Top Nav */}
      <div className="top-nav">
        <div className="nav-brand">Talking P&IDs</div>
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
                  <span className="sidebar-icon">📐</span>
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
              {selectedMapping?.pdfExists ? (
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
                    borderColor: sourceMode === mode ? '#2563eb' : '#d1d5db',
                    background: sourceMode === mode ? '#2563eb' : 'transparent',
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
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
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
                                      style={{ cursor: 'pointer', textDecoration: 'underline', color: '#2563eb' }}
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
                        message.content
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
                <button type="submit" className="send-button" disabled={loading || !query.trim() || !sessionStarted}>
                  {loading ? '…' : '→'}
                </button>
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
