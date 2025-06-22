import React, { useEffect, useRef, useState } from 'react'

const MapView = ({ rooms, friends, userLocation, onJoinRoom }) => {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markersRef = useRef([])
  const [selectedRoom, setSelectedRoom] = useState(null)

  useEffect(() => {
    if (!mapInstanceRef.current && window.L) {
      initializeMap()
    }
    
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (mapInstanceRef.current) {
      updateMarkers()
    }
  }, [rooms, friends, userLocation])

  const initializeMap = () => {
    const defaultCenter = userLocation 
      ? [userLocation.latitude, userLocation.longitude]
      : [37.7749, -122.4194] // San Francisco default

    const map = window.L.map(mapRef.current, {
      zoomControl: false
    }).setView(defaultCenter, 15)

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map)

    // Add zoom control to bottom right
    window.L.control.zoom({
      position: 'bottomright'
    }).addTo(map)

    mapInstanceRef.current = map
    updateMarkers()
  }

  const updateMarkers = () => {
    if (!mapInstanceRef.current) return

    // Clear existing markers
    markersRef.current.forEach(marker => {
      mapInstanceRef.current.removeLayer(marker)
    })
    markersRef.current = []

    // Add user location marker
    if (userLocation) {
      const userIcon = window.L.divIcon({
        className: 'user-marker',
        html: '<div class="user-marker-inner"><i data-feather="user"></i></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      })

      const userMarker = window.L.marker(
        [userLocation.latitude, userLocation.longitude],
        { icon: userIcon }
      ).addTo(mapInstanceRef.current)

      userMarker.bindPopup(`
        <div class="marker-popup user-popup">
          <strong>Your Location</strong>
          <br>
          <small>Accuracy: ±${Math.round(userLocation.accuracy)}m</small>
        </div>
      `)

      markersRef.current.push(userMarker)
    }

    // Add room markers
    rooms.forEach(room => {
      if (room.location) {
        const roomIcon = window.L.divIcon({
          className: `room-marker ${room.mode}`,
          html: `
            <div class="room-marker-inner">
              <i data-feather="${room.mode === 'professional' ? 'briefcase' : 'coffee'}"></i>
              <span class="room-count">${room.user_count || 0}</span>
            </div>
          `,
          iconSize: [40, 40],
          iconAnchor: [20, 20]
        })

        const roomMarker = window.L.marker(
          [room.location.lat, room.location.lng],
          { icon: roomIcon }
        ).addTo(mapInstanceRef.current)

        roomMarker.bindPopup(`
          <div class="marker-popup room-popup">
            <div class="room-popup-header">
              <strong>${room.name}</strong>
              <span class="mode-badge ${room.mode}">
                ${room.mode === 'professional' ? '🏢' : '🎉'}
              </span>
            </div>
            ${room.description ? `<p>${room.description}</p>` : ''}
            <div class="room-popup-stats">
              <span><i data-feather="users"></i> ${room.user_count || 0}/${room.max_users}</span>
              ${room.is_private ? '<span><i data-feather="lock"></i> Private</span>' : ''}
            </div>
            <button class="join-room-btn" onclick="window.joinRoomFromMap('${room.id}')">
              ${room.user_count >= room.max_users ? 'Full' : 'Join Room'}
            </button>
          </div>
        `)

        roomMarker.on('click', () => {
          setSelectedRoom(room)
        })

        markersRef.current.push(roomMarker)
      }
    })

    // Add friend markers
    friends.forEach(friend => {
      if (friend.location && friend.location_sharing_enabled) {
        const friendIcon = window.L.divIcon({
          className: 'friend-marker',
          html: `
            <div class="friend-marker-inner">
              <div class="friend-avatar">
                ${friend.name?.charAt(0)?.toUpperCase() || 'F'}
              </div>
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        })

        const friendMarker = window.L.marker(
          [friend.location.lat, friend.location.lng],
          { icon: friendIcon }
        ).addTo(mapInstanceRef.current)

        friendMarker.bindPopup(`
          <div class="marker-popup friend-popup">
            <div class="friend-popup-header">
              <div class="friend-avatar-large">
                ${friend.name?.charAt(0)?.toUpperCase() || 'F'}
              </div>
              <div>
                <strong>${friend.name || 'Friend'}</strong>
                <br>
                <small>
                  <i data-feather="clock"></i>
                  Last seen: ${new Date(friend.last_seen).toLocaleTimeString()}
                </small>
              </div>
            </div>
          </div>
        `)

        markersRef.current.push(friendMarker)
      }
    })

    // Update feather icons
    setTimeout(() => {
      if (window.feather) {
        window.feather.replace()
      }
    }, 100)
  }

  // Make join room function available globally for popup buttons
  useEffect(() => {
    window.joinRoomFromMap = (roomId) => {
      onJoinRoom(roomId)
    }
    
    return () => {
      delete window.joinRoomFromMap
    }
  }, [onJoinRoom])

  const centerOnUser = () => {
    if (mapInstanceRef.current && userLocation) {
      mapInstanceRef.current.setView(
        [userLocation.latitude, userLocation.longitude], 
        18
      )
    }
  }

  const centerOnRooms = () => {
    if (mapInstanceRef.current && rooms.length > 0) {
      const roomsWithLocation = rooms.filter(room => room.location)
      if (roomsWithLocation.length > 0) {
        const group = window.L.featureGroup(
          roomsWithLocation.map(room => 
            window.L.marker([room.location.lat, room.location.lng])
          )
        )
        mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1))
      }
    }
  }

  return (
    <div className="map-view">
      <div className="map-header">
        <h2>
          <i data-feather="map"></i>
          Location Map
        </h2>
        <div className="map-controls">
          <button className="map-control-btn" onClick={centerOnUser}>
            <i data-feather="crosshair"></i>
            My Location
          </button>
          <button className="map-control-btn" onClick={centerOnRooms}>
            <i data-feather="home"></i>
            Show Rooms
          </button>
        </div>
      </div>

      <div className="map-legend">
        <div className="legend-item">
          <div className="legend-marker user">
            <i data-feather="user"></i>
          </div>
          <span>You</span>
        </div>
        <div className="legend-item">
          <div className="legend-marker room casual">
            <i data-feather="coffee"></i>
          </div>
          <span>Casual Room</span>
        </div>
        <div className="legend-item">
          <div className="legend-marker room professional">
            <i data-feather="briefcase"></i>
          </div>
          <span>Professional Room</span>
        </div>
        <div className="legend-item">
          <div className="legend-marker friend">
            <span>F</span>
          </div>
          <span>Friend</span>
        </div>
      </div>

      <div ref={mapRef} className="map-container"></div>

      {!userLocation && (
        <div className="map-overlay">
          <div className="location-prompt">
            <i data-feather="map-pin"></i>
            <h3>Location Access Needed</h3>
            <p>Enable location permissions to see your position and nearby rooms on the map.</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default MapView
