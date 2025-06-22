let socket = null
let messageHandler = null
let reconnectAttempts = 0
const maxReconnectAttempts = 5
const reconnectDelay = 1000

export const initializeWebSocket = (userId, onMessage) => {
  messageHandler = onMessage
  connectWebSocket(userId)
}

const connectWebSocket = (userId) => {
  try {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      console.log('WebSocket connected')
      reconnectAttempts = 0
      
      // Authenticate with user ID
      socket.send(JSON.stringify({
        type: 'authenticate',
        userId: userId
      }))
    }

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        if (messageHandler) {
          messageHandler(message)
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    socket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason)
      
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++
        console.log(`Attempting to reconnect... (${reconnectAttempts}/${maxReconnectAttempts})`)
        
        setTimeout(() => {
          connectWebSocket(userId)
        }, reconnectDelay * reconnectAttempts)
      } else {
        console.error('Max reconnection attempts reached')
        if (messageHandler) {
          messageHandler({
            type: 'connection_error',
            message: 'Unable to maintain connection to server'
          })
        }
      }
    }

    socket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

  } catch (error) {
    console.error('Failed to create WebSocket connection:', error)
  }
}

export const sendMessage = (message) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message))
  } else {
    console.warn('WebSocket not connected, message not sent:', message)
  }
}

export const closeWebSocket = () => {
  if (socket) {
    socket.close()
    socket = null
  }
  messageHandler = null
  reconnectAttempts = 0
}
