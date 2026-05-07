import { useState } from 'react'
import { adminApi } from '../../api'

export default function ExportPanel({ password }) {
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await adminApi.exportGifts(password)
      const blob = new Blob([res.data.csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `gift_list_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
    setExporting(false)
  }

  const handleReset = async () => {
    if (!confirm('确定重置所有礼物状态？此操作不可撤销！')) return
    try {
      await adminApi.resetGifts(password)
      alert('已重置')
    } catch {}
  }

  return (
    <div className="card">
      <h3 className="text-xl font-bold text-gray-700 mb-4">数据操作</h3>
      <div className="flex gap-4">
        <button onClick={handleExport} disabled={exporting} className="btn-primary">
          {exporting ? '导出中...' : '📥 导出送礼清单'}
        </button>
        <button onClick={handleReset} className="btn-danger">
          🔄 重置所有状态
        </button>
      </div>
    </div>
  )
}
