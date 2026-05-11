import { useState, useCallback } from 'react'
import { drawApi } from '../api'

export function useDrawStore() {
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [currentGift, setCurrentGift] = useState(null)
  const [lockedGifts, setLockedGifts] = useState([])
  const [regretRemaining, setRegretRemaining] = useState(1)
  const [remainingBudget, setRemainingBudget] = useState(0)
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchPlans = useCallback(async (budget) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.getPlans(budget)
      setPlans(res.data.plans)
      return res.data.plans
    } catch (err) {
      setError(err.response?.data?.detail || '获取方案失败')
      return []
    } finally { setLoading(false) }
  }, [])

  const startDrawSession = useCallback(async (fingerprintId, budget, planType) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.startDraw(fingerprintId, budget, planType)
      setSessionId(res.data.session_id)
      setRemainingBudget(res.data.remaining_budget)
      return res.data
    } catch (err) {
      setError(err.response?.data?.detail || '开始抽奖失败')
      return null
    } finally { setLoading(false) }
  }, [])

  const spinGift = useCallback(async (tier, fingerprintId) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.spinGift(tier, fingerprintId, sessionId)
      setCurrentGift(res.data)
      setRemainingBudget(res.data.remaining_budget)
      setLockedGifts(prev => [...prev, res.data])
      return res.data
    } catch (err) {
      setError(err.response?.data?.detail || '抽奖失败')
      return null
    } finally { setLoading(false) }
  }, [sessionId])

  const claimGift = useCallback(async (fingerprintId, giftId) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.claimGift(fingerprintId, giftId)
      setRemainingBudget(res.data.remaining_budget)
      setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
      setCurrentGift(null)
      return { ok: true, remaining: res.data.remaining_budget }
    } catch (err) {
      setError(err.response?.data?.detail || '确认失败')
      return { ok: false }
    } finally { setLoading(false) }
  }, [])

  const releaseGift = useCallback(async (fingerprintId, giftId) => {
    setLoading(true); setError(null)
    try {
      await drawApi.releaseGift(fingerprintId, giftId)
      setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
      setCurrentGift(null)
      setRegretRemaining(prev => Math.max(0, prev - 1))
      return true
    } catch (err) {
      setError(err.response?.data?.detail || '释放失败')
      return false
    } finally { setLoading(false) }
  }, [])

  const fetchStatus = useCallback(async (fingerprintId) => {
    try {
      const res = await drawApi.getStatus(fingerprintId)
      setLockedGifts(res.data.locked_gifts)
      setRegretRemaining(res.data.regret_remaining)
      setRemainingBudget(res.data.remaining_budget)
      setSessionId(res.data.session_id)
      return res.data
    } catch { return null }
  }, [])

  return {
    plans, selectedPlan, currentGift, lockedGifts,
    regretRemaining, remainingBudget, sessionId, loading, error,
    setSelectedPlan, setRemainingBudget, fetchPlans, startDrawSession,
    spinGift, claimGift, releaseGift, fetchStatus, setError,
  }
}
