import { motion } from 'framer-motion'

export default function ResultCard({ gift }) {
  const tierConfig = {
    A: { emoji: '💎', label: '高级', bgClass: 'bg-red-50 border-red-200' },
    B: { emoji: '🎁', label: '中级', bgClass: 'bg-blue-50 border-blue-200' },
    C: { emoji: '🎈', label: '普通', bgClass: 'bg-green-50 border-green-200' },
  }
  const config = tierConfig[gift.tier] || tierConfig.C

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5, rotateY: -180 }}
      animate={{ opacity: 1, scale: 1, rotateY: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className={`card ${config.bgClass} border-2 text-center`}
    >
      <div className="text-6xl mb-4">{config.emoji}</div>
      <h3 className="text-2xl font-bold text-gray-800 mb-2">{gift.name}</h3>
      <div className="flex items-center justify-center gap-3 mb-4">
        <span className={`tier-badge-${gift.tier.toLowerCase()}`}>{config.label}礼物</span>
        <span className="text-lg font-semibold text-primary-700">¥{gift.price}</span>
      </div>

      {gift.url && (
        <a
          href={gift.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 px-6 rounded-xl transition-all duration-200 shadow-md hover:shadow-lg active:scale-95 text-base"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
          </svg>
          去购买 - 点击直达商家
        </a>
      )}
      {!gift.url && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 text-yellow-700 text-sm">
          该礼物暂未提供购买链接，请联系管理员补充
        </div>
      )}
    </motion.div>
  )
}
