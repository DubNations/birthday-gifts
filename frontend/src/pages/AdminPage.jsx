import { useState } from 'react'
import GiftManager from '../components/admin/GiftManager'
import ExportPanel from '../components/admin/ExportPanel'
import { adminApi, setAdminToken, getApiErrorMessage } from '../api'

export default function AdminPage() {
  const [password, setPassword] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [stats, setStats] = useState(null)
  const [authError, setAuthError] = useState('')
  const [statsError, setStatsError] = useState('')

  const handleLogin = async () => {
    try {
      const loginRes = await adminApi.login(password)
      setAdminToken(loginRes.data.token)
      const res = await adminApi.getStats()
      setStats(res.data)
      setAuthenticated(true)
      setAuthError('')
    } catch (err) {
      setAuthError(getApiErrorMessage(err, '密码错误或登录失败'))
    }
  }

  const refreshStats = async () => {
    try {
      const res = await adminApi.getStats()
      setStats(res.data)
      setStatsError('')
    } catch (err) {
      setStatsError(getApiErrorMessage(err, '刷新统计失败，请稍后重试'))
    }
  }

  if (!authenticated) {
    return (
      <div className="max-w-md mx-auto mt-20">
        <div className="card">
          <h2 className="text-2xl font-bold text-primary-700 mb-6 text-center">管理员登录</h2>
          {authError && <p className="text-red-500 text-sm mb-3 text-center">{authError}</p>}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
            placeholder="输入管理员密码"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none mb-4"
          />
          <button onClick={handleLogin} className="btn-primary w-full">登录</button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-primary-700 mb-4">管理后台</h2>
        {statsError && <p className="text-red-500 text-sm mb-3">{statsError}</p>}
        {stats && (
          <div className="grid grid-cols-4 gap-4">
            <div className="card text-center">
              <div className="text-3xl font-bold text-gray-700">{stats.total}</div>
              <div className="text-sm text-gray-500">总礼物</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-green-600">{stats.available}</div>
              <div className="text-sm text-gray-500">可抽取</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-amber-600">{stats.locked}</div>
              <div className="text-sm text-gray-500">锁定中</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-blue-600">{stats.claimed}</div>
              <div className="text-sm text-gray-500">已领取</div>
            </div>
          </div>
        )}
      </div>
      <GiftManager onRefresh={refreshStats} />
      <ExportPanel onRefresh={refreshStats} />
    </div>
  )
}
