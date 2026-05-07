import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import DrawAnimation from '../components/client/DrawAnimation'
import ResultCard from '../components/client/ResultCard'
import ClaimActions from '../components/client/ClaimActions'
import { useDrawStore } from '../store/drawStore'
import { useFingerprint } from '../hooks/useFingerprint'

export default function DrawPage() {
  const location = useLocation()
  const { fingerprint } = useFingerprint()
  const { spinGift, claimGift, releaseGift, fetchStatus, loading, error, setError,
    lockedGifts, regretRemaining, currentGift } = useDrawStore()
  const [plan, setPlan] = useState(location.state?.plan || null)
  const [budget] = useState(location.state?.budget || 0)
  const [phase, setPhase] = useState('ready')
  const [spinQueue, setSpinQueue] = useState([])
  const [spinIndex, setSpinIndex] = useState(0)

  useEffect(() => {
    if (fingerprint) {
      fetchStatus(fingerprint)
    }
  }, [fingerprint])

  useEffect(() => {
    if (plan && plan.draws) {
      const queue = []
      for (const [tier, count] of Object.entries(plan.draws)) {
        for (let i = 0; i < count; i++) {
          queue.push(tier)
        }
      }
      setSpinQueue(queue)
    }
  }, [plan])

  const handleSpin = async () => {
    if (spinIndex >= spinQueue.length || !fingerprint) return
    setPhase('spinning')
    const tier = spinQueue[spinIndex]
    const result = await spinGift(tier, fingerprint)
    if (result) {
      setPhase('result')
      setSpinIndex(prev => prev + 1)
    } else {
      setPhase('ready')
    }
  }

  const handleClaim = async (giftId) => {
    const ok = await claimGift(fingerprint, giftId)
    if (ok) {
      if (spinIndex < spinQueue.length) {
        setPhase('ready')
      } else {
        setPhase('done')
      }
    }
  }

  const handleRelease = async (giftId) => {
    const ok = await releaseGift(fingerprint, giftId)
    if (ok) {
      setPhase('ready')
    }
  }

  if (!plan) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 text-lg">请先从首页选择方案</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card mb-6">
        <h2 className="text-2xl font-bold text-primary-700 mb-2">抽奖方案</h2>
        <p className="text-gray-600">{plan.description}</p>
        <p className="text-sm text-gray-400 mt-1">
          预计花费: ¥{plan.estimated_cost} | 反悔机会剩余: {regretRemaining} 次
        </p>
        <div className="flex gap-2 mt-3">
          {spinQueue.map((tier, i) => (
            <span
              key={i}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                i < spinIndex ? 'bg-gray-300 text-gray-500' :
                tier === 'A' ? 'bg-red-100 text-red-700' :
                tier === 'B' ? 'bg-blue-100 text-blue-700' :
                'bg-green-100 text-green-700'
              }`}
            >
              {tier}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {phase === 'ready' && spinIndex < spinQueue.length && (
          <motion.div
            key="ready"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-10"
          >
            <p className="text-lg text-gray-600 mb-6">
              第 {spinIndex + 1} 次抽奖 — {spinQueue[spinIndex]} 级礼物
            </p>
            <button onClick={handleSpin} disabled={loading} className="btn-primary text-lg px-10 py-3">
              🎰 开始抽奖
            </button>
          </motion.div>
        )}

        {phase === 'spinning' && (
          <motion.div
            key="spinning"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <DrawAnimation tier={spinQueue[spinIndex]} />
          </motion.div>
        )}

        {phase === 'result' && currentGift && (
          <motion.div
            key="result"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
          >
            <ResultCard gift={currentGift} />
            <ClaimActions
              giftId={currentGift.gift_id}
              onClaim={handleClaim}
              onRelease={handleRelease}
              regretRemaining={regretRemaining}
              loading={loading}
            />
          </motion.div>
        )}

        {phase === 'done' && (
          <motion.div
            key="done"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-10"
          >
            <div className="text-6xl mb-4">🎉</div>
            <h3 className="text-2xl font-bold text-primary-700 mb-2">抽奖完成！</h3>
            <p className="text-gray-600">感谢参与，祝生日快乐！</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
