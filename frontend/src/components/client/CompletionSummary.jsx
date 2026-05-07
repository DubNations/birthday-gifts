import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import FeedbackMessage from './FeedbackMessage'

const tierLabel = { A: 'A级（高级）', B: 'B级（中级）', C: 'C级（普通）' }

const formatPrice = (price) => Number(price || 0).toFixed(2)

export default function CompletionSummary({ gifts }) {
  const [copyMessage, setCopyMessage] = useState('')
  const finalGifts = gifts || []
  const total = useMemo(
    () => finalGifts.reduce((sum, gift) => sum + Number(gift.price || 0), 0),
    [finalGifts],
  )

  const shareText = useMemo(() => {
    const lines = finalGifts.map((gift, index) => (
      `${index + 1}. ${gift.name}｜${tierLabel[gift.tier] || `${gift.tier}级`}｜¥${formatPrice(gift.price)}${gift.url ? `｜${gift.url}` : ''}`
    ))
    return ['生日礼物最终清单', ...lines, `总金额：¥${formatPrice(total)}`].join('\n')
  }, [finalGifts, total])

  const copyList = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareText)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = shareText
        textarea.setAttribute('readonly', '')
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setCopyMessage('清单已复制，可以直接分享给朋友')
    } catch (err) {
      setCopyMessage(`复制失败：${err.message || '请手动复制清单内容'}`)
    }
  }

  return (
    <motion.div
      key="done"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
    >
      <div className="text-center mb-6">
        <div className="text-6xl mb-4">🎉</div>
        <h3 className="text-2xl font-bold text-primary-700 mb-2">抽奖完成！</h3>
        <p className="text-gray-600">以下是本次确认的生日礼物最终清单。</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="px-3 py-2">名称</th>
              <th className="px-3 py-2">等级</th>
              <th className="px-3 py-2">价格</th>
              <th className="px-3 py-2">链接</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {finalGifts.map((gift) => (
              <tr key={gift.gift_id}>
                <td className="px-3 py-3 font-medium text-gray-800">{gift.name}</td>
                <td className="px-3 py-3">
                  <span className={`tier-badge-${gift.tier.toLowerCase()}`}>{tierLabel[gift.tier] || `${gift.tier}级`}</span>
                </td>
                <td className="px-3 py-3 text-primary-700 font-semibold">¥{formatPrice(gift.price)}</td>
                <td className="px-3 py-3">
                  {gift.url ? (
                    <a href={gift.url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
                      购买链接
                    </a>
                  ) : (
                    <span className="text-gray-400">暂无</span>
                  )}
                </td>
              </tr>
            ))}
            {finalGifts.length === 0 && (
              <tr>
                <td colSpan="4" className="px-3 py-6 text-center text-gray-400">暂无已确认礼物</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <p className="text-lg font-bold text-gray-800">总金额：¥{formatPrice(total)}</p>
        <button onClick={copyList} className="btn-primary" disabled={finalGifts.length === 0}>
          📋 复制清单
        </button>
      </div>
      <div className="mt-3">
        <FeedbackMessage type={copyMessage.startsWith('复制失败') ? 'error' : 'success'}>{copyMessage}</FeedbackMessage>
      </div>
    </motion.div>
  )
}
