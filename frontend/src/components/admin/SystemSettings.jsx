import { useState, useEffect } from 'react'
import { adminApi } from '../../api'

export default function SystemSettings() {
  const [config, setConfig] = useState(null)
  const [maxRegret, setMaxRegret] = useState(1)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    adminApi.getConfig().then(res => {
      setConfig(res.data)
      setMaxRegret(res.data.max_regret_chances)
    }).catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    setError('')
    try {
      await adminApi.updateConfig({ max_regret_chances: parseInt(maxRegret) })
      setMessage('配置已保存')
    } catch (err) {
      setError(err.response?.data?.detail || '保存失败')
    }
    setSaving(false)
  }

  return (
    <div>
      <h3 className='text-xl font-bold text-gray-700 mb-4'>系统设置</h3>

      {error && (
        <div className='bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm'>
          {error}
        </div>
      )}
      {message && (
        <div className='bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg mb-4 text-sm'>
          {message}
        </div>
      )}

      <div className='bg-white rounded-xl shadow p-6 space-y-6'>
        <div>
          <label className='block text-sm font-semibold text-gray-700 mb-2'>
            反悔次数上限
          </label>
          <p className='text-xs text-gray-500 mb-2'>
            每个用户最多可以反悔（释放已抽礼物）的次数。设为 0 则不允许反悔。
          </p>
          <div className='flex items-center gap-3'>
            <input
              type='number'
              min={0}
              max={99}
              value={maxRegret}
              onChange={(e) => setMaxRegret(e.target.value)}
              className='w-24 px-3 py-2 border border-gray-300 rounded-lg text-center text-lg focus:ring-2 focus:ring-primary-500 outline-none'
            />
            <span className='text-sm text-gray-500'>次</span>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className='btn-primary'
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>

      {config && (
        <div className='mt-6 bg-gray-50 rounded-xl p-4'>
          <h4 className='text-sm font-semibold text-gray-600 mb-2'>当前配置信息</h4>
          <div className='text-sm text-gray-500 space-y-1'>
            <p>反悔次数: {config.max_regret_chances}</p>
          </div>
        </div>
      )}
    </div>
  )
}
