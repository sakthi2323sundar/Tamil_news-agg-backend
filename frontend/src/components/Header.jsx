import React from 'react'

export default function Header({ route, onNavigate, activeFilter = 'all', onFilterChange = () => {}, lang = 'ta', onLanguageChange = () => {} }) {
  const labels = {
    ta: { brand:'தமிழ்', home:'முகப்பு', admin:'நிர்வாகம்', all:'அனைத்தும்', world:'உலகம்', business:'வணிகம்', tech:'தொழில்நுட்பம்', sports:'விளையாட்டு' },
    en: { brand:'English', home:'Home', admin:'Admin', all:'All', world:'World', business:'Business', tech:'Tech', sports:'Sports' },
    hi: { brand:'हिन्दी', home:'मुखपृष्ठ', admin:'प्रशासन', all:'सभी', world:'विश्व', business:'व्यापार', tech:'टेक', sports:'खेल' },
    kn: { brand:'ಕನ್ನಡ', home:'ಮುಖಪುಟ', admin:'ನಿರ್ವಹಣೆ', all:'ಎಲ್ಲ', world:'ವಿಶ್ವ', business:'ವ್ಯಾಪಾರ', tech:'ಟೆಕ್', sports:'ಕ್ರೀಡೆ' },
    ml: { brand:'മലയാളം', home:'ഹോം', admin:'അഡ്മിൻ', all:'എല്ലാം', world:'ലോകം', business:'ബിസിനസ്', tech:'ടെക്ക്', sports:'സ്പോർട്സ്' },
    te: { brand:'తెలుగు', home:'హోమ్', admin:'అడ్మిన్', all:'అన్నీ', world:'ప్రపంచం', business:'వ్యాపారం', tech:'టెక్', sports:'క్రీడలు' },
  }
  const t = labels[lang] || labels.ta
  return (
    <header className="topbar">
      <div className="container topbar-row">
        <button className="icon-btn" aria-label="Menu">≡</button>
        <div className="brand-box">{t.brand}</div>
        <nav className="primary-nav">
          <button className={route==='home'? 'nav-link active':'nav-link'} onClick={() => onNavigate('home')}>{t.home}</button>
          <button className={route==='admin'? 'nav-link active':'nav-link'} onClick={() => onNavigate('admin')}>{t.admin}</button>
          <button className={activeFilter==='all'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('all')}>{t.all}</button>
          <button className={activeFilter==='world'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('world')}>{t.world}</button>
          <button className={activeFilter==='business'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('business')}>{t.business}</button>
          <button className={activeFilter==='tech'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('tech')}>{t.tech}</button>
          <button className={activeFilter==='sports'? 'nav-link active':'nav-link'} onClick={() => onFilterChange('sports')}>{t.sports}</button>
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
