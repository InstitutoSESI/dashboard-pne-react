import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ALLOWED_COMMANDS = new Set(['serve', 'build', 'preview'])
const repoRoot = fileURLToPath(new URL('..', import.meta.url))

export function parseStateViteArguments(argv) {
  const [command, rawState, ...viteArguments] = argv
  if (!ALLOWED_COMMANDS.has(command)) {
    throw new Error('Comando Vite inválido; use serve, build ou preview.')
  }
  const stateCode = String(rawState ?? '').trim().toUpperCase()
  if (!/^[A-Z]{2}$/.test(stateCode)) {
    throw new Error('UF inválida; informe exatamente duas letras.')
  }
  return { command, stateCode, viteArguments }
}

export function runStateVite(argv = process.argv.slice(2)) {
  const { command, stateCode, viteArguments } = parseStateViteArguments(argv)
  const viteEntry = path.join(repoRoot, 'node_modules', 'vite', 'bin', 'vite.js')
  if (!existsSync(viteEntry)) {
    throw new Error('Vite não instalado. Execute npm ci antes deste comando.')
  }
  const child = spawn(
    process.execPath,
    [viteEntry, command, ...viteArguments],
    {
      cwd: repoRoot,
      env: { ...process.env, PLATFORM_STATE: stateCode },
      stdio: 'inherit',
    },
  )
  child.once('error', (error) => {
    console.error(error.message)
    process.exitCode = 1
  })
  child.once('exit', (code, signal) => {
    if (signal) {
      console.error(`Vite encerrado pelo sinal ${signal}.`)
      process.exitCode = 1
      return
    }
    process.exitCode = code ?? 1
  })
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : ''
if (invokedPath === fileURLToPath(import.meta.url)) {
  try {
    runStateVite()
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error))
    process.exitCode = 2
  }
}
