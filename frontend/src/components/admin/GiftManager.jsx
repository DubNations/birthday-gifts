import { useState, useEffect } from 'react'
import GiftForm from './GiftForm'
import { adminApi } from '../../api'

export default function GiftManager({ onRefresh }) {
  const [gifts, setGifts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingGift, setEditingGift] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [tierFilter, setTierFilter] = useState('')

  const fetchGifts = async () => {
    try {
      const params = {}
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      if (tierFilter) params.tier = tierFilter
      const res = await adminApi.getGifts(params)
      setGifts(res.data)
    } catch (err) {
      console.error('获取礼物列表失败:', err)
      setActionError('获取礼物列表失败')
    }
  }

  useEffect(() => { fetchGifts() }, [search, statusFilter, tierFilter])

  const handleCreate = async (data) => {
    try {
      await adminApi.createGift(data)
      setShowForm(false)
      setActionError(null)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setActionError(err.response?.data?.detail || '添加礼物失败')
    }
  }

  const handleUpdate = async (id, data) => {
    try {
      await adminApi.updateGift(id, data)
      setEditingGift(null)
      setActionError(null)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setActionError(err.response?.data?.detail || '更新礼物失败')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确定删除此礼物？')) return
    try {
      await adminApi.deleteGift(id)
      setActionError(null)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setActionError(err.response?.data?.detail || '删除礼物失败')
    }
  }

  const handleStatusChange = async (giftId, newStatus) => {
    try {
      await adminApi.updateGiftStatus(giftId, newStatus)
      setActionError(null)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setActionError(err.response?.data?.detail || '更新状态失败')
    }
  }

  const handleUnlock = async (giftId) => {
    if (!confirm('确定解锁此礼物？')) return
    try {
      await adminApi.unlockGift(giftId)
      setActionError(null)
      fetchGifts()
      onRefresh()
    } catch (err) {
      setActionError(err.response?.data?.detail || '解锁失败')
    }
  }

  const tierLabel = (t) => ({ A: '高级', B: '中级', C: '普通' }[t] || t)

  return (
    <div className='mb-8'>
      <div className='flex items-center justify-between mb-4'>
        <h3 className='text-xl font-bold text-gray-700'>礼物列表</h3>
        <button onClick={() => { setEditingGift(null); setShowForm(true) }} className='btn-primary'>
          + 添加礼物
        </button>
      </div>

      {/* 搜索和筛选 */}
      <div className='flex flex-wrap gap-3 mb-4'>
        <input
          type='text'
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder='搜索名称或手机号...'
          className='px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none flex-1 min-w-[200px]'
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className='px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none'
        >
          <option value=''>全部状态</option>
          <option value='available'>可抽取</option>
          <option value='locked'>锁定中</option>
          <option value='claimed'>已领取</option>
        </select>
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className='px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none'
        >
          <option value=''>全部等级</option>
          <option value='A'>高级</option>
          <option value='B'>中级</option>
          <option value='C'>普通</option>
        </select>
      </div>

      {actionError && (
        <div className='bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4'>
          {actionError}
          <button onClick={() => setActionError(null)} className='ml-2 text-red-500 hover:text-red-700 font-bold'>x</button>
        </div>
      )}

      {showForm && (
        <GiftForm
          gift={editingGift}
          onSubmit={editingGift ? (d) => handleUpdate(editingGift.id, d) : handleCreate}
          onCancel={() => { setShowForm(false); setEditingGift(null) }}
        />
      )}

      <div className='overflow-x-auto'>
        <table className='w-full bg-white rounded-xl shadow overflow-hidden'>
          <thead className='bg-gray-50'>
            <tr>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>名称</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>等级</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>价格</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>购买链接</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>权重</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>状态</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>领取者</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>操作</th>
            </tr>
          </thead>
          <tbody className='divide-y divide-gray-100'>
            {gifts.map(gift => (
              <tr key={gift.id} className='hover:bg-gray-50'>
                <td className='px-4 py-3'>
                  <div className='font-medium text-gray-800'>{gift.name}</div>
                </td>
                <td className='px-4 py-3'>
                  <span className={'tier-badge-' + gift.tier.toLowerCase()}>{tierLabel(gift.tier)}</span>
                </td>
                <td className='px-4 py-3 text-gray-700'>{'\u00a5'}{gift.price}</td>
                <td className='px-4 py-3'>
                  {gift.url ? (
                    <a href={gift.url} target='_blank' rel='noreferrer'
                      className='inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline'>
                      查看
                    </a>
                  ) : (
                    <span className='text-xs text-red-500'>未填写</span>
                  )}
                </td>
                <td className='px-4 py-3'>
                  <span className='text-sm text-gray-600'>{gift.weight}</span>
                </td>
                <td className='px-4 py-3'>
                  <select
                    value={gift.status}
                    onChange={(e) => handleStatusChange(gift.id, e.target.value)}
                    className={`px-2 py-1 rounded-full text-xs font-medium border-0 outline-none cursor-pointer ${
                      gift.status === 'available' ? 'bg-green-100 text-green-700' :
                      gift.status === 'locked' ? 'bg-amber-100 text-amber-700' :
                      'bg-blue-100 text-blue-700'
                    }`}
                  >
                    <option value='available'>可抽取</option>
                    <option value='locked'>锁定中</option>
                    <option value='claimed'>已领取</option>
                  </select>
                </td>
                <td className='px-4 py-3 text-sm text-gray-600'>
                  {gift.claimed_by || (gift.locked_by ? gift.locked_by : '-')}
                </td>
                <td className='px-4 py-3'>
                  <button
                    onClick={() => { setEditingGift(gift); setShowForm(true) }}
                    className='text-sm text-blue-600 hover:text-blue-800 mr-2'
                    disabled={gift.status === 'claimed'}
                  >编辑</button>
                  {gift.status === 'locked' && (
                    <button
                      onClick={() => handleUnlock(gift.id)}
                      className='text-sm text-amber-600 hover:text-amber-800 mr-2'
                    >解锁</button>
                  )}
                  <button
                    onClick={() => handleDelete(gift.id)}
                    className='text-sm text-red-600 hover:text-red-800'
                    disabled={gift.status === 'locked'}
                  >删除</button>
                </td>
              </tr>
            ))}
            {gifts.length === 0 && (
              <tr>
                <td colSpan='8' className='px-4 py-8 text-center text-gray-400'>暂无礼物</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
