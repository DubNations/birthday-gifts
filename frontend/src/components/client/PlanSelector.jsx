import { motion } from 'framer-motion'

const tierEmoji = { A: '💎', B: '🎁', C: '🎈' }

export default function PlanSelector({ plans, onSelect, onBack }) {
  return (
    <div className="w-full max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-700">{'选择抽奖方案'}</h2>
        <button onClick={onBack} className="btn-secondary text-sm">{'← 返回修改预算'}</button>
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
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-800 mb-1">
                  {plan.plan_type === 'premium' && '👑 '}
                  {plan.plan_type === 'diverse' && '✨ '}
                  {plan.description}
                </h3>
                <p className="text-sm text-gray-500">
                  {'☺'} {'最低花费'} ¥{plan.estimated_cost}
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                {Object.entries(plan.draws).map(([tier, count]) =>
                  count > 0 && plan.tier_prices?.[tier] ? (
                    <div key={tier} className={`tier-badge-${tier.toLowerCase()} flex items-center gap-1`}>
                      <span>{tierEmoji[tier]} {tier}{'券'}</span>
                      <span className="text-xs">{'×'}{count}</span>
                    </div>
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
