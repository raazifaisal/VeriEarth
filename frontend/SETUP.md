# VeriEarth Frontend - Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```

Update `.env` with your backend URL:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### 4. Build for Production
```bash
npm run build
npm start
```

## Docker Setup

### Option 1: Docker Compose (Recommended)

If you have an existing backend service, add the frontend to your `docker-compose.yml`:

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
```

Then run:
```bash
docker-compose up --build
```

### Option 2: Standalone Docker

Build the image:
```bash
docker build -t veriearth-frontend .
```

Run the container:
```bash
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  veriearth-frontend
```

## Features Overview

### 1. Landing Page
- Organization selection
- Auto-redirect to dashboard when organization is selected
- Persistent organization context across sessions

### 2. Dashboard (`/dashboard`)
- 6 KPI cards showing key metrics:
  - Total Facilities
  - Total Shipments
  - Total Routes
  - Total CO₂ Emissions
  - Average AQI
  - Facilities with Poor Air Quality
- CO₂ emissions trend chart (6 months)
- Transport mode distribution pie chart

### 3. Data Ingestion (`/ingestion`)
- Drag-and-drop CSV file upload
- Entity type selection:
  - Facilities
  - Shipments
  - Routes
  - Suppliers
  - Products
- Data preview before import
- Real-time upload progress
- Success/error notifications

### 4. Enrichment (`/enrichment`)
- Facility table with:
  - Checkbox selection (individual or bulk)
  - EO data status indicators
  - Last enrichment timestamp
  - AQI scores
  - Pollution level badges
- Real-time enrichment progress tracking:
  - Current pollutant being fetched
  - Progress percentage
  - Estimated time remaining
  - Success/failure status
- Single facility or bulk enrichment

### 5. Analytics (`/analytics`)
- **Emissions Tab:**
  - Emissions by transport mode (bar chart)
  - Top 5 CO₂ emitters (horizontal bar chart)
  - Summary statistics
- **Air Quality Tab:**
  - Pollutant concentrations (radar chart)
  - Facilities ranked by AQI
  - Pollutant trends over time (line chart)

### 6. Knowledge Graph (`/knowledge-graph`)
- Coming soon placeholder
- Network statistics preview
- Critical hubs display
- Network health metrics

## Technical Architecture

### Stack
- **Framework:** Next.js 13.5 with App Router
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui (Radix UI primitives)
- **Data Fetching:** React Query (TanStack Query)
- **HTTP Client:** Axios
- **Charts:** Recharts
- **Forms:** React Hook Form with Zod validation
- **Themes:** next-themes

### Project Structure
```
├── app/                    # Next.js pages (App Router)
│   ├── dashboard/
│   ├── ingestion/
│   ├── enrichment/
│   ├── analytics/
│   ├── knowledge-graph/
│   ├── layout.tsx
│   └── page.tsx
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── dashboard-header.tsx
│   ├── dashboard-nav.tsx
│   ├── data-upload.tsx
│   ├── enrichment-progress-card.tsx
│   ├── facility-table.tsx
│   ├── org-selector.tsx
│   └── pollution-badge.tsx
├── lib/                  # Utilities
│   ├── api.ts           # API client with typed endpoints
│   ├── organization-context.tsx
│   └── utils.ts
├── types/               # TypeScript definitions
│   └── index.ts
└── public/              # Static assets
```

### State Management
- **Organization Context:** React Context for organization selection
- **Server State:** React Query for API data caching and synchronization
- **Local State:** React hooks (useState, useEffect)

### API Integration

The frontend connects to the FastAPI backend via Axios. All API calls are typed and use React Query for:
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

Key API endpoints:
```typescript
// Facilities
GET  /api/facilities?org_id={org_id}
POST /api/supply-chain/facilities/{facility_id}/enrich-eo

// Ingestion
POST /api/ingestion/upload
POST /api/ingestion/preview
POST /api/ingestion/import

// Dashboard
GET  /api/dashboard/kpis?org_id={org_id}
GET  /api/dashboard/emissions-trend?org_id={org_id}
```

## Development Tips

### Mock Data
The application includes comprehensive mock data for development. When the backend is unavailable, the UI will gracefully fall back to mock data.

### Hot Reload
Next.js provides hot module replacement. Changes to components are reflected immediately.

### Type Safety
All components, API responses, and props are fully typed. Use TypeScript's IntelliSense for better DX.

### Theming
- The app supports light and dark modes
- Toggle via the header icon
- Preferences persist across sessions
- CSS variables in `globals.css` control the theme

### Adding New Pages
1. Create a new directory in `app/`
2. Add a `page.tsx` file
3. Wrap content with `<DashboardHeader />`
4. Add route to `dashboard-nav.tsx`

## Troubleshooting

### Build Errors
If you encounter build errors:
```bash
rm -rf .next
npm run build
```

### Port Already in Use
Change the port in `package.json`:
```json
"dev": "next dev -p 3001"
```

### API Connection Issues
- Ensure backend is running on the configured `NEXT_PUBLIC_API_URL`
- Check CORS settings on the backend
- Verify network connectivity

### TypeScript Errors
Run type checking:
```bash
npm run typecheck
```

## Performance Optimizations

- Server-side rendering for initial page load
- Automatic code splitting per route
- Image optimization via Next.js Image component
- React Query caching reduces API calls
- Lazy loading for heavy components

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## Contributing

1. Follow the existing code structure
2. Use TypeScript for all new code
3. Ensure responsive design (mobile, tablet, desktop)
4. Add proper error handling
5. Test with both real and mock data
6. Run `npm run build` before committing

## Support

For issues or questions, please contact the VeriEarth development team.
