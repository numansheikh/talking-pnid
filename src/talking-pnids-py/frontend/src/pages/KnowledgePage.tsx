import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './KnowledgePage.css'

interface KnowledgeEntry {
  id: string
  title: string
  content: string
  created_at: string
  updated_at: string
  page_count?: number
}

export default function KnowledgePage() {
  const navigate = useNavigate()
  const [knowledge, setKnowledge] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState({ id: '', title: '', content: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    loadKnowledge()
  }, [])

  const loadKnowledge = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/api/knowledge')
      if (!response.ok) throw new Error('Failed to load knowledge')
      const data = await response.json()
      setKnowledge(data.entries)
      setError('')
    } catch (err) {
      setError(`Error loading knowledge: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateNew = () => {
    setEditingId(null)
    setFormData({ id: '', title: '', content: '' })
  }

  const handleEdit = (entry: KnowledgeEntry) => {
    setEditingId(entry.id)
    setFormData({
      id: entry.id,
      title: entry.title,
      content: entry.content
    })
  }

  const handleSave = async () => {
    if (!formData.id || !formData.title || !formData.content) {
      setError('Please fill in all fields')
      return
    }

    try {
      setLoading(true)
      const method = editingId ? 'PUT' : 'POST'
      const url = editingId
        ? `http://localhost:8000/api/knowledge/${editingId}`
        : 'http://localhost:8000/api/knowledge'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: formData.id,
          title: formData.title,
          content: formData.content
        })
      })

      if (!response.ok) throw new Error('Failed to save knowledge')
      
      setSuccess(`Knowledge "${formData.title}" saved successfully!`)
      setEditingId(null)
      setFormData({ id: '', title: '', content: '' })
      loadKnowledge()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(`Error saving knowledge: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this entry?')) return

    try {
      setLoading(true)
      const response = await fetch(`http://localhost:8000/api/knowledge/${id}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to delete knowledge')
      
      setSuccess('Knowledge entry deleted successfully!')
      loadKnowledge()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(`Error deleting knowledge: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const calculatePages = (text: string) => {
    const wordCount = text.split(/\s+/).length
    return Math.max(1, Math.ceil(wordCount / 400))
  }

  return (
    <div className="knowledge-page">
      <div className="knowledge-header">
        <button 
          className="back-button"
          onClick={() => navigate('/app')}
          title="Go back to chat"
        >
          ← Back to Chat
        </button>
        <h1>📚 Knowledge Base Management</h1>
        <p>Manage your knowledge entries to provide context to GPT 5.2</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="content-layout">
        {/* List Section */}
        <div className="knowledge-list-section">
          <div className="section-header">
            <h2>Your Knowledge Entries ({knowledge.length})</h2>
            <button 
              className="btn btn-primary"
              onClick={handleCreateNew}
              disabled={loading}
            >
              + Add New Knowledge
            </button>
          </div>

          <div className="knowledge-list">
            {knowledge.length === 0 ? (
              <div className="empty-state">
                <p>No knowledge entries yet. Create one to get started!</p>
              </div>
            ) : (
              knowledge.map(entry => (
                <div
                  key={entry.id}
                  className={`knowledge-card ${editingId === entry.id ? 'active' : ''}`}
                  onClick={() => handleEdit(entry)}
                >
                  <div className="card-header">
                    <h3>{entry.title}</h3>
                    <span className="page-badge">{entry.page_count} pages</span>
                  </div>
                  <p className="card-preview">{entry.content.substring(0, 100)}...</p>
                  <div className="card-meta">
                    <small>Updated: {new Date(entry.updated_at).toLocaleDateString()}</small>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Editor Section */}
        <div className="knowledge-editor-section">
          {editingId !== null || formData.id !== '' ? (
            <div className="editor-form">
              <h2>{editingId ? 'Edit Knowledge' : 'Create New Knowledge'}</h2>
              
              <div className="form-group">
                <label htmlFor="id">Unique ID *</label>
                <input
                  id="id"
                  type="text"
                  placeholder="e.g., operating-procedures, system-specs"
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                  disabled={editingId !== null}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="title">Title *</label>
                <input
                  id="title"
                  type="text"
                  placeholder="e.g., System Operating Procedures"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="content">Content *</label>
                <textarea
                  id="content"
                  placeholder="Paste your knowledge content here... (100+ pages supported)"
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  className="form-textarea"
                  rows={12}
                />
                {formData.content && (
                  <div className="content-stats">
                    <small>
                      {formData.content.split(/\s+/).length} words • {calculatePages(formData.content)} pages
                    </small>
                  </div>
                )}
              </div>

              <div className="form-actions">
                <button
                  className="btn btn-primary"
                  onClick={handleSave}
                  disabled={loading || !formData.id || !formData.title || !formData.content}
                >
                  {loading ? 'Saving...' : editingId ? 'Update Knowledge' : 'Create Knowledge'}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setEditingId(null)
                    setFormData({ id: '', title: '', content: '' })
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                {editingId && (
                  <button
                    className="btn btn-danger"
                    onClick={() => {
                      handleDelete(editingId)
                      setEditingId(null)
                      setFormData({ id: '', title: '', content: '' })
                    }}
                    disabled={loading}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-editor">
              <h2>Create or Edit Knowledge</h2>
              <p>Select a knowledge entry from the list to edit it, or create a new one.</p>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleCreateNew}
              >
                Create Your First Knowledge Entry
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Info Section */}
      <div className="knowledge-info">
        <h3>💡 How to Use</h3>
        <ul>
          <li><strong>Create Entries:</strong> Paste your knowledge/context text with a title and unique ID</li>
          <li><strong>Page Calculation:</strong> Approximately 400 words = 1 page</li>
          <li><strong>GPT Integration:</strong> All knowledge entries are automatically included when querying GPT 5.2</li>
          <li><strong>Multiple Files:</strong> Create separate entries for different documents/topics</li>
          <li><strong>Context Memory:</strong> GPT will remember and use all stored knowledge in its analysis</li>
        </ul>
      </div>
    </div>
  )
}
