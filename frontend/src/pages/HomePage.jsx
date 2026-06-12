import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import BudgetInput from '../components/client/BudgetInput'
import PlanSelector from '../components/client/PlanSelector'
import PhoneLogin from '../components/client/PhoneLogin'
import { useDrawStore } from '../store/drawStore'
import { useFingerprint } from '../hooks/useFingerprint'

export default function HomePage() {
  const navigate = useNavigate()
  const { fingerprint, login, logout } = useFingerprint()
  const { plans, fetchPlans, selectedPlan, setSelectedPlan, loading, error } = useDrawStore()
  const [budget, setBudget] = useState('')
  const [step, setStep] = useState('input')

  const handleBudgetSubmit = async () => {
    const val = parseFloat(budget)
    if (isNaN(val) || val <= 0) return
    const result = await fetchPlans(val)
    if (result && result.length > 0 && result[0].plan_type !== 'none') {
      setStep('plans')
    }
  }

  const handlePlanSelect = (plan) => {
    setSelectedPlan(plan)
    navigate('/draw', { state: { budget: parseFloat(budget), plan } })
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-10"
      >
        <h1 className="text-5xl font-bold text-primary-700 mb-4">🎁 Birthday Gift</h1>
        <p className="text-lg text-gray-600">输入预算，智能分配抽奖方案</p>
      </motion.div>

      {fingerprint && (
        <div className="text-center mb-4 flex items-center justify-center gap-3">
          <span className="text-sm text-gray-500">📱 {fingerprint}</span>
          <button onClick={logout} className="text-xs text-red-500 hover:text-red-700">切换账号</button>
        </div>
      )}

      {!fingerprint ? (
        <PhoneLogin onLogin={login} />
      ) : step === 'input' ? (
        <BudgetInput
          budget={budget}
          setBudget={setBudget}
          onSubmit={handleBudgetSubmit}
          loading={loading}
          error={error}
        />
      ) : (
        <PlanSelector
          plans={plans}
          onSelect={handlePlanSelect}
          onBack={() => setStep('input')}
        />
      )}
    </div>
  )
}
