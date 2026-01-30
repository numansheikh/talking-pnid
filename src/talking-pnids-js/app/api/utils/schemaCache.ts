import fs from 'fs/promises'
import path from 'path'

interface CachedSchema {
  schema: any
  summary: any
  mtime: Date
}

interface SchemaCache {
  schemas: Map<string, CachedSchema>
  summaries: any[] | null
  lastLoaded: number | null
  jsonsPath: string | null
}

// Module-level cache
const cache: SchemaCache = {
  schemas: new Map(),
  summaries: null,
  lastLoaded: null,
  jsonsPath: null,
}

async function loadConfig() {
  const configPath = path.join(process.cwd(), 'config', 'config.json')
  let config: any = {
    openai: {
      model: process.env.OPENAI_MODEL || 'gpt-4',
    },
    directories: {
      pdfs: process.env.PDFS_DIR || './data/pdfs',
      jsons: process.env.JSONS_DIR || './data/jsons',
    },
    settings: {
      maxTokens: parseInt(process.env.MAX_TOKENS || '2000', 10),
      temperature: parseFloat(process.env.TEMPERATURE || '0.7'),
    },
  }

  try {
    const configData = await fs.readFile(configPath, 'utf-8')
    const fileConfig = JSON.parse(configData)
    // Merge file config with defaults (file config takes precedence, but env vars override)
    config = {
      openai: {
        model: process.env.OPENAI_MODEL || fileConfig.openai?.model || config.openai.model,
      },
      directories: {
        pdfs: process.env.PDFS_DIR || fileConfig.directories?.pdfs || config.directories.pdfs,
        jsons: process.env.JSONS_DIR || fileConfig.directories?.jsons || config.directories.jsons,
      },
      settings: {
        maxTokens: parseInt(process.env.MAX_TOKENS || fileConfig.settings?.maxTokens?.toString() || '2000', 10),
        temperature: parseFloat(process.env.TEMPERATURE || fileConfig.settings?.temperature?.toString() || '0.7'),
      },
    }
  } catch (error: any) {
    // File doesn't exist or can't be read - use defaults from env vars
    if (error.code !== 'ENOENT') {
      console.warn('Error reading config file:', error.message)
    }
  }

  return config
}

function createSchemaSummary(schema: any) {
  const metadata = schema.metadata || {}
  const nodes = schema.nodes || []
  const nodeTypeCounts: Record<string, number> = {}
  const equipment: any[] = []
  const instruments: any[] = []

  nodes.forEach((node: any) => {
    const type = node.type || 'unknown'
    nodeTypeCounts[type] = (nodeTypeCounts[type] || 0) + 1

    if (type === 'equipment') {
      equipment.push({
        id: node.id,
        tag: node.tag,
        subtype: node.subtype,
        service: node.service,
      })
    } else if (type === 'instrument') {
      instruments.push({
        id: node.id,
        tag: node.tag,
        subtype: node.subtype,
      })
    }
  })

  const edges = schema.edges || []

  return {
    metadata: {
      doc_id: metadata.doc_id,
      rev: metadata.rev,
      plant: metadata.plant,
      unit: metadata.unit,
      status: metadata.status,
    },
    summary: {
      total_nodes: nodes.length,
      total_edges: edges.length,
      node_types: nodeTypeCounts,
      equipment_count: equipment.length,
      instruments_count: instruments.length,
    },
    key_equipment: equipment.slice(0, 10),
    key_instruments: instruments.slice(0, 10),
  }
}

export async function getAllSchemas(): Promise<any[]> {
  const config = await loadConfig()
  let jsonsPath = config.directories.jsons
  if (jsonsPath.startsWith('./')) {
    jsonsPath = jsonsPath.substring(2)
  }
  const fullPath = path.join(process.cwd(), jsonsPath)

  // Check if path changed
  if (cache.jsonsPath !== fullPath) {
    cache.jsonsPath = fullPath
    cache.schemas.clear()
    cache.summaries = null
  }

  try {
    const files = await fs.readdir(fullPath)
    const jsonFiles = files.filter((f) => f.endsWith('.json'))

    const schemas: any[] = []
    const now = Date.now()

    for (const file of jsonFiles) {
      const filePath = path.join(fullPath, file)

      // Check if we need to reload this file
      let needsReload = true
      if (cache.schemas.has(file)) {
        const cached = cache.schemas.get(file)!
        try {
          const stats = await fs.stat(filePath)
          if (stats.mtime.getTime() === cached.mtime.getTime()) {
            needsReload = false
            schemas.push(cached.schema)
          }
        } catch {
          // File might have been deleted, remove from cache
          cache.schemas.delete(file)
        }
      }

      if (needsReload) {
        const content = await fs.readFile(filePath, 'utf-8')
        const schema = JSON.parse(content)
        const stats = await fs.stat(filePath)

        // Cache the schema
        cache.schemas.set(file, {
          schema,
          summary: createSchemaSummary(schema),
          mtime: stats.mtime,
        })

        schemas.push(schema)
      }
    }

    // Invalidate summaries cache if schemas changed
    cache.summaries = null
    cache.lastLoaded = now

    return schemas
  } catch (error: any) {
    console.error('Error loading JSON schemas:', error)
    return []
  }
}

export async function getSchemaSummaries(): Promise<any[]> {
  // If summaries are cached and schemas haven't changed, return cached summaries
  if (cache.summaries) {
    return cache.summaries
  }

  // Load all schemas (which will update cache)
  await getAllSchemas()

  // Generate summaries from cached schemas
  cache.summaries = Array.from(cache.schemas.values()).map((cached) => cached.summary)

  return cache.summaries
}

export async function getSchemaByFilename(filename: string): Promise<any | null> {
  const config = await loadConfig()
  let jsonsPath = config.directories.jsons
  if (jsonsPath.startsWith('./')) {
    jsonsPath = jsonsPath.substring(2)
  }
  const fullPath = path.join(process.cwd(), jsonsPath)
  const filePath = path.join(fullPath, filename)

  // Check cache first
  if (cache.schemas.has(filename)) {
    const cached = cache.schemas.get(filename)!
    try {
      const stats = await fs.stat(filePath)
      if (stats.mtime.getTime() === cached.mtime.getTime()) {
        return cached.schema
      }
    } catch {
      cache.schemas.delete(filename)
    }
  }

  // Load and cache
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    const schema = JSON.parse(content)
    const stats = await fs.stat(filePath)

    cache.schemas.set(filename, {
      schema,
      summary: createSchemaSummary(schema),
      mtime: stats.mtime,
    })

    // Invalidate summaries cache
    cache.summaries = null

    return schema
  } catch (error) {
    console.error('Error loading JSON schema:', filename, error)
    return null
  }
}
