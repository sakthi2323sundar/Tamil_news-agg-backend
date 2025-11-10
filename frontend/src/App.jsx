import React, { useEffect, useMemo, useState } from 'react'
import Home from './pages/Home.jsx'
import Admin from './pages/Admin.jsx'
import Header from './components/Header.jsx'

export default function App() {
  const [route, setRoute] = useState('home')
  const [activeFilter, setActiveFilter] = useState('all')
  const [lang, setLang] = useState(() => {
    try { return localStorage.getItem('lang') || 'ta' } catch { return 'ta' }
  })
  const Page = useMemo(() => (route === 'admin' ? Admin : Home), [route])

  return (
    <div className="app">
      <Header route={route} onNavigate={setRoute} activeFilter={activeFilter} onFilterChange={setActiveFilter} lang={lang} onLanguageChange={(v)=>{setLang(v); try{localStorage.setItem('lang', v)}catch{}}} />
      <main className="container">{
        route === 'admin' ? <Admin /> : <Home activeFilter={activeFilter} lang={lang} />
      }</main>
    </div>
  )
}
