import React, { useState } from 'react'
import { api } from '../services/api'
import { formatDistanceToNow } from 'date-fns'

const FriendsList = ({ friends, onRefresh, user }) => {
  const [activeTab, setActiveTab] = useState('friends') // 'friends', 'requests', 'add'
  const [friendRequests, setFriendRequests] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)

  React.useEffect(() => {
    fetchFriendRequests()
  }, [])

  const fetchFriendRequests = async () => {
    try {
      const response = await api.get('/friends/requests')
      setFriendRequests(response.data)
    } catch (error) {
      console.error('Failed to fetch friend requests:', error)
    }
  }

  const searchUsers = async (query) => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    setLoading(true)
    try {
      const response = await api.get(`/users/search?q=${encodeURIComponent(query)}`)
      setSearchResults(response.data)
    } catch (error) {
      console.error('Failed to search users:', error)
    } finally {
      setLoading(false)
    }
  }

  const sendFriendRequest = async (userId) => {
    try {
      await api.post('/friends/request', { user_id: userId })
      // Update search results to show request sent
      setSearchResults(prev => 
        prev.map(u => u.id === userId ? { ...u, request_sent: true } : u)
      )
    } catch (error) {
      console.error('Failed to send friend request:', error)
      alert('Failed to send friend request')
    }
  }

  const respondToRequest = async (requestId, accept) => {
    try {
      await api.post(`/friends/requests/${requestId}`, { accept })
      fetchFriendRequests()
      if (accept) {
        onRefresh()
      }
    } catch (error) {
      console.error('Failed to respond to friend request:', error)
      alert('Failed to respond to friend request')
    }
  }

  const removeFriend = async (friendId) => {
    if (window.confirm('Are you sure you want to remove this friend?')) {
      try {
        await api.delete(`/friends/${friendId}`)
        onRefresh()
      } catch (error) {
        console.error('Failed to remove friend:', error)
        alert('Failed to remove friend')
      }
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    searchUsers(searchQuery)
  }

  return (
    <div className="friends-container">
      <div className="friends-header">
        <h2>
          <i data-feather="users"></i>
          Friends & Connections
        </h2>
      </div>

      {/* Tabs */}
      <div className="friends-tabs">
        <button 
          className={`tab ${activeTab === 'friends' ? 'active' : ''}`}
          onClick={() => setActiveTab('friends')}
        >
          <i data-feather="users"></i>
          Friends ({friends.length})
        </button>
        <button 
          className={`tab ${activeTab === 'requests' ? 'active' : ''}`}
          onClick={() => setActiveTab('requests')}
        >
          <i data-feather="user-plus"></i>
          Requests ({friendRequests.length})
        </button>
        <button 
          className={`tab ${activeTab === 'add' ? 'active' : ''}`}
          onClick={() => setActiveTab('add')}
        >
          <i data-feather="search"></i>
          Add Friends
        </button>
      </div>

      {/* Friends List */}
      {activeTab === 'friends' && (
        <div className="friends-list">
          {friends.length === 0 ? (
            <div className="empty-state">
              <i data-feather="user-plus"></i>
              <h3>No friends yet</h3>
              <p>Start connecting with people by searching for users or sending friend requests in rooms!</p>
            </div>
          ) : (
            friends.map(friend => (
              <div key={friend.id} className="friend-item">
                <div className="friend-avatar">
                  {friend.name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                
                <div className="friend-info">
                  <div className="friend-name">{friend.name || 'Anonymous'}</div>
                  <div className="friend-status">
                    {friend.is_online ? (
                      <span className="status online">
                        <i data-feather="circle"></i>
                        Online
                      </span>
                    ) : (
                      <span className="status offline">
                        <i data-feather="circle"></i>
                        Last seen {formatDistanceToNow(new Date(friend.last_seen), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                  
                  {friend.current_room && (
                    <div className="friend-room">
                      <i data-feather="map-pin"></i>
                      In {friend.current_room.name}
                    </div>
                  )}
                </div>

                <div className="friend-actions">
                  {friend.location_sharing_enabled && friend.location && (
                    <button className="action-btn" title="View on map">
                      <i data-feather="map"></i>
                    </button>
                  )}
                  
                  <button className="action-btn" title="Send message">
                    <i data-feather="message-circle"></i>
                  </button>
                  
                  <button 
                    className="action-btn danger" 
                    onClick={() => removeFriend(friend.id)}
                    title="Remove friend"
                  >
                    <i data-feather="user-minus"></i>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Friend Requests */}
      {activeTab === 'requests' && (
        <div className="requests-list">
          {friendRequests.length === 0 ? (
            <div className="empty-state">
              <i data-feather="inbox"></i>
              <h3>No pending requests</h3>
              <p>Friend requests will appear here when people want to connect with you.</p>
            </div>
          ) : (
            friendRequests.map(request => (
              <div key={request.id} className="request-item">
                <div className="request-avatar">
                  {request.sender_name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                
                <div className="request-info">
                  <div className="request-name">{request.sender_name || 'Anonymous'}</div>
                  <div className="request-time">
                    Sent {formatDistanceToNow(new Date(request.created_at), { addSuffix: true })}
                  </div>
                  {request.message && (
                    <div className="request-message">"{request.message}"</div>
                  )}
                </div>

                <div className="request-actions">
                  <button 
                    className="accept-btn"
                    onClick={() => respondToRequest(request.id, true)}
                  >
                    <i data-feather="check"></i>
                    Accept
                  </button>
                  <button 
                    className="decline-btn"
                    onClick={() => respondToRequest(request.id, false)}
                  >
                    <i data-feather="x"></i>
                    Decline
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Add Friends */}
      {activeTab === 'add' && (
        <div className="add-friends">
          <form onSubmit={handleSearch} className="search-form">
            <div className="search-input-container">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name or email..."
                className="search-input"
              />
              <button type="submit" className="search-btn" disabled={loading}>
                {loading ? (
                  <div className="spinner-small"></div>
                ) : (
                  <i data-feather="search"></i>
                )}
              </button>
            </div>
          </form>

          <div className="search-results">
            {searchResults.length === 0 && searchQuery ? (
              <div className="empty-state">
                <i data-feather="search"></i>
                <h3>No users found</h3>
                <p>Try searching with a different name or email address.</p>
              </div>
            ) : (
              searchResults.map(searchUser => (
                <div key={searchUser.id} className="search-result-item">
                  <div className="result-avatar">
                    {searchUser.name?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                  
                  <div className="result-info">
                    <div className="result-name">{searchUser.name || 'Anonymous'}</div>
                    {searchUser.bio && (
                      <div className="result-bio">{searchUser.bio}</div>
                    )}
                    <div className="result-mutual">
                      {searchUser.mutual_friends > 0 && (
                        <span>
                          <i data-feather="users"></i>
                          {searchUser.mutual_friends} mutual friend{searchUser.mutual_friends !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="result-actions">
                    {searchUser.id === user.id ? (
                      <span className="you-badge">You</span>
                    ) : searchUser.is_friend ? (
                      <span className="friend-badge">
                        <i data-feather="check"></i>
                        Friends
                      </span>
                    ) : searchUser.request_sent ? (
                      <span className="sent-badge">
                        <i data-feather="clock"></i>
                        Request Sent
                      </span>
                    ) : (
                      <button 
                        className="add-friend-btn"
                        onClick={() => sendFriendRequest(searchUser.id)}
                      >
                        <i data-feather="user-plus"></i>
                        Add Friend
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default FriendsList
