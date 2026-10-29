// 端到端验证新端点 GET /topics/{id}/messages
const base = 'http://127.0.0.1:5000'
const g = await fetch(base + '/auth/guest', { method: 'POST' })
const { token } = await g.json()
const H = { 'Content-Type': 'application/json', Token: token }

const r1 = await fetch(base + '/chat', {
  method: 'POST', headers: H,
  body: JSON.stringify({ message: '用一句话解释递归' }),
})
const c1 = await r1.json()
await fetch(base + '/chat', {
  method: 'POST', headers: H,
  body: JSON.stringify({ message: '再给一个递归的代码例子', topic_id: c1.topic_id }),
})

const res = await fetch(`${base}/topics/${c1.topic_id}/messages`, { headers: H })
console.log('status:', res.status)
const data = await res.json()
console.log('topic:', JSON.stringify(data.topic))
for (const m of data.messages) {
  console.log(` #${m.id} [${m.role}] ${m.content.slice(0, 30)} (${m.created_at})`)
}
console.log('共', data.messages.length, '条，顺序:', data.messages.map((x) => x.role).join(' -> '))

// 越权校验：另一个游客访问该话题应 404
const g2 = await fetch(base + '/auth/guest', { method: 'POST' })
const t2 = await g2.json()
const res2 = await fetch(`${base}/topics/${c1.topic_id}/messages`, {
  headers: { Token: t2.token },
})
console.log('他人访问同话题 status:', res2.status)
