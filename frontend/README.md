# VeriEarth Frontend

Modern, professional Next.js-based SaaS dashboard for VeriEarth - a supply chain carbon tracking and air quality monitoring platform.

## Features

### Core Functionality
- **Dashboard**: Overview with KPI cards, CO₂ emissions trends, and transport mode distribution
- **Data Ingestion**: Drag-and-drop CSV upload with preview and validation
- **Enrichment**: Real-time Earth Observation data enrichment with progress tracking
- **Analytics**: Detailed emissions and air quality insights with interactive charts
- **Knowledge Graph**: Network visualization (coming soon)

### Technical Features
- Multi-organization support with context switching
- Real-time progress tracking for enrichment operations
- Responsive design with dark mode support
- Interactive data visualizations using Recharts
- Type-safe API integration with React Query
- Modern UI components from shadcn/ui

## Tech Stack

- **Next.js 13.5** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **React Query** for data fetching and caching
- **Axios** for API calls
- **Recharts** for data visualizations
- **React Hook Form** with Zod validation

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

4. Update the `.env` file with your API URL:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

Build the application:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

## Docker Setup

### Build and Run with Docker Compose

If you have an existing backend service, you can integrate the frontend using Docker Compose:

```bash
docker-compose up --build
```

This will:
- Build the frontend Docker image
- Start the frontend on port 3000
- Connect to the backend service

### Standalone Docker Build

Build the Docker image:

```bash
docker build -t veriearth-frontend .
```

Run the container:

```bash
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 veriearth-frontend
```

## Project Structure

```
veriearth-frontend/
├── app/                       # Next.js App Router pages
│   ├── dashboard/            # Dashboard overview
│   ├── ingestion/            # Data upload page
│   ├── enrichment/           # EO enrichment page
│   ├── analytics/            # Analytics and charts
│   ├── knowledge-graph/      # Network visualization
│   ├── layout.tsx            # Root layout
│   └── page.tsx              # Landing/login page
├── components/               # React components
│   ├── ui/                   # shadcn components
│   ├── dashboard-header.tsx
│   ├── dashboard-nav.tsx
│   ├── data-upload.tsx
│   ├── enrichment-progress-card.tsx
│   ├── facility-table.tsx
│   ├── org-selector.tsx
│   └── pollution-badge.tsx
├── lib/                      # Utilities
│   ├── api.ts               # API client
│   ├── organization-context.tsx
│   └── utils.ts
├── types/                    # TypeScript types
│   └── index.ts
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Integration

The frontend integrates with the FastAPI backend at `http://localhost:8000`.

### Key Endpoints

- `GET /api/facilities?org_id={org_id}` - List facilities
- `POST /api/ingestion/upload` - Upload CSV files
- `POST /api/ingestion/preview` - Preview uploaded data
- `POST /api/ingestion/import` - Import data
- `POST /api/supply-chain/organizations/{org_id}/enrich-all` - Enrich all facilities
- `POST /api/supply-chain/facilities/{facility_id}/enrich-eo` - Enrich single facility
- `GET /api/supply-chain/shipments?org_id={org_id}` - List shipments
- `GET /api/supply-chain/routes?org_id={org_id}` - List routes
- `GET /api/dashboard/kpis?org_id={org_id}` - Get dashboard KPIs

## Features Guide

### 1. Organization Selection

Select your organization from the dropdown in the header. The selected organization context is persisted across sessions.

### 2. Dashboard

View key metrics:
- Total facilities, shipments, and routes
- Total CO₂ emissions
- Average AQI score
- Facilities with poor air quality

Interactive charts show emissions trends and transport mode distribution.

### 3. Data Ingestion

Upload CSV files for:
- Facilities
- Shipments
- Routes
- Suppliers
- Products

Features:
- Drag-and-drop file upload
- Data preview before import
- Progress tracking
- Success/error notifications

### 4. Enrichment

Enrich facilities with Earth Observation data:
- Select individual facilities or multiple
- Real-time progress tracking
- View enrichment status for each pollutant
- Historical enrichment data

### 5. Analytics

Analyze your supply chain:
- **Emissions Tab**: View emissions by transport mode, top emitters, and trends
- **Air Quality Tab**: Pollutant concentrations, facility rankings, and trends

### 6. Knowledge Graph

Visual network representation of your supply chain (coming soon).

## Development Notes

### Mock Data

The application includes mock data for development and testing. When the backend is unavailable, the frontend will use mock data to demonstrate functionality.

### Error Handling

All API calls include proper error handling with user-friendly toast notifications.

### Real-time Updates

Enrichment progress uses polling (2-second intervals) to provide real-time updates.

### Theme Support

The application supports light and dark modes via the theme toggle in the header.

## Contributing

1. Follow the existing code structure and conventions
2. Use TypeScript for all new code
3. Ensure components are responsive
4. Add proper error handling
5. Test with both real and mock data

## License

Proprietary - VeriEarth Platform
