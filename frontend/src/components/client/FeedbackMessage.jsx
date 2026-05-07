export default function FeedbackMessage({ type = 'info', children }) {
  if (!children) return null

  const styles = {
    loading: 'bg-blue-50 border-blue-200 text-blue-700',
    error: 'bg-red-50 border-red-200 text-red-700',
    success: 'bg-green-50 border-green-200 text-green-700',
    info: 'bg-gray-50 border-gray-200 text-gray-700',
  }

  const icons = {
    loading: '⏳',
    error: '⚠️',
    success: '✅',
    info: 'ℹ️',
  }

  return (
    <div className={`border px-4 py-3 rounded-lg text-sm ${styles[type] || styles.info}`} role={type === 'error' ? 'alert' : 'status'}>
      <span className="mr-2">{icons[type] || icons.info}</span>
      {children}
    </div>
  )
}
