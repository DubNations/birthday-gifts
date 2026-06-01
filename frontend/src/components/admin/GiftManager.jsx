import { useState, useEffect } from 'react'
import GiftForm from './GiftForm'
import { adminApi } from '../../api'

export default function GiftManager({ onRefresh }) {
  const [gifts, setGifts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingGift, setEditingGift] = useState(null)
  const [actionError, setActionError] = useState(null)

  const fetchGifts = async () => {
    try {
      const res = await adminApi.getGifts()
      setGifts(res.data)
    } catch (err) {
      console.error('获取礼物列表失败:', err)
      setActionError('获取礼物列表失败')
    }
  }

  useEffect(() => { fetchGifts() }, [])

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

  const tierLabel = (t) => ({ A: '高级', B: '中级', C: '普通' }[t] || t)
  const statusLabel = (s) => ({ available: '可抽取', locked: '锁定中', claimed: '已领取' }[s] || s)

  return (
    <div className='mb-8'>
      <div className='flex items-center justify-between mb-4'>
        <h3 className='text-xl font-bold text-gray-700'>礼物列表</h3>
        <button onClick={() => { setEditingGift(null); setShowForm(true) }} className='btn-primary'>
          + 添加礼物
        </button>
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
                      <svg className='w-4 h-4' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
                        <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14' />
                      </svg>
                      查看
                    </a>
                  ) : (
                    <span className='inline-flex items-center gap-1 text-xs text-red-500 bg-red-50 px-2 py-1 rounded-full'>
                      <svg className='w-3 h-3' fill='currentColor' viewBox='0 0 20 20'>
                        <path fillRule='evenodd' d='M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z' clipRule='evenodd' />
                      </svg>
                      未填写
                    </span>
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
                <td className='px-4 py-3'>
                  <button
                    onClick={() => { setEditingGift(gift); setShowForm(true) }}
                    className='text-sm text-blue-600 hover:text-blue-800 mr-3'
                    disabled={gift.status === 'claimed'}
                  >编辑</button>
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
                <td colSpan='7' className='px-4 py-8 text-center text-gray-400'>暂无礼物</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
