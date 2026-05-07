import { useState } from 'react'
import { adminApi, getApiErrorMessage } from '../../api'

const EXPORT_TYPES = [
  { value: 'claimed', label: '已确认送礼清单', filename: 'confirmed_gifts' },
  { value: 'inventory', label: '全部库存', filename: 'gift_inventory' },
  { value: 'locked', label: '当前锁定中', filename: 'locked_gifts' },
  { value: 'actions', label: '操作日志', filename: 'admin_actions' },
  { value: 'grouped', label: '按 session / 用户分组领取清单', filename: 'grouped_claims' },
]

export default function ExportPanel({ onRefresh }) {
  const [exporting, setExporting] = useState(false)
  const [exportType, setExportType] = useState('claimed')
  const [groupBy, setGroupBy] = useState('session')
  const [error, setError] = useState('')

  const handleExport = async () => {
    setExporting(true)
    setError('')
    try {
      const selected = EXPORT_TYPES.find((item) => item.value === exportType)
      const res = await adminApi.exportGifts(exportType, groupBy)
      const blob = new Blob([res.data.csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selected?.filename || exportType}_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(getApiErrorMessage(err, '导出失败，请稍后重试'))
    }
    setExporting(false)
  }

  const handleReset = async () => {
    const confirmation = prompt('此操作不可撤销。请输入 RESET 确认重置：')
    if (confirmation !== 'RESET') return
    setError('')
    try {
      const res = await adminApi.resetGifts(confirmation)
      alert(`已重置，快照已保存：${res.data.snapshot}`)
      onRefresh?.()
    } catch (err) {
      setError(getApiErrorMessage(err, '重置失败，请稍后重试'))
    }
  }

  return (
    <div className="card">
      <h3 className="text-xl font-bold text-gray-700 mb-4">数据操作</h3>
      {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <select value={exportType} onChange={(e) => setExportType(e.target.value)} className="px-3 py-2 border rounded-lg">
          {EXPORT_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
        {exportType === 'grouped' && (
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)} className="px-3 py-2 border rounded-lg">
            <option value="session">按 session 分组</option>
            <option value="user">按用户分组</option>
          </select>
        )}
        <button onClick={handleExport} disabled={exporting} className="btn-primary">
          {exporting ? '导出中...' : '📥 导出 CSV'}
        </button>
      </div>
      <div className="flex gap-4">
        <button onClick={handleReset} className="btn-danger">
          🔄 重置所有状态
        </button>
      </div>
    </div>
  )
}
