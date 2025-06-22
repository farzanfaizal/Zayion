import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import WebSocket
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import and_, or_

from models import (
    User, Room, Message, LocationData, RoomMembership, 
    is_location_within_room_boundary, SessionLocal
)

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time communication"""
    
    def __init__(self):
        # Active connections: user_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        
        # Room memberships: room_id -> set of user_ids
        self.room_memberships: Dict[int, set] = {}
        
        # User locations: user_id -> location_data
        self.user_locations: Dict[int, dict] = {}
        
        # Proximity tracking
        self.proximity_threshold = 0.1  # 100 meters in km
        
    async def connect(self, user_id: int, websocket: WebSocket):
        """Connect a user to WebSocket"""
        try:
            # Store connection
            self.active_connections[user_id] = websocket
            
            # Update user online status
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.is_online = True
                    user.last_seen = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"User {user_id} connected to WebSocket")
            
            # Send initial data
            await self._send_initial_data(user_id)
            
        except Exception as e:
            logger.error(f"Error connecting user {user_id}: {e}")
            
    async def disconnect(self, user_id: int):
        """Disconnect a user from WebSocket"""
        try:
            # Remove from active connections
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            
            # Remove from all rooms
            for room_id in list(self.room_memberships.keys()):
                if user_id in self.room_memberships[room_id]:
                    await self._leave_room(user_id, room_id)
            
            # Remove location data
            if user_id in self.user_locations:
                del self.user_locations[user_id]
            
            # Update user offline status
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.is_online = False
                    user.last_seen = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"User {user_id} disconnected from WebSocket")
            
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")
    
    async def disconnect_all(self):
        """Disconnect all users (for shutdown)"""
        user_ids = list(self.active_connections.keys())
        for user_id in user_ids:
            await self.disconnect(user_id)
    
    async def handle_message(self, user_id: int, message: dict):
        """Handle incoming WebSocket message"""
        try:
            message_type = message.get("type")
            
            if message_type == "join_room":
                await self._handle_join_room(user_id, message)
            elif message_type == "leave_room":
                await self._handle_leave_room(user_id, message)
            elif message_type == "send_message":
                await self._handle_send_message(user_id, message)
            elif message_type == "location_update":
                await self._handle_location_update(user_id, message)
            elif message_type == "ping":
                await self._handle_ping(user_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self._send_to_user(user_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except Exception as e:
            logger.error(f"Error handling message from user {user_id}: {e}")
            await self._send_to_user(user_id, {
                "type": "error",
                "message": "Failed to process message"
            })
    
    async def _send_initial_data(self, user_id: int):
        """Send initial data to newly connected user"""
        try:
            db = SessionLocal()
            try:
                # Get user's active room memberships
                memberships = db.query(RoomMembership).filter(
                    and_(
                        RoomMembership.user_id == user_id,
                        RoomMembership.is_active == True
                    )
                ).all()
                
                for membership in memberships:
                    await self._rejoin_room(user_id, membership.room_id, db)
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error sending initial data to user {user_id}: {e}")
    
    async def _handle_join_room(self, user_id: int, message: dict):
        """Handle join room request"""
        try:
            room_id = message.get("roomId")
            location = message.get("location")
            
            if not room_id:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "message": "Room ID required"
                })
                return
            
            db = SessionLocal()
            try:
                # Verify room exists
                room = db.query(Room).filter(
                    and_(Room.id == room_id, Room.is_active == True)
                ).first()
                
                if not room:
                    await self._send_to_user(user_id, {
                        "type": "error",
                        "message": "Room not found"
                    })
                    return
                
                # Check if room is at capacity
                current_members = db.query(RoomMembership).filter(
                    and_(
                        RoomMembership.room_id == room_id,
                        RoomMembership.is_active == True
                    )
                ).count()
                
                if current_members >= room.max_users:
                    await self._send_to_user(user_id, {
                        "type": "error",
                        "message": "Room is at maximum capacity"
                    })
                    return
                
                # Check location if provided
                if location and not is_location_within_room_boundary(
                    location.get("lat"), location.get("lng"), room
                ):
                    await self._send_to_user(user_id, {
                        "type": "error",
                        "message": "Outside room boundaries"
                    })
                    return
                
                # Check if already in room
                existing_membership = db.query(RoomMembership).filter(
                    and_(
                        RoomMembership.room_id == room_id,
                        RoomMembership.user_id == user_id,
                        RoomMembership.is_active == True
                    )
                ).first()
                
                if not existing_membership:
                    # Create new membership
                    membership = RoomMembership(
                        room_id=room_id,
                        user_id=user_id,
                        join_latitude=location.get("lat") if location else None,
                        join_longitude=location.get("lng") if location else None,
                        join_accuracy=location.get("accuracy") if location else None
                    )
                    db.add(membership)
                    db.commit()
                
                await self._join_room(user_id, room_id, db)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling join room for user {user_id}: {e}")
            await self._send_to_user(user_id, {
                "type": "error",
                "message": "Failed to join room"
            })
    
    async def _handle_leave_room(self, user_id: int, message: dict):
        """Handle leave room request"""
        try:
            room_id = message.get("roomId")
            
            if not room_id:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "message": "Room ID required"
                })
                return
            
            await self._leave_room(user_id, room_id)
            
        except Exception as e:
            logger.error(f"Error handling leave room for user {user_id}: {e}")
    
    async def _handle_send_message(self, user_id: int, message: dict):
        """Handle send message request"""
        try:
            room_id = message.get("roomId")
            content = message.get("message")
            
            if not room_id or not content:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "message": "Room ID and message content required"
                })
                return
            
            # Verify user is in room
            if room_id not in self.room_memberships or user_id not in self.room_memberships[room_id]:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "message": "Not a member of this room"
                })
                return
            
            db = SessionLocal()
            try:
                # Create message
                msg = Message(
                    room_id=room_id,
                    user_id=user_id,
                    content=content,
                    message_type="text"
                )
                
                db.add(msg)
                db.commit()
                db.refresh(msg)
                
                # Get user info
                user = db.query(User).filter(User.id == user_id).first()
                
                # Broadcast message to all room members
                message_data = {
                    "type": "new_message",
                    "message": {
                        **msg.to_dict(),
                        "user_name": user.name if user else "Anonymous"
                    }
                }
                
                await self._broadcast_to_room(room_id, message_data)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling send message for user {user_id}: {e}")
            await self._send_to_user(user_id, {
                "type": "error",
                "message": "Failed to send message"
            })
    
    async def _handle_location_update(self, user_id: int, message: dict):
        """Handle location update"""
        try:
            location = message.get("location")
            
            if not location:
                return
            
            # Update user location in memory
            self.user_locations[user_id] = {
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "accuracy": location.get("accuracy"),
                "timestamp": location.get("timestamp", int(datetime.utcnow().timestamp() * 1000))
            }
            
            # Update location in database
            db = SessionLocal()
            try:
                location_data = db.query(LocationData).filter(LocationData.user_id == user_id).first()
                
                if not location_data:
                    location_data = LocationData(user_id=user_id)
                    db.add(location_data)
                
                location_data.latitude = location.get("lat")
                location_data.longitude = location.get("lng")
                location_data.accuracy = location.get("accuracy")
                location_data.updated_at = datetime.utcnow()
                location_data.expires_at = datetime.utcnow() + timedelta(hours=24)
                
                db.commit()
                
                # Check proximity to other users and rooms
                await self._check_proximity(user_id, location, db)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling location update for user {user_id}: {e}")
    
    async def _handle_ping(self, user_id: int):
        """Handle ping message"""
        await self._send_to_user(user_id, {
            "type": "pong",
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        })
    
    async def _join_room(self, user_id: int, room_id: int, db: Session):
        """Add user to room"""
        try:
            # Add to room membership
            if room_id not in self.room_memberships:
                self.room_memberships[room_id] = set()
            self.room_memberships[room_id].add(user_id)
            
            # Get room data
            room = db.query(Room).filter(Room.id == room_id).first()
            if not room:
                return
            
            # Get room members
            members = self._get_room_members(room_id, db)
            
            # Get recent messages
            messages = db.query(Message).filter(Message.room_id == room_id).order_by(Message.created_at.desc()).limit(50).all()
            
            # Send room data to user
            await self._send_to_user(user_id, {
                "type": "room_joined",
                "room": room.to_dict(),
                "users": members,
                "messages": [msg.to_dict() for msg in reversed(messages)]
            })
            
            # Notify other room members
            user = db.query(User).filter(User.id == user_id).first()
            user_joined_message = {
                "type": "user_joined",
                "user": {
                    "id": user_id,
                    "name": user.name if user else "Anonymous"
                },
                "room_id": room_id
            }
            
            await self._broadcast_to_room(room_id, user_joined_message, exclude_user=user_id)
            
            # Update room users list for all members
            await self._broadcast_room_users(room_id, db)
            
        except Exception as e:
            logger.error(f"Error joining room {room_id} for user {user_id}: {e}")
    
    async def _rejoin_room(self, user_id: int, room_id: int, db: Session):
        """Rejoin room on reconnection"""
        await self._join_room(user_id, room_id, db)
    
    async def _leave_room(self, user_id: int, room_id: int):
        """Remove user from room"""
        try:
            # Remove from room membership
            if room_id in self.room_memberships:
                self.room_memberships[room_id].discard(user_id)
                
                # Remove empty room
                if not self.room_memberships[room_id]:
                    del self.room_memberships[room_id]
            
            # Update database
            db = SessionLocal()
            try:
                membership = db.query(RoomMembership).filter(
                    and_(
                        RoomMembership.room_id == room_id,
                        RoomMembership.user_id == user_id,
                        RoomMembership.is_active == True
                    )
                ).first()
                
                if membership:
                    membership.is_active = False
                    membership.left_at = datetime.utcnow()
                    db.commit()
                
                # Notify other room members
                user = db.query(User).filter(User.id == user_id).first()
                user_left_message = {
                    "type": "user_left",
                    "user": {
                        "id": user_id,
                        "name": user.name if user else "Anonymous"
                    },
                    "room_id": room_id
                }
                
                await self._broadcast_to_room(room_id, user_left_message, exclude_user=user_id)
                
                # Update room users list for remaining members
                await self._broadcast_room_users(room_id, db)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error leaving room {room_id} for user {user_id}: {e}")
    
    async def _check_proximity(self, user_id: int, location: dict, db: Session):
        """Check proximity to other users and send notifications"""
        try:
            user_lat = location.get("lat")
            user_lng = location.get("lng")
            
            if not user_lat or not user_lng:
                return
            
            # Check proximity to friends
            from models import Friend, calculate_distance_between_points
            
            friends = db.query(Friend).filter(
                and_(
                    or_(Friend.user1_id == user_id, Friend.user2_id == user_id),
                    Friend.is_active == True,
                    Friend.can_see_location == True
                )
            ).all()
            
            for friendship in friends:
                friend_id = friendship.user2_id if friendship.user1_id == user_id else friendship.user1_id
                
                # Get friend's location
                friend_location = db.query(LocationData).filter(LocationData.user_id == friend_id).first()
                
                if friend_location:
                    distance = calculate_distance_between_points(
                        user_lat, user_lng,
                        friend_location.latitude, friend_location.longitude
                    )
                    
                    # Notify if within proximity threshold
                    if distance <= self.proximity_threshold:
                        await self._send_proximity_notification(user_id, friend_id, distance, db)
            
        except Exception as e:
            logger.error(f"Error checking proximity for user {user_id}: {e}")
    
    async def _send_proximity_notification(self, user_id: int, friend_id: int, distance: float, db: Session):
        """Send proximity notification"""
        try:
            friend = db.query(User).filter(User.id == friend_id).first()
            if not friend:
                return
            
            notification = {
                "type": "friend_nearby",
                "friend": {
                    "id": friend_id,
                    "name": friend.name
                },
                "distance": round(distance * 1000)  # Convert to meters
            }
            
            await self._send_to_user(user_id, notification)
            
        except Exception as e:
            logger.error(f"Error sending proximity notification: {e}")
    
    def _get_room_members(self, room_id: int, db: Session) -> List[dict]:
        """Get list of room members"""
        try:
            memberships = db.query(RoomMembership).join(User).filter(
                and_(
                    RoomMembership.room_id == room_id,
                    RoomMembership.is_active == True
                )
            ).all()
            
            members = []
            for membership in memberships:
                user = membership.user
                location_data = self.user_locations.get(user.id)
                
                member_data = {
                    "id": user.id,
                    "name": user.name,
                    "is_online": user.id in self.active_connections,
                    "joined_at": membership.joined_at.isoformat()
                }
                
                if location_data:
                    member_data["location"] = location_data
                
                members.append(member_data)
            
            return members
            
        except Exception as e:
            logger.error(f"Error getting room members for room {room_id}: {e}")
            return []
    
    async def _broadcast_room_users(self, room_id: int, db: Session):
        """Broadcast updated user list to all room members"""
        try:
            members = self._get_room_members(room_id, db)
            
            message = {
                "type": "room_users_update",
                "room_id": room_id,
                "users": members
            }
            
            await self._broadcast_to_room(room_id, message)
            
        except Exception as e:
            logger.error(f"Error broadcasting room users for room {room_id}: {e}")
    
    async def _broadcast_to_room(self, room_id: int, message: dict, exclude_user: Optional[int] = None):
        """Broadcast message to all users in a room"""
        try:
            if room_id not in self.room_memberships:
                return
            
            members = self.room_memberships[room_id].copy()
            if exclude_user:
                members.discard(exclude_user)
            
            # Send to all connected members
            for user_id in members:
                await self._send_to_user(user_id, message)
                
        except Exception as e:
            logger.error(f"Error broadcasting to room {room_id}: {e}")
    
    async def _send_to_user(self, user_id: int, message: dict):
        """Send message to a specific user"""
        try:
            if user_id in self.active_connections:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
                
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            # Remove broken connection
            if user_id in self.active_connections:
                del self.active_connections[user_id]
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected users"""
        disconnected_users = []
        
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            await self.disconnect(user_id)
    
    def get_online_users_count(self) -> int:
        """Get count of online users"""
        return len(self.active_connections)
    
    def get_room_users_count(self, room_id: int) -> int:
        """Get count of users in a room"""
        return len(self.room_memberships.get(room_id, set()))
    
    def is_user_online(self, user_id: int) -> bool:
        """Check if user is online"""
        return user_id in self.active_connections
    
    def get_user_rooms(self, user_id: int) -> List[int]:
        """Get list of rooms user is in"""
        rooms = []
        for room_id, members in self.room_memberships.items():
            if user_id in members:
                rooms.append(room_id)
        return rooms
