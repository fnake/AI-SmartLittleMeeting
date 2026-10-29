// 开发启动器：先起 Vite dev server，端口就绪后拉起 Electron 窗口
// 不依赖 concurrently / wait-on，避免额外安装依赖
import { createRequire } from 'node:module'
import { spawn } from 'node:child_process'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const PORT = 5173
const DEV_URL = `http://127.0.0.1:${PORT}/`

// Vite 8 的 exports 不再暴露 ./bin/vite.js，改由 package.json 定位
const viteBin = path.join(path.dirname(require.resolve('vite/package.json')), 'bin', 'vite.js')
const vite = spawn(process.execPath, [viteBin], {
  cwd: root,
  stdio: 'inherit',
  env: process.env,
})

async function waitForServer(url, timeoutMs = 30000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 300))
  }
  return false
}

const ok = await waitForServer(DEV_URL)
if (!ok) {
  console.error('[desktop] Vite dev server failed to start in time')
  vite.kill()
  process.exit(1)
}

const electronCli = path.join(path.dirname(require.resolve('electron/package.json')), 'cli.js')
// ELECTRON_RUN_AS_NODE 会让 electron.exe 降级为纯 Node（无任何 Electron API），必须剔除
const electronEnv = { ...process.env, VITE_DEV_SERVER_URL: DEV_URL }
delete electronEnv.ELECTRON_RUN_AS_NODE
const electron = spawn(process.execPath, [electronCli, '.'], {
  cwd: root,
  stdio: 'inherit',
  env: electronEnv,
})

electron.on('exit', (code) => {
  vite.kill()
  process.exit(code ?? 0)
})

function shutdown() {
  vite.kill()
  electron.kill()
  process.exit(0)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
