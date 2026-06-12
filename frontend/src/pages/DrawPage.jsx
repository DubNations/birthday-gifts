import { useState, useEffect, useMemo, useCallback } from 'react'
import { useLocation, Link } from 'react-router-dom'
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
    spinGift, claimGift, releaseGift, fetchStatus, startDrawSession,
    loading, error, setError, lockedGifts, regretRemaining, currentGift,
    remainingBudget, setRemainingBudget, minPrices,
  } = useDrawStore()
  const [plan, setPlan] = useState(location.state?.plan || null)
  const [budget] = useState(location.state?.budget || 0)
  const [phase, setPhase] = useState('idle')
  const [spinningTier, setSpinningTier] = useState(null)
  const [tickets, setTickets] = useState([])
  const [sessionStarted, setSessionStarted] = useState(false)
  const [nextId, setNextId] = useState(0)

  useEffect(() => {
    if (fingerprint) { fetchStatus(fingerprint) }
  }, [fingerprint])

  useEffect(() => {
    if (plan && plan.draws) {
      const list = []
      let id = 0
      for (const [tier, count] of Object.entries(plan.draws)) {
        for (let i = 0; i < count; i++) {
          list.push({ id: id++, tier, used: false })
        }
      }
      setTickets(list)
      setNextId(id)
    }
  }, [plan])

  useEffect(() => {
    if (!sessionStarted && budget > 0 && fingerprint && plan) {
      startDrawSession(fingerprint, budget, plan.plan_type).then(data => {
        if (data) {
          setSessionStarted(true)
          setRemainingBudget(data.remaining_budget)
        }
      })
    }
  }, [fingerprint, budget, plan, sessionStarted])

  const canAfford = useCallback((tier) => {
    const minP = minPrices?.[tier] || 0
    return minP > 0 && remainingBudget >= minP
  }, [minPrices, remainingBudget])

  const getAffordableTiers = useCallback(() => {
    const tiers = []
    for (const t of ['A', 'B', 'C']) {
      if (canAfford(t)) tiers.push(t)
    }
    return tiers
  }, [canAfford])

  const availableCount = useMemo(
    () => tickets.filter(t => !t.used && canAfford(t.tier)).length,
    [tickets, remainingBudget, canAfford]
  )

  const allPlanUsed = useMemo(
    () => tickets.length > 0 && tickets.every(t => t.used),
    [tickets]
  )

  const hasBudgetLeft = remainingBudget > 0 && getAffordableTiers().length > 0

  const handleAddMoreTickets = () => {
    const affordable = getAffordableTiers()
    if (affordable.length === 0) return
    const newTickets = []
    let id = nextId
    for (const tier of affordable) {
      newTickets.push({ id: id++, tier, used: false })
    }
    setTickets(prev => [...prev, ...newTickets])
    setNextId(id)
  }

  const handlePickTicket = async (ticket) => {
    if (ticket.used || loading || !fingerprint || !canAfford(ticket.tier)) return
    setSpinningTier(ticket.tier)
    setPhase('spinning')
    const result = await spinGift(ticket.tier, fingerprint)
    if (result) { setPhase('result') }
    else { setPhase('idle'); setSpinningTier(null) }
  }

  const handleClaim = async (giftId) => {
    const result = await claimGift(fingerprint, giftId)
    if (result.ok) {
      setTickets(prev => {
        const updated = [...prev]
        const idx = updated.findIndex(t => !t.used && t.tier === spinningTier)
        if (idx !== -1) updated[idx] = { ...updated[idx], used: true }
        return updated
      })
      setRemainingBudget(result.remaining)
      setPhase('idle')
      setSpinningTier(null)
    }
  }

  const handleRelease = async (giftId) => {
    const ok = await releaseGift(fingerprint, giftId)
    if (ok) { setPhase('idle'); setSpinningTier(null) }
  }

  if (!fingerprint) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 text-lg mb-4">请先登录后再抽奖</p>
        <Link to="/" className="btn-primary">去登录</Link>
      </div>
    )
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
        <div className="flex items-center gap-4 mt-2">
          <span className="text-lg font-bold text-primary-600">
            剩余预算: ¥{remainingBudget}
          </span>
          <span className="text-sm text-gray-400">
            反悔机会: {regretRemaining} 次
          </span>
        </div>
      </div>

      {allPlanUsed && !hasBudgetLeft && phase !== 'result' && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="text-center py-10">
          <div className="text-6xl mb-4">🎉</div>
          <h3 className="text-2xl font-bold text-primary-700 mb-2">抽奖完成！</h3>
          <p className="text-gray-600 mb-4">预算已用完，感谢参与，祝生日快乐！</p>
          <Link to="/my-gifts" className="btn-primary inline-block">
            🎁 查看我的礼物
          </Link>
        </motion.div>
      )}

      {allPlanUsed && hasBudgetLeft && phase === 'idle' && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="card text-center mb-6">
          <div className="text-4xl mb-3">🎁</div>
          <h3 className="text-xl font-bold text-primary-700 mb-2">还有剩余预算！</h3>
          <p className="text-gray-600 mb-4">
            剩余 ¥{remainingBudget}，可以继续抽奖
          </p>
          <button onClick={handleAddMoreTickets} className="btn-primary text-lg">
            ➕ 继续抽奖
          </button>
        </motion.div>
      )}

      {availableCount > 0 && (
        <>
          <p className="text-sm text-gray-500 mb-3">
            👇 点击任意未使用的券开始抽奖（预算足够才可点击）
          </p>
          <div className="flex flex-wrap gap-3 mb-6">
            {tickets.map((ticket) => {
              const affordable = canAfford(ticket.tier)
              const clickable = !ticket.used && affordable && phase === 'idle'
              return (
                <motion.button
                  key={ticket.id}
                  initial={{ scale: 0 }} animate={{ scale: 1 }}
                  whileHover={clickable ? { scale: 1.08, y: -2 } : {}}
                  whileTap={clickable ? { scale: 0.95 } : {}}
                  onClick={() => handlePickTicket(ticket)}
                  disabled={!clickable}
                  className={`relative flex flex-col items-center px-3 py-2 rounded-xl border-2 transition-all ${
                    ticket.used
                      ? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
                      : !affordable
                      ? 'border-red-200 bg-red-50 opacity-60 cursor-not-allowed'
                      : 'border-gray-200 bg-white cursor-pointer hover:border-primary-400 hover:shadow-lg hover:bg-primary-50'
                  }`}
                >
                  <span className={`text-xs font-bold ${
                    ticket.tier === 'A' ? 'text-red-600' :
                    ticket.tier === 'B' ? 'text-blue-600' : 'text-green-600'
                  }`}>{ticket.tier}级券</span>
                  {ticket.used && <span className="absolute -top-1 -right-1 text-xs">✅</span>}
                  {!ticket.used && !affordable && (
                    <span className="absolute -top-1 -right-1 text-xs">⚠️</span>
                  )}
                </motion.button>
              )
            })}
          </div>
        </>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {phase === 'spinning' && (
          <motion.div key="spinning" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <DrawAnimation tier={spinningTier} />
          </motion.div>
        )}

        {phase === 'result' && currentGift && (
          <motion.div key="result" initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
            <ResultCard gift={currentGift} />
            <div className="text-center mt-2 mb-2">
              <span className="text-sm text-gray-500">
                此礼物价格: ¥{currentGift.price} | 剩余预算: ¥
                {Math.max(0, remainingBudget).toFixed(0)}
              </span>
            </div>
            <ClaimActions
              giftId={currentGift.gift_id}
              onClaim={handleClaim}
              onRelease={handleRelease}
              regretRemaining={regretRemaining}
              loading={loading}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
