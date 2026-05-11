import { useState, useEffect } from 'react'
import GiftForm from './GiftForm'
import { adminApi } from '../../api'

export default function GiftManager({ onRefresh }) {
  const [gifts, setGifts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingGift, setEditingGift] = useState(null)

  const fetchGifts = async () => {
    try {
      const res = await adminApi.getGifts()
      setGifts(res.data)
    } catch {}
  }

  useEffect(() => { fetchGifts() }, [])

  const handleCreate = async (data) => {
    await adminApi.createGift(data)
    setShowForm(false)
    fetchGifts()
    onRefresh()
  }

  const handleUpdate = async (id, data) => {
    await adminApi.updateGift(id, data)
    setEditingGift(null)
    fetchGifts()
    onRefresh()
  }

  const handleDelete = async (id) => {
    if (!confirm('确定删除此礼物？')) return
    await adminApi.deleteGift(id)
    fetchGifts()
    onRefresh()
  }

  const handleStatusChange = async (giftId, newStatus) => {
    await adminApi.updateGiftStatus(giftId, newStatus)
    fetchGifts()
    onRefresh()
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
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>状态</th>
              <th className='px-4 py-3 text-left text-sm font-semibold text-gray-600'>操作</th>
            </tr>
          </thead>
          <tbody className='divide-y divide-gray-100'>
            {gifts.map(gift => (
              <tr key={gift.id} className='hover:bg-gray-50'>
                <td className='px-4 py-3'>
                  <div className='font-medium text-gray-800'>{gift.name}</div>
                  {gift.url && <a href={gift.url} target='_blank' rel='noreferrer' className='text-xs text-blue-500 hover:underline'>链接</a>}
                </td>
                <td className='px-4 py-3'>
                  <span className={'tier-badge-' + gift.tier.toLowerCase()}>{tierLabel(gift.tier)}</span>
                </td>
                <td className='px-4 py-3 text-gray-700'>{'\u00a5'}{gift.price}</td>
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
                <td colSpan='5' className='px-4 py-8 text-center text-gray-400'>暂无礼物</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
