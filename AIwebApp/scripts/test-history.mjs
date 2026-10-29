// 端到端验证：聊天后用 /memory/search 还原话题历史
const base = 'http://127.0.0.1:5000'
const g = await fetch(base + '/auth/guest', { method: 'POST' })
const { token } = await g.json()
const H = { 'Content-Type': 'application/json', Token: token }

// 第一轮：自动建话题
const r1 = await fetch(base + '/chat', {
  method: 'POST', headers: H,
  body: JSON.stringify({ message: '什么是闭包？用一句话回答' }),
})
const c1 = await r1.json()
console.log('话题ID:', c1.topic_id)

// 第二轮：同话题续聊
await fetch(base + '/chat', {
  method: 'POST', headers: H,
  body: JSON.stringify({ message: '再举一个闭包的例子', topic_id: c1.topic_id }),
})

// 还原历史：以标题（首条消息前20字）为查询词
const title = '什么是闭包？用一句话回答'.slice(0, 20)
const m = await fetch(base + '/memory/search', {
  method: 'POST', headers: H,
  body: JSON.stringify({ query: title, top_k: 20 }),
})
const { results } = await m.json()
const history = results
  .filter((h) => h.topic_id === c1.topic_id)
  .sort((a, b) => (a.created_at ?? '').localeCompare(b.created_at ?? ''))
console.log('还原出的历史消息:')
for (const h of history) {
  console.log(` [${h.role}] ${h.content.slice(0, 40)} (${h.created_at})`)
}
console.log('共', history.length, '条')
