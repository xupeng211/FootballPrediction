# Football Prediction Frontend

Modern Vue 3 + TypeScript frontend for the Football Prediction system.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🛠️ Tech Stack

- **Framework**: Vue 3 (Composition API)
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Pinia
- **Routing**: Vue Router
- **API Client**: Axios

## 📁 Project Structure

```
src/
├── api/           # API client and configuration
├── components/    # Vue components
├── composables/    # Vue composition functions
├── router/         # Vue Router configuration
├── stores/         # Pinia stores
├── types/          # TypeScript type definitions
├── views/          # Page components
├── utils/          # Utility functions
├── assets/         # Static assets
├── App.vue         # Root component
├── main.ts         # Application entry point
└── style.css       # Global styles
```

## 🔗 Backend Integration

The frontend connects to the backend API at `http://localhost:8000/api/v1`.

### API Endpoints Used

- `GET /api/v1/predictions` - Get predictions
- `GET /api/v1/matches` - Get recent matches
- `GET /api/v1/health` - Health check

### Environment Variables

Create `.env.development`:
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 🧪 Development

### Code Style

This project uses ESLint and TypeScript for code quality.

```bash
# Lint code
npm run lint

# Type checking
npm run type-check
```

### Mock Data

When the backend API is not available, the frontend automatically falls back to mock data for development.

## 📱 Features

- **Dashboard**: Real-time prediction display
- **Match Information**: Upcoming and live matches
- **Prediction Analysis**: Confidence scores and probability breakdowns
- **Responsive Design**: Works on all device sizes

## 🚀 Deployment

The frontend is configured for Docker deployment in the main project.

```bash
# From project root
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up
```

Then access the frontend at: http://localhost:3000
