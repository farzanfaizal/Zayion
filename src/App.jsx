import React, { useState, useEffect } from 'react'
import AuthForm from './components/AuthForm'
import RoomList from './components/RoomList'
import RoomView from './components/RoomView'
import MapView from './components/MapView'
import ProfileModal from './components/ProfileModal'
import FriendsList from './components/FriendsList'
import { initializeWebSocket, sendMessage } from './services/websocket'
import { getCurrentLocation, startLocationTracking, stopLocationTracking } from './services/location'
import { api } from './services/api'
import './styles/App.css'

function App() {
  const [user, setUser] = useState(null)
  const [currentView, setCurrentView] = useState('rooms') // 'rooms', 'room', 'map', 'friends'
  const [currentRoom, setCurrentRoom] = useState(null)
  const [rooms, setRooms] = useState([])
  const [friends, setFriends] = useState([])
  const [userLocation, setUserLocation] = useState(null)
  const [showProfile, setShowProfile] = useState(false)
  const [mode, setMode] = useState('casual') // 'professional' or 'casual'
  const [roomUsers, setRoomUsers] = useState([])
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('zayion_token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      fetchUserProfile()
    } else {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (user) {
      initializeWebSocket(user.id, handleWebSocketMessage)
      fetchRooms()
      fetchFriends()
      startLocationTracking(handleLocationUpdate)
    }
    
    return () => {
      stopLocationTracking()
    }
  }, [user])

  const fetchUserProfile = async () => {
    try {
      const response = await api.get('/user/profile')
      setUser(response.data)
      setLoading(false)
    } catch (error) {
      localStorage.removeItem('zayion_token')
      delete api.defaults.headers.common['Authorization']
      setLoading(false)
    }
  }

  const fetchRooms = async () => {
    try {
      const response = await api.get('/rooms/nearby')
      setRooms(response.data)
    } catch (error) {
      console.error('Failed to fetch rooms:', error)
    }
  }

  const fetchFriends = async () => {
    try {
      const response = await api.get('/friends')
      setFriends(response.data)
    } catch (error) {
      console.error('Failed to fetch friends:', error)
    }
  }

  const handleLocationUpdate = (location) => {
    setUserLocation(location)
    if (user) {
      sendMessage({
        type: 'location_update',
        location: {
          lat: location.latitude,
          lng: location.longitude,
          accuracy: location.accuracy,
          timestamp: Date.now()
        }
      })
    }
  }

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'room_users_update':
        setRoomUsers(message.users)
        break
      case 'new_message':
        setMessages(prev => [...prev, message.message])
        break
      case 'room_joined':
        setCurrentRoom(message.room)
        setMessages(message.messages || [])
        setRoomUsers(message.users || [])
        setCurrentView('room')
        break
      case 'rooms_update':
        setRooms(message.rooms)
        break
      case 'friend_request':
        // Handle friend request notification
        fetchFriends()
        break
      default:
        console.log('Unknown message type:', message.type)
    }
  }

  const handleLogin = (userData, token) => {
    localStorage.setItem('zayion_token', token)
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('zayion_token')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
    setCurrentView('rooms')
    setCurrentRoom(null)
    stopLocationTracking()
  }

  const handleJoinRoom = async (roomId) => {
    try {
      if (!userLocation) {
        const location = await getCurrentLocation()
        setUserLocation(location)
      }
      
      sendMessage({
        type: 'join_room',
        roomId: roomId,
        location: userLocation
      })
    } catch (error) {
      console.error('Failed to join room:', error)
      alert('Failed to join room. Please ensure location permissions are enabled.')
    }
  }

  const handleCreateRoom = async (roomData) => {
    try {
      if (!userLocation) {
        const location = await getCurrentLocation()
        setUserLocation(location)
      }

      const response = await api.post('/rooms/create', {
        ...roomData,
        location: userLocation,
        mode: mode
      })

      const newRoom = response.data
      setRooms(prev => [newRoom, ...prev])
      handleJoinRoom(newRoom.id)
    } catch (error) {
      console.error('Failed to create room:', error)
      alert('Failed to create room. Please try again.')
    }
  }

  const handleSendMessage = (messageText) => {
    if (currentRoom && messageText.trim()) {
      sendMessage({
        type: 'send_message',
        roomId: currentRoom.id,
        message: messageText.trim()
      })
    }
  }

  const handleLeaveRoom = () => {
    if (currentRoom) {
      sendMessage({
        type: 'leave_room',
        roomId: currentRoom.id
      })
      setCurrentRoom(null)
      setRoomUsers([])
      setMessages([])
      setCurrentView('rooms')
    }
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        Loading Zayion...
      </div>
    )
  }

  if (!user) {
    return <AuthForm onLogin={handleLogin} />
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1 className="app-title">Zayion</h1>
            <div className="mode-toggle">
              <button 
                className={`mode-btn ${mode === 'casual' ? 'active' : ''}`}
                onClick={() => setMode('casual')}
              >
                🎉 Casual
              </button>
              <button 
                className={`mode-btn ${mode === 'professional' ? 'active' : ''}`}
                onClick={() => setMode('professional')}
              >
                🏢 Professional
              </button>
            </div>
          </div>
          <div className="header-right">
            <button 
              className="profile-btn"
              onClick={() => setShowProfile(true)}
            >
              <div className="avatar">
                {user.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="app-nav">
        <button 
          className={`nav-btn ${currentView === 'rooms' ? 'active' : ''}`}
          onClick={() => setCurrentView('rooms')}
        >
          <i data-feather="home"></i>
          Rooms
        </button>
        <button 
          className={`nav-btn ${currentView === 'map' ? 'active' : ''}`}
          onClick={() => setCurrentView('map')}
        >
          <i data-feather="map"></i>
          Map
        </button>
        <button 
          className={`nav-btn ${currentView === 'friends' ? 'active' : ''}`}
          onClick={() => setCurrentView('friends')}
        >
          <i data-feather="users"></i>
          Friends
        </button>
      </nav>

      {/* Main Content */}
      <main className="app-main">
        {currentView === 'rooms' && (
          <RoomList 
            rooms={rooms}
            onJoinRoom={handleJoinRoom}
            onCreateRoom={handleCreateRoom}
            userLocation={userLocation}
            mode={mode}
          />
        )}
        
        {currentView === 'room' && currentRoom && (
          <RoomView 
            room={currentRoom}
            users={roomUsers}
            messages={messages}
            onSendMessage={handleSendMessage}
            onLeaveRoom={handleLeaveRoom}
            user={user}
          />
        )}
        
        {currentView === 'map' && (
          <MapView 
            rooms={rooms}
            friends={friends}
            userLocation={userLocation}
            onJoinRoom={handleJoinRoom}
          />
        )}
        
        {currentView === 'friends' && (
          <FriendsList 
            friends={friends}
            onRefresh={fetchFriends}
            user={user}
          />
        )}
      </main>

      {/* Profile Modal */}
      {showProfile && (
        <ProfileModal 
          user={user}
          onClose={() => setShowProfile(false)}
          onLogout={handleLogout}
          onUpdateProfile={fetchUserProfile}
        />
      )}
    </div>
  )
}

export default App
