# Zayion - Location-Based Social Rooms

## Overview

Zayion is a real-time, location-based social networking application that creates shared digital rooms for physical spaces. Users can discover and join chat rooms based on their geographical location, enabling spontaneous connections and conversations with people nearby. The application features dual modes (casual and professional networking), real-time messaging, proximity detection, and AI-powered room introductions.

## System Architecture

The application follows a modern full-stack architecture with clear separation of concerns:

**Frontend**: React-based Progressive Web App (PWA) with Vite as the build tool
**Backend**: Python FastAPI server providing REST APIs and WebSocket connections
**Database**: PostgreSQL with SQLAlchemy ORM for data persistence
**Real-time Communication**: WebSocket-based messaging system
**AI Integration**: Anthropic Claude API for intelligent room introductions and context generation
**Location Services**: Browser Geolocation API with adaptive tracking algorithms

The architecture is designed for scalability and real-time performance, with efficient location-based querying and proximity detection algorithms.

## Key Components

### Backend Services

**FastAPI Application (`main.py`)**
- Main application entry point with CORS middleware
- JWT-based authentication system
- Database session management
- Static file serving for the PWA

**WebSocket Manager (`websocket_handler.py`)**
- Real-time connection management for users
- Room membership tracking
- Proximity detection and notifications
- Message broadcasting to room participants

**Location Service (`location_service.py`)**
- Adaptive location tracking based on user movement patterns
- Geofencing capabilities for room boundaries
- Distance calculations using geodesic algorithms
- Movement state detection (stationary, walking, driving)

**AI Service (`ai_service.py`)**
- Integration with Anthropic Claude API (using latest claude-sonnet-4-20250514 model)
- Room introduction generation
- Context-aware conversation starters
- Intelligent content moderation capabilities

**Database Models (`models.py`)**
- User management with privacy controls
- Room creation and membership tracking
- Message history with real-time synchronization
- Friend requests and social connections
- Location data with accuracy tracking

**API Routes (`routes.py`)**
- RESTful endpoints for all application features
- User authentication and profile management
- Room CRUD operations with location-based filtering
- Friend system with request/accept workflow
- Location updates with privacy controls

### Frontend Components

**React Application (`src/App.jsx`)**
- Main application state management
- Authentication flow handling
- Real-time WebSocket message processing
- Location tracking coordination

**Authentication (`src/components/AuthForm.jsx`)**
- Login and registration forms
- Token-based session management
- Error handling and validation

**Room Management**
- Room listing with distance-based sorting
- Real-time chat interface
- User presence indicators
- Professional/casual mode switching

**Map Integration (`src/components/MapView.jsx`)**
- Interactive map using Leaflet
- Room and friend location visualization
- Proximity-based room discovery

**Social Features**
- Friend request system
- User search and discovery
- Profile management with privacy controls

## Data Flow

1. **User Authentication**: JWT tokens stored in localStorage, sent with API requests
2. **Location Updates**: Browser geolocation → backend location service → room membership evaluation
3. **Real-time Messaging**: WebSocket connections for instant message delivery
4. **Room Discovery**: Location-based queries filtered by proximity and user preferences
5. **AI Integration**: Room context sent to Claude API for intelligent introductions
6. **Proximity Detection**: Continuous location monitoring with adaptive update intervals

## External Dependencies

### Core Libraries
- **FastAPI**: High-performance Python web framework
- **SQLAlchemy**: Database ORM with PostgreSQL support
- **Anthropic**: AI service integration for Claude API
- **Geopy**: Geographic calculations and geocoding
- **Passlib**: Password hashing and security
- **PyJWT**: JSON Web Token implementation

### Frontend Libraries
- **React**: Component-based UI framework
- **Leaflet**: Interactive mapping library
- **Date-fns**: Date formatting utilities
- **Feather Icons**: Consistent iconography

### Infrastructure
- **PostgreSQL**: Primary database for persistent storage
- **WebSocket**: Real-time bidirectional communication
- **Browser APIs**: Geolocation, Push Notifications, Service Workers

## Deployment Strategy

The application is configured for Replit deployment with:

- **Python 3.11** runtime environment
- **Nix package management** for consistent dependencies
- **Parallel workflows** for development server
- **Environment variable configuration** for secrets management
- **Progressive Web App** capabilities for mobile-like experience

The deployment uses:
1. Backend server on port 8000
2. Frontend development server with proxy configuration
3. WebSocket connections for real-time features
4. Static file serving for PWA assets

## Changelog

- June 22, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.