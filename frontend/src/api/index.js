import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
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
  getGifts: () => api.get('/admin/gifts'),
  createGift: (data) => api.post('/admin/gifts', data),
  updateGift: (id, data) => api.put(`/admin/gifts/${id}`, data),
  deleteGift: (id) => api.delete(`/admin/gifts/${id}`),
  getStats: () => api.get('/admin/stats'),
  exportGifts: () => api.post('/admin/export'),
  resetGifts: (confirmation) => api.post('/admin/reset', { confirmation }),
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
