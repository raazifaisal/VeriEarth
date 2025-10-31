# Frontend UI Reference: Knowledge Graph Analytics

This document describes the visual design and user experience of the Knowledge Graph Analytics page.

---

## Page Structure

### Navigation
**Path**: `/knowledge-graph`  
**Header**: DashboardHeader component (consistent across platform)  
**Tabs**: Two main tabs
1. 🌐 **Graph Visualization** - Interactive network graph
2. 📈 **Analytics** - Tables, charts, and insights

---

## Tab 1: Graph Visualization

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD HEADER                                           │
└─────────────────────────────────────────────────────────────┘
┌────────────┬────────────────────────────────────────────────┐
│  Filters   │  Knowledge Graph                               │
│  Card      │  Card                                          │
│            │  ┌──────────────────────────────────────────┐  │
│  Search    │  │  Interactive Cytoscape Canvas            │  │
│  [......] │  │  [Nodes and Edges]                       │  │
│            │  │                                          │  │
│  Modes     │  │  [Facilities: Blue Circles]              │  │
│  □ truck   │  │  [Suppliers: Green Hexagons]             │  │
│  □ rail    │  │  [Routes: Gray Arrows]                   │  │
│  □ sea     │  │                                          │  │
│  □ air     │  │                                          │  │
│            │  │                                          │  │
│  Entities  │  │                                          │  │
│  ☑ Suppl.  │  │                                          │  │
│  ☑ Facil.  │  │                                          │  │
│  ☑ Routes  │  │                                          │  │
│            │  │                                          │  │
│  [Apply]   │  │  [Fit] [Re-layout]                       │  │
│            │  └──────────────────────────────────────────┘  │
│            │  12 nodes / 15 edges                           │
└────────────┴────────────────────────────────────────────────┘
```

### Features
- **Drag**: Move nodes
- **Zoom**: Scroll to zoom in/out
- **Click Node**: Load neighbors (expands graph)
- **Fit Button**: Auto-fit graph to viewport
- **Re-layout Button**: Apply force-directed layout

### Visual Design
- **Facilities**: Blue circles (#60a5fa)
- **Suppliers**: Green hexagons (#22c55e)
- **Routes**: Gray arrows (#94a3b8)
- **Supplies**: Dashed green lines (#10b981)

---

## Tab 2: Analytics

### Section 1: KPI Cards (Top Row)

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ ⚠️ Top Choke │ 📈 Top Hub   │ 🍃 Top Emit  │ 💨 AQI Alert │
│ F003         │ F003         │ 1250.1 kg    │ 3            │
│ Score: 18.00 │ Score: 0.298 │ F101→...→F001│ Facilities   │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**Design**:
- 4 cards in grid (responsive: 1 col mobile, 2 cols tablet, 4 cols desktop)
- Icons: AlertTriangle (orange), TrendingUp (blue), Leaf (green), Wind (red)
- Large number (2xl font, bold)
- Small description text (muted)

---

### Section 2: Facility Analytics

```
┌─────────────────────────────────────────────────────────────┐
│  Facility Analytics                                         │
│  Structural importance and risk scores                      │
│  ────────────────────────────────────────────────────────  │
│  Facility | Betweenness | PageRank | Community | Risk      │
│  ───────────────────────────────────────────────────────── │
│  F003     │ 18.00       │ 0.298    │ 5         │ 🔴 High  │
│  F001     │ 4.00        │ 0.243    │ 5         │          │
│  F101     │ 2.00        │ 0.189    │ 7         │          │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Design**:
- Card with table
- Risk badge: Red "High Risk" for top 10% betweenness
- Mono font for facility IDs
- Numeric columns right-aligned

---

### Section 3: Route Analytics

```
┌─────────────────────────────────────────────────────────────┐
│  Route Analytics                                            │
│  Important corridors by PageRank                            │
│  ────────────────────────────────────────────────────────  │
│  Route ID | PageRank Score | Importance                    │
│  ───────────────────────────────────────────────────────── │
│  R001     │ 0.289          │ 🔵 Critical                   │
│  R002     │ 0.245          │ 🔵 Critical                   │
│  R003     │ 0.198          │ 🔵 Critical                   │
│  R004     │ 0.156          │ ⚪ High                       │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Design**:
- Top 3: Blue "Critical" badge
- 4–6: Gray "High" badge (secondary variant)
- Mono font for route IDs

---

### Section 4: Frequent Emission Patterns

```
┌─────────────────────────────────────────────────────────────┐
│  Frequent Emission Patterns                                 │
│  Routes that occur often and accumulate high emissions      │
│  ────────────────────────────────────────────────────────  │
│  Pattern                  | Occur | Total Emis | Avg/Trip  │
│  ───────────────────────────────────────────────────────── │
│  F101 → road_truck → F003 │ 5     │ 1250.50 kg │ 250.10 kg │
│  F003 → rail_freight→F001 │ 3     │ 450.25 kg  │ 150.08 kg │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Design**:
- Pattern in mono font (smaller)
- Emissions in bold font
- CO₂ subscript (kg CO₂)

---

### Section 5: Path Comparison

```
┌─────────────────────────────────────────────────────────────┐
│  Path Comparison                                            │
│  Find optimal routes between facilities                     │
│  ────────────────────────────────────────────────────────  │
│  [Source: F101]  [Dest: F003]  [Weight ▼]  [Find Path]     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Path Found              [emission]                    │ │
│  │ Route: F101 → F003 → F001                             │ │
│  │ Total Cost: 1250.50 kg CO₂                            │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Design**:
- Input row: 4 cols (responsive)
- Select dropdown: Distance (km) / Duration (hours) / Emission (kg CO₂)
- Result card: Muted background, badge for weight type
- Large bold number for total cost

---

### Section 6: Environmental Hotspots

```
┌─────────────────────────────────────────────────────────────┐
│  Environmental Hotspots                                     │
│  Facilities with high air quality index                     │
│  ────────────────────────────────────────────────────────  │
│  Facility | Latest AQI | 3-Month Trend | Status            │
│  ───────────────────────────────────────────────────────── │
│  F003     │ 125.3      │ +8.5          │ 🔴 Alert         │
│  F001     │ 78.2       │ +2.1          │ ⚪ Moderate      │
│  F101     │ 45.0       │ -1.3          │ ⚪ Good          │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Design**:
- AQI in bold font
- Trend: Red for positive (worsening), green for negative (improving)
- Status badges:
  - Red "Alert" for AQI ≥100
  - Gray "Moderate" for 50–99
  - Outline "Good" for <50

---

### Section 7: Graph Health

```
┌─────────────────────────────────────────────────────────────┐
│  Graph Health                                               │
│  Status of projected graphs                                 │
│  ────────────────────────────────────────────────────────  │
│  ┌─────────────────────┐  ┌─────────────────────┐         │
│  │ Facility Graph      │  │ Route Graph         │         │
│  │ 12 nodes, 15 rels   │  │ 8 nodes, 10 rels    │         │
│  └─────────────────────┘  └─────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

**Design**:
- 2 cards side by side (responsive: 1 col mobile, 2 cols desktop)
- Small text, border, subtle background

---

## Loading States

### Initial Load (Analytics Tab)
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│               ⟳ (spinning animation)                        │
│     Building graphs and loading analytics...                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Individual Skeletons (if used)
```
┌────────────┐
│ ▒▒▒▒▒▒▒▒  │  (gray animated shimmer)
│ ▒▒▒▒      │
└────────────┘
```

---

## Color Palette

### Primary Colors
- **Primary**: Blue (#3b82f6 or theme primary)
- **Success/Green**: #22c55e
- **Warning/Orange**: #f97316
- **Destructive/Red**: #ef4444

### Neutral Colors
- **Muted Text**: Gray 500 (#6b7280)
- **Border**: Gray 300 (#d1d5db)
- **Background Muted**: Gray 100 (#f3f4f6)

### Semantic Colors
- **Facility**: Blue (#60a5fa)
- **Supplier**: Green (#22c55e)
- **Route**: Gray (#94a3b8)
- **Emission**: Red/Orange gradient
- **AQI Alert**: Red (#ef4444)
- **AQI Good**: Green (#10b981)

---

## Typography

### Headings
- **Page Title**: Not shown (tabs replace top-level title)
- **Card Title**: 1rem, font-semibold
- **Card Description**: 0.875rem, text-muted-foreground

### Body Text
- **Table Cell**: 0.875rem, default weight
- **Facility/Route ID**: Mono font, medium weight
- **Numbers**: Bold for emphasis (KPIs, emissions, scores)

### Icons
- **Size**: 16px (w-4 h-4) for tabs, KPI cards
- **Color**: Matches semantic meaning (orange alert, blue trend, green leaf, red wind)

---

## Responsive Behavior

### Mobile (<768px)
- KPI cards: 1 column
- Filters sidebar: Full width, collapse to accordion
- Graph: Full width, reduced height (500px)
- Tables: Horizontal scroll

### Tablet (768–1024px)
- KPI cards: 2 columns
- Filters sidebar: Fixed width (288px)
- Graph: Remaining width

### Desktop (>1024px)
- KPI cards: 4 columns
- Full layout as shown in diagrams
- Tables: Full width, no scroll

---

## Interactions

### Hover States
- **Buttons**: Background color shift, subtle shadow
- **Table Rows**: Light background highlight
- **Graph Nodes**: Cursor changes to pointer

### Click/Tap Actions
- **KPI Cards**: No action (static display)
- **Table Rows**: No action (future: click to drill down)
- **Graph Nodes**: Load neighbors (expand graph)
- **Path Find Button**: Submit form, show loading spinner
- **Fit/Re-layout Buttons**: Apply graph transformation

### Loading States
- **Buttons**: Change text ("Loading..."), disable
- **Full Page**: Spinner with descriptive message
- **Partial**: Skeleton placeholders (optional)

---

## Accessibility

### Keyboard Navigation
- All interactive elements (buttons, inputs, selects) are keyboard accessible
- Tab order follows visual layout
- Enter key activates buttons

### Screen Readers
- Labels for all inputs
- Alt text for icons (via aria-label)
- Table headers properly marked

### Color Contrast
- All text meets WCAG AA standards (4.5:1 minimum)
- Status badges use both color and text

---

## Animation

### Graph Layout
- `animate: true` in cose-bilkent layout
- Smooth transition as nodes settle

### Tab Switching
- Instant (no animation) for tab content
- Subtle fade-in for analytics data (optional)

### Loading Spinner
- 360° rotation, 1s duration, infinite loop
- Border-bottom colored with theme primary

---

## Error States

### Empty State (No Data)
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              No data available.                             │
│     Please ingest data and sync to Neo4j first.             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Error State (API Failure)
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              ⚠️ Failed to load analytics.                   │
│          Please try again or contact support.               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### No Path Found
```
┌───────────────────────────────────────────────────────────┐
│ No path found between facilities.                         │
└───────────────────────────────────────────────────────────┘
```

---

## Design Tokens (shadcn/ui)

### Components Used
- `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`
- `Table`, `TableHeader`, `TableRow`, `TableHead`, `TableCell`, `TableBody`
- `Badge` (variants: default, destructive, secondary, outline)
- `Button` (variants: default, outline, size: sm)
- `Input`, `Label`, `Select`, `SelectTrigger`, `SelectValue`, `SelectContent`, `SelectItem`
- `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`
- `Skeleton` (for loading states)

### Custom Styling
- `className="text-muted-foreground"` for secondary text
- `className="font-mono"` for facility/route IDs
- `className="font-semibold"` for emphasis
- `className="text-2xl font-bold"` for KPI numbers
- `className="text-xs"` for small text (badges, descriptions)

---

## Implementation Notes

### State Management
- All state via React hooks (`useState`, `useEffect`)
- No global state library (Redux/Zustand) needed for MVP
- `useOrganization()` context hook for org ID

### API Calls
- `apiClient.get/post` from `/lib/api.ts` (Axios wrapper)
- CSRF token automatically handled by `apiClient`
- Parallel fetching with `Promise.all` for multiple endpoints

### Performance
- Lazy loading: Analytics tab data fetched only on first visit
- Memoization: `useMemo` for Cytoscape elements
- Debouncing: Not implemented for MVP (graph filters apply on button click, not on every keystroke)

---

## Future Enhancements

### Visualizations
- **Charts**: Add Chart.js/Recharts for trend lines (AQI over time, emissions by mode)
- **Heatmap**: Geographic overlay of EO hotspots on map
- **Network Metrics Panel**: Real-time graph stats (density, diameter, clustering coefficient)

### Interactions
- **Drill-Down**: Click facility/route in table to highlight in graph
- **Filtering**: Filter analytics by community, AQI range, emission threshold
- **Export**: Download tables as CSV, graph as PNG

### Polish
- **Dark Mode**: Respect user theme preference
- **Tooltips**: Hover over table headers for metric definitions
- **Help Modals**: "What is Betweenness?" explanatory dialogs

---

## Conclusion
The Knowledge Graph Analytics page delivers a professional, data-dense interface that balances visual appeal with information density. The two-tab structure separates exploratory graph visualization from structured analytics, catering to different user workflows. The design language is consistent with the VeriEarth platform, using shadcn/ui components for a modern, polished look.

**Status**: ✅ Fully implemented  
**Figma Mockup**: Not created (implementation-first approach)  
**User Feedback**: Pending

