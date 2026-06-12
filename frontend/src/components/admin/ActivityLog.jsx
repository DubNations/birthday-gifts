import { useState, useEffect } from 'react'
import { adminApi } from '../../api'

const actionColors = {
  lock: 'bg-amber-100 text-amber-700',
  claim: 'bg-green-100 text-green-700',
  release: 'bg-red-100 text-red-700',
}

const actionLabels = {
  lock: '锁定',
  claim: '领取',
  release: '释放',
}

export default function ActivityLog() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [phoneFilter, setPhoneFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const pageSize = 50

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize }
      if (phoneFilter) params.phone = phoneFilter
      if (actionFilter) params.action = actionFilter
      const res = await adminApi.getActivityLog(params)
      setLogs(res.data.items)
      setTotal(res.data.total)
    } catch (err) {
      console.error('获取活动日志失败:', err)
    }
    setLoading(false)
  }

  useEffect(() => { fetchLogs() }, [page, phoneFilter, actionFilter])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div>
      <h3 className='text-xl font-bold text-gray-700 mb-4'>活动日志</h3>

      <div className='flex flex-wrap gap-3 mb-4'>
        <input
          type='text'
          value={phoneFilter}
          onChange={(e) => { setPhoneFilter(e.target.value); setPage(1) }}
          placeholder='按手机号筛选...'
          className='px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none w-48'
        />
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
          className='px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none'
        >
          <option value=''>全部操作</option>
          <option value='lock'>锁定</option>
          <option value='claim'>领取</option>
          <option value='release'>释放</option>
        </select>
        <span className='text-sm text-gray-500 self-center'>共 {total} 条记录</span>
      </div>

      {loading ? (
        <p className='text-gray-500 text-center py-8'>加载中...</p>
      ) : logs.length === 0 ? (
        <p className='text-gray-400 text-center py-8'>暂无活动记录</p>
      ) : (
        <div className='space-y-1'>
          {logs.map(log => (
            <div key={log.id} className='flex items-center gap-3 px-3 py-2 bg-white rounded-lg text-sm hover:bg-gray-50'>
              <span className='text-xs text-gray-400 w-36 shrink-0'>
                {log.created_at ? new Date(log.created_at).toLocaleString('zh-CN') : ''}
              </span>
              <span className='font-mono text-gray-800 w-28 shrink-0'>{log.phone}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${actionColors[log.action] || 'bg-gray-100 text-gray-600'}`}>
                {actionLabels[log.action] || log.action}
              </span>
              <span className='text-gray-600 truncate'>
                {log.gift_name || (log.gift_id ? `礼物#${log.gift_id}` : '-')}
              </span>
              {log.regret_used && (
                <span className='text-xs text-red-500 shrink-0'>[反悔]</span>
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
