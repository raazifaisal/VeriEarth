'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Upload, Sparkles, BarChart3, Database, Settings } from 'lucide-react';

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Data Ingestion',
    href: '/ingestion',
    icon: Upload,
  },
  {
    title: 'Data Management',
    href: '/data-management',
    icon: Database,
  },
  {
    title: 'Enrichment',
    href: '/enrichment',
    icon: Sparkles,
  },
  {
    title: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center space-x-2 md:space-x-4 lg:space-x-6 overflow-x-auto scrollbar-hide">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'text-xs md:text-sm font-medium transition-colors hover:text-primary flex items-center gap-1 md:gap-2 whitespace-nowrap',
              pathname === item.href
                ? 'text-primary'
                : 'text-muted-foreground'
            )}
          >
            <Icon className="h-3 w-3 md:h-4 md:w-4" />
            <span className="hidden sm:inline">{item.title}</span>
          </Link>
        );
      })}
    </nav>
  );
}
