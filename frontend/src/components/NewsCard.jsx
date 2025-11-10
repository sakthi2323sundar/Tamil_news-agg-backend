import React from 'react'

export default function NewsCard({ item, variant = 'list' }) {
  const date = item.published_at || item.created_at
  const d = date ? new Date(date) : null

  const exactTa = React.useMemo(() => {
    if (!d) return ''
    try {
      return new Intl.DateTimeFormat('ta-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
        hour12: false,
        timeZone: 'Asia/Kolkata',
      }).format(d)
    } catch {
      return d.toLocaleString('en-GB')
    }
  }, [d])

  const [imgOk, setImgOk] = React.useState(true)
  const [expanded, setExpanded] = React.useState(false)

  const relTimeTa = (dt) => {
    if (!dt) return ''
    const now = new Date()
    const diff = Math.max(0, (now - dt) / 1000)
    const units = [
      ['வருடம்', 31536000],
      ['மாதம்', 2592000],
      ['வாரம்', 604800],
      ['நாள்', 86400],
      ['மணி', 3600],
      ['நிமிடம்', 60],
      ['வினாடி', 1],
    ]
    for (const [label, sec] of units) {
      const v = Math.floor(diff / sec)
      if (v >= 1) return `${v} ${label} முன்பு`
    }
    return 'இப்பொழுது'
  }

  const category = React.useMemo(() => {
    const text = [item.title, item.description, item.summary, item.source]
      .filter(Boolean).join(' ').toLowerCase()
    const has = (arr) => arr.some((k) => text.includes(k.toLowerCase()))
    if (has(['sports','விளையாட்டு','கிரிக்கெட்','ஐபிஎல்','டென்னிஸ்','கால்பந்து','ஃபுட்பால்'])) return {key:'sports', ta:'விளையாட்டு'}
    if (has(['tech','தொழில்நுட்ப','ஐடி','மொபைல்','ஸ்மார்ட்போன்','ஆப்','ஏஐ','ai','சாஃப்ட்வேர்'])) return {key:'tech', ta:'தொழில்நுட்பம்'}
    if (has(['business','வணிக','பங்கு','ஷேர்','சந்தை','வருவாய்','பொருளாதாரம்'])) return {key:'business', ta:'வணிகம்'}
    if (has(['cinema','சினிமா','திரை','பாலிவுட்','கோலிவுட்','தமிழ் சினிமா','நடிகர்','நடிகை'])) return {key:'cinema', ta:'சினிமா'}
    if (has(['tamil nadu','தமிழ்நாடு','சென்னை','மதுரை','கோயம்புத்தூர்','திருச்சி'])) return {key:'tamilnadu', ta:'தமிழ்நாடு'}
    if (has(['world','உலக','அமெரிக்கா','சீனா','பாகிஸ்தான்','இங்கிலாந்து','இஸ்ரேல்','யூரோப்','ஆப்ரிக்கா','ஆசியா'])) return {key:'world', ta:'உலகம்'}
    return {key:'general', ta:'செய்தி'}
  }, [item.title, item.description, item.summary, item.source])

  const handleCopy = async () => {
    try {
      const text = `${item.title}\n${item.url}`
      await navigator.clipboard.writeText(text)
      // no toast system yet; stay silent
    } catch {}
  }

  const handleShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({ title: item.title, url: item.url, text: item.summary || item.description || '' })
      } else {
        await handleCopy()
      }
    } catch {}
  }
  return (
    <article className={`news-card ${variant}`}>
      <a href={item.url} target="_blank" rel="noreferrer" className="thumb-wrap">
        {item.image_url && imgOk ? (
          <img
            className={`thumb ${variant}`}
            src={item.image_url}
            alt={item.title}
            loading="lazy"
            onError={() => setImgOk(false)}
          />
        ) : (
          <div className="thumb placeholder" aria-hidden="true"></div>
        )}
        <div className={`cat-badge overlay ${category.key}`}>{category.ta}</div>
      </a>
      <div className="subbar">
        <div className="sub-left"></div>
        <div className="sub-right"></div>
      </div>
      <div className="content">
        <a href={item.url} target="_blank" rel="noreferrer" className={`title ${variant}`}>{item.title}</a>
        {variant === 'grid' ? (
          item.summary ? (
            <p className={expanded ? 'summary' : 'summary clamp'}>{item.summary}</p>
          ) : (
            item.description && <p className={expanded ? 'desc' : 'desc clamp short'}>{item.description}</p>
          )
        ) : (
          <>
            {item.description && <p className={expanded ? 'desc' : 'desc clamp'}>{item.description}</p>}
            {item.summary && variant !== 'secondary' && <p className={expanded ? 'summary' : 'summary clamp'}>{item.summary}</p>}
          </>
        )}
        <div className="meta">
          <div className="meta-left">
            {d && <span className="muted" title={d.toISOString()}>{exactTa}</span>}
          </div>
          <div className="meta-right">
            <span className="muted">{item.source}</span>
          </div>
        </div>
        <div className="actions">
          <h6
            className="chip-btn"
            role="button"
            tabIndex={0}
            onClick={()=>setExpanded((v)=>!v)}
            onKeyDown={(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setExpanded((v)=>!v)}}}
          >{expanded ? 'சிறிதாக்கு' : 'சுருக்கம்'}</h6>
          <h6
            className="chip-btn"
            role="button"
            tabIndex={0}
            onClick={async()=>{try{await navigator.clipboard.writeText(`${item.title} – இதன் முக்கிய அம்சம் என்ன?\n${item.url}`)}catch{}}}
            onKeyDown={async(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();try{await navigator.clipboard.writeText(`${item.title} – இதன் முக்கிய அம்சம் என்ன?\n${item.url}`)}catch{}}}}
          >கேள்வி</h6>
          <h6
            className="chip-btn"
            role="button"
            tabIndex={0}
            onClick={async()=>{try{await navigator.clipboard.writeText(item.title)}catch{}}}
            onKeyDown={async(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();try{await navigator.clipboard.writeText(item.title)}catch{}}}}
          >தலைப்பு</h6>
        </div>
        <div className="icons">
          <button className="icon-btn small" title="நகலெடு" onClick={handleCopy}>📋</button>
          <button className="icon-btn small" title="பகிர்" onClick={handleShare}>🔗</button>
          <a className="icon-btn small" title="முழு செய்தி" href={item.url} target="_blank" rel="noreferrer">↗</a>
        </div>
      </div>
    </article>
  )
}

