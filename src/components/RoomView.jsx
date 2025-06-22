import React, { useState, useEffect, useRef } from 'react'
import { formatDistanceToNow } from 'date-fns'

const RoomView = ({ room, users, messages, onSendMessage, onLeaveRoom, user }) => {
  const [messageText, setMessageText] = useState('')
  const [showUsers, setShowUsers] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (messageText.trim()) {
      onSendMessage(messageText)
      setMessageText('')
    }
  }

  const formatMessageTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="room-view">
      {/* Room Header */}
      <div className="room-header">
        <div className="room-info">
          <button className="back-btn" onClick={onLeaveRoom}>
            <i data-feather="arrow-left"></i>
          </button>
          <div className="room-details">
            <h2 className="room-name">{room.name}</h2>
            <div className="room-meta">
              <span className="user-count">
                <i data-feather="users"></i>
                {users.length} {users.length === 1 ? 'person' : 'people'}
              </span>
              {room.mode === 'professional' && (
                <span className="mode-badge professional">
                  <i data-feather="briefcase"></i>
                  Professional
                </span>
              )}
              {room.mode === 'casual' && (
                <span className="mode-badge casual">
                  <i data-feather="coffee"></i>
                  Casual
                </span>
              )}
            </div>
          </div>
        </div>
        
        <button 
          className="users-btn"
          onClick={() => setShowUsers(!showUsers)}
        >
          <i data-feather="users"></i>
        </button>
      </div>

      {/* Room Description */}
      {room.description && (
        <div className="room-description">
          <p>{room.description}</p>
        </div>
      )}

      {/* Users Panel */}
      {showUsers && (
        <div className="users-panel">
          <h3>People in this room</h3>
          <div className="users-list">
            {users.map(roomUser => (
              <div key={roomUser.id} className="user-item">
                <div className="user-avatar">
                  {roomUser.name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="user-info">
                  <span className="user-name">
                    {roomUser.name || 'Anonymous'}
                    {roomUser.id === user.id && <span className="you-badge">You</span>}
                  </span>
                  <span className="user-status">
                    <i data-feather="circle" className="status-online"></i>
                    Online
                  </span>
                </div>
                {roomUser.location && (
                  <div className="user-location">
                    <i data-feather="map-pin"></i>
                    <span>Nearby</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="messages-container">
        <div className="messages-list">
          {messages.length === 0 ? (
            <div className="empty-messages">
              <i data-feather="message-circle"></i>
              <p>No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((message, index) => {
              const isOwnMessage = message.user_id === user.id
              const showAvatar = index === 0 || messages[index - 1].user_id !== message.user_id
              
              return (
                <div 
                  key={message.id || index} 
                  className={`message ${isOwnMessage ? 'own' : 'other'}`}
                >
                  {!isOwnMessage && showAvatar && (
                    <div className="message-avatar">
                      {message.user_name?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                  )}
                  <div className="message-content">
                    {!isOwnMessage && showAvatar && (
                      <div className="message-sender">{message.user_name || 'Anonymous'}</div>
                    )}
                    <div className="message-bubble">
                      <p>{message.content}</p>
                      <span className="message-time">
                        {formatMessageTime(message.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Message Input */}
      <form className="message-form" onSubmit={handleSubmit}>
        <div className="message-input-container">
          <input
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder={room.mode === 'professional' 
              ? 'Share your thoughts professionally...' 
              : 'Type a message...'
            }
            maxLength="500"
            className="message-input"
          />
          <button 
            type="submit" 
            className="send-btn"
            disabled={!messageText.trim()}
          >
            <i data-feather="send"></i>
          </button>
        </div>
      </form>

      {/* Room Actions */}
      <div className="room-actions">
        <button className="action-btn" onClick={() => {
          const url = `${window.location.origin}/room/${room.id}`
          navigator.share ? 
            navigator.share({ title: room.name, url }) :
            navigator.clipboard.writeText(url).then(() => alert('Room link copied!'))
        }}>
          <i data-feather="share-2"></i>
          Share Room
        </button>
        
        <button className="action-btn danger" onClick={onLeaveRoom}>
          <i data-feather="log-out"></i>
          Leave Room
        </button>
      </div>
    </div>
  )
}

export default RoomView
