import React from 'react'

export default function Header({ route, onNavigate, activeFilter = 'all', onFilterChange = () => {}, lang = 'ta', onLanguageChange = () => {} }) {
  return (
    <header className="topbar">
      <div className="container topbar-row">
        <button className="icon-btn" aria-label="Menu">≡</button>
        <div className="brand-box">தமிழ்</div>
        <nav className="primary-nav">
          <button className={route==='home'? 'nav-link active':'nav-link'} onClick={() => onNavigate('home')}>முகப்பு</button>
          <button className={route==='admin'? 'nav-link active':'nav-link'} onClick={() => onNavigate('admin')}>நிர்வாகம்</button>
          <button className={activeFilter==='all'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('all')}>அனைத்தும்</button>
          <button className={activeFilter==='world'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('world')}>உலகம்</button>
          <button className={activeFilter==='business'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('business')}>வணிகம்</button>
          <button className={activeFilter==='tech'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('tech')}>தொழில்நுட்பம்</button>
          <button className={activeFilter==='sports'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('sports')}>விளையாட்டு</button>
        </nav>
        <div className="lang-switch">
          <select className="select" value={lang} onChange={(e)=>onLanguageChange(e.target.value)} title="Language">
            <option value="ta">தமிழ்</option>
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
            <option value="kn">ಕನ್ನಡ</option>
            <option value="ml">മലയാളം</option>
            <option value="te">తెలుగు</option>
          </select>
        </div>
      </div>
    </header>
  )
}
