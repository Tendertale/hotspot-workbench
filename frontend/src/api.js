const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

async function request(path, options = {}) {
  const { headers = {}, ...requestOptions } = options
  const response = await fetch(`${API_BASE}${path}`, {
    ...requestOptions,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  })

  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string') {
        message = payload.detail
      } else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((item) => item.msg).join('；')
      }
    } catch {
      // Keep the HTTP fallback message when the response has no JSON body.
    }
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  return response.json()
}

export const api = {
  aiConfig: () => request('/ai/config'),
  verifyDeepSeek: (apiKey) =>
    request('/ai/verify', {
      method: 'POST',
      headers: { 'X-DeepSeek-API-Key': apiKey },
    }),
  listHotspots: (filters) => request(`/hotspots?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== '' && value != null))}`),
  stats: () => request('/stats'),
  hotspot: (id) => request(`/hotspots/${id}`),
  createHotspot: (payload) =>
    request('/hotspots', { method: 'POST', body: JSON.stringify(payload) }),
  analyze: (id, { mode, expected_version, apiKey = '' }) =>
    request(`/hotspots/${id}/analyze`, {
      method: 'POST',
      headers: apiKey ? { 'X-DeepSeek-API-Key': apiKey } : {},
      body: JSON.stringify({ mode, expected_version }),
    }),
  editAnalysis: (id, payload) =>
    request(`/hotspots/${id}/analysis`, { method: 'PATCH', body: JSON.stringify(payload) }),
  confirmAnalysis: (id, payload) =>
    request(`/hotspots/${id}/analysis/confirm`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateStatus: (id, payload) =>
    request(`/hotspots/${id}/status`, { method: 'PATCH', body: JSON.stringify(payload) }),
}
