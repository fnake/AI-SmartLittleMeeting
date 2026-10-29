import { createRequire } from 'node:module'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))


// Electron 运行时会拦截 require('electron') 返回主进程 API；
// 裸 ESM 具名导入会被 node_modules/electron（仅导出 exe 路径）劫持而报错
const require = createRequire(import.meta.url)
const { app, BrowserWindow, Menu } = require('electron')

// 移除默认应用菜单栏（File/Edit/View/Window）
Menu.setApplicationMenu(null)

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    title: '小会',
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#ffffff',
      symbolColor: '#1f1f1f',
      height: 44,
    },
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
    },
  })

  // 开发模式加载 Vite dev server；打包/构建后加载 dist/index.html
  if (process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
