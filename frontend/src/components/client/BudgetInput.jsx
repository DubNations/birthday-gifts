import { motion } from 'framer-motion'

export default function BudgetInput({ budget, setBudget, onSubmit, loading, error }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card max-w-md w-full"
    >
      <h2 className="text-xl font-bold text-gray-700 mb-4 text-center">输入你的预算</h2>
      <div className="relative mb-4">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">¥</span>
        <input
          type="number"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSubmit()}
          placeholder="0.00"
          className="w-full pl-10 pr-4 py-4 text-2xl text-center border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
        />
      </div>
      {error && <p className="text-red-500 text-sm mb-3 text-center">{error}</p>}
      <button
        onClick={onSubmit}
        disabled={loading || !budget}
        className="btn-primary w-full text-lg py-3"
      >
        {loading ? '计算中...' : '获取方案 ✨'}
      </button>
    </motion.div>
  )
}
