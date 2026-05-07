import { useState, useEffect, useMemo, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import DrawAnimation from '../components/client/DrawAnimation'
import ResultCard from '../components/client/ResultCard'
import ClaimActions from '../components/client/ClaimActions'
import CompletionSummary from '../components/client/CompletionSummary'
import FeedbackMessage from '../components/client/FeedbackMessage'
import { useDrawStore } from '../store/drawStore'
import { useFingerprint } from '../hooks/useFingerprint'

const nextActionText = {
  claim_or_release: '确认或反悔',
  completed: '已完成',
  spin: '继续抽奖',
  start: '重新选择方案',
}

export default function DrawPage() {
  const location = useLocation()
  const { fingerprint } = useFingerprint()
  const searchParams = new URLSearchParams(location.search)
  const initialSessionId = location.state?.sessionId || searchParams.get('session_id') || localStorage.getItem('draw_session_id')
  const {
    spinGift, claimGift, releaseGift, fetchStatus, loading, error, success, loadingMessage,
    regretRemaining, currentGift, activeSession, remainingDraws, nextAction, claimedGifts,
  } = useDrawStore()
  const [plan, setPlan] = useState(location.state?.plan || null)
  const [sessionId, setSessionId] = useState(initialSessionId || null)
  const [budget] = useState(location.state?.budget || 0)
  const [phase, setPhase] = useState('restoring')
  const [hasRestored, setHasRestored] = useState(false)

  const applyStatusToPage = useCallback((status) => {
    if (!status) return false
    if (status.session_id) setSessionId(status.session_id)
    if (status.active_session?.plan_detail?.original_plan) {
      setPlan(status.active_session.plan_detail.original_plan)
    }
    if (status.locked_gift) {
      setPhase('result')
    } else if (status.next_action === 'completed' || status.status === 'completed') {
      setPhase('done')
    } else if (status.active_session && status.next_action !== 'start') {
      setPhase('ready')
    } else {
      setPhase('missing')
    }
    return true
  }, [])

  useEffect(() => {
    if (!fingerprint) return
    let ignore = false
    fetchStatus(fingerprint, initialSessionId).then((status) => {
      if (ignore) return
      if (!applyStatusToPage(status)) {
        setPhase('missing')
      }
      setHasRestored(true)
    })
    return () => {
      ignore = true
    }
  }, [applyStatusToPage, fetchStatus, fingerprint, initialSessionId])

  const planDetail = activeSession?.plan_detail || location.state?.planDetail || null
  const originalPlan = plan || planDetail?.original_plan || null
  const spinQueue = useMemo(() => {
    const draws = planDetail?.original_plan?.draws || originalPlan?.draws || {}
    const queue = []
    for (const tier of ['A', 'B', 'C']) {
      for (let i = 0; i < (draws[tier] || 0); i += 1) {
        queue.push(tier)
      }
    }
    return queue
  }, [originalPlan, planDetail])

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
    const status = await fetchStatus(fingerprint, effectiveSessionId)
    applyStatusToPage(status)
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
      setPhase(status?.next_action === 'completed' || status?.status === 'completed' ? 'done' : 'ready')
    }
  }

  const handleRelease = async (giftId) => {
    const ok = await releaseGift(fingerprint, giftId, effectiveSessionId)
    if (ok) {
      await refreshAfterAction()
      setPhase('ready')
    }
  }

  if (phase === 'restoring' || (!hasRestored && loading)) {
    return (
      <div className="max-w-2xl mx-auto py-20">
        <FeedbackMessage type="loading">{loadingMessage || '正在根据当前设备恢复抽奖进度...'}</FeedbackMessage>
      </div>
    )
  }

  if (phase === 'missing' || (!originalPlan && !activeSession)) {
    return (
      <div className="max-w-2xl mx-auto py-20 text-center">
        <div className="card">
          <h2 className="text-2xl font-bold text-primary-700 mb-3">暂无可恢复的抽奖流程</h2>
          <p className="text-gray-500 mb-5">请先从首页输入预算并选择方案；如果刚刚开始过抽奖，请刷新页面重试。</p>
          <div className="mb-5">
            <FeedbackMessage type="error">{error}</FeedbackMessage>
          </div>
          <Link to="/" className="btn-primary">返回首页</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card mb-6">
        <h2 className="text-2xl font-bold text-primary-700 mb-2">抽奖方案</h2>
        <p className="text-gray-600">{originalPlan?.description || '已恢复进行中的抽奖方案'}</p>
        <p className="text-sm text-gray-400 mt-1">
          预计花费: ¥{originalPlan?.estimated_cost || activeSession?.budget || budget} | 反悔机会剩余: {regretRemaining} 次
        </p>
        <p className="text-xs text-gray-400 mt-1">
          会话 #{effectiveSessionId} | 下一步: {nextActionText[nextAction] || '继续抽奖'}
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
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

      <div className="space-y-3 mb-4">
        {loading && phase !== 'spinning' && <FeedbackMessage type="loading">{loadingMessage || '处理中，请稍候...'}</FeedbackMessage>}
        <FeedbackMessage type="error">{error}</FeedbackMessage>
        <FeedbackMessage type="success">{success}</FeedbackMessage>
      </div>

      <AnimatePresence mode="wait">
        {phase === 'ready' && currentTier && (
          <motion.div
            key="ready"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="card text-center py-10"
          >
            <p className="text-sm text-gray-500 mb-2">当前没有待确认的锁定礼物</p>
            <p className="text-lg text-gray-600 mb-6">
              下一次抽奖：第 {completedCount + 1} 次 — {currentTier} 级礼物
            </p>
            <button onClick={handleSpin} disabled={loading || !effectiveSessionId} className="btn-primary text-lg px-10 py-3">
              {loading ? '抽取中...' : '🎰 开始抽奖'}
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
          <CompletionSummary gifts={claimedGifts} />
        )}
      </AnimatePresence>
    </div>
  )
}
