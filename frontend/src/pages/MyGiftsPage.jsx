import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { drawApi } from '../api'
import { useFingerprint } from '../hooks/useFingerprint'

const tierConfig = {
  A: { label: '高级', color: 'text-red-600', bg: 'bg-red-50 border-red-200' },
  B: { label: '中级', color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200' },
  C: { label: '普通', color: 'text-green-600', bg: 'bg-green-50 border-green-200' },
}

export default function MyGiftsPage() {
  const { fingerprint } = useFingerprint()
  const [gifts, setGifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!fingerprint) { setLoading(false); return }
    setError(null)
    drawApi.getHistory(fingerprint)
      .then(res => setGifts(res.data))
      .catch(() => setError('加载失败，请刷新重试'))
      .finally(() => setLoading(false))
  }, [fingerprint])

  if (!fingerprint) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 text-lg mb-4">请先登录后查看您的礼物</p>
        <Link to="/" className="btn-primary">去登录</Link>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500">加载中...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-primary-700 mb-2">🎁 我的礼物</h1>
        <p className="text-gray-500">手机号 {fingerprint} 共领取 {gifts.length} 件礼物</p>
      </div>

      {error ? (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">😵</div>
          <p className="text-red-500 text-lg mb-4">{error}</p>
          <button onClick={() => window.location.reload()} className="btn-primary">刷新重试</button>
        </div>
      ) : gifts.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">📦</div>
          <p className="text-gray-500 text-lg mb-4">还没有领取任何礼物</p>
          <Link to="/" className="btn-primary">去抽奖</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {gifts.map((gift, idx) => {
            const tier = tierConfig[gift.tier] || tierConfig.C
            return (
              <motion.div
                key={gift.gift_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`card border ${tier.bg}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold text-gray-800 text-lg">{gift.name}</h3>
                  <span className={`text-xs font-bold px-2 py-1 rounded-full ${tier.color} bg-white`}>
                    {tier.label}
                  </span>
                </div>
                <div className="text-2xl font-bold text-primary-600 mb-2">
                  ¥{gift.price}
                </div>
                {gift.url && (
                  <a
                    href={gift.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline mb-2"
                  >
                    购买链接 ↗
                  </a>
                )}
                {gift.claimed_at && (
                  <p className="text-xs text-gray-400 mt-1">
                    领取时间: {new Date(gift.claimed_at).toLocaleString('zh-CN')}
                  </p>
                )}
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
