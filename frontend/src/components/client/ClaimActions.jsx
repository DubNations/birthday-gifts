import { motion } from 'framer-motion'

export default function ClaimActions({ giftId, onClaim, onRelease, regretRemaining, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="flex flex-col items-center gap-3 mt-6"
    >
      <button
        onClick={() => onClaim(giftId)}
        disabled={loading}
        className="btn-primary text-lg px-10 py-3"
      >
        ✅ 确认要送
      </button>
      {regretRemaining > 0 && (
        <button
          onClick={() => onRelease(giftId)}
          disabled={loading}
          className="btn-secondary text-sm"
        >
          😅 反悔重抽（剩余 {regretRemaining} 次机会）
        </button>
      )}
      {regretRemaining <= 0 && (
        <p className="text-sm text-gray-400">反悔机会已用完</p>
      )}
    </motion.div>
  )
}
