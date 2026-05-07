import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import BudgetInput from '../components/client/BudgetInput'
import PlanSelector from '../components/client/PlanSelector'
import FeedbackMessage from '../components/client/FeedbackMessage'
import { useDrawStore } from '../store/drawStore'
import { useFingerprint } from '../hooks/useFingerprint'

export default function HomePage() {
  const navigate = useNavigate()
  const { fingerprint } = useFingerprint()
  const { plans, fetchPlans, setSelectedPlan, startDraw, loading, error, success, loadingMessage, setError } = useDrawStore()
  const [budget, setBudget] = useState('')
  const [step, setStep] = useState('input')

  const handleBudgetSubmit = async () => {
    const val = parseFloat(budget)
    if (Number.isNaN(val) || val <= 0) {
      setError('请输入大于 0 的有效预算金额')
      return
    }
    const result = await fetchPlans(val)
    if (result && result.length > 0 && result[0].plan_type !== 'none') {
      setStep('plans')
    }
  }

  const handlePlanSelect = async (plan) => {
    if (!fingerprint) {
      setError('正在生成设备标识，请稍候再试')
      return
    }
    setSelectedPlan(plan)
    const started = await startDraw(fingerprint, parseFloat(budget), plan)
    if (started) {
      navigate('/draw', {
        state: {
          budget: parseFloat(budget),
          plan: { ...plan, draws: started.draws },
          sessionId: started.session_id,
          planDetail: started.plan_detail,
        },
      })
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] gap-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h1 className="text-5xl font-bold text-primary-700 mb-4">🎁 Birthday Gift</h1>
        <p className="text-lg text-gray-600">输入预算，智能分配抽奖方案</p>
      </motion.div>

      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="card max-w-2xl w-full"
      >
        <h2 className="text-xl font-bold text-gray-700 mb-4">活动规则说明</h2>
        <div className="grid gap-3 text-sm text-gray-600 sm:grid-cols-2">
          <p><strong>预算影响方案：</strong>系统会根据预算自动组合 A/B/C 抽奖次数，预算越高越可能包含更高等级或更多礼物。</p>
          <p><strong>A/B/C 等级：</strong>A 级通常为高价惊喜，B 级为中价礼物，C 级为轻量小礼物。</p>
          <p><strong>锁定时长：</strong>抽中礼物后会临时锁定，请在锁定期内确认或反悔，超时可能释放回礼物池。</p>
          <p><strong>反悔次数：</strong>每位参与者有有限反悔机会，用完后只能确认当前锁定礼物。</p>
          <p className="sm:col-span-2"><strong>价格说明：</strong>方案中的预计花费仅用于预算规划，最终实际价格可能因商品改价、库存或购买渠道不同而变化。</p>
        </div>
      </motion.section>

      {step === 'input' && (
        <BudgetInput
          budget={budget}
          setBudget={setBudget}
          onSubmit={handleBudgetSubmit}
          loading={loading}
          error={error}
          loadingMessage={loadingMessage}
        />
      )}

      {step === 'plans' && (
        <div className="w-full max-w-2xl space-y-3">
          {loading && <FeedbackMessage type="loading">{loadingMessage || '处理中，请稍候...'}</FeedbackMessage>}
          <FeedbackMessage type="error">{error}</FeedbackMessage>
          <FeedbackMessage type="success">{success}</FeedbackMessage>
          <PlanSelector
            plans={plans}
            onSelect={handlePlanSelect}
            onBack={() => setStep('input')}
          />
        </div>
      )}
    </div>
  )
}
