import { useState, useCallback } from 'react'
import { drawApi } from '../api'

export function useDrawStore() {
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [currentGift, setCurrentGift] = useState(null)
  const [lockedGifts, setLockedGifts] = useState([])
  const [claimedGifts, setClaimedGifts] = useState([])
  const [remainingDraws, setRemainingDraws] = useState({ A: 0, B: 0, C: 0 })
  const [nextAction, setNextAction] = useState('start')
  const [regretRemaining, setRegretRemaining] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const applyStatus = useCallback((status) => {
    if (!status) return
    setSessionId(status.session_id || null)
    setActiveSession(status.active_session || null)
    setLockedGifts(status.locked_gifts || [])
    setClaimedGifts(status.claimed_gifts || [])
    setRemainingDraws(status.remaining_draws || { A: 0, B: 0, C: 0 })
    setRegretRemaining(status.regret_remaining)
    setNextAction(status.next_action || 'start')
    setCurrentGift(status.locked_gift || null)
  }, [])

  const fetchPlans = useCallback(async (budget) => {
    setLoading(true)
    setError(null)
    try {
      const res = await drawApi.getPlans(budget)
      setPlans(res.data.plans)
      return res.data.plans
    } catch (err) {
      setError(err.response?.data?.detail || '获取方案失败')
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  const startDraw = useCallback(async (fingerprintId, budget, plan) => {
    setLoading(true)
    setError(null)
    try {
      const res = await drawApi.startDraw(fingerprintId, budget, plan.plan_type)
      setSelectedPlan({ ...plan, draws: res.data.draws })
      setSessionId(res.data.session_id)
      setActiveSession({
        session_id: res.data.session_id,
        budget,
        plan_type: plan.plan_type,
        plan_detail: res.data.plan_detail,
      })
      setRemainingDraws(res.data.draws)
      setNextAction('spin')
      return res.data
    } catch (err) {
      setError(err.response?.data?.detail || '创建抽奖会话失败')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const spinGift = useCallback(async (activeSessionId, fingerprintId) => {
    setLoading(true)
    setError(null)
    try {
      const res = await drawApi.spinGift(activeSessionId, fingerprintId)
      setCurrentGift(res.data)
      setLockedGifts([res.data])
      setNextAction('claim_or_release')
      return res.data
    } catch (err) {
      setError(err.response?.data?.detail || '抽奖失败')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const claimGift = useCallback(async (fingerprintId, giftId, activeSessionId) => {
    setLoading(true)
    setError(null)
    try {
      await drawApi.claimGift(fingerprintId, giftId, activeSessionId)
      setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
      setClaimedGifts(prev => [...prev, currentGift].filter(Boolean))
      setCurrentGift(null)
      setNextAction('spin')
      return true
    } catch (err) {
      setError(err.response?.data?.detail || '确认失败')
      return false
    } finally {
      setLoading(false)
    }
  }, [currentGift])

  const releaseGift = useCallback(async (fingerprintId, giftId, activeSessionId) => {
    setLoading(true)
    setError(null)
    try {
      await drawApi.releaseGift(fingerprintId, giftId, activeSessionId)
      setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
      setCurrentGift(null)
      setRegretRemaining(prev => Math.max(0, prev - 1))
      setNextAction('spin')
      return true
    } catch (err) {
      setError(err.response?.data?.detail || '释放失败')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchStatus = useCallback(async (fingerprintId) => {
    try {
      const res = await drawApi.getStatus(fingerprintId)
      applyStatus(res.data)
      return res.data
    } catch (err) {
      return null
    }
  }, [applyStatus])

  return {
    plans, selectedPlan, sessionId, activeSession, currentGift, lockedGifts,
    claimedGifts, remainingDraws, nextAction, regretRemaining, loading, error,
    setSelectedPlan, setSessionId, setActiveSession, fetchPlans, startDraw, spinGift,
    claimGift, releaseGift, fetchStatus, setError,
  }
}
