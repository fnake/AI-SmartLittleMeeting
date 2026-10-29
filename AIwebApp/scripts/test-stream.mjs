// 诊断脚本：直连后端 /chat/stream，打印每个数据块到达时间
const base = 'http://127.0.0.1:5000'

const g = await fetch(base + '/auth/guest', { method: 'POST' })
const guest = await g.json()
console.log('guest token:', guest.token)

const t0 = Date.now()
const res = await fetch(base + '/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Token: guest.token },
  body: JSON.stringify({ message: '请从1数到20，每个数字单独一行，不要其他内容' }),
})
console.log('status:', res.status)
console.log('content-type:', res.headers.get('content-type'))
console.log('transfer-encoding:', res.headers.get('transfer-encoding'))
console.log('--- chunks ---')

const reader = res.body.getReader()
const decoder = new TextDecoder()
let chunks = 0
let total = 0
for (;;) {
  const { done, value } = await reader.read()
  if (done) break
  chunks++
  total += value.length
  const text = decoder.decode(value, { stream: true })
  console.log(`+${String(Date.now() - t0).padStart(5)}ms  bytes=${String(value.length).padStart(4)}  ${JSON.stringify(text.slice(0, 60))}`)
}
console.log(`--- total: ${chunks} chunks, ${total} bytes, ${Date.now() - t0}ms ---`)
