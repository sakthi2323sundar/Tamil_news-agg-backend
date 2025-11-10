import React, { useEffect, useMemo, useState } from 'react'
import { getNews } from '../lib/api'
import NewsCard from '../components/NewsCard.jsx'
import Loader from '../components/Loader.jsx'

export default function Home({ activeFilter = 'all', lang = 'ta' }) {
  const [limit, setLimit] = useState(50)
  const [query, setQuery] = useState('')
  const [view, setView] = useState('grid') // 'grid' | 'list'
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getNews(limit, lang)
      .then((data) => {
        if (!active) return
        setNews(Array.isArray(data) ? data : [])
      })
      .catch((e) => {
        if (!active) return
        setError(e?.message || 'Failed to load news')
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [limit, lang])

  const filtered = useMemo(() => {
    const textMatch = (n, q) => [n.title, n.description, n.summary, n.source]
      .filter(Boolean)
      .some((t) => String(t).toLowerCase().includes(q))

    // naive keyword-based category mapping
    const categoryMap = {
      all: [],
      world: ['world','உலக','இஸ்ரேல்','பாகிஸ்தான்','சீனா','அமெரிக்கா','இங்கிலாந்து','யூரோப்','ஆப்ரிக்கா','ஆசியா'],
      business: ['business','வணிக','பங்குச்சந்தை','ஷேர்','நிறுவனம்','வருவாய்','சந்தை','பொருளாதாரம்'],
      tech: ['tech','தொழில்நுட்ப','ஐடி','ஆப்','அப்','மொபைல்','ஸ்மார்ட்போன்','ஏஐ','AI','சாப்ட்','சாஃப்ட்வேர்'],
      sports: ['sports','விளையாட்டு','கிரிக்கெட்','ஐபிஎல்','ஃபுட்பால்','கால்பந்து','டென்னிஸ்']
    }

    const applyFilter = (arr) => {
      if (activeFilter === 'all') return arr
      const keys = categoryMap[activeFilter] || []
      if (!keys.length) return arr
      return arr.filter((n) => keys.some((k) => textMatch(n, String(k).toLowerCase())))
    }

    let arr = news
    // apply category first
    arr = applyFilter(arr)
    // then search query
    if (query.trim()) {
      const q = query.toLowerCase()
      arr = arr.filter((n) => textMatch(n, q))
    }
    return arr
  }, [news, query, activeFilter])

  // Uniform grid view (5 per row with responsive breakpoints)

  return (
    <section>
      <div className="toolbar">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="செய்திகளை தேடு"
          className="input"
        />
        
      </div>

      {loading && <Loader />}
      {error && <div className="error">{error}</div>}

      {!loading && !error && (
        <>
          <h2 className="section-title">செய்திகள்</h2>
          {!filtered.length && <div className="empty">No results</div>}
          {!!filtered.length && (
            view === 'grid' ? (
              <div className="grid four">
                {filtered.map((item) => (
                  <NewsCard key={item.id} item={item} variant="grid" />
                ))}
              </div>
            ) : (
              <div className="list">
                {filtered.map((item) => (
                  <NewsCard key={item.id} item={item} variant="list" />
                ))}
              </div>
            )
          )}
          {!!filtered.length && (
            <div style={{display:'flex', justifyContent:'center', marginTop: 16}}>
              <button className="button" onClick={()=> setLimit(limit + 50)} title="மேலும் செய்திகள்">
                மேலும் செய்திகள்
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
