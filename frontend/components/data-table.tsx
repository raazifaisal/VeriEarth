'use client';

import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Edit2, Trash2, Save, X, Loader2 } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

interface DataTableProps {
  data: any[];
  entityType: string;
  isLoading: boolean;
  onDelete: (id: string) => void;
  onUpdate: (id: string, data: any) => void;
}

export function DataTable({ data, entityType, isLoading, onDelete, onUpdate }: DataTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editedData, setEditedData] = useState<any>({});

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No data found. Import some data to get started.</p>
      </div>
    );
  }

  // Special handling for shipments to show ESG-relevant columns
  const getDisplayColumns = () => {
    if (entityType === 'facilities') {
      // Explicit column order for facilities, including supplier ownership
      const base = [
        'id',
        'name',
        'facility_type',
        'city',
        'country',
        'lat',
        'lon',
        'address',
        'capacity_tons',
      ];
      // Add supplier columns if present in data
      const hasSupplier = data.some((r) => 'supplier_name' in r || 'supplier_id' in r);
      return hasSupplier ? [...base, 'supplier_name'] : base;
    }
    if (entityType === 'shipments') {
      return [
        'origin_facility_name',
        'destination_facility_name', 
        'transport_mode',
        'weight_tonnes',
        'volume_m3',
        'distance_km',
        'calculated_emissions_kg_co2',
        'unit_emissions_kg_per_tonne_km',
        'calculated_cost',
        'unit_transportation_cost',
        'pickup_date',
        'delivery_date',
        'carrier',
        'status'
      ];
    }
    
    if (entityType === 'routes') {
      return [
        'origin_facility_name',
        'origin_location',
        'destination_facility_name',
        'destination_location',
        'transport_mode',
        'distance_km',
        'duration_hours',
        'is_multi_leg',
        'is_active'
      ];
    }
    
    return Object.keys(data[0] || {}).filter(
      (key) => !key.startsWith('_') && key !== 'created_at' && key !== 'updated_at'
    );
  };

  const columns = getDisplayColumns();

  const formatCellValue = (key: string, value: any) => {
    if (entityType === 'shipments') {
      switch (key) {
        case 'origin_facility_name':
        case 'destination_facility_name':
          return value || '-';
        case 'transport_mode':
          return value ? value.replace('_', ' ').toUpperCase() : '-';
        case 'weight_tonnes':
          return value ? `${value} t` : '-';
        case 'volume_m3':
          return value ? `${value} m³` : '-';
        case 'distance_km':
          return value ? `${value.toLocaleString()} km` : '-';
        case 'calculated_emissions_kg_co2':
          return value ? `${value} kg CO₂` : '-';
        case 'unit_emissions_kg_per_tonne_km':
          return value ? `${value} kg/t·km` : '-';
        case 'calculated_cost':
          return value ? `$${value.toLocaleString()}` : '-';
        case 'unit_transportation_cost':
          return value ? `$${value}/t·km` : '-';
        case 'pickup_date':
        case 'delivery_date':
          return value ? new Date(value).toLocaleDateString() : '-';
        case 'carrier':
          return value || '-';
        case 'status':
          return value ? value.replace('_', ' ').toUpperCase() : '-';
        default:
          return value || '-';
      }
    }
    
    if (entityType === 'routes') {
      switch (key) {
        case 'origin_facility_name':
        case 'destination_facility_name':
          return value || '-';
        case 'origin_location':
        case 'destination_location':
          return value || '-';
        case 'transport_mode':
          return value ? value.replace('_', ' ').toUpperCase() : '-';
        case 'distance_km':
          return value ? `${value} km` : '-';
        case 'duration_hours':
          return value ? `${value} hrs` : '-';
        case 'is_multi_leg':
        case 'is_active':
          return value ? 'Yes' : 'No';
        default:
          return value || '-';
      }
    }
    
    // Handle boolean values for all entity types
    if (key === 'is_active' || key === 'is_multi_leg') {
      return value ? 'Yes' : 'No';
    }
    
    return value || '-';
  };

  const getColumnHeader = (key: string) => {
    if (entityType === 'facilities') {
      const headerMap: { [key: string]: string } = {
        'facility_type': 'Facility Type',
        'capacity_tons': 'Capacity Tons',
        'supplier_name': 'Supplier',
      };
      return headerMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    if (entityType === 'shipments') {
      const headerMap: { [key: string]: string } = {
        'origin_facility_name': 'From',
        'destination_facility_name': 'To',
        'transport_mode': 'Transport',
        'weight_tonnes': 'Weight',
        'volume_m3': 'Volume',
        'distance_km': 'Distance',
        'calculated_emissions_kg_co2': 'Emissions',
        'unit_emissions_kg_per_tonne_km': 'Unit Emissions',
        'calculated_cost': 'Cost',
        'unit_transportation_cost': 'Unit Cost',
        'pickup_date': 'Pickup Date',
        'delivery_date': 'Delivery Date',
        'carrier': 'Carrier',
        'status': 'Status'
      };
      return headerMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    if (entityType === 'routes') {
      const headerMap: { [key: string]: string } = {
        'origin_facility_name': 'From Facility',
        'origin_location': 'From Location',
        'destination_facility_name': 'To Facility',
        'destination_location': 'To Location',
        'transport_mode': 'Transport',
        'distance_km': 'Distance',
        'duration_hours': 'Duration',
        'is_multi_leg': 'Multi-Leg',
        'is_active': 'Active'
      };
      return headerMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const handleSave = () => {
    if (editingId) {
      onUpdate(editingId, editedData);
      setEditingId(null);
      setEditedData({});
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditedData({});
  };

  const handleEdit = (row: any) => {
    setEditingId(row.id);
    setEditedData({ ...row });
  };

  const handleChange = (key: string, value: any) => {
    setEditedData((prev: any) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col} className="capitalize">
                  {getColumnHeader(col)}
                </TableHead>
              ))}
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row) => {
              const isEditing = editingId === row.id;
              return (
                <TableRow key={row.id}>
                  {columns.map((col) => (
                    <TableCell key={col}>
                      {isEditing ? (
                        <Input
                          value={editedData[col] || ''}
                          onChange={(e) => handleChange(col, e.target.value)}
                          className="h-8"
                        />
                      ) : (
                        <span className="text-sm">
                          {formatCellValue(col, row[col])}
                        </span>
                      )}
                    </TableCell>
                  ))}
                  <TableCell className="text-right">
                    {isEditing ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="default"
                          onClick={handleSave}
                        >
                          <Save className="h-3 w-3 mr-1" />
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleCancel}
                        >
                          <X className="h-3 w-3 mr-1" />
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEdit(row)}
                        >
                          <Edit2 className="h-3 w-3 mr-1" />
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => onDelete(row.id)}
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          Delete
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

