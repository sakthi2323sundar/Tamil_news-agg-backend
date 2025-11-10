import React, { useState } from 'react'
import { triggerFetch } from '../lib/api'

export default function Admin() {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const onFetch = async () => {
    setLoading(true)
    setMessage('')
    setError('')
    try {
      const res = await triggerFetch()
      setMessage(res?.message || 'Triggered')
    } catch (e) {
      setError(e?.message || 'Failed to trigger')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <div className="card">
        <h2>Admin</h2>
        <p>Manually trigger Tamil news fetch.</p>
        <button disabled={loading} onClick={onFetch} className="button">
          {loading ? 'Working...' : 'Fetch now'}
        </button>
        {message && <div className="success mt">{message}</div>}
        {error && <div className="error mt">{error}</div>}
      </div>
    </section>
  )
}
