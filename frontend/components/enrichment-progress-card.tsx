'use client';

import { Card, CardContent } from './ui/card';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { CheckCircle2, Loader2, XCircle, Clock } from 'lucide-react';
import type { EnrichmentProgress } from '@/types';

interface EnrichmentProgressCardProps {
  progress: EnrichmentProgress;
}

export function EnrichmentProgressCard({ progress }: EnrichmentProgressCardProps) {
  const getStatusIcon = () => {
    switch (progress.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = () => {
    switch (progress.status) {
      case 'completed':
        return <Badge className="bg-green-500">Completed</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'processing':
        return <Badge className="bg-blue-500">Processing</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              {getStatusIcon()}
              <div>
                <h4 className="font-semibold">{progress.facility_name}</h4>
                {progress.current_pollutant && (
                  <p className="text-sm text-muted-foreground">
                    Fetching {progress.current_pollutant} ({progress.completed_pollutants}/{progress.total_pollutants})
                  </p>
                )}
              </div>
            </div>
            {getStatusBadge()}
          </div>

          {progress.status === 'processing' && (
            <>
              <Progress value={progress.progress_percent} />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{progress.progress_percent}% complete</span>
                {progress.estimated_time_remaining && (
                  <span>{progress.estimated_time_remaining}s remaining</span>
                )}
              </div>
            </>
          )}

          {progress.status === 'failed' && progress.error_message && (
            <p className="text-sm text-red-500">{progress.error_message}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
