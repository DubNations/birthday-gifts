import { useState, useEffect, useMemo } from 'react'
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
  const {
    spinGift, claimGift, releaseGift, fetchStatus, loading, error,
    regretRemaining, currentGift, activeSession, remainingDraws, nextAction,
  } = useDrawStore()
  const [plan, setPlan] = useState(location.state?.plan || null)
  const [sessionId, setSessionId] = useState(location.state?.sessionId || null)
  const [budget] = useState(location.state?.budget || 0)
  const [phase, setPhase] = useState('ready')

  useEffect(() => {
    if (!fingerprint) return
    fetchStatus(fingerprint).then((status) => {
      if (!status) return
      if (status.session_id) setSessionId(status.session_id)
      if (status.active_session?.plan_detail?.original_plan && !plan) {
        setPlan(status.active_session.plan_detail.original_plan)
      }
      if (status.locked_gift) {
        setPhase('result')
      } else if (status.next_action === 'completed') {
        setPhase('done')
      } else {
        setPhase('ready')
      }
    })
  }, [fingerprint])

  const planDetail = activeSession?.plan_detail || location.state?.planDetail || null
  const spinQueue = useMemo(() => {
    const draws = planDetail?.original_plan?.draws || plan?.draws || {}
    const queue = []
    for (const tier of ['A', 'B', 'C']) {
      for (let i = 0; i < (draws[tier] || 0); i++) {
        queue.push(tier)
      }
    }
    return queue
  }, [plan, planDetail])

  const completedCount = useMemo(() => {
    if (planDetail?.tiers) {
      return Object.values(planDetail.tiers).reduce((sum, tier) => sum + (tier.claimed || 0), 0)
    }
    const total = spinQueue.length
    const remaining = Object.values(remainingDraws || {}).reduce((sum, count) => sum + count, 0)
    return Math.max(0, total - remaining)
  }, [planDetail, remainingDraws, spinQueue.length])

  const currentTier = planDetail?.current_tier || spinQueue[completedCount]
  const effectiveSessionId = sessionId || activeSession?.session_id

  const refreshAfterAction = async () => {
    if (!fingerprint) return null
    const status = await fetchStatus(fingerprint)
    if (status?.active_session?.plan_detail?.original_plan) {
      setPlan(status.active_session.plan_detail.original_plan)
    }
    if (status?.session_id) setSessionId(status.session_id)
    return status
  }

  const handleSpin = async () => {
    if (!effectiveSessionId || !fingerprint || !currentTier) return
    setPhase('spinning')
    const result = await spinGift(effectiveSessionId, fingerprint)
    if (result) {
      await refreshAfterAction()
      setPhase('result')
    } else {
      setPhase('ready')
    }
  }

  const handleClaim = async (giftId) => {
    const ok = await claimGift(fingerprint, giftId, effectiveSessionId)
    if (ok) {
      const status = await refreshAfterAction()
      setPhase(status?.next_action === 'completed' ? 'done' : 'ready')
    }
  }

  const handleRelease = async (giftId) => {
    const ok = await releaseGift(fingerprint, giftId, effectiveSessionId)
    if (ok) {
      await refreshAfterAction()
      setPhase('ready')
    }
  }

  if (!plan && !activeSession) {
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
        <p className="text-gray-600">{plan?.description || planDetail?.original_plan?.description}</p>
        <p className="text-sm text-gray-400 mt-1">
          预计花费: ¥{plan?.estimated_cost || planDetail?.original_plan?.estimated_cost || budget} | 反悔机会剩余: {regretRemaining} 次
        </p>
        <p className="text-xs text-gray-400 mt-1">
          会话 #{effectiveSessionId} | 下一步: {nextAction === 'claim_or_release' ? '确认或反悔' : nextAction === 'completed' ? '已完成' : '继续抽奖'}
        </p>
        <div className="flex gap-2 mt-3">
          {spinQueue.map((tier, i) => (
            <span
              key={`${tier}-${i}`}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                i < completedCount ? 'bg-gray-300 text-gray-500' :
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
        {phase === 'ready' && currentTier && (
          <motion.div
            key="ready"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-10"
          >
            <p className="text-lg text-gray-600 mb-6">
              第 {completedCount + 1} 次抽奖 — {currentTier} 级礼物
            </p>
            <button onClick={handleSpin} disabled={loading || !effectiveSessionId} className="btn-primary text-lg px-10 py-3">
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
            <DrawAnimation tier={currentTier} />
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
