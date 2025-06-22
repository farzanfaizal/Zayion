import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

const ProfileModal = ({ user, onClose, onLogout, onUpdateProfile }) => {
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState({
    name: user.name || '',
    phone: user.phone || '',
    bio: user.bio || '',
    location_sharing_enabled: user.location_sharing_enabled ?? true,
    profile_visibility: user.profile_visibility || 'friends',
    notification_enabled: user.notification_enabled ?? true
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // Update feather icons when modal opens
    setTimeout(() => {
      if (window.feather) {
        window.feather.replace()
      }
    }, 100)
  }, [])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await api.put('/user/profile', formData)
      if (response.data.success) {
        onUpdateProfile()
        setEditMode(false)
      } else {
        setError(response.data.message || 'Failed to update profile')
      }
    } catch (error) {
      setError(error.response?.data?.message || 'Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      try {
        await api.delete('/user/account')
        onLogout()
      } catch (error) {
        setError('Failed to delete account. Please try again.')
      }
    }
  }

  return (
    <div className="modal-overlay">
      <div className="profile-modal">
        <div className="modal-header">
          <h2>
            <i data-feather="user"></i>
            Profile Settings
          </h2>
          <button className="close-btn" onClick={onClose}>
            <i data-feather="x"></i>
          </button>
        </div>

        <div className="profile-content">
          {!editMode ? (
            // View Mode
            <div className="profile-view">
              <div className="profile-avatar-section">
                <div className="profile-avatar-large">
                  {user.name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="profile-info">
                  <h3>{user.name || 'Anonymous User'}</h3>
                  <p className="profile-email">{user.email}</p>
                  {user.bio && <p className="profile-bio">{user.bio}</p>}
                </div>
              </div>

              <div className="profile-stats">
                <div className="stat-item">
                  <i data-feather="calendar"></i>
                  <div>
                    <span className="stat-label">Member since</span>
                    <span className="stat-value">
                      {new Date(user.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                
                <div className="stat-item">
                  <i data-feather="users"></i>
                  <div>
                    <span className="stat-label">Rooms joined</span>
                    <span className="stat-value">{user.rooms_joined || 0}</span>
                  </div>
                </div>
              </div>

              <div className="privacy-settings">
                <h4>Privacy Settings</h4>
                <div className="setting-item">
                  <div className="setting-info">
                    <i data-feather="map-pin"></i>
                    <span>Location Sharing</span>
                  </div>
                  <span className={`status ${user.location_sharing_enabled ? 'enabled' : 'disabled'}`}>
                    {user.location_sharing_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>

                <div className="setting-item">
                  <div className="setting-info">
                    <i data-feather="eye"></i>
                    <span>Profile Visibility</span>
                  </div>
                  <span className="status">
                    {user.profile_visibility === 'public' ? 'Public' : 
                     user.profile_visibility === 'friends' ? 'Friends Only' : 'Private'}
                  </span>
                </div>

                <div className="setting-item">
                  <div className="setting-info">
                    <i data-feather="bell"></i>
                    <span>Notifications</span>
                  </div>
                  <span className={`status ${user.notification_enabled ? 'enabled' : 'disabled'}`}>
                    {user.notification_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>

              <div className="profile-actions">
                <button className="edit-btn" onClick={() => setEditMode(true)}>
                  <i data-feather="edit-2"></i>
                  Edit Profile
                </button>
              </div>
            </div>
          ) : (
            // Edit Mode
            <form onSubmit={handleSubmit} className="profile-form">
              <div className="form-group">
                <label htmlFor="name">Full Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter your full name"
                  maxLength="50"
                />
              </div>

              <div className="form-group">
                <label htmlFor="phone">Phone Number</label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="Enter your phone number"
                />
              </div>

              <div className="form-group">
                <label htmlFor="bio">Bio</label>
                <textarea
                  id="bio"
                  name="bio"
                  value={formData.bio}
                  onChange={handleChange}
                  placeholder="Tell others about yourself..."
                  maxLength="200"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label htmlFor="profile_visibility">Profile Visibility</label>
                <select
                  id="profile_visibility"
                  name="profile_visibility"
                  value={formData.profile_visibility}
                  onChange={handleChange}
                >
                  <option value="private">Private</option>
                  <option value="friends">Friends Only</option>
                  <option value="public">Public</option>
                </select>
              </div>

              <div className="checkbox-groups">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="location_sharing_enabled"
                    checked={formData.location_sharing_enabled}
                    onChange={handleChange}
                  />
                  <span className="checkmark"></span>
                  <div className="checkbox-info">
                    <span>Enable Location Sharing</span>
                    <small>Allow friends to see your location on the map</small>
                  </div>
                </label>

                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="notification_enabled"
                    checked={formData.notification_enabled}
                    onChange={handleChange}
                  />
                  <span className="checkmark"></span>
                  <div className="checkbox-info">
                    <span>Enable Notifications</span>
                    <small>Receive alerts for room invites and friend requests</small>
                  </div>
                </label>
              </div>

              {error && (
                <div className="error-message">
                  <i data-feather="alert-circle"></i>
                  {error}
                </div>
              )}

              <div className="form-actions">
                <button 
                  type="button" 
                  className="cancel-btn"
                  onClick={() => {
                    setEditMode(false)
                    setError('')
                    // Reset form data
                    setFormData({
                      name: user.name || '',
                      phone: user.phone || '',
                      bio: user.bio || '',
                      location_sharing_enabled: user.location_sharing_enabled ?? true,
                      profile_visibility: user.profile_visibility || 'friends',
                      notification_enabled: user.notification_enabled ?? true
                    })
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="save-btn" disabled={loading}>
                  {loading ? (
                    <>
                      <div className="spinner-small"></div>
                      Saving...
                    </>
                  ) : (
                    <>
                      <i data-feather="check"></i>
                      Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="profile-footer">
          <button className="logout-btn" onClick={onLogout}>
            <i data-feather="log-out"></i>
            Sign Out
          </button>
          <button className="delete-account-btn" onClick={handleDeleteAccount}>
            <i data-feather="trash-2"></i>
            Delete Account
          </button>
        </div>
      </div>
    </div>
  )
}

export default ProfileModal
