// Proximity detection utilities using phone sensors
// This simulates proximity detection using Bluetooth RSSI and Wi-Fi RTT

export const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371 // Radius of the Earth in kilometers
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  return R * c // Distance in kilometers
}

export const calculateBearing = (lat1, lon1, lat2, lon2) => {
  const dLon = (lon2 - lon1) * Math.PI / 180
  const lat1Rad = lat1 * Math.PI / 180
  const lat2Rad = lat2 * Math.PI / 180
  
  const y = Math.sin(dLon) * Math.cos(lat2Rad)
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) - 
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon)
  
  const bearing = Math.atan2(y, x) * 180 / Math.PI
  return (bearing + 360) % 360 // Normalize to 0-360 degrees
}

// Simulated proximity detection
export class ProximityDetector {
  constructor() {
    this.nearbyUsers = new Map()
    this.proximityThreshold = 0.1 // 100 meters in km
    this.callbacks = new Set()
  }

  addProximityCallback(callback) {
    this.callbacks.add(callback)
  }

  removeProximityCallback(callback) {
    this.callbacks.delete(callback)
  }

  updateUserLocations(users, currentUserLocation) {
    if (!currentUserLocation) return

    const previousNearby = new Set(this.nearbyUsers.keys())
    const currentNearby = new Set()

    users.forEach(user => {
      if (user.location) {
        const distance = calculateDistance(
          currentUserLocation.latitude,
          currentUserLocation.longitude,
          user.location.lat,
          user.location.lng
        )

        if (distance <= this.proximityThreshold) {
          currentNearby.add(user.id)
          
          const proximityData = {
            user,
            distance,
            bearing: calculateBearing(
              currentUserLocation.latitude,
              currentUserLocation.longitude,
              user.location.lat,
              user.location.lng
            ),
            timestamp: Date.now()
          }

          this.nearbyUsers.set(user.id, proximityData)

          // Notify if this is a new nearby user
          if (!previousNearby.has(user.id)) {
            this.notifyProximityCallbacks('user_nearby', proximityData)
          }
        }
      }
    })

    // Check for users who are no longer nearby
    previousNearby.forEach(userId => {
      if (!currentNearby.has(userId)) {
        const userData = this.nearbyUsers.get(userId)
        this.nearbyUsers.delete(userId)
        this.notifyProximityCallbacks('user_left', userData)
      }
    })
  }

  notifyProximityCallbacks(event, data) {
    this.callbacks.forEach(callback => {
      try {
        callback(event, data)
      } catch (error) {
        console.error('Proximity callback error:', error)
      }
    })
  }

  getNearbyUsers() {
    return Array.from(this.nearbyUsers.values())
  }

  isUserNearby(userId) {
    return this.nearbyUsers.has(userId)
  }

  getUserDistance(userId) {
    const userData = this.nearbyUsers.get(userId)
    return userData ? userData.distance : null
  }
}

// Simulated Bluetooth RSSI-based ranging
export class BluetoothRSSI {
  constructor() {
    this.devices = new Map()
    this.scanInterval = null
  }

  startScanning(callback) {
    // Simulate Bluetooth scanning
    this.scanInterval = setInterval(() => {
      // In a real implementation, this would use Web Bluetooth API
      // For now, we simulate by generating mock RSSI values
      this.generateMockRSSI(callback)
    }, 2000)
  }

  stopScanning() {
    if (this.scanInterval) {
      clearInterval(this.scanInterval)
      this.scanInterval = null
    }
  }

  generateMockRSSI(callback) {
    // Mock RSSI values for demonstration
    // In reality, these would come from actual Bluetooth scanning
    const mockDevices = [
      { id: 'device1', rssi: -45, distance: 2.1 },
      { id: 'device2', rssi: -65, distance: 8.5 },
      { id: 'device3', rssi: -78, distance: 15.2 }
    ]

    callback(mockDevices)
  }

  rssiToDistance(rssi) {
    // Convert RSSI to estimated distance in meters
    // This is a simplified calculation; real-world factors affect accuracy
    if (rssi === 0) return -1
    
    const ratio = (-69 - rssi) / 20.0 // -69 is the RSSI at 1 meter for most devices
    if (ratio < 1.0) {
      return Math.pow(ratio, 10)
    } else {
      const accuracy = (0.89976) * Math.pow(ratio, 7.7095) + 0.111
      return accuracy
    }
  }
}

// Wi-Fi RTT (Round Trip Time) simulation
export class WiFiRTT {
  constructor() {
    this.accessPoints = new Map()
  }

  async measureDistance(accessPointId) {
    // Simulate Wi-Fi RTT measurement
    // In reality, this would use the Wi-Fi RTT API where available
    return new Promise((resolve) => {
      setTimeout(() => {
        // Mock RTT measurement result
        const mockDistance = Math.random() * 20 + 1 // 1-21 meters
        const mockStandardDeviation = Math.random() * 2 + 0.5 // 0.5-2.5 meters
        
        resolve({
          distance: mockDistance,
          distanceStandardDeviation: mockStandardDeviation,
          timestamp: Date.now()
        })
      }, 100)
    })
  }

  isRTTAvailable() {
    // Check if Wi-Fi RTT is supported
    // This would check for actual RTT capability in a real implementation
    return 'geolocation' in navigator // Simplified check
  }
}

// Sensor fusion for improved accuracy
export class SensorFusion {
  constructor() {
    this.accelerometer = null
    this.gyroscope = null
    this.magnetometer = null
    
    this.initializeSensors()
  }

  async initializeSensors() {
    try {
      // Request device motion permissions
      if (typeof DeviceMotionEvent.requestPermission === 'function') {
        const permission = await DeviceMotionEvent.requestPermission()
        if (permission !== 'granted') {
          console.warn('Device motion permission denied')
          return
        }
      }

      // Listen to device motion events
      window.addEventListener('devicemotion', this.handleDeviceMotion.bind(this))
      window.addEventListener('deviceorientation', this.handleDeviceOrientation.bind(this))
      
    } catch (error) {
      console.error('Failed to initialize sensors:', error)
    }
  }

  handleDeviceMotion(event) {
    if (event.acceleration) {
      this.accelerometer = {
        x: event.acceleration.x,
        y: event.acceleration.y,
        z: event.acceleration.z,
        timestamp: Date.now()
      }
    }

    if (event.rotationRate) {
      this.gyroscope = {
        alpha: event.rotationRate.alpha,
        beta: event.rotationRate.beta,
        gamma: event.rotationRate.gamma,
        timestamp: Date.now()
      }
    }
  }

  handleDeviceOrientation(event) {
    this.magnetometer = {
      alpha: event.alpha, // Compass heading
      beta: event.beta,   // Tilt front/back
      gamma: event.gamma, // Tilt left/right
      timestamp: Date.now()
    }
  }

  getMotionData() {
    return {
      accelerometer: this.accelerometer,
      gyroscope: this.gyroscope,
      magnetometer: this.magnetometer
    }
  }

  // Detect if user is stationary, walking, or moving in vehicle
  detectMovementState() {
    if (!this.accelerometer) return 'unknown'

    const acceleration = Math.sqrt(
      this.accelerometer.x ** 2 + 
      this.accelerometer.y ** 2 + 
      this.accelerometer.z ** 2
    )

    if (acceleration < 0.5) return 'stationary'
    if (acceleration < 2.0) return 'walking'
    return 'vehicle'
  }
}

// Initialize proximity detector instance
export const proximityDetector = new ProximityDetector()
export const bluetoothRSSI = new BluetoothRSSI()
export const wifiRTT = new WiFiRTT()
export const sensorFusion = new SensorFusion()
