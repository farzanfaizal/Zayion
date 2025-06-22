from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import jwt

Base = declarative_base()

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    
    # Privacy settings
    location_sharing_enabled = Column(Boolean, default=True)
    profile_visibility = Column(String(20), default="friends")  # private, friends, public
    notification_enabled = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rooms_created = relationship("Room", back_populates="creator", foreign_keys="Room.creator_id")
    messages = relationship("Message", back_populates="user")
    location_data = relationship("LocationData", back_populates="user", uselist=False)
    sent_friend_requests = relationship("FriendRequest", back_populates="sender", foreign_keys="FriendRequest.sender_id")
    received_friend_requests = relationship("FriendRequest", back_populates="receiver", foreign_keys="FriendRequest.receiver_id")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_online', 'is_online'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for API responses"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "phone": self.phone,
            "bio": self.bio,
            "location_sharing_enabled": self.location_sharing_enabled,
            "profile_visibility": self.profile_visibility,
            "notification_enabled": self.notification_enabled,
            "is_online": self.is_online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Room(Base):
    """Room model for location-based social spaces"""
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Location data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    address = Column(String(255), nullable=True)
    
    # Room settings
    mode = Column(String(20), default="casual")  # casual, professional
    is_private = Column(Boolean, default=False)
    max_users = Column(Integer, default=10)
    password_hash = Column(String(255), nullable=True)  # For private rooms
    
    # Room boundaries (GeoJSON polygon for complex shapes)
    boundary = Column(JSON, nullable=True)
    boundary_radius = Column(Float, default=50.0)  # Default 50 meter radius
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-expire rooms
    
    # Creator
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="rooms_created", foreign_keys=[creator_id])
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    room_members = relationship("RoomMembership", back_populates="room", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_room_location', 'latitude', 'longitude'),
        Index('idx_room_active', 'is_active'),
        Index('idx_room_mode', 'mode'),
        Index('idx_room_creator', 'creator_id'),
        Index('idx_room_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert room to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "location": {
                "lat": self.latitude,
                "lng": self.longitude,
                "accuracy": self.accuracy,
                "address": self.address
            },
            "mode": self.mode,
            "is_private": self.is_private,
            "max_users": self.max_users,
            "boundary_radius": self.boundary_radius,
            "is_active": self.is_active,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

class RoomMembership(Base):
    """Track users in rooms with their join/leave times"""
    __tablename__ = "room_memberships"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Membership details
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # User's location when they joined
    join_latitude = Column(Float, nullable=True)
    join_longitude = Column(Float, nullable=True)
    join_accuracy = Column(Float, nullable=True)
    
    # Relationships
    room = relationship("Room", back_populates="room_members")
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_room_membership_active', 'room_id', 'user_id', 'is_active'),
        Index('idx_room_membership_user', 'user_id'),
        Index('idx_room_membership_joined', 'joined_at'),
    )

class Message(Base):
    """Message model for room chat"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, system, ai_generated
    
    # AI enhancement
    is_ai_enhanced = Column(Boolean, default=False)
    ai_context = Column(JSON, nullable=True)  # Store AI processing context
    
    # Status
    is_deleted = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    room = relationship("Room", back_populates="messages")
    user = relationship("User", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_room', 'room_id'),
        Index('idx_message_user', 'user_id'),
        Index('idx_message_created', 'created_at'),
        Index('idx_message_room_created', 'room_id', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for API responses"""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "content": self.content,
            "message_type": self.message_type,
            "is_ai_enhanced": self.is_ai_enhanced,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "timestamp": int(self.created_at.timestamp() * 1000) if self.created_at else None
        }

class LocationData(Base):
    """Real-time location data for users"""
    __tablename__ = "location_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Current location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    
    # Session data
    session_token = Column(String(255), nullable=True)  # For privacy-preserving tracking
    
    # Indoor positioning data
    bluetooth_beacons = Column(JSON, nullable=True)  # Nearby Bluetooth beacons
    wifi_networks = Column(JSON, nullable=True)      # Nearby Wi-Fi networks
    sensor_data = Column(JSON, nullable=True)        # IMU sensor data
    
    # Current room
    current_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    
    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-expire for privacy
    
    # Relationships
    user = relationship("User", back_populates="location_data")
    current_room = relationship("Room")
    
    # Indexes
    __table_args__ = (
        Index('idx_location_user', 'user_id'),
        Index('idx_location_position', 'latitude', 'longitude'),
        Index('idx_location_room', 'current_room_id'),
        Index('idx_location_updated', 'updated_at'),
        Index('idx_location_expires', 'expires_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert location data to dictionary for API responses"""
        return {
            "user_id": self.user_id,
            "lat": self.latitude,
            "lng": self.longitude,
            "accuracy": self.accuracy,
            "altitude": self.altitude,
            "speed": self.speed,
            "heading": self.heading,
            "current_room_id": self.current_room_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class FriendRequest(Base):
    """Friend request model"""
    __tablename__ = "friend_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Request details
    message = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, accepted, rejected, cancelled
    
    # Response details
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_friend_requests")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_friend_requests")
    
    # Indexes
    __table_args__ = (
        Index('idx_friend_request_sender', 'sender_id'),
        Index('idx_friend_request_receiver', 'receiver_id'),
        Index('idx_friend_request_status', 'status'),
        Index('idx_friend_request_unique', 'sender_id', 'receiver_id', unique=True),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert friend request to dictionary for API responses"""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.name if self.sender else None,
            "receiver_id": self.receiver_id,
            "receiver_name": self.receiver.name if self.receiver else None,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None
        }

class Friend(Base):
    """Friend relationship model"""
    __tablename__ = "friends"
    
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Friendship details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Mutual settings
    can_see_location = Column(Boolean, default=True)
    can_message = Column(Boolean, default=True)
    
    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_friendship_users', 'user1_id', 'user2_id', unique=True),
        Index('idx_friendship_user1', 'user1_id'),
        Index('idx_friendship_user2', 'user2_id'),
        Index('idx_friendship_active', 'is_active'),
    )
    
    def to_dict(self, current_user_id: int) -> Dict[str, Any]:
        """Convert friendship to dictionary for API responses"""
        # Determine which user is the friend (not the current user)
        friend_user = self.user2 if self.user1_id == current_user_id else self.user1
        
        return {
            "id": self.id,
            "friend_id": friend_user.id,
            "name": friend_user.name,
            "is_online": friend_user.is_online,
            "last_seen": friend_user.last_seen.isoformat() if friend_user.last_seen else None,
            "can_see_location": self.can_see_location,
            "can_message": self.can_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class AIInteraction(Base):
    """Track AI interactions for analytics and improvement"""
    __tablename__ = "ai_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False)  # room_intro, message_enhance, matching
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    # Quality feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    user_feedback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    room = relationship("Room")
    
    # Indexes
    __table_args__ = (
        Index('idx_ai_interaction_type', 'interaction_type'),
        Index('idx_ai_interaction_user', 'user_id'),
        Index('idx_ai_interaction_room', 'room_id'),
        Index('idx_ai_interaction_created', 'created_at'),
    )

# Database utility functions
def create_user_session_token() -> str:
    """Create a secure session token for location tracking"""
    import secrets
    return secrets.token_urlsafe(32)

def is_location_within_room_boundary(lat: float, lng: float, room: Room) -> bool:
    """Check if location is within room boundary"""
    import math
    
    # Simple radius check for now
    # In production, use PostGIS for complex polygon boundaries
    room_lat = room.latitude
    room_lng = room.longitude
    radius_km = room.boundary_radius / 1000.0  # Convert to km
    
    # Haversine distance calculation
    dlat = math.radians(lat - room_lat)
    dlng = math.radians(lng - room_lng)
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(room_lat)) * math.cos(math.radians(lat)) * 
         math.sin(dlng/2) * math.sin(dlng/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance_km = 6371 * c
    
    return distance_km <= radius_km

def calculate_distance_between_points(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in kilometers"""
    import math
    
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlng/2) * math.sin(dlng/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 6371 * c  # Earth's radius in km

# Database dependency
def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT token utilities
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
