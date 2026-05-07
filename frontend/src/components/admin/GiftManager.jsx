import { useState, useEffect } from 'react'
import GiftForm from './GiftForm'
import { adminApi, getApiErrorMessage } from '../../api'

const PAGE_SIZES = [10, 20, 50, 100]

export default function GiftManager({ onRefresh }) {
  const [gifts, setGifts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingGift, setEditingGift] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedIds, setSelectedIds] = useState([])
  const [filters, setFilters] = useState({ q: '', status: '', tier: '', min_price: '', max_price: '' })
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0 })
  const [importing, setImporting] = useState(false)

  const fetchGifts = async (overrides = {}) => {
    setLoading(true)
    try {
      const nextPage = overrides.page || pagination.page
      const nextPageSize = overrides.page_size || pagination.page_size
      const params = {
        ...filters,
        ...overrides.filters,
        page: nextPage,
        page_size: nextPageSize,
      }
      Object.keys(params).forEach((key) => params[key] === '' && delete params[key])
      const res = await adminApi.getGifts(params)
      const data = Array.isArray(res.data) ? { items: res.data, total: res.data.length, page: 1, page_size: res.data.length || 20 } : res.data
      setGifts(data.items)
      setPagination({ page: data.page, page_size: data.page_size, total: data.total })
      setSelectedIds([])
      setError('')
    } catch (err) {
      setError(getApiErrorMessage(err, '获取礼物列表失败，请稍后重试'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchGifts({ page: 1 }) }, [])

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const applyFilters = () => fetchGifts({ page: 1 })

  const resetFilters = () => {
    const empty = { q: '', status: '', tier: '', min_price: '', max_price: '' }
    setFilters(empty)
    fetchGifts({ page: 1, filters: empty })
  }

  const handleCreate = async (data) => {
    try {
      await adminApi.createGift(data)
      setShowForm(false)
      setError('')
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '创建礼物失败，请稍后重试'))
    }
  }

  const handleUpdate = async (id, data) => {
    try {
      await adminApi.updateGift(id, data)
      setEditingGift(null)
      setShowForm(false)
      setError('')
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '更新礼物失败，请稍后重试'))
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确定删除此未领取礼物？')) return
    try {
      await adminApi.deleteGift(id)
      setError('')
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '删除礼物失败，请稍后重试'))
    }
  }

  const handleImport = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setImporting(true)
    setError('')
    try {
      const res = await adminApi.importGifts(file)
      alert(`CSV 导入完成：新增 ${res.data.created} 个礼物`)
      fetchGifts({ page: 1 })
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, 'CSV 导入失败，请检查文件格式'))
    } finally {
      setImporting(false)
    }
  }

  const selectedCount = selectedIds.length
  const allVisibleSelected = gifts.length > 0 && gifts.every((gift) => selectedIds.includes(gift.id))

  const toggleAll = () => {
    setSelectedIds(allVisibleSelected ? [] : gifts.map((gift) => gift.id))
  }

  const toggleOne = (id) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id])
  }

  const bulkDelete = async () => {
    if (!selectedCount || !confirm(`确定删除选中的 ${selectedCount} 个未领取礼物？`)) return
    try {
      await adminApi.bulkDeleteGifts(selectedIds)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '批量删除失败'))
    }
  }

  const bulkTier = async () => {
    const tier = prompt('请输入目标等级：A、B 或 C')?.toUpperCase()
    if (!tier) return
    try {
      await adminApi.bulkUpdateTier(selectedIds, tier)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '批量调整等级失败'))
    }
  }

  const bulkStatus = async (status) => {
    try {
      await adminApi.bulkUpdateStatus(selectedIds, status)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '批量更新状态失败'))
    }
  }

  const tierLabel = (t) => ({ A: '高级', B: '中级', C: '普通' }[t] || t)
  const statusLabel = (s) => ({ available: '可抽取', locked: '锁定中', claimed: '已领取', disabled: '不可用' }[s] || s)
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.page_size))

  return (
    <div className="mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="text-xl font-bold text-gray-700">礼物列表</h3>
        <div className="flex gap-2">
          <label className="btn-secondary cursor-pointer">
            {importing ? '导入中...' : 'CSV 批量导入'}
            <input type="file" accept=".csv,text/csv" onChange={handleImport} disabled={importing} className="hidden" />
          </label>
          <button onClick={() => { setEditingGift(null); setShowForm(true) }} className="btn-primary">
            + 添加礼物
          </button>
        </div>
      </div>

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <input value={filters.q} onChange={(e) => handleFilterChange('q', e.target.value)} placeholder="搜索名称或链接" className="px-3 py-2 border rounded-lg md:col-span-2" />
          <select value={filters.status} onChange={(e) => handleFilterChange('status', e.target.value)} className="px-3 py-2 border rounded-lg">
            <option value="">全部状态</option>
            <option value="available">可抽取</option>
            <option value="locked">锁定中</option>
            <option value="claimed">已领取</option>
            <option value="disabled">不可用</option>
          </select>
          <select value={filters.tier} onChange={(e) => handleFilterChange('tier', e.target.value)} className="px-3 py-2 border rounded-lg">
            <option value="">全部等级</option>
            <option value="A">高级</option>
            <option value="B">中级</option>
            <option value="C">普通</option>
          </select>
          <input type="number" min="0" value={filters.min_price} onChange={(e) => handleFilterChange('min_price', e.target.value)} placeholder="最低价" className="px-3 py-2 border rounded-lg" />
          <input type="number" min="0" value={filters.max_price} onChange={(e) => handleFilterChange('max_price', e.target.value)} placeholder="最高价" className="px-3 py-2 border rounded-lg" />
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={applyFilters} className="btn-primary">筛选</button>
          <button onClick={resetFilters} className="btn-secondary">重置</button>
        </div>
      </div>

      {selectedCount > 0 && (
        <div className="card mb-4 flex flex-wrap items-center gap-3 bg-amber-50">
          <span className="text-sm text-gray-700">已选择 {selectedCount} 个礼物</span>
          <button onClick={bulkDelete} className="btn-danger">批量删除未领取</button>
          <button onClick={bulkTier} className="btn-secondary">批量调整等级</button>
          <button onClick={() => bulkStatus('disabled')} className="btn-secondary">设为不可用</button>
          <button onClick={() => bulkStatus('available')} className="btn-secondary">恢复可用</button>
        </div>
      )}

      {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
      {loading && <p className="text-gray-500 text-sm mb-3">正在加载礼物列表...</p>}

      {showForm && (
        <GiftForm
          gift={editingGift}
          onSubmit={editingGift ? (d) => handleUpdate(editingGift.id, d) : handleCreate}
          onCancel={() => { setShowForm(false); setEditingGift(null) }}
        />
      )}

      <div className="overflow-x-auto">
        <table className="w-full bg-white rounded-xl shadow overflow-hidden">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left"><input type="checkbox" checked={allVisibleSelected} onChange={toggleAll} /></th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">名称</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">等级</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">价格</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">状态</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {gifts.map(gift => (
              <tr key={gift.id} className="hover:bg-gray-50">
                <td className="px-4 py-3"><input type="checkbox" checked={selectedIds.includes(gift.id)} onChange={() => toggleOne(gift.id)} /></td>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-800">{gift.name}</div>
                  {gift.url && <a href={gift.url} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:underline">链接</a>}
                </td>
                <td className="px-4 py-3">
                  <span className={`tier-badge-${gift.tier.toLowerCase()}`}>{tierLabel(gift.tier)}</span>
                </td>
                <td className="px-4 py-3 text-gray-700">¥{gift.price}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    gift.status === 'available' ? 'bg-green-100 text-green-700' :
                    gift.status === 'locked' ? 'bg-amber-100 text-amber-700' :
                    gift.status === 'disabled' ? 'bg-gray-100 text-gray-600' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {statusLabel(gift.status)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => { setEditingGift(gift); setShowForm(true) }} className="text-sm text-blue-600 hover:text-blue-800 mr-3" disabled={gift.status === 'claimed'}>
                    编辑
                  </button>
                  <button onClick={() => handleDelete(gift.id)} className="text-sm text-red-600 hover:text-red-800" disabled={gift.status === 'locked' || gift.status === 'claimed'}>
                    删除
                  </button>
                </td>
              </tr>
            ))}
            {!loading && gifts.length === 0 && (
              <tr>
                <td colSpan="6" className="px-4 py-8 text-center text-gray-400">暂无礼物</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-gray-600">
        <span>共 {pagination.total} 条，第 {pagination.page} / {totalPages} 页</span>
        <div className="flex items-center gap-2">
          <select value={pagination.page_size} onChange={(e) => fetchGifts({ page: 1, page_size: Number(e.target.value) })} className="px-2 py-1 border rounded">
            {PAGE_SIZES.map((size) => <option key={size} value={size}>{size} 条/页</option>)}
          </select>
          <button disabled={pagination.page <= 1 || loading} onClick={() => fetchGifts({ page: pagination.page - 1 })} className="btn-secondary disabled:opacity-50">上一页</button>
          <button disabled={pagination.page >= totalPages || loading} onClick={() => fetchGifts({ page: pagination.page + 1 })} className="btn-secondary disabled:opacity-50">下一页</button>
        </div>
      </div>
    </div>
  )
}
