import { motion } from 'framer-motion'

export default function PlanSelector({ plans, onSelect, onBack }) {
  const tierEmoji = { A: '💎', B: '🎁', C: '🎈' }
  const formatMoney = (value) => Number(value || 0).toFixed(2)

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
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-3">
                <div>
                  <h3 className="text-lg font-bold text-gray-800">{plan.description}</h3>
                  <p className="text-sm text-gray-500 mt-1">预计花费: ¥{formatMoney(plan.estimated_cost)}</p>
                </div>
                <div className="rounded-lg bg-amber-50 border border-amber-100 p-3 text-sm text-amber-800">
                  <p className="font-semibold">预算解释</p>
                  <p className="mt-1">{plan.explanation || '预计花费仅为按库存价格测算的参考值，不代表最终实际花费。'}</p>
                  <p className="mt-2 text-xs">
                    可能成本区间：¥{formatMoney(plan.min_possible_cost)} - ¥{formatMoney(plan.max_possible_cost)}；按预计花费计算的预算余量：¥{formatMoney(plan.remaining_budget_estimate)}。
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 sm:justify-end">
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
