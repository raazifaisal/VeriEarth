export interface Organization {
  id: string;
  name: string;
}

export interface Facility {
  id: string;
  name: string;
  type: string;
  location: string;
  latitude?: number;
  longitude?: number;
  org_id: string;
  eo_data_status?: 'completed' | 'pending' | 'failed' | null;
  last_enrichment?: string;
  aqi_score?: number;
  pollution_level?: PollutionLevel;
  created_at?: string;
}

export interface Shipment {
  id: string;
  origin: string;
  destination: string;
  weight: number;
  transport_mode: TransportMode;
  distance_km: number;
  co2_emissions_kg: number;
  org_id: string;
  created_at?: string;
}

export interface Route {
  id: string;
  name: string;
  origin: string;
  destination: string;
  distance_km: number;
  transport_mode: TransportMode;
  co2_emissions_kg: number;
  org_id: string;
  created_at?: string;
}

export interface EOData {
  facility_id: string;
  pollutant: string;
  value: number;
  unit: string;
  timestamp: string;
}

export interface EnrichmentProgress {
  facility_id: string;
  facility_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_pollutant?: string;
  progress_percent: number;
  total_pollutants: number;
  completed_pollutants: number;
  estimated_time_remaining?: number;
  error_message?: string;
}

export interface DashboardKPIs {
  total_facilities: number;
  total_shipments: number;
  total_routes: number;
  total_co2_emissions: number;
  average_aqi: number;
  facilities_poor_air_quality: number;
}

export interface EmissionsData {
  month: string;
  emissions: number;
}

export interface TransportModeDistribution {
  mode: TransportMode;
  count: number;
  percentage: number;
}

export type TransportMode = 'truck' | 'ship' | 'train' | 'air' | 'rail';

export type PollutionLevel = 'good' | 'moderate' | 'unhealthy_sensitive' | 'unhealthy' | 'very_unhealthy' | 'hazardous';

export interface UploadProgress {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  message?: string;
  preview_data?: any[];
  error?: string;
}

export interface IngestResult {
  status: string;
  created?: number;
  rows_imported?: number;
  rows_failed?: number;
  errors?: any[];
  errors_count?: number;
}
