import { useState } from 'react'
import { motion } from 'framer-motion'

export default function PhoneLogin({ onLogin }) {
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = () => {
    const trimmed = phone.trim()
    if (!trimmed) {
      setError('请输入手机号')
      return
    }
    if (!/^\d{11}$/.test(trimmed)) {
      setError('手机号必须为11位数字')
      return
    }
    setError('')
    onLogin(trimmed)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="card max-w-sm mx-auto"
    >
      <div className="text-center mb-6">
        <div className="text-4xl mb-3">📱</div>
        <h2 className="text-xl font-bold text-primary-700">手机号登录</h2>
        <p className="text-sm text-gray-500 mt-1">输入手机号参与抽奖</p>
      </div>
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}
      <input
        type="tel"
        value={phone}
        onChange={(e) => {
          const val = e.target.value.replace(/\D/g, '').slice(0, 11)
          setPhone(val)
          if (error) setError('')
        }}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        placeholder="请输入11位手机号"
        maxLength={11}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none mb-4 text-center text-lg tracking-widest"
      />
      <button onClick={handleSubmit} className="btn-primary w-full">
        登录
      </button>
    </motion.div>
  )
}
