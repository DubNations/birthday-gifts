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
  const [statsLoading, setStatsLoading] = useState(false)

  const handleLogin = async () => {
    try {
      setStatsLoading(true)
      const loginRes = await adminApi.login(password)
      setAdminToken(loginRes.data.token)
      const res = await adminApi.getStats()
      setStats(res.data)
      setAuthenticated(true)
      setAuthError('')
    } catch (err) {
      setAuthError(getApiErrorMessage(err, '密码错误或登录失败'))
    } finally {
      setStatsLoading(false)
    }
  }

  const refreshStats = async () => {
    try {
      setStatsLoading(true)
      const res = await adminApi.getStats()
      setStats(res.data)
      setStatsError('')
    } catch (err) {
      setStatsError(getApiErrorMessage(err, '刷新统计失败，请稍后重试'))
    } finally {
      setStatsLoading(false)
    }
  }

  const formatCountdown = (seconds = 0) => {
    const minutes = Math.floor(seconds / 60)
    const rest = seconds % 60
    return `${minutes}分${String(rest).padStart(2, '0')}秒`
  }

  const actionLabel = (action) => ({
    lock: '用户锁定',
    claim: '用户领取',
    release: '释放礼物',
    admin_create: '管理员新增',
    admin_edit: '管理员编辑',
    admin_delete: '管理员删除',
    admin_import: 'CSV 导入',
    admin_bulk_delete: '批量删除',
    admin_bulk_tier: '批量调级',
    admin_bulk_status: '批量状态',
    admin_reset: '管理员重置',
  }[action] || action)

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
          <button onClick={handleLogin} disabled={statsLoading} className="btn-primary w-full">{statsLoading ? '登录中...' : '登录'}</button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-3xl font-bold text-primary-700">管理后台</h2>
          <button onClick={refreshStats} disabled={statsLoading} className="btn-secondary">{statsLoading ? '刷新中...' : '刷新统计'}</button>
        </div>
        {statsError && <p className="text-red-500 text-sm mb-3">{statsError}</p>}
        {stats && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <div className="card text-center"><div className="text-3xl font-bold text-gray-700">{stats.total}</div><div className="text-sm text-gray-500">总礼物</div></div>
              <div className="card text-center"><div className="text-3xl font-bold text-green-600">{stats.available}</div><div className="text-sm text-gray-500">可抽取</div></div>
              <div className="card text-center"><div className="text-3xl font-bold text-amber-600">{stats.locked}</div><div className="text-sm text-gray-500">锁定中</div></div>
              <div className="card text-center"><div className="text-3xl font-bold text-blue-600">{stats.claimed}</div><div className="text-sm text-gray-500">已领取</div></div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <div className="card text-center"><div className="text-3xl font-bold text-purple-600">{stats.today_participants}</div><div className="text-sm text-gray-500">今日参与人数</div></div>
              <div className="card text-center"><div className="text-3xl font-bold text-indigo-600">{stats.active_sessions}</div><div className="text-sm text-gray-500">active session</div></div>
              <div className="card text-center"><div className="text-3xl font-bold text-rose-600">¥{stats.claimed_value}</div><div className="text-sm text-gray-500">已领取总金额</div></div>
              <div className="card text-center"><div className="text-3xl font-bold text-gray-500">{stats.disabled || 0}</div><div className="text-sm text-gray-500">不可用库存</div></div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="card">
                <h3 className="font-bold text-gray-700 mb-3">各 tier 剩余库存</h3>
                <div className="space-y-2">
                  {Object.entries(stats.tiers || {}).map(([tier, item]) => (
                    <div key={tier} className="flex items-center justify-between text-sm">
                      <span className={`tier-badge-${tier.toLowerCase()}`}>{tier}</span>
                      <span>剩余 {item.remaining} / 总计 {item.total}（锁定 {item.locked}）</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card">
                <h3 className="font-bold text-gray-700 mb-3">锁定中礼物与倒计时</h3>
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {(stats.locked_details || []).map((gift) => (
                    <div key={gift.id} className="text-sm border-b pb-2 last:border-b-0">
                      <div className="font-medium text-gray-800">#{gift.id} {gift.name}</div>
                      <div className="text-amber-700">剩余 {formatCountdown(gift.remaining_seconds)}</div>
                    </div>
                  ))}
                  {(!stats.locked_details || stats.locked_details.length === 0) && <p className="text-sm text-gray-400">暂无锁定礼物</p>}
                </div>
              </div>
              <div className="card">
                <h3 className="font-bold text-gray-700 mb-3">最近操作记录</h3>
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {(stats.recent_actions || []).map((action) => (
                    <div key={action.id} className="text-sm border-b pb-2 last:border-b-0">
                      <div className="font-medium text-gray-800">{actionLabel(action.action)} {action.gift_id ? `#${action.gift_id}` : ''}</div>
                      <div className="text-gray-500">{action.fingerprint_id} · {new Date(action.created_at).toLocaleString()}</div>
                    </div>
                  ))}
                  {(!stats.recent_actions || stats.recent_actions.length === 0) && <p className="text-sm text-gray-400">暂无操作记录</p>}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
      <GiftManager onRefresh={refreshStats} />
      <ExportPanel onRefresh={refreshStats} />
    </div>
  )
}
