import { useState, useEffect } from 'react'

export function useFingerprint() {
  const [fingerprint, setFingerprint] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('fingerprint_id')
    if (stored) {
      setFingerprint(stored)
      setLoading(false)
      return
    }

    import('@fingerprintjs/fingerprintjs').then(({ default: FingerprintJS }) => {
      FingerprintJS.load().then(fp => {
        fp.get().then(result => {
          const visitorId = result.visitorId
          localStorage.setItem('fingerprint_id', visitorId)
          document.cookie = `fp_id=${visitorId};path=/;max-age=31536000`
          setFingerprint(visitorId)
          setLoading(false)
        })
      })
    }).catch(() => {
      const fallback = 'fp_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)
      localStorage.setItem('fingerprint_id', fallback)
      setFingerprint(fallback)
      setLoading(false)
    })
  }, [])

  return { fingerprint, loading }
}
