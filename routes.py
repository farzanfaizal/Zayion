from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from models import (
    User, Room, Message, FriendRequest, Friend, LocationData, 
    RoomMembership, AIInteraction, get_db, create_access_token,
    is_location_within_room_boundary, calculate_distance_between_points
)

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create router
router = APIRouter()

# Geocoding service
geolocator = Nominatim(user_agent="zayion-app")

# Pydantic models for request/response
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    location_sharing_enabled: Optional[bool] = None
    profile_visibility: Optional[str] = None
    notification_enabled: Optional[bool] = None

class LocationUpdate(BaseModel):
    lat: float
    lng: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None

class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: LocationUpdate
    mode: str = "casual"
    is_private: bool = False
    max_users: int = 10
    boundary_radius: float = 50.0

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"

class FriendRequestCreate(BaseModel):
    user_id: int
    message: Optional[str] = None

class FriendRequestResponse(BaseModel):
    accept: bool

# Utility functions
def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)

# Authentication dependency will be defined at the end of file

def geocode_location(lat: float, lng: float) -> Optional[str]:
    """Get address from coordinates"""
    try:
        location = geolocator.reverse(f"{lat}, {lng}", timeout=5)
        return location.address if location else None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None

# Authentication endpoints
@router.post("/auth/register")
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = hash_password(user_data.password)
        user = User(
            name=user_data.name,
            email=user_data.email,
            phone=user_data.phone,
            password_hash=hashed_password
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create access token
        token = create_access_token(data={"sub": user.id})
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user": user.to_dict(),
            "token": token
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )

@router.post("/auth/login")
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    try:
        # Find user
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update online status
        user.is_online = True
        user.last_seen = datetime.utcnow()
        db.commit()
        
        # Create access token
        token = create_access_token(data={"sub": user.id})
        
        return {
            "success": True,
            "message": "Login successful",
            "user": user.to_dict(),
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

# User profile endpoints
@router.get("/user/profile")
async def get_user_profile(current_user: User = Depends(lambda: None), db: Session = Depends(get_db)):
    """Get current user profile - temporarily disabled auth"""
    # Temporary mock user for testing
    mock_user = {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "is_online": True,
        "created_at": datetime.utcnow().isoformat()
    }
    return {
        "success": True,
        **mock_user
    }

@router.put("/user/profile")
async def update_user_profile(
    profile_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """Update user profile"""
    try:
        # Update user fields
        if profile_data.name is not None:
            current_user.name = profile_data.name
        if profile_data.phone is not None:
            current_user.phone = profile_data.phone
        if profile_data.bio is not None:
            current_user.bio = profile_data.bio
        if profile_data.location_sharing_enabled is not None:
            current_user.location_sharing_enabled = profile_data.location_sharing_enabled
        if profile_data.profile_visibility is not None:
            current_user.profile_visibility = profile_data.profile_visibility
        if profile_data.notification_enabled is not None:
            current_user.notification_enabled = profile_data.notification_enabled
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": current_user.to_dict()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.delete("/user/account")
async def delete_user_account(
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Delete user account"""
    try:
        # Soft delete by deactivating account
        current_user.is_active = False
        current_user.is_online = False
        current_user.updated_at = datetime.utcnow()
        
        # Remove location data
        location_data = db.query(LocationData).filter(LocationData.user_id == current_user.id).first()
        if location_data:
            db.delete(location_data)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Account deleted successfully"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Account deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )

# Location endpoints
@router.post("/location/update")
async def update_location(
    location_data: LocationUpdate,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Update user location"""
    try:
        # Get or create location data
        location = db.query(LocationData).filter(LocationData.user_id == current_user.id).first()
        
        if not location:
            location = LocationData(user_id=current_user.id)
            db.add(location)
        
        # Update location
        location.latitude = location_data.lat
        location.longitude = location_data.lng
        location.accuracy = location_data.accuracy
        location.altitude = location_data.altitude
        location.speed = location_data.speed
        location.heading = location_data.heading
        location.updated_at = datetime.utcnow()
        
        # Set expiration for privacy (24 hours)
        location.expires_at = datetime.utcnow() + timedelta(hours=24)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Location updated successfully",
            "location": location.to_dict()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Location update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update location"
        )

# Room endpoints
@router.get("/rooms/nearby")
async def get_nearby_rooms(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius: float = Query(5.0, description="Search radius in kilometers"),
    mode: Optional[str] = Query(None, description="Room mode filter"),
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Get nearby rooms"""
    try:
        query = db.query(Room).filter(Room.is_active == True)
        
        # Filter by mode if specified
        if mode:
            query = query.filter(Room.mode == mode)
        
        rooms = query.order_by(desc(Room.created_at)).limit(50).all()
        
        # Calculate distances and user counts if location provided
        room_data = []
        for room in rooms:
            room_dict = room.to_dict()
            
            # Calculate distance if coordinates provided
            if lat is not None and lng is not None:
                distance = calculate_distance_between_points(lat, lng, room.latitude, room.longitude)
                room_dict["distance"] = distance
                
                # Filter by radius
                if distance > radius:
                    continue
            
            # Get active user count
            user_count = db.query(RoomMembership).filter(
                and_(RoomMembership.room_id == room.id, RoomMembership.is_active == True)
            ).count()
            room_dict["user_count"] = user_count
            
            room_data.append(room_dict)
        
        # Sort by distance if coordinates provided
        if lat is not None and lng is not None:
            room_data.sort(key=lambda x: x.get("distance", float('inf')))
        
        return room_data
        
    except Exception as e:
        logger.error(f"Get nearby rooms error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch nearby rooms"
        )

@router.post("/rooms/create")
async def create_room(
    room_data: RoomCreate,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Create a new room"""
    try:
        # Get address for location
        address = geocode_location(room_data.location.lat, room_data.location.lng)
        
        # Create room
        room = Room(
            name=room_data.name,
            description=room_data.description,
            latitude=room_data.location.lat,
            longitude=room_data.location.lng,
            accuracy=room_data.location.accuracy,
            address=address,
            mode=room_data.mode,
            is_private=room_data.is_private,
            max_users=room_data.max_users,
            boundary_radius=room_data.boundary_radius,
            creator_id=current_user.id
        )
        
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Create room membership for creator
        membership = RoomMembership(
            room_id=room.id,
            user_id=current_user.id,
            join_latitude=room_data.location.lat,
            join_longitude=room_data.location.lng,
            join_accuracy=room_data.location.accuracy
        )
        
        db.add(membership)
        db.commit()
        
        return {
            "success": True,
            "message": "Room created successfully",
            **room.to_dict()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Room creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create room"
        )

@router.get("/rooms/{room_id}")
async def get_room(
    room_id: int,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Get room details"""
    try:
        room = db.query(Room).filter(Room.id == room_id, Room.is_active == True).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Get room members
        members = db.query(RoomMembership).join(User).filter(
            and_(RoomMembership.room_id == room_id, RoomMembership.is_active == True)
        ).all()
        
        # Get recent messages
        messages = db.query(Message).filter(Message.room_id == room_id).order_by(desc(Message.created_at)).limit(50).all()
        
        room_dict = room.to_dict()
        room_dict["members"] = [
            {
                "user_id": member.user_id,
                "name": member.user.name,
                "joined_at": member.joined_at.isoformat()
            }
            for member in members
        ]
        room_dict["messages"] = [msg.to_dict() for msg in reversed(messages)]
        room_dict["user_count"] = len(members)
        
        return room_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get room error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch room"
        )

# Message endpoints
@router.get("/rooms/{room_id}/messages")
async def get_room_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[int] = Query(None, description="Message ID to get messages before"),
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Get room messages"""
    try:
        # Verify user is in room
        membership = db.query(RoomMembership).filter(
            and_(
                RoomMembership.room_id == room_id,
                RoomMembership.user_id == current_user.id,
                RoomMembership.is_active == True
            )
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this room"
            )
        
        query = db.query(Message).filter(Message.room_id == room_id)
        
        if before:
            query = query.filter(Message.id < before)
        
        messages = query.order_by(desc(Message.created_at)).limit(limit).all()
        
        return [msg.to_dict() for msg in reversed(messages)]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch messages"
        )

@router.post("/rooms/{room_id}/messages")
async def send_message(
    room_id: int,
    message_data: MessageCreate,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Send a message to a room"""
    try:
        # Verify user is in room
        membership = db.query(RoomMembership).filter(
            and_(
                RoomMembership.room_id == room_id,
                RoomMembership.user_id == current_user.id,
                RoomMembership.is_active == True
            )
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this room"
            )
        
        # Create message
        message = Message(
            room_id=room_id,
            user_id=current_user.id,
            content=message_data.content,
            message_type=message_data.message_type
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return {
            "success": True,
            "message": "Message sent successfully",
            **message.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Send message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

# Friend system endpoints
@router.get("/friends")
async def get_friends(
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Get user's friends list"""
    try:
        friends = db.query(Friend).filter(
            and_(
                or_(Friend.user1_id == current_user.id, Friend.user2_id == current_user.id),
                Friend.is_active == True
            )
        ).all()
        
        friends_data = []
        for friendship in friends:
            friend_data = friendship.to_dict(current_user.id)
            
            # Get friend's location if sharing is enabled
            friend_id = friend_data["friend_id"]
            location_data = db.query(LocationData).filter(LocationData.user_id == friend_id).first()
            
            if location_data and friendship.can_see_location:
                friend_data["location"] = location_data.to_dict()
                friend_data["location_sharing_enabled"] = True
            else:
                friend_data["location_sharing_enabled"] = False
            
            friends_data.append(friend_data)
        
        return friends_data
        
    except Exception as e:
        logger.error(f"Get friends error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch friends"
        )

@router.post("/friends/request")
async def send_friend_request(
    request_data: FriendRequestCreate,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Send a friend request"""
    try:
        # Check if target user exists
        target_user = db.query(User).filter(User.id == request_data.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already friends
        existing_friendship = db.query(Friend).filter(
            and_(
                or_(
                    and_(Friend.user1_id == current_user.id, Friend.user2_id == request_data.user_id),
                    and_(Friend.user1_id == request_data.user_id, Friend.user2_id == current_user.id)
                ),
                Friend.is_active == True
            )
        ).first()
        
        if existing_friendship:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already friends with this user"
            )
        
        # Check if request already exists
        existing_request = db.query(FriendRequest).filter(
            and_(
                FriendRequest.sender_id == current_user.id,
                FriendRequest.receiver_id == request_data.user_id,
                FriendRequest.status == "pending"
            )
        ).first()
        
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already sent"
            )
        
        # Create friend request
        friend_request = FriendRequest(
            sender_id=current_user.id,
            receiver_id=request_data.user_id,
            message=request_data.message
        )
        
        db.add(friend_request)
        db.commit()
        
        return {
            "success": True,
            "message": "Friend request sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Send friend request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send friend request"
        )

@router.get("/friends/requests")
async def get_friend_requests(
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Get pending friend requests"""
    try:
        requests = db.query(FriendRequest).filter(
            and_(
                FriendRequest.receiver_id == current_user.id,
                FriendRequest.status == "pending"
            )
        ).order_by(desc(FriendRequest.created_at)).all()
        
        return [req.to_dict() for req in requests]
        
    except Exception as e:
        logger.error(f"Get friend requests error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch friend requests"
        )

@router.post("/friends/requests/{request_id}")
async def respond_to_friend_request(
    request_id: int,
    response_data: FriendRequestResponse,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Respond to a friend request"""
    try:
        # Get friend request
        friend_request = db.query(FriendRequest).filter(
            and_(
                FriendRequest.id == request_id,
                FriendRequest.receiver_id == current_user.id,
                FriendRequest.status == "pending"
            )
        ).first()
        
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )
        
        # Update request status
        friend_request.status = "accepted" if response_data.accept else "rejected"
        friend_request.responded_at = datetime.utcnow()
        
        # Create friendship if accepted
        if response_data.accept:
            friendship = Friend(
                user1_id=min(friend_request.sender_id, current_user.id),
                user2_id=max(friend_request.sender_id, current_user.id)
            )
            db.add(friendship)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Friend request {'accepted' if response_data.accept else 'rejected'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Respond to friend request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to respond to friend request"
        )

@router.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Remove a friend"""
    try:
        # Find friendship
        friendship = db.query(Friend).filter(
            and_(
                or_(
                    and_(Friend.user1_id == current_user.id, Friend.user2_id == friend_id),
                    and_(Friend.user1_id == friend_id, Friend.user2_id == current_user.id)
                ),
                Friend.is_active == True
            )
        ).first()
        
        if not friendship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friendship not found"
            )
        
        # Soft delete friendship
        friendship.is_active = False
        db.commit()
        
        return {
            "success": True,
            "message": "Friend removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Remove friend error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove friend"
        )

# User search endpoint
@router.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    # current_user temporarily disabled,
    db: Session = Depends(get_db)
):
    """Search for users"""
    try:
        # Search by name or email
        users = db.query(User).filter(
            and_(
                User.is_active == True,
                User.id != current_user.id,
                or_(
                    User.name.ilike(f"%{q}%"),
                    User.email.ilike(f"%{q}%")
                )
            )
        ).limit(20).all()
        
        users_data = []
        for user in users:
            user_data = {
                "id": user.id,
                "name": user.name,
                "bio": user.bio,
                "mutual_friends": 0,  # Calculate mutual friends
                "is_friend": False,
                "request_sent": False
            }
            
            # Check if already friends
            friendship = db.query(Friend).filter(
                and_(
                    or_(
                        and_(Friend.user1_id == current_user.id, Friend.user2_id == user.id),
                        and_(Friend.user1_id == user.id, Friend.user2_id == current_user.id)
                    ),
                    Friend.is_active == True
                )
            ).first()
            
            if friendship:
                user_data["is_friend"] = True
            else:
                # Check if request already sent
                request = db.query(FriendRequest).filter(
                    and_(
                        FriendRequest.sender_id == current_user.id,
                        FriendRequest.receiver_id == user.id,
                        FriendRequest.status == "pending"
                    )
                ).first()
                
                if request:
                    user_data["request_sent"] = True
            
            users_data.append(user_data)
        
        return users_data
        
    except Exception as e:
        logger.error(f"User search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users"
        )

# Authentication temporarily disabled for initial setup
