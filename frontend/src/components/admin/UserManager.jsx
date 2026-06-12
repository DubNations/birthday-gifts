import { useState, useEffect } from 'react'
import { adminApi } from '../../api'

export default function UserManager({ onRefresh }) {
  const [users, setUsers] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [expandedPhone, setExpandedPhone] = useState(null)
  const [userDetail, setUserDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const pageSize = 20

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const res = await adminApi.getUsers({ search: search || undefined, page, page_size: pageSize })
      setUsers(res.data.users)
      setTotal(res.data.total)
    } catch (err) {
      console.error('获取用户列表失败:', err)
    }
    setLoading(false)
  }

  useEffect(() => { fetchUsers() }, [search, page])

  const handleViewDetail = async (phone) => {
    if (expandedPhone === phone) {
      setExpandedPhone(null)
      setUserDetail(null)
      return
    }
    setExpandedPhone(phone)
    setDetailLoading(true)
    try {
      const res = await adminApi.getUserDetail(phone)
      setUserDetail(res.data)
    } catch {
      setUserDetail(null)
    }
    setDetailLoading(false)
  }

  const handleResetUser = async (phone) => {
    if (!confirm(`确定重置用户 ${phone} 的所有状态？此操作不可撤销！`)) return
    try {
      await adminApi.resetUser(phone)
      alert('已重置')
      fetchUsers()
      if (onRefresh) onRefresh()
    } catch (err) {
      alert(err.response?.data?.detail || '重置失败')
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  const actionLabel = (a) => ({
    lock: '🔒 锁定', claim: '✅ 领取', release: '🔄 释放'
  }[a] || a)

  return (
    <div>
      <div className='flex items-center justify-between mb-4'>
        <h3 className='text-xl font-bold text-gray-700'>用户管理</h3>
        <span className='text-sm text-gray-500'>共 {total} 个用户</span>
      </div>

      <div className='mb-4'>
        <input
          type='text'
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          placeholder='搜索手机号...'
          className='px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none w-full max-w-xs'
        />
      </div>

      {loading ? (
        <p className='text-gray-500 text-center py-8'>加载中...</p>
      ) : users.length === 0 ? (
        <p className='text-gray-400 text-center py-8'>暂无用户</p>
      ) : (
        <div className='space-y-2'>
          {users.map(user => (
            <div key={user.phone} className='bg-white rounded-xl shadow overflow-hidden'>
              <div className='flex items-center justify-between px-4 py-3'>
                <div className='flex items-center gap-4'>
                  <span className='font-mono font-bold text-gray-800'>{user.phone}</span>
                  <span className='text-xs bg-gray-100 px-2 py-1 rounded-full text-gray-600'>
                    抽奖 {user.session_count} 次
                  </span>
                  <span className='text-xs bg-blue-50 px-2 py-1 rounded-full text-blue-700'>
                    领取 {user.claimed_count} 件
                  </span>
                  <span className='text-xs bg-amber-50 px-2 py-1 rounded-full text-amber-700'>
                    反悔 {user.regret_count} 次
                  </span>
                  <span className='text-xs bg-green-50 px-2 py-1 rounded-full text-green-700'>
                    ¥{user.claimed_value}
                  </span>
                </div>
                <div className='flex gap-2'>
                  <button
                    onClick={() => handleViewDetail(user.phone)}
                    className='text-sm text-blue-600 hover:text-blue-800'
                  >
                    {expandedPhone === user.phone ? '收起' : '详情'}
                  </button>
                  <button
                    onClick={() => handleResetUser(user.phone)}
                    className='text-sm text-red-600 hover:text-red-800'
                  >重置</button>
                </div>
              </div>

              {expandedPhone === user.phone && (
                <div className='border-t border-gray-100 px-4 py-3 bg-gray-50'>
                  {detailLoading ? (
                    <p className='text-gray-500 text-sm'>加载中...</p>
                  ) : userDetail ? (
                    <div className='space-y-3'>
                      {userDetail.claimed_gifts.length > 0 && (
                        <div>
                          <h4 className='text-sm font-semibold text-gray-600 mb-1'>已领取礼物</h4>
                          <div className='flex flex-wrap gap-2'>
                            {userDetail.claimed_gifts.map(g => (
                              <span key={g.id} className='text-xs bg-white border px-2 py-1 rounded-lg'>
                                {g.name} (¥{g.price})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {userDetail.actions.length > 0 && (
                        <div>
                          <h4 className='text-sm font-semibold text-gray-600 mb-1'>操作记录</h4>
                          <div className='max-h-40 overflow-y-auto space-y-1'>
                            {userDetail.actions.slice(0, 20).map(a => (
                              <div key={a.id} className='text-xs text-gray-600 flex gap-2'>
                                <span className='text-gray-400'>
                                  {a.created_at ? new Date(a.created_at).toLocaleString('zh-CN') : ''}
                                </span>
                                <span>{actionLabel(a.action)}</span>
                                <span className='text-gray-400'>礼物#{a.gift_id}</span>
                                {a.regret_used && <span className='text-red-500'>[反悔]</span>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className='text-gray-500 text-sm'>无法加载详情</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className='flex items-center justify-center gap-2 mt-4'>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className='px-3 py-1 rounded border text-sm disabled:opacity-50'
          >上一页</button>
          <span className='text-sm text-gray-500'>{page} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className='px-3 py-1 rounded border text-sm disabled:opacity-50'
          >下一页</button>
        </div>
      )}
    </div>
  )
}
