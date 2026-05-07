import { motion } from 'framer-motion'

export default function PlanSelector({ plans, onSelect, onBack }) {
  const tierEmoji = { A: '💎', B: '🎁', C: '🎈' }

  return (
    <div className="w-full max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-700">选择抽奖方案</h2>
        <button onClick={onBack} className="btn-secondary text-sm">← 返回修改预算</button>
      </div>
      <div className="grid gap-4">
        {plans.map((plan, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            onClick={() => plan.plan_type !== 'none' && onSelect(plan)}
            className={`card cursor-pointer transition-all hover:shadow-xl hover:scale-[1.02] ${
              plan.plan_type === 'none' ? 'opacity-60 cursor-not-allowed' : 'hover:border-primary-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-gray-800">{plan.description}</h3>
                <p className="text-sm text-gray-500 mt-1">预计花费: ¥{plan.estimated_cost}</p>
              </div>
              <div className="flex gap-2">
                {Object.entries(plan.draws).map(([tier, count]) =>
                  count > 0 ? (
                    <span key={tier} className={`tier-badge-${tier.toLowerCase()}`}>
                      {tierEmoji[tier]} {tier}×{count}
                    </span>
                  ) : null
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
