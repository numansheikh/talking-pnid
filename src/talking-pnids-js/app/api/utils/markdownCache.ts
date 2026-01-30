import fs from 'fs/promises'
import path from 'path'

interface MarkdownFile {
  filename: string
  content: string
  mtime: Date
}

interface MarkdownSummary {
  filename: string
  preview: string
  size: number
}

const cache: {
  markdowns: Map<string, MarkdownFile>
  summaries: MarkdownSummary[] | null
  lastLoaded: number | null
  mdsPath: string | null
} = {
  markdowns: new Map(),
  summaries: null,
  lastLoaded: null,
  mdsPath: null,
}

async function loadConfig() {
  const configPath = path.join(process.cwd(), 'config', 'config.json')
  let config: any = {
    directories: {
      mds: process.env.MDS_DIR || './data/mds',
    },
  }

  try {
    const configData = await fs.readFile(configPath, 'utf-8')
    const fileConfig = JSON.parse(configData)
    config = {
      directories: {
        mds: process.env.MDS_DIR || fileConfig.directories?.mds || config.directories.mds,
      },
    }
  } catch (error: any) {
    if (error.code !== 'ENOENT') {
      console.warn('Error reading config file:', error.message)
    }
  }

  return config
}

function createMarkdownSummary(content: string, filename: string): MarkdownSummary {
  // Get first 500 characters as preview
  const preview = content.substring(0, 500).replace(/\n/g, ' ').trim()
  return {
    filename,
    preview,
    size: content.length,
  }
}

export async function getAllMarkdowns(): Promise<string[]> {
  const config = await loadConfig()
  let mdsPath = config.directories.mds
  if (mdsPath.startsWith('./')) {
    mdsPath = mdsPath.substring(2)
  }
  const fullPath = path.join(process.cwd(), mdsPath)

  // Check if path changed
  if (cache.mdsPath !== fullPath) {
    cache.mdsPath = fullPath
    cache.markdowns.clear()
    cache.summaries = null
  }

  try {
    const files = await fs.readdir(fullPath)
    const mdFiles = files.filter((f) => f.endsWith('.md'))

    const markdowns: string[] = []
    const now = Date.now()

    for (const file of mdFiles) {
      const filePath = path.join(fullPath, file)

      // Check if we need to reload this file
      let needsReload = true
      if (cache.markdowns.has(file)) {
        const cached = cache.markdowns.get(file)!
        try {
          const stats = await fs.stat(filePath)
          if (stats.mtime.getTime() === cached.mtime.getTime()) {
            needsReload = false
            markdowns.push(cached.content)
          }
        } catch {
          // File might have been deleted, remove from cache
          cache.markdowns.delete(file)
        }
      }

      if (needsReload) {
        const content = await fs.readFile(filePath, 'utf-8')
        const stats = await fs.stat(filePath)

        // Cache the markdown
        cache.markdowns.set(file, {
          filename: file,
          content,
          mtime: stats.mtime,
        })

        markdowns.push(content)
      }
    }

    // Invalidate summaries cache if markdowns changed
    cache.summaries = null
    cache.lastLoaded = now

    return markdowns
  } catch (error: any) {
    console.error('Error loading markdown files:', error)
    return []
  }
}

async function loadFileMappings() {
  const mappingsPath = path.join(process.cwd(), 'config', 'file-mappings.json')
  try {
    const content = await fs.readFile(mappingsPath, 'utf-8')
    return JSON.parse(content)
  } catch (error) {
    return { mappings: [] }
  }
}

async function saveFileMappings(mappings: any) {
  const mappingsPath = path.join(process.cwd(), 'config', 'file-mappings.json')
  try {
    await fs.writeFile(mappingsPath, JSON.stringify(mappings, null, 2), 'utf-8')
    return true
  } catch (error: any) {
    console.error('Error saving file mappings:', error)
    return false
  }
}

export async function getMarkdownSummaries(): Promise<MarkdownSummary[]> {
  // If summaries are cached and markdowns haven't changed, return cached summaries
  if (cache.summaries) {
    return cache.summaries
  }

  // Load file mappings to check for existing summaries
  const fileMappings = await loadFileMappings()
  const mappings = fileMappings.mappings || []
  
  // Load all markdowns (which will update cache)
  await getAllMarkdowns()

  const summaries: MarkdownSummary[] = []
  let needsUpdate = false

  // For each markdown file, check if summary exists in mappings
  for (const cached of cache.markdowns.values()) {
    // Find mapping by md filename
    const mapping = mappings.find((m: any) => m.md === cached.filename)
    
    // Check if summary exists and if file size matches (simple validation)
    const hasValidSummary = mapping && 
                            mapping.summary && 
                            mapping.summary.preview && 
                            mapping.summary.size &&
                            mapping.summary.size === cached.content.length
    
    if (hasValidSummary) {
      // Use existing summary from file-mappings.json
      summaries.push({
        filename: cached.filename,
        preview: mapping.summary.preview,
        size: mapping.summary.size,
      })
    } else {
      // Generate new summary
      const summary = createMarkdownSummary(cached.content, cached.filename)
      summaries.push(summary)
      
      // Update the mapping with the new summary
      if (mapping) {
        // Preserve all existing mapping fields, just add/update summary
        if (!mapping.summary) {
          mapping.summary = {}
        }
        mapping.summary.preview = summary.preview
        mapping.summary.size = summary.size
        needsUpdate = true
      } else {
        // No mapping found for this file, create a minimal one
        // Note: This shouldn't happen if file-mappings.json is properly maintained
        console.warn(`No mapping found for ${cached.filename}, creating minimal entry`)
        mappings.push({
          id: `pid-${cached.filename.replace('.md', '')}`,
          md: cached.filename,
          name: `P&ID ${cached.filename.replace('.md', '')}`,
          description: `Piping & Instrumentation Diagram ${cached.filename.replace('.md', '')}`,
          summary: {
            preview: summary.preview,
            size: summary.size,
          },
        })
        needsUpdate = true
      }
    }
  }

  // Save updated mappings if any summaries were generated
  if (needsUpdate) {
    fileMappings.mappings = mappings
    await saveFileMappings(fileMappings)
    console.log('Updated file-mappings.json with markdown summaries')
  }

  // Cache summaries in memory
  cache.summaries = summaries

  return summaries
}

export async function getMarkdownByFilename(filename: string): Promise<string | null> {
  const config = await loadConfig()
  let mdsPath = config.directories.mds
  if (mdsPath.startsWith('./')) {
    mdsPath = mdsPath.substring(2)
  }
  const fullPath = path.join(process.cwd(), mdsPath)

  // Check cache first
  if (cache.markdowns.has(filename)) {
    const cached = cache.markdowns.get(filename)!
    const filePath = path.join(fullPath, filename)
    try {
      const stats = await fs.stat(filePath)
      if (stats.mtime.getTime() === cached.mtime.getTime()) {
        return cached.content
      }
    } catch {
      // File might have been deleted
      cache.markdowns.delete(filename)
    }
  }

  // Load from disk
  const filePath = path.join(fullPath, filename)
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    const stats = await fs.stat(filePath)

    // Cache it
    cache.markdowns.set(filename, {
      filename,
      content,
      mtime: stats.mtime,
    })

    return content
  } catch (error: any) {
    console.error(`Error loading markdown file ${filename}:`, error)
    return null
  }
}
