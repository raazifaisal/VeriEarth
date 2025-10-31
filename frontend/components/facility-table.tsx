'use client';

import { useState } from 'react';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { PollutionBadge } from './pollution-badge';
import { CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react';
import type { Facility } from '@/types';
import { format } from 'date-fns';

interface FacilityTableProps {
  facilities: Facility[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onEnrich?: (facilityId: string) => void;
  loading?: boolean;
}

export function FacilityTable({
  facilities,
  selectedIds,
  onSelectionChange,
  onEnrich,
  loading = false,
}: FacilityTableProps) {
  const [sortColumn, setSortColumn] = useState<keyof Facility | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const isAllSelected = facilities.length > 0 && selectedIds.length === facilities.length;
  const isSomeSelected = selectedIds.length > 0 && selectedIds.length < facilities.length;

  const handleSelectAll = () => {
    if (isAllSelected) {
      onSelectionChange([]);
    } else {
      onSelectionChange(facilities.map((f) => f.id));
    }
  };

  const handleSelectOne = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((selectedId) => selectedId !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  const getStatusIcon = (status: Facility['eo_data_status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <span className="h-4 w-4 text-muted-foreground">—</span>;
    }
  };

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">
              <Checkbox
                checked={isAllSelected}
                onCheckedChange={handleSelectAll}
                aria-label="Select all"
              />
            </TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Location</TableHead>
            <TableHead className="text-center">EO Status</TableHead>
            <TableHead>Last Enrichment</TableHead>
            <TableHead className="text-center">AQI Score</TableHead>
            <TableHead>Air Quality</TableHead>
            <TableHead className="w-12"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={9} className="text-center py-8">
                <Loader2 className="h-6 w-6 animate-spin mx-auto" />
              </TableCell>
            </TableRow>
          ) : facilities.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                No facilities found
              </TableCell>
            </TableRow>
          ) : (
            facilities.map((facility) => (
              <TableRow key={facility.id}>
                <TableCell>
                  <Checkbox
                    checked={selectedIds.includes(facility.id)}
                    onCheckedChange={() => handleSelectOne(facility.id)}
                    aria-label={`Select ${facility.name}`}
                  />
                </TableCell>
                <TableCell className="font-medium">{facility.name}</TableCell>
                <TableCell>{facility.type}</TableCell>
                <TableCell>{facility.location}</TableCell>
                <TableCell className="text-center">
                  {getStatusIcon(facility.eo_data_status)}
                </TableCell>
                <TableCell>
                  {facility.last_enrichment
                    ? format(new Date(facility.last_enrichment), 'MMM d, yyyy HH:mm')
                    : '—'}
                </TableCell>
                <TableCell className="text-center">
                  {facility.aqi_score ? (
                    <Badge variant="outline">{facility.aqi_score.toFixed(1)}</Badge>
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell>
                  <PollutionBadge level={facility.pollution_level} />
                </TableCell>
                <TableCell>
                  {onEnrich && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onEnrich(facility.id)}
                    >
                      Enrich
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
