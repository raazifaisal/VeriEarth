import { Badge } from '@/components/ui/badge';
import type { PollutionLevel } from '@/types';

interface PollutionBadgeProps {
  level: PollutionLevel | undefined;
}

export function PollutionBadge({ level }: PollutionBadgeProps) {
  if (!level) {
    return <Badge variant="outline">Unknown</Badge>;
  }

  const configs: Record<PollutionLevel, { label: string; className: string }> = {
    good: {
      label: 'Good',
      className: 'bg-green-500 text-white hover:bg-green-600',
    },
    moderate: {
      label: 'Moderate',
      className: 'bg-yellow-500 text-white hover:bg-yellow-600',
    },
    unhealthy_sensitive: {
      label: 'Unhealthy (Sensitive)',
      className: 'bg-orange-500 text-white hover:bg-orange-600',
    },
    unhealthy: {
      label: 'Unhealthy',
      className: 'bg-red-500 text-white hover:bg-red-600',
    },
    very_unhealthy: {
      label: 'Very Unhealthy',
      className: 'bg-red-700 text-white hover:bg-red-800',
    },
    hazardous: {
      label: 'Hazardous',
      className: 'bg-purple-700 text-white hover:bg-purple-800',
    },
  };

  const config = configs[level];

  return <Badge className={config.className}>{config.label}</Badge>;
}
