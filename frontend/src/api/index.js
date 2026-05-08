import axios from 'axios'

export const getApiErrorMessage = (error, fallback = '请求失败，请稍后重试') => {
  if (error?.code === 'ECONNABORTED') return '请求超时，请检查网络后重试'
  if (!error?.response) return error?.message ? `网络异常：${error.message}` : fallback

  const detail = error.response.data?.detail || error.response.data?.message
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join('；')
  }
  if (typeof detail === 'object' && detail !== null) {
    return detail.msg || detail.message || JSON.stringify(detail)
  }
  if (detail) return detail

  const statusText = error.response.statusText || '服务器错误'
  return `${fallback}（${error.response.status} ${statusText}）`
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

export const setAdminToken = (token) => {
  if (token) {
    localStorage.setItem('admin_token', token)
  } else {
    localStorage.removeItem('admin_token')
  }
}

api.interceptors.request.use((config) => {
  const fp = localStorage.getItem('fingerprint_id')
  if (fp) {
    config.headers['X-Fingerprint'] = fp
  }

  const token = localStorage.getItem('admin_token')
  if (token && config.url?.startsWith('/admin')) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token')
    }
    return Promise.reject(error)
  },
)

export const adminApi = {
  login: (password) => api.post('/admin/login', { password }),
  getGifts: (params) => api.get('/admin/gifts', { params }),
  createGift: (data) => api.post('/admin/gifts', data),
  updateGift: (id, data) => api.put(`/admin/gifts/${id}`, data),
  deleteGift: (id) => api.delete(`/admin/gifts/${id}`),
  importGifts: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/admin/gifts/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  bulkDeleteGifts: (giftIds) => api.post('/admin/gifts/bulk-delete', { gift_ids: giftIds }),
  bulkUpdateTier: (giftIds, tier) => api.post('/admin/gifts/bulk-tier', { gift_ids: giftIds, tier }),
  bulkUpdateStatus: (giftIds, status) => api.post('/admin/gifts/bulk-status', { gift_ids: giftIds, status }),
  getStats: () => api.get('/admin/stats'),
  getCampaign: () => api.get('/admin/campaign/current'),
  updateCampaign: (data) => api.put('/admin/campaign/current', data),
  exportGifts: (exportType = 'claimed', groupBy = 'session') => api.post('/admin/export', null, { params: { export_type: exportType, group_by: groupBy } }),
  resetGifts: (confirmation) => api.post('/admin/reset', { confirmation }),
}

export const drawApi = {
  getCampaign: () => api.get('/draw/campaign'),
  getPlans: (budget) => api.post('/draw/plans', { budget }),
  startDraw: (fingerprintId, budget, planType) => api.post('/draw/start', {
    fingerprint_id: fingerprintId,
    budget,
    plan_type: planType,
  }),
  spinGift: (sessionId, fingerprintId) => api.post('/draw/spin', {
    session_id: sessionId,
    fingerprint_id: fingerprintId,
  }),
  claimGift: (fingerprintId, giftId, sessionId) => api.post('/draw/claim', {
    fingerprint_id: fingerprintId,
    gift_id: giftId,
    session_id: sessionId,
  }),
  releaseGift: (fingerprintId, giftId, sessionId) => api.post('/draw/release', {
    fingerprint_id: fingerprintId,
    gift_id: giftId,
    session_id: sessionId,
  }),
  getStatus: (fingerprintId, sessionId) => api.get('/draw/status', {
    params: {
      fingerprint_id: fingerprintId,
      ...(sessionId ? { session_id: sessionId } : {}),
    },
  }),
}

export default api
