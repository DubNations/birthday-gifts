import { useState } from 'react'

export default function GiftForm({ gift, onSubmit, onCancel }) {
  const [form, setForm] = useState({
    name: gift?.name || '',
    url: gift?.url || '',
    price: gift?.price || '',
    tier: gift?.tier || 'A',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      ...form,
      price: parseFloat(form.price),
    })
  }

  return (
    <div className="card mb-4">
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">礼物名称</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">价格</label>
            <input
              type="number"
              step="0.01"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">等级</label>
            <select
              value={form.tier}
              onChange={(e) => setForm({ ...form, tier: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
            >
              <option value="A">A - 高级</option>
              <option value="B">B - 中级</option>
              <option value="C">C - 普通</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">购买链接</label>
            <input
              type="url"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
            />
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <button type="submit" className="btn-primary">
            {gift ? '保存修改' : '添加礼物'}
          </button>
          <button type="button" onClick={onCancel} className="btn-secondary">取消</button>
        </div>
      </form>
    </div>
  )
}
