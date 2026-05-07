import { useState, useEffect } from 'react'
import GiftForm from './GiftForm'
import { adminApi, getApiErrorMessage } from '../../api'

export default function GiftManager({ onRefresh }) {
  const [gifts, setGifts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingGift, setEditingGift] = useState(null)
  const [error, setError] = useState('')

  const fetchGifts = async () => {
    try {
      const res = await adminApi.getGifts()
      setGifts(res.data)
      setError('')
    } catch (err) {
      setError(getApiErrorMessage(err, '获取礼物列表失败，请稍后重试'))
    }
  }

  useEffect(() => { fetchGifts() }, [])

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
      setError('')
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '更新礼物失败，请稍后重试'))
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确定删除此礼物？')) return
    try {
      await adminApi.deleteGift(id)
      setError('')
      fetchGifts()
      onRefresh()
    } catch (err) {
      setError(getApiErrorMessage(err, '删除礼物失败，请稍后重试'))
    }
  }

  const tierLabel = (t) => ({ A: '高级', B: '中级', C: '普通' }[t] || t)
  const statusLabel = (s) => ({ available: '可抽取', locked: '锁定中', claimed: '已领取' }[s] || s)

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-700">礼物列表</h3>
        <button onClick={() => { setEditingGift(null); setShowForm(true) }} className="btn-primary">
          + 添加礼物
        </button>
      </div>

      {error && <p className="text-red-500 text-sm mb-3">{error}</p>}

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
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {statusLabel(gift.status)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => { setEditingGift(gift); setShowForm(true) }}
                    className="text-sm text-blue-600 hover:text-blue-800 mr-3"
                    disabled={gift.status === 'claimed'}
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(gift.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                    disabled={gift.status === 'locked'}
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
            {gifts.length === 0 && (
              <tr>
                <td colSpan="5" className="px-4 py-8 text-center text-gray-400">暂无礼物</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
