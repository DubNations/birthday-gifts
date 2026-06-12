import { useState, useEffect } from 'react'
import GiftManager from '../components/admin/GiftManager'
import UserManager from '../components/admin/UserManager'
import SystemSettings from '../components/admin/SystemSettings'
import ActivityLog from '../components/admin/ActivityLog'
import ExportPanel from '../components/admin/ExportPanel'
import { adminApi } from '../api'

const tabs = [
  { key: 'gifts', label: '礼物管理', icon: '🎁' },
  { key: 'users', label: '用户管理', icon: '👥' },
  { key: 'settings', label: '系统设置', icon: '⚙️' },
  { key: 'activity', label: '活动日志', icon: '📋' },
  { key: 'data', label: '数据操作', icon: '💾' },
]

export default function AdminPage() {
  const [password, setPassword] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [stats, setStats] = useState(null)
  const [authError, setAuthError] = useState('')
  const [loggingIn, setLoggingIn] = useState(false)
  const [activeTab, setActiveTab] = useState('gifts')

  useEffect(() => {
    const token = sessionStorage.getItem('admin_token')
    if (token) {
      setLoggingIn(true)
      adminApi.getStats().then(res => {
        setStats(res.data)
        setAuthenticated(true)
      }).catch(() => {
        sessionStorage.removeItem('admin_token')
      }).finally(() => setLoggingIn(false))
    }
  }, [])

  const handleLogin = async () => {
    setLoggingIn(true)
    setAuthError('')
    try {
      const res = await adminApi.login(password)
      sessionStorage.setItem('admin_token', res.data.token)
      const statsRes = await adminApi.getStats()
      setStats(statsRes.data)
      setAuthenticated(true)
    } catch {
      setAuthError('密码错误')
    } finally {
      setLoggingIn(false)
    }
  }

  const handleLogout = () => {
    sessionStorage.removeItem('admin_token')
    setAuthenticated(false)
    setStats(null)
    setPassword('')
  }

  const refreshStats = async () => {
    try {
      const res = await adminApi.getStats()
      setStats(res.data)
    } catch {}
  }

  if (loggingIn) {
    return (
      <div className='max-w-md mx-auto mt-20 text-center'>
        <p className='text-gray-500'>验证中...</p>
      </div>
    )
  }

  if (!authenticated) {
    return (
      <div className='max-w-md mx-auto mt-20'>
        <div className='card'>
          <h2 className='text-2xl font-bold text-primary-700 mb-6 text-center'>管理员登录</h2>
          {authError && <p className='text-red-500 text-sm mb-3 text-center'>{authError}</p>}
          <input
            type='password'
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
            placeholder='输入管理员密码'
            className='w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none mb-4'
          />
          <button onClick={handleLogin} disabled={loggingIn} className='btn-primary w-full'>
            {loggingIn ? '登录中...' : '登录'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className='flex items-center justify-between mb-6'>
        <h2 className='text-3xl font-bold text-primary-700'>管理后台</h2>
        <button onClick={handleLogout} className='btn-secondary text-sm'>退出登录</button>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className='grid grid-cols-3 sm:grid-cols-6 gap-3 mb-6'>
          <div className='card text-center py-3'>
            <div className='text-2xl font-bold text-gray-700'>{stats.total}</div>
            <div className='text-xs text-gray-500'>总礼物</div>
          </div>
          <div className='card text-center py-3'>
            <div className='text-2xl font-bold text-green-600'>{stats.available}</div>
            <div className='text-xs text-gray-500'>可抽取</div>
          </div>
          <div className='card text-center py-3'>
            <div className='text-2xl font-bold text-amber-600'>{stats.locked}</div>
            <div className='text-xs text-gray-500'>锁定中</div>
          </div>
          <div className='card text-center py-3'>
            <div className='text-2xl font-bold text-blue-600'>{stats.claimed}</div>
            <div className='text-xs text-gray-500'>已领取</div>
          </div>
          <div className='card text-center py-3'>
            <div className='text-2xl font-bold text-purple-600'>{stats.total_users || 0}</div>
            <div className='text-xs text-gray-500'>总用户</div>
          </div>
          <div className='card text-center py-3'>
            <div className='text-2xl font-bold text-pink-600'>{stats.today_users || 0}</div>
            <div className='text-xs text-gray-500'>今日活跃</div>
          </div>
        </div>
      )}

      {/* Tab 导航 */}
      <div className='flex gap-1 mb-6 overflow-x-auto border-b border-gray-200 pb-0'>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all whitespace-nowrap ${
              activeTab === tab.key
                ? 'bg-white text-primary-700 border border-b-0 border-gray-200 -mb-px'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div>
        {activeTab === 'gifts' && <GiftManager onRefresh={refreshStats} />}
        {activeTab === 'users' && <UserManager onRefresh={refreshStats} />}
        {activeTab === 'settings' && <SystemSettings />}
        {activeTab === 'activity' && <ActivityLog />}
        {activeTab === 'data' && <ExportPanel />}
      </div>
    </div>
  )
}
