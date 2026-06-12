import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { drawApi } from '../api'

const DrawContext = createContext(null)

export function DrawProvider({ children }) {
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [currentGift, setCurrentGift] = useState(null)
  const [lockedGifts, setLockedGifts] = useState([])
  const [regretRemaining, setRegretRemaining] = useState(1)
  const [remainingBudget, setRemainingBudget] = useState(0)
  const [minPrices, setMinPrices] = useState({})
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 使用 ref 记录 sessionId，避免闭包陈旧值
  const sessionIdRef = useRef(null)
  sessionIdRef.current = sessionId

  const fetchPlans = useCallback(async (budget) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.getPlans(budget)
      setPlans(res.data.plans)
      return res.data.plans
    } catch (err) {
      const msg = err.response?.data?.detail || '获取方案失败'
      setError(msg)
      return []
    } finally { setLoading(false) }
  }, [])

  const startDrawSession = useCallback(async (fingerprintId, budget, planType) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.startDraw(fingerprintId, budget, planType)
      setSessionId(res.data.session_id)
      setRemainingBudget(res.data.remaining_budget)
      setMinPrices(res.data.min_prices || {})
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail || '开始抽奖失败'
      setError(msg)
      return null
    } finally { setLoading(false) }
  }, [])

  const spinGift = useCallback(async (tier, fingerprintId) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.spinGift(tier, fingerprintId, sessionIdRef.current)
      setCurrentGift(res.data)
      setRemainingBudget(res.data.remaining_budget)
      setLockedGifts(prev => [...prev, res.data])
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail || '抽奖失败'
      setError(msg)
      return null
    } finally { setLoading(false) }
  }, [])

  const claimGift = useCallback(async (fingerprintId, giftId) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.claimGift(fingerprintId, giftId)
      setRemainingBudget(res.data.remaining_budget)
      setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
      setCurrentGift(null)
      return { ok: true, remaining: res.data.remaining_budget }
    } catch (err) {
      const msg = err.response?.data?.detail || '确认失败'
      setError(msg)
      return { ok: false }
    } finally { setLoading(false) }
  }, [])

  const releaseGift = useCallback(async (fingerprintId, giftId) => {
    setLoading(true); setError(null)
    try {
      const res = await drawApi.releaseGift(fingerprintId, giftId)
      setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
      setCurrentGift(null)
      setRegretRemaining(prev => Math.max(0, prev - 1))
      if (res.data.remaining_budget !== undefined) {
        setRemainingBudget(res.data.remaining_budget)
      }
      return true
    } catch (err) {
      const msg = err.response?.data?.detail || '释放失败'
      setError(msg)
      return false
    } finally { setLoading(false) }
  }, [])

  const fetchStatus = useCallback(async (fingerprintId) => {
    try {
      const res = await drawApi.getStatus(fingerprintId)
      setLockedGifts(res.data.locked_gifts)
      setRegretRemaining(res.data.regret_remaining)
      setRemainingBudget(res.data.remaining_budget)
      if (res.data.session_id > 0) {
        setSessionId(res.data.session_id)
      }
      return res.data
    } catch (err) {
      console.error('获取状态失败:', err)
      return null
    }
  }, [])

  const value = {
    plans, selectedPlan, currentGift, lockedGifts,
    regretRemaining, remainingBudget, minPrices, sessionId, loading, error,
    setSelectedPlan, setRemainingBudget, setPlans,
    fetchPlans, startDrawSession, spinGift, claimGift, releaseGift,
    fetchStatus, setError,
  }

  return <DrawContext.Provider value={value}>{children}</DrawContext.Provider>
}

export function useDrawStore() {
  const ctx = useContext(DrawContext)
  if (!ctx) {
    throw new Error('useDrawStore must be used within DrawProvider')
  }
  return ctx
}
