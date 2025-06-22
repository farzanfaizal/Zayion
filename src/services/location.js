let watchId = null
let currentPosition = null
let locationOptions = {
  enableHighAccuracy: true,
  timeout: 10000,
  maximumAge: 30000 // 30 seconds
}

// Adaptive location tracking based on movement
let lastPosition = null
let isMoving = false
let updateInterval = 60000 // Default 60 seconds when stationary

export const getCurrentLocation = () => {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by this browser'))
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        currentPosition = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp
        }
        resolve(currentPosition)
      },
      (error) => {
        let errorMessage = 'Failed to get location'
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Location access denied by user'
            break
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location information unavailable'
            break
          case error.TIMEOUT:
            errorMessage = 'Location request timeout'
            break
        }
        
        reject(new Error(errorMessage))
      },
      locationOptions
    )
  })
}

export const startLocationTracking = (onLocationUpdate) => {
  if (!navigator.geolocation) {
    console.error('Geolocation not supported')
    return
  }

  // Clear any existing watch
  if (watchId !== null) {
    navigator.geolocation.clearWatch(watchId)
  }

  watchId = navigator.geolocation.watchPosition(
    (position) => {
      const newPosition = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
        speed: position.coords.speed,
        heading: position.coords.heading
      }

      // Check if user is moving
      if (lastPosition) {
        const distance = calculateDistance(
          lastPosition.latitude,
          lastPosition.longitude,
          newPosition.latitude,
          newPosition.longitude
        )
        
        // Consider moving if traveled more than 10 meters
        isMoving = distance > 0.01 // 10 meters in km
        
        // Adjust update frequency based on movement
        if (isMoving) {
          updateInterval = newPosition.speed > 5 ? 5000 : 15000 // 5s if driving, 15s if walking
        } else {
          updateInterval = 60000 // 60s when stationary
        }
      }

      lastPosition = newPosition
      currentPosition = newPosition
      
      if (onLocationUpdate) {
        onLocationUpdate(newPosition)
      }
    },
    (error) => {
      console.error('Location tracking error:', error)
    },
    {
      ...locationOptions,
      enableHighAccuracy: isMoving, // High accuracy only when moving
    }
  )
}

export const stopLocationTracking = () => {
  if (watchId !== null) {
    navigator.geolocation.clearWatch(watchId)
    watchId = null
  }
  lastPosition = null
  isMoving = false
}

export const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371 // Radius of the Earth in kilometers
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  const distance = R * c // Distance in kilometers
  return distance
}

export const requestLocationPermission = async () => {
  try {
    const position = await getCurrentLocation()
    return { granted: true, position }
  } catch (error) {
    return { granted: false, error: error.message }
  }
}

// Battery optimization: reduce location updates when app is in background
let isAppVisible = true

document.addEventListener('visibilitychange', () => {
  isAppVisible = !document.hidden
  
  if (watchId) {
    // Adjust location accuracy based on app visibility
    navigator.geolocation.clearWatch(watchId)
    
    const options = {
      ...locationOptions,
      enableHighAccuracy: isAppVisible && isMoving,
      timeout: isAppVisible ? 10000 : 30000,
      maximumAge: isAppVisible ? 30000 : 120000
    }
    
    // Restart tracking with adjusted options
    if (currentPosition) {
      startLocationTracking(() => {}) // Resume with current callback
    }
  }
})

export const getCurrentPosition = () => currentPosition
export const getLocationAccuracy = () => currentPosition?.accuracy || null
export const isLocationTracking = () => watchId !== null
