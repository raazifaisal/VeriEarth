'use client';

import { OrgSelector } from './org-selector';
import { DashboardNav } from './dashboard-nav';
import { Button } from './ui/button';
import { Moon, Sun, Laptop, Leaf, LogOut } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useAuth } from '@/lib/auth-context';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function DashboardHeader() {
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();

  return (
    <header className="fixed top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center gap-4 px-4 md:px-6 lg:px-8 w-full">
        <div className="mr-2 md:mr-8 flex items-center space-x-2 flex-shrink-0">
          <Leaf className="h-6 w-6 text-emerald-600 dark:text-emerald-500" />
          <span className="text-lg md:text-xl font-bold">VeriEarth</span>
        </div>

        <div className="flex-1 min-w-0">
          <DashboardNav />
        </div>

        <div className="ml-auto flex items-center gap-2 md:gap-4 flex-shrink-0">
          <div className="hidden md:block">
            <OrgSelector />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" title="Theme">
                <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                <span className="sr-only">Theme</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-36">
              <DropdownMenuRadioGroup value={theme as string} onValueChange={(v) => setTheme(v)}>
                <DropdownMenuRadioItem value="light">
                  <Sun className="mr-2 h-4 w-4" /> Light
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="dark">
                  <Moon className="mr-2 h-4 w-4" /> Dark
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="system">
                  <Laptop className="mr-2 h-4 w-4" /> System
                </DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
            <span className="sr-only">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
