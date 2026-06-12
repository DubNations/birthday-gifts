import { useState, useEffect } from 'react'

export function useFingerprint() {
  const [fingerprint, setFingerprint] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('fingerprint_id')
    if (stored) {
      setFingerprint(stored)
    }
    setLoading(false)
  }, [])

  const login = (phone) => {
    localStorage.setItem('fingerprint_id', phone)
    setFingerprint(phone)
  }

  const logout = () => {
    localStorage.removeItem('fingerprint_id')
    setFingerprint(null)
  }

  return { fingerprint, loading, login, logout }
}
