import { useState, useCallback } from 'react'
import { drawApi, getApiErrorMessage } from '../api'

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
  const [success, setSuccess] = useState(null)
  const [loadingMessage, setLoadingMessage] = useState('')

  const rememberSession = useCallback((id) => {
    if (id) {
      localStorage.setItem('draw_session_id', String(id))
    } else {
      localStorage.removeItem('draw_session_id')
    }
  }, [])

  const applyStatus = useCallback((status) => {
    if (!status) return
    const nextSessionId = status.session_id || null
    setSessionId(nextSessionId)
    rememberSession(nextSessionId)
    setActiveSession(status.active_session || null)
    setLockedGifts(status.locked_gifts || [])
    setClaimedGifts(status.claimed_gifts || [])
    setRemainingDraws(status.remaining_draws || { A: 0, B: 0, C: 0 })
    setRegretRemaining(status.regret_remaining ?? 0)
    setNextAction(status.next_action || 'start')
    setCurrentGift(status.locked_gift || null)
  }, [rememberSession])

  const runRequest = useCallback(async (message, fallback, request) => {
    setLoading(true)
    setLoadingMessage(message)
    setError(null)
    setSuccess(null)
    try {
      return await request()
    } catch (err) {
      setError(getApiErrorMessage(err, fallback))
      return null
    } finally {
      setLoading(false)
      setLoadingMessage('')
    }
  }, [])

  const fetchPlans = useCallback(async (budget) => {
    const res = await runRequest('正在计算预算方案...', '获取方案失败，请稍后重试', () => drawApi.getPlans(budget))
    if (!res) return []
    setPlans(res.data.plans || [])
    return res.data.plans || []
  }, [runRequest])

  const startDraw = useCallback(async (fingerprintId, budget, plan) => {
    const res = await runRequest('正在创建抽奖会话...', '创建抽奖会话失败，请稍后重试', () => drawApi.startDraw(fingerprintId, budget, plan.plan_type))
    if (!res) return null
    setSelectedPlan({ ...plan, draws: res.data.draws })
    setSessionId(res.data.session_id)
    rememberSession(res.data.session_id)
    setActiveSession({
      session_id: res.data.session_id,
      budget,
      plan_type: plan.plan_type,
      plan_detail: res.data.plan_detail,
    })
    setRemainingDraws(res.data.draws)
    setNextAction('spin')
    setSuccess('抽奖会话已创建，准备开始抽奖')
    return res.data
  }, [rememberSession, runRequest])

  const spinGift = useCallback(async (activeSessionId, fingerprintId) => {
    const res = await runRequest('正在抽取礼物...', '抽奖失败，请稍后重试', () => drawApi.spinGift(activeSessionId, fingerprintId))
    if (!res) return null
    setCurrentGift(res.data)
    setLockedGifts([res.data])
    setNextAction('claim_or_release')
    setSuccess('礼物已锁定，请确认或反悔')
    return res.data
  }, [runRequest])

  const claimGift = useCallback(async (fingerprintId, giftId, activeSessionId) => {
    const res = await runRequest('正在确认礼物...', '确认失败，请稍后重试', () => drawApi.claimGift(fingerprintId, giftId, activeSessionId))
    if (!res) return false
    const claimedGift = currentGift || lockedGifts.find((gift) => gift.gift_id === giftId)
    setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
    setClaimedGifts(prev => claimedGift ? [...prev.filter(g => g.gift_id !== giftId), claimedGift] : prev)
    setCurrentGift(null)
    setNextAction('spin')
    setSuccess('已确认加入最终清单')
    return true
  }, [currentGift, lockedGifts, runRequest])

  const releaseGift = useCallback(async (fingerprintId, giftId, activeSessionId) => {
    const res = await runRequest('正在处理反悔...', '反悔失败，请稍后重试', () => drawApi.releaseGift(fingerprintId, giftId, activeSessionId))
    if (!res) return false
    setLockedGifts(prev => prev.filter(g => g.gift_id !== giftId))
    setCurrentGift(null)
    setRegretRemaining(prev => Math.max(0, prev - 1))
    setNextAction('spin')
    setSuccess('已反悔，本次机会可重新抽取')
    return true
  }, [runRequest])

  const fetchStatus = useCallback(async (fingerprintId, activeSessionId) => {
    const res = await runRequest('正在恢复抽奖进度...', '恢复抽奖进度失败，请刷新页面或返回首页重试', () => drawApi.getStatus(fingerprintId, activeSessionId))
    if (!res) return null
    applyStatus(res.data)
    return res.data
  }, [applyStatus, runRequest])

  return {
    plans, selectedPlan, sessionId, activeSession, currentGift, lockedGifts,
    claimedGifts, remainingDraws, nextAction, regretRemaining, loading, error,
    success, loadingMessage, setSelectedPlan, setSessionId, setActiveSession,
    fetchPlans, startDraw, spinGift, claimGift, releaseGift, fetchStatus,
    setError, setSuccess,
  }
}
