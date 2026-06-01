import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const fp = localStorage.getItem('fingerprint_id')
  if (fp) { config.headers['X-Fingerprint'] = fp }
  const token = sessionStorage.getItem('admin_token')
  if (token) { config.headers['Authorization'] = 'Bearer ' + token }
  return config
})

export const adminApi = {
  login: (password) => api.post('/admin/login', { password }),
  getGifts: () => api.get('/admin/gifts'),
  createGift: (data) => api.post('/admin/gifts', data),
  updateGift: (id, data) => api.put('/admin/gifts/' + id, data),
  updateGiftStatus: (id, status) => api.put('/admin/gifts/' + id + '/status', { status }),
  deleteGift: (id) => api.delete('/admin/gifts/' + id),
  getStats: () => api.get('/admin/stats'),
  exportGifts: () => api.post('/admin/export'),
  resetGifts: () => api.post('/admin/reset'),
}

export const drawApi = {
  getPlans: (budget) => api.post('/draw/plans', { budget }),
  startDraw: (fingerprintId, budget, planType) => api.post('/draw/start', {
    fingerprint_id: fingerprintId, budget, plan_type: planType,
  }),
  spinGift: (tier, fingerprintId, sessionId) => api.post('/draw/spin', {
    tier, fingerprint_id: fingerprintId, session_id: sessionId,
  }),
  claimGift: (fingerprintId, giftId) => api.post('/draw/claim', {
    fingerprint_id: fingerprintId, gift_id: giftId,
  }),
  releaseGift: (fingerprintId, giftId) => api.post('/draw/release', {
    fingerprint_id: fingerprintId, gift_id: giftId,
  }),
  getStatus: (fingerprintId) => api.get('/draw/status', {
    params: { fingerprint_id: fingerprintId },
  }),
}

export default api
