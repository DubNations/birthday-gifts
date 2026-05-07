import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const fp = localStorage.getItem('fingerprint_id')
  if (fp) {
    config.headers['X-Fingerprint'] = fp
  }
  return config
})

export const adminApi = {
  getGifts: (password) => api.get('/admin/gifts', { params: { password } }),
  createGift: (password, data) => api.post('/admin/gifts', data, { params: { password } }),
  updateGift: (password, id, data) => api.put(`/admin/gifts/${id}`, data, { params: { password } }),
  deleteGift: (password, id) => api.delete(`/admin/gifts/${id}`, { params: { password } }),
  getStats: (password) => api.get('/admin/stats', { params: { password } }),
  exportGifts: (password) => api.post('/admin/export', null, { params: { password } }),
  resetGifts: (password) => api.post('/admin/reset', null, { params: { password } }),
}

export const drawApi = {
  getPlans: (budget) => api.post('/draw/plans', { budget }),
  startDraw: (fingerprintId, budget, planType) => api.post('/draw/start', {
    fingerprint_id: fingerprintId,
    budget,
    plan_type: planType,
  }),
  spinGift: (tier, fingerprintId) => api.post('/draw/spin', null, {
    params: { tier, fingerprint_id: fingerprintId },
  }),
  claimGift: (fingerprintId, giftId) => api.post('/draw/claim', {
    fingerprint_id: fingerprintId,
    gift_id: giftId,
  }),
  releaseGift: (fingerprintId, giftId) => api.post('/draw/release', {
    fingerprint_id: fingerprintId,
    gift_id: giftId,
  }),
  getStatus: (fingerprintId) => api.get('/draw/status', {
    params: { fingerprint_id: fingerprintId },
  }),
}

export default api
