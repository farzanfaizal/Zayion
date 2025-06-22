// API service for making HTTP requests
const API_BASE_URL = '/api'

class APIService {
  constructor() {
    this.defaults = {
      headers: {
        common: {
          'Content-Type': 'application/json'
        }
      }
    }
  }

  async request(method, url, data = null, config = {}) {
    const fullUrl = `${API_BASE_URL}${url}`
    
    const requestConfig = {
      method: method.toUpperCase(),
      headers: {
        ...this.defaults.headers.common,
        ...config.headers
      }
    }

    if (data && (method.toUpperCase() === 'POST' || method.toUpperCase() === 'PUT' || method.toUpperCase() === 'PATCH')) {
      requestConfig.body = JSON.stringify(data)
    }

    try {
      const response = await fetch(fullUrl, requestConfig)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`)
      }

      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        const responseData = await response.json()
        return { data: responseData, status: response.status }
      } else {
        return { data: null, status: response.status }
      }
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Network error - please check your connection')
      }
      throw error
    }
  }

  async get(url, config = {}) {
    return this.request('GET', url, null, config)
  }

  async post(url, data, config = {}) {
    return this.request('POST', url, data, config)
  }

  async put(url, data, config = {}) {
    return this.request('PUT', url, data, config)
  }

  async patch(url, data, config = {}) {
    return this.request('PATCH', url, data, config)
  }

  async delete(url, config = {}) {
    return this.request('DELETE', url, null, config)
  }
}

export const api = new APIService()
