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

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.code === 'ECONNABORTED') {
      err.message = '请求超时，请检查网络后重试'
    } else if (err.response?.status === 503) {
      err.message = '系统繁忙，请稍后重试'
    } else if (!err.response) {
      err.message = '网络连接失败，请稍后重试'
    }
    return Promise.reject(err)
  }
)

export const adminApi = {
  login: (password) => api.post('/admin/login', { password }),
  // 礼物管理
  getGifts: (params) => api.get('/admin/gifts', { params }),
  createGift: (data) => api.post('/admin/gifts', data),
  updateGift: (id, data) => api.put('/admin/gifts/' + id, data),
  updateGiftStatus: (id, status) => api.put('/admin/gifts/' + id + '/status', { status }),
  deleteGift: (id) => api.delete('/admin/gifts/' + id),
  unlockGift: (id) => api.post('/admin/gifts/' + id + '/unlock'),
  // 统计
  getStats: () => api.get('/admin/stats'),
  // 导出 & 重置
  exportGifts: () => api.post('/admin/export'),
  resetGifts: () => api.post('/admin/reset'),
  // 用户管理
  getUsers: (params) => api.get('/admin/users', { params }),
  getUserDetail: (phone) => api.get('/admin/users/' + phone),
  resetUser: (phone) => api.post('/admin/users/' + phone + '/reset'),
  // 系统配置
  getConfig: () => api.get('/admin/config'),
  updateConfig: (data) => api.put('/admin/config', data),
  // 活动日志
  getActivityLog: (params) => api.get('/admin/activity-log', { params }),
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
  getHistory: (fingerprintId) => api.get('/draw/history', {
    params: { fingerprint_id: fingerprintId },
  }),
}

export default api
