import React, { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { calculateDistance } from '../utils/proximity'

const RoomList = ({ rooms, onJoinRoom, onCreateRoom, userLocation, mode }) => {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [roomName, setRoomName] = useState('')
  const [roomDescription, setRoomDescription] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [maxUsers, setMaxUsers] = useState(10)

  const handleCreateRoom = (e) => {
    e.preventDefault()
    
    if (!roomName.trim()) {
      alert('Please enter a room name')
      return
    }

    onCreateRoom({
      name: roomName.trim(),
      description: roomDescription.trim(),
      isPrivate,
      maxUsers,
      mode
    })

    // Reset form
    setRoomName('')
    setRoomDescription('')
    setIsPrivate(false)
    setMaxUsers(10)
    setShowCreateForm(false)
  }

  const getRoomDistance = (room) => {
    if (!userLocation || !room.location) return null
    return calculateDistance(
      userLocation.latitude,
      userLocation.longitude,
      room.location.lat,
      room.location.lng
    )
  }

  const sortedRooms = rooms
    .filter(room => room.mode === mode)
    .sort((a, b) => {
      const distA = getRoomDistance(a) || Infinity
      const distB = getRoomDistance(b) || Infinity
      return distA - distB
    })

  return (
    <div className="room-list-container">
      <div className="room-list-header">
        <h2>
          {mode === 'professional' ? '🏢 Professional Rooms' : '🎉 Casual Rooms'}
        </h2>
        <button 
          className="create-room-btn"
          onClick={() => setShowCreateForm(true)}
        >
          <i data-feather="plus"></i>
          Create Room
        </button>
      </div>

      {!userLocation && (
        <div className="location-warning">
          <i data-feather="map-pin"></i>
          <p>Enable location access to see nearby rooms and create your own!</p>
        </div>
      )}

      {showCreateForm && (
        <div className="modal-overlay">
          <div className="create-room-modal">
            <div className="modal-header">
              <h3>Create New Room</h3>
              <button 
                className="close-btn"
                onClick={() => setShowCreateForm(false)}
              >
                <i data-feather="x"></i>
              </button>
            </div>

            <form onSubmit={handleCreateRoom} className="create-room-form">
              <div className="form-group">
                <label htmlFor="roomName">Room Name *</label>
                <input
                  type="text"
                  id="roomName"
                  value={roomName}
                  onChange={(e) => setRoomName(e.target.value)}
                  placeholder={mode === 'professional' ? 'Conference Room A' : 'Coffee Chat'}
                  maxLength="50"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="roomDescription">Description</label>
                <textarea
                  id="roomDescription"
                  value={roomDescription}
                  onChange={(e) => setRoomDescription(e.target.value)}
                  placeholder={mode === 'professional' 
                    ? 'Quarterly planning meeting for Q2 2025' 
                    : 'Come hang out and chat about anything!'
                  }
                  maxLength="200"
                  rows="3"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="maxUsers">Max Users</label>
                  <select
                    id="maxUsers"
                    value={maxUsers}
                    onChange={(e) => setMaxUsers(parseInt(e.target.value))}
                  >
                    <option value="5">5 people</option>
                    <option value="10">10 people</option>
                    <option value="20">20 people</option>
                    <option value="50">50 people</option>
                  </select>
                </div>

                <div className="form-group checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={isPrivate}
                      onChange={(e) => setIsPrivate(e.target.checked)}
                    />
                    <span className="checkmark"></span>
                    Private Room
                  </label>
                </div>
              </div>

              <div className="form-actions">
                <button 
                  type="button" 
                  className="cancel-btn"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="create-btn">
                  Create Room
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="rooms-grid">
        {sortedRooms.length === 0 ? (
          <div className="empty-state">
            <i data-feather="map-pin"></i>
            <h3>No rooms nearby</h3>
            <p>
              {mode === 'professional' 
                ? 'Be the first to create a professional networking room in this area!'
                : 'Start a casual conversation by creating the first room here!'
              }
            </p>
          </div>
        ) : (
          sortedRooms.map(room => {
            const distance = getRoomDistance(room)
            const isNearby = distance && distance < 0.1 // Within 100 meters
            
            return (
              <div 
                key={room.id} 
                className={`room-card ${isNearby ? 'nearby' : ''}`}
              >
                <div className="room-header">
                  <div className="room-info">
                    <h3 className="room-name">{room.name}</h3>
                    <div className="room-meta">
                      <span className="room-users">
                        <i data-feather="users"></i>
                        {room.user_count || 0}/{room.max_users}
                      </span>
                      {room.is_private && (
                        <span className="private-badge">
                          <i data-feather="lock"></i>
                          Private
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {distance && (
                    <div className="room-distance">
                      <i data-feather="navigation"></i>
                      {distance < 0.001 
                        ? '<1m' 
                        : distance < 1 
                          ? `${Math.round(distance * 1000)}m`
                          : `${distance.toFixed(1)}km`
                      }
                    </div>
                  )}
                </div>

                {room.description && (
                  <p className="room-description">{room.description}</p>
                )}

                <div className="room-footer">
                  <div className="room-time">
                    <i data-feather="clock"></i>
                    Created {formatDistanceToNow(new Date(room.created_at), { addSuffix: true })}
                  </div>
                  
                  <button 
                    className="join-btn"
                    onClick={() => onJoinRoom(room.id)}
                    disabled={room.user_count >= room.max_users}
                  >
                    {room.user_count >= room.max_users ? 'Full' : 'Join'}
                  </button>
                </div>

                {isNearby && (
                  <div className="nearby-indicator">
                    <i data-feather="radio"></i>
                    Very close
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default RoomList
