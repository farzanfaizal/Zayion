import asyncio
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger(__name__)

class MovementState(Enum):
    """User movement states for adaptive tracking"""
    STATIONARY = "stationary"
    WALKING = "walking"
    DRIVING = "driving"
    UNKNOWN = "unknown"

@dataclass
class LocationPoint:
    """Represents a location point with metadata"""
    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None

@dataclass
class ProximityEvent:
    """Represents a proximity event between users"""
    user1_id: int
    user2_id: int
    distance_meters: float
    event_type: str  # "entered", "exited", "updated"
    timestamp: datetime
    location1: LocationPoint
    location2: LocationPoint

@dataclass
class GeofenceEvent:
    """Represents a geofence entry/exit event"""
    user_id: int
    room_id: int
    event_type: str  # "entered", "exited"
    timestamp: datetime
    user_location: LocationPoint
    distance_to_center: float

class LocationService:
    """Service for handling location tracking, proximity detection, and geofencing"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="zayion-location-service")
        
        # Proximity tracking
        self.proximity_threshold = 100.0  # meters
        self.proximity_cache: Dict[Tuple[int, int], float] = {}
        self.last_proximity_check: Dict[int, datetime] = {}
        
        # Movement tracking
        self.user_movement_history: Dict[int, List[LocationPoint]] = {}
        self.movement_states: Dict[int, MovementState] = {}
        
        # Geofencing
        self.active_geofences: Dict[int, Dict] = {}  # room_id -> geofence_data
        self.user_geofence_status: Dict[Tuple[int, int], bool] = {}  # (user_id, room_id) -> inside
        
        # Location update intervals based on movement
        self.update_intervals = {
            MovementState.STATIONARY: 60,  # 60 seconds
            MovementState.WALKING: 15,     # 15 seconds
            MovementState.DRIVING: 5,      # 5 seconds
            MovementState.UNKNOWN: 30      # 30 seconds
        }
        
        # Background tasks
        self._proximity_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the location service"""
        try:
            # Start background tasks
            self._proximity_task = asyncio.create_task(self._proximity_monitoring_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("Location service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize location service: {e}")
            raise
    
    async def cleanup(self):
        """Clean up location service resources"""
        try:
            # Cancel background tasks
            if self._proximity_task:
                self._proximity_task.cancel()
                try:
                    await self._proximity_task
                except asyncio.CancelledError:
                    pass
            
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Clear caches
            self.proximity_cache.clear()
            self.last_proximity_check.clear()
            self.user_movement_history.clear()
            self.movement_states.clear()
            self.active_geofences.clear()
            self.user_geofence_status.clear()
            
            logger.info("Location service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during location service cleanup: {e}")
    
    async def update_user_location(
        self, 
        user_id: int, 
        latitude: float, 
        longitude: float,
        accuracy: float = None,
        altitude: float = None,
        speed: float = None,
        heading: float = None
    ) -> Dict[str, Any]:
        """Update user location and trigger proximity/geofence checks"""
        try:
            # Create location point
            location = LocationPoint(
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy or 10.0,
                timestamp=datetime.utcnow(),
                altitude=altitude,
                speed=speed,
                heading=heading
            )
            
            # Update movement history
            await self._update_movement_history(user_id, location)
            
            # Detect movement state
            movement_state = await self._detect_movement_state(user_id)
            self.movement_states[user_id] = movement_state
            
            # Update database
            await self._update_location_in_db(user_id, location)
            
            # Check proximity to other users
            proximity_events = await self._check_user_proximity(user_id, location)
            
            # Check geofences
            geofence_events = await self._check_geofences(user_id, location)
            
            # Get address if not cached
            address = await self._get_address_cached(latitude, longitude)
            
            return {
                "success": True,
                "location": {
                    "lat": latitude,
                    "lng": longitude,
                    "accuracy": accuracy,
                    "timestamp": location.timestamp.isoformat(),
                    "address": address
                },
                "movement_state": movement_state.value,
                "proximity_events": [self._proximity_event_to_dict(e) for e in proximity_events],
                "geofence_events": [self._geofence_event_to_dict(e) for e in geofence_events],
                "recommended_update_interval": self.update_intervals[movement_state]
            }
            
        except Exception as e:
            logger.error(f"Error updating location for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_nearby_users(
        self,
        user_id: int,
        radius_meters: float = 1000.0,
        include_offline: bool = False
    ) -> List[Dict[str, Any]]:
        """Get nearby users within specified radius"""
        try:
            from models import SessionLocal, LocationData, User
            
            db = SessionLocal()
            try:
                # Get user's current location
                user_location = db.query(LocationData).filter(LocationData.user_id == user_id).first()
                if not user_location:
                    return []
                
                # Get all other users with location data
                query = db.query(LocationData).join(User).filter(
                    LocationData.user_id != user_id,
                    User.is_active == True,
                    User.location_sharing_enabled == True
                )
                
                if not include_offline:
                    query = query.filter(User.is_online == True)
                
                other_locations = query.all()
                
                nearby_users = []
                for location in other_locations:
                    distance = self._calculate_distance(
                        user_location.latitude, user_location.longitude,
                        location.latitude, location.longitude
                    )
                    
                    if distance <= radius_meters:
                        user_data = {
                            "user_id": location.user_id,
                            "name": location.user.name,
                            "distance_meters": round(distance, 1),
                            "location": {
                                "lat": location.latitude,
                                "lng": location.longitude,
                                "accuracy": location.accuracy,
                                "updated_at": location.updated_at.isoformat()
                            },
                            "is_online": location.user.is_online,
                            "last_seen": location.user.last_seen.isoformat() if location.user.last_seen else None
                        }
                        nearby_users.append(user_data)
                
                # Sort by distance
                nearby_users.sort(key=lambda x: x["distance_meters"])
                
                return nearby_users
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting nearby users for user {user_id}: {e}")
            return []
    
    async def create_geofence(
        self,
        room_id: int,
        center_lat: float,
        center_lng: float,
        radius_meters: float,
        room_name: str = None
    ):
        """Create a geofence for a room"""
        try:
            geofence_data = {
                "room_id": room_id,
                "center_lat": center_lat,
                "center_lng": center_lng,
                "radius_meters": radius_meters,
                "room_name": room_name,
                "created_at": datetime.utcnow(),
                "active": True
            }
            
            self.active_geofences[room_id] = geofence_data
            
            logger.info(f"Created geofence for room {room_id} at ({center_lat}, {center_lng}) with radius {radius_meters}m")
            
        except Exception as e:
            logger.error(f"Error creating geofence for room {room_id}: {e}")
    
    async def remove_geofence(self, room_id: int):
        """Remove a geofence for a room"""
        try:
            if room_id in self.active_geofences:
                del self.active_geofences[room_id]
                
                # Remove user statuses for this geofence
                keys_to_remove = [k for k in self.user_geofence_status.keys() if k[1] == room_id]
                for key in keys_to_remove:
                    del self.user_geofence_status[key]
                
                logger.info(f"Removed geofence for room {room_id}")
                
        except Exception as e:
            logger.error(f"Error removing geofence for room {room_id}: {e}")
    
    async def get_user_movement_state(self, user_id: int) -> MovementState:
        """Get user's current movement state"""
        return self.movement_states.get(user_id, MovementState.UNKNOWN)
    
    async def get_location_analytics(self, user_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get location analytics for a user"""
        try:
            from models import SessionLocal, LocationData
            from sqlalchemy import func
            
            db = SessionLocal()
            try:
                since_time = datetime.utcnow() - timedelta(hours=hours)
                
                # Get movement history from database (if implemented)
                # For now, use in-memory data
                movement_history = self.user_movement_history.get(user_id, [])
                recent_history = [
                    loc for loc in movement_history 
                    if loc.timestamp >= since_time
                ]
                
                if not recent_history:
                    return {"error": "No location data available"}
                
                # Calculate analytics
                total_distance = 0.0
                for i in range(1, len(recent_history)):
                    distance = self._calculate_distance(
                        recent_history[i-1].latitude, recent_history[i-1].longitude,
                        recent_history[i].latitude, recent_history[i].longitude
                    )
                    total_distance += distance
                
                # Movement state distribution
                movement_states = [self.movement_states.get(user_id, MovementState.UNKNOWN)]
                
                # Average accuracy
                avg_accuracy = sum(loc.accuracy for loc in recent_history) / len(recent_history)
                
                return {
                    "user_id": user_id,
                    "period_hours": hours,
                    "total_distance_meters": round(total_distance, 1),
                    "location_updates": len(recent_history),
                    "average_accuracy": round(avg_accuracy, 1),
                    "current_movement_state": self.movement_states.get(user_id, MovementState.UNKNOWN).value,
                    "time_stationary": 0,  # TODO: Calculate from movement states
                    "time_walking": 0,     # TODO: Calculate from movement states
                    "time_driving": 0      # TODO: Calculate from movement states
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting location analytics for user {user_id}: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _update_movement_history(self, user_id: int, location: LocationPoint):
        """Update user's movement history"""
        if user_id not in self.user_movement_history:
            self.user_movement_history[user_id] = []
        
        history = self.user_movement_history[user_id]
        history.append(location)
        
        # Keep only last 100 locations to limit memory usage
        if len(history) > 100:
            self.user_movement_history[user_id] = history[-100:]
    
    async def _detect_movement_state(self, user_id: int) -> MovementState:
        """Detect user's movement state based on location history"""
        try:
            history = self.user_movement_history.get(user_id, [])
            if len(history) < 2:
                return MovementState.UNKNOWN
            
            # Analyze last few points
            recent_points = history[-5:]  # Last 5 points
            if len(recent_points) < 2:
                return MovementState.UNKNOWN
            
            total_distance = 0.0
            total_time = 0.0
            
            for i in range(1, len(recent_points)):
                distance = self._calculate_distance(
                    recent_points[i-1].latitude, recent_points[i-1].longitude,
                    recent_points[i].latitude, recent_points[i].longitude
                )
                time_diff = (recent_points[i].timestamp - recent_points[i-1].timestamp).total_seconds()
                
                total_distance += distance
                total_time += time_diff
            
            if total_time <= 0:
                return MovementState.STATIONARY
            
            # Calculate average speed in m/s
            avg_speed_ms = total_distance / total_time
            avg_speed_kmh = avg_speed_ms * 3.6
            
            # Classify movement state
            if avg_speed_kmh < 1.0:
                return MovementState.STATIONARY
            elif avg_speed_kmh < 8.0:  # Walking speed
                return MovementState.WALKING
            else:  # Driving speed
                return MovementState.DRIVING
                
        except Exception as e:
            logger.error(f"Error detecting movement state for user {user_id}: {e}")
            return MovementState.UNKNOWN
    
    async def _update_location_in_db(self, user_id: int, location: LocationPoint):
        """Update location in database"""
        try:
            from models import SessionLocal, LocationData
            
            db = SessionLocal()
            try:
                location_data = db.query(LocationData).filter(LocationData.user_id == user_id).first()
                
                if not location_data:
                    location_data = LocationData(user_id=user_id)
                    db.add(location_data)
                
                location_data.latitude = location.latitude
                location_data.longitude = location.longitude
                location_data.accuracy = location.accuracy
                location_data.altitude = location.altitude
                location_data.speed = location.speed
                location_data.heading = location.heading
                location_data.updated_at = location.timestamp
                location_data.expires_at = location.timestamp + timedelta(hours=24)
                
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error updating location in database for user {user_id}: {e}")
    
    async def _check_user_proximity(self, user_id: int, location: LocationPoint) -> List[ProximityEvent]:
        """Check proximity to other users"""
        try:
            from models import SessionLocal, LocationData, User, Friend
            from sqlalchemy import and_, or_
            
            db = SessionLocal()
            try:
                # Get user's friends with location sharing enabled
                friends_query = db.query(LocationData).join(User).join(
                    Friend, 
                    or_(
                        and_(Friend.user1_id == user_id, Friend.user2_id == User.id),
                        and_(Friend.user2_id == user_id, Friend.user1_id == User.id)
                    )
                ).filter(
                    User.is_active == True,
                    User.location_sharing_enabled == True,
                    Friend.is_active == True,
                    Friend.can_see_location == True,
                    LocationData.user_id != user_id
                )
                
                friend_locations = friends_query.all()
                
                proximity_events = []
                
                for friend_location in friend_locations:
                    friend_id = friend_location.user_id
                    distance = self._calculate_distance(
                        location.latitude, location.longitude,
                        friend_location.latitude, friend_location.longitude
                    )
                    
                    # Check if proximity state changed
                    cache_key = (min(user_id, friend_id), max(user_id, friend_id))
                    previous_distance = self.proximity_cache.get(cache_key)
                    
                    was_nearby = previous_distance is not None and previous_distance <= self.proximity_threshold
                    is_nearby = distance <= self.proximity_threshold
                    
                    if was_nearby != is_nearby:
                        event_type = "entered" if is_nearby else "exited"
                        
                        event = ProximityEvent(
                            user1_id=user_id,
                            user2_id=friend_id,
                            distance_meters=distance,
                            event_type=event_type,
                            timestamp=datetime.utcnow(),
                            location1=location,
                            location2=LocationPoint(
                                latitude=friend_location.latitude,
                                longitude=friend_location.longitude,
                                accuracy=friend_location.accuracy,
                                timestamp=friend_location.updated_at
                            )
                        )
                        
                        proximity_events.append(event)
                    
                    # Update cache
                    self.proximity_cache[cache_key] = distance
                
                return proximity_events
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error checking user proximity for user {user_id}: {e}")
            return []
    
    async def _check_geofences(self, user_id: int, location: LocationPoint) -> List[GeofenceEvent]:
        """Check geofence entry/exit events"""
        try:
            geofence_events = []
            
            for room_id, geofence in self.active_geofences.items():
                if not geofence.get("active", False):
                    continue
                
                # Calculate distance to geofence center
                distance = self._calculate_distance(
                    location.latitude, location.longitude,
                    geofence["center_lat"], geofence["center_lng"]
                )
                
                is_inside = distance <= geofence["radius_meters"]
                cache_key = (user_id, room_id)
                was_inside = self.user_geofence_status.get(cache_key, False)
                
                if was_inside != is_inside:
                    event_type = "entered" if is_inside else "exited"
                    
                    event = GeofenceEvent(
                        user_id=user_id,
                        room_id=room_id,
                        event_type=event_type,
                        timestamp=datetime.utcnow(),
                        user_location=location,
                        distance_to_center=distance
                    )
                    
                    geofence_events.append(event)
                    
                    logger.info(f"User {user_id} {event_type} geofence for room {room_id}")
                
                # Update status
                self.user_geofence_status[cache_key] = is_inside
            
            return geofence_events
            
        except Exception as e:
            logger.error(f"Error checking geofences for user {user_id}: {e}")
            return []
    
    async def _get_address_cached(self, latitude: float, longitude: float) -> Optional[str]:
        """Get address from coordinates with caching"""
        try:
            # Simple caching based on rounded coordinates
            cache_key = (round(latitude, 4), round(longitude, 4))
            
            # In production, implement proper caching (Redis, etc.)
            location = self.geolocator.reverse(f"{latitude}, {longitude}", timeout=5)
            return location.address if location else None
            
        except (GeocoderTimedOut, GeocoderServiceError):
            return None
        except Exception as e:
            logger.error(f"Error geocoding location ({latitude}, {longitude}): {e}")
            return None
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in meters"""
        return geodesic((lat1, lng1), (lat2, lng2)).meters
    
    def _proximity_event_to_dict(self, event: ProximityEvent) -> Dict[str, Any]:
        """Convert proximity event to dictionary"""
        return {
            "user1_id": event.user1_id,
            "user2_id": event.user2_id,
            "distance_meters": round(event.distance_meters, 1),
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat()
        }
    
    def _geofence_event_to_dict(self, event: GeofenceEvent) -> Dict[str, Any]:
        """Convert geofence event to dictionary"""
        return {
            "user_id": event.user_id,
            "room_id": event.room_id,
            "event_type": event.event_type,
            "distance_to_center": round(event.distance_to_center, 1),
            "timestamp": event.timestamp.isoformat()
        }
    
    async def _proximity_monitoring_loop(self):
        """Background task for proximity monitoring"""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Clean up old proximity cache entries
                current_time = datetime.utcnow()
                users_to_remove = []
                
                for user_id, last_check in self.last_proximity_check.items():
                    if (current_time - last_check).total_seconds() > 300:  # 5 minutes
                        users_to_remove.append(user_id)
                
                for user_id in users_to_remove:
                    del self.last_proximity_check[user_id]
                    
                    # Remove proximity cache entries for this user
                    keys_to_remove = [
                        k for k in self.proximity_cache.keys() 
                        if user_id in k
                    ]
                    for key in keys_to_remove:
                        del self.proximity_cache[key]
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in proximity monitoring loop: {e}")
    
    async def _cleanup_loop(self):
        """Background task for general cleanup"""
        try:
            while True:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up old movement history
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(hours=2)
                
                for user_id in list(self.user_movement_history.keys()):
                    history = self.user_movement_history[user_id]
                    # Keep only recent history
                    recent_history = [
                        loc for loc in history 
                        if loc.timestamp >= cutoff_time
                    ]
                    
                    if recent_history:
                        self.user_movement_history[user_id] = recent_history
                    else:
                        del self.user_movement_history[user_id]
                        # Also clean up movement state
                        if user_id in self.movement_states:
                            del self.movement_states[user_id]
                
                logger.info("Completed location service cleanup")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
