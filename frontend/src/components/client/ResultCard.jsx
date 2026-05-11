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
      <div className="flex items-center justify-center gap-3 mb-3">
        <span className={`tier-badge-${gift.tier.toLowerCase()}`}>{config.label}礼物</span>
        <span className="text-lg font-semibold text-primary-700">¥{gift.price}</span>
      </div>
      {gift.url && (
        <a
          href={gift.url}
          target="_blank"
          rel="noreferrer"
          className="text-blue-500 hover:underline text-sm"
        >
          查看购买链接 →
        </a>
      )}
    </motion.div>
  )
}
