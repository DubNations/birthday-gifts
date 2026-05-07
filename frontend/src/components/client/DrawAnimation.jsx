import { motion } from 'framer-motion'

export default function DrawAnimation({ tier }) {
  const tierConfig = {
    A: { emoji: '💎', color: 'from-red-400 to-pink-500', label: '高级' },
    B: { emoji: '🎁', color: 'from-blue-400 to-indigo-500', label: '中级' },
    C: { emoji: '🎈', color: 'from-green-400 to-emerald-500', label: '普通' },
  }
  const config = tierConfig[tier] || tierConfig.C

  return (
    <div className="flex flex-col items-center justify-center py-10">
      <motion.div
        className={`w-40 h-40 rounded-2xl bg-gradient-to-br ${config.color} flex items-center justify-center shadow-2xl`}
        animate={{
          rotateY: [0, 360],
          scale: [1, 1.2, 1],
        }}
        transition={{
          rotateY: { duration: 1.5, repeat: Infinity, ease: 'linear' },
          scale: { duration: 0.8, repeat: Infinity, repeatType: 'reverse' },
        }}
      >
        <span className="text-6xl">{config.emoji}</span>
      </motion.div>
      <motion.p
        className="mt-6 text-xl font-bold text-gray-700"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        正在抽取 {config.label} 礼物...
      </motion.p>
    </div>
  )
}
