const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function http(path, opts = {}) {
  const url = `${base}${path}`
  return fetch(url, {
    method: opts.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers || {})
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    cache: 'no-store'
  }).then(async (r) => {
    const txt = await r.text()
    let data
    try { data = txt ? JSON.parse(txt) : null } catch { data = txt }
    if (!r.ok) throw new Error(data?.detail || r.statusText || 'Request failed')
    return data
  })
}

export function getNews(limit = 50, lang = 'ta') {
  const p = new URLSearchParams({ limit: String(limit), lang: String(lang), _t: String(Date.now()) })
  return http(`/news/?${p.toString()}`)
}

export function triggerFetch() {
  return http('/admin/fetch', { method: 'POST' })
}
