import { createReadStream } from 'node:fs'
import { cp, mkdir, readdir, rm, stat } from 'node:fs/promises'
import path from 'node:path'

function isPathInside(parent, candidate) {
  const relative = path.relative(parent, candidate)
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
}

function assertSafeOutputDirectory(repoRoot, outDir, sourceDirectories) {
  if (!isPathInside(repoRoot, outDir)) {
    throw new Error(`Diretório de build inseguro: ${outDir}.`)
  }
  for (const sourceDirectory of sourceDirectories) {
    if (
      outDir === sourceDirectory
      || isPathInside(sourceDirectory, outDir)
      || isPathInside(outDir, sourceDirectory)
    ) {
      throw new Error(`Diretório de build conflita com fonte publicada: ${outDir}.`)
    }
  }
}

export async function copyStatePublicAssets({
  repoRoot,
  sharedPublicDirectory,
  publicDataDirectory,
  outDir,
}) {
  const resolvedOutput = path.resolve(outDir)
  assertSafeOutputDirectory(
    path.resolve(repoRoot),
    resolvedOutput,
    [path.resolve(sharedPublicDirectory), path.resolve(publicDataDirectory)],
  )
  await mkdir(resolvedOutput, { recursive: true })

  const sharedEntries = await readdir(sharedPublicDirectory, { withFileTypes: true })
  for (const entry of sharedEntries) {
    if (entry.name === 'data') continue
    await cp(
      path.join(sharedPublicDirectory, entry.name),
      path.join(resolvedOutput, entry.name),
      { recursive: true, force: true },
    )
  }

  const outputDataDirectory = path.join(resolvedOutput, 'data')
  await rm(outputDataDirectory, { recursive: true, force: true })
  await cp(publicDataDirectory, outputDataDirectory, { recursive: true, force: true })
}

function contentType(filePath) {
  switch (path.extname(filePath).toLocaleLowerCase('en-US')) {
    case '.json': return 'application/json; charset=utf-8'
    case '.svg': return 'image/svg+xml'
    case '.png': return 'image/png'
    case '.jpg':
    case '.jpeg': return 'image/jpeg'
    case '.webp': return 'image/webp'
    case '.pdf': return 'application/pdf'
    case '.csv': return 'text/csv; charset=utf-8'
    default: return 'application/octet-stream'
  }
}

export function resolveStateDataRequestPath(publicDataDirectory, requestUrl) {
  const rawPathname = String(requestUrl || '/').split(/[?#]/, 1)[0]
  let pathname
  try {
    pathname = decodeURIComponent(rawPathname)
  } catch {
    throw new Error('Caminho de dados possui codificação inválida.')
  }
  if (pathname !== '/data' && !pathname.startsWith('/data/')) return null
  const relativePath = pathname.slice('/data'.length).replace(/^\/+/, '')
  if (!relativePath) return undefined
  const resolvedRoot = path.resolve(publicDataDirectory)
  const resolvedPath = path.resolve(resolvedRoot, relativePath)
  if (!isPathInside(resolvedRoot, resolvedPath)) {
    throw new Error('Caminho de dados deve permanecer dentro da publicação estadual.')
  }
  return resolvedPath
}

async function serveStateDataRequest(req, res, publicDataDirectory) {
  let filePath
  try {
    filePath = resolveStateDataRequestPath(publicDataDirectory, req.url)
  } catch (error) {
    res.statusCode = 400
    res.end(error.message)
    return true
  }
  if (filePath === null) return false
  if (filePath === undefined || !['GET', 'HEAD'].includes(req.method || 'GET')) {
    res.statusCode = filePath === undefined ? 404 : 405
    res.end()
    return true
  }

  try {
    const fileStat = await stat(filePath)
    if (!fileStat.isFile()) {
      res.statusCode = 404
      res.end()
      return true
    }
    res.statusCode = 200
    res.setHeader('Content-Type', contentType(filePath))
    res.setHeader('Content-Length', String(fileStat.size))
    if (req.method === 'HEAD') {
      res.end()
      return true
    }
    const stream = createReadStream(filePath)
    stream.on('error', () => {
      if (!res.headersSent) res.statusCode = 500
      res.end()
    })
    stream.pipe(res)
    return true
  } catch (error) {
    if (error?.code !== 'ENOENT') {
      res.statusCode = 500
      res.end()
      return true
    }
    res.statusCode = 404
    res.end()
    return true
  }
}

export function statePublicAssetsPlugin(profile) {
  if (!profile.publicDataDirectory) {
    throw new Error(`Publicação estadual ausente para ${profile.stateCode}.`)
  }
  let resolvedConfig
  return {
    name: 'state-public-assets',
    configResolved(config) {
      resolvedConfig = config
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        serveStateDataRequest(req, res, profile.publicDataDirectory)
          .then((handled) => {
            if (!handled) next()
          })
          .catch(next)
      })
    },
    async closeBundle() {
      if (resolvedConfig.command !== 'build' || resolvedConfig.mode === 'app-only') return
      await copyStatePublicAssets({
        repoRoot: profile.repoRoot,
        sharedPublicDirectory: profile.sharedPublicDirectory,
        publicDataDirectory: profile.publicDataDirectory,
        outDir: path.resolve(profile.repoRoot, resolvedConfig.build.outDir),
      })
    },
  }
}
