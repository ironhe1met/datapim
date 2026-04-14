import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  Package,
  FolderTree,
  Users,
  Upload,
  Settings,
  Menu,
  LogOut,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { ThemeToggle } from '@/components/theme-toggle';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import type { DashboardStats, UserRole } from '@/types/api';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: UserRole[];
  badgeKey?: keyof DashboardStats;
}

const navItems: NavItem[] = [
  { to: '/', label: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/products', label: 'nav.products', icon: Package },
  { to: '/categories', label: 'nav.categories', icon: FolderTree },
];

const managementItems: NavItem[] = [
  { to: '/users', label: 'nav.users', icon: Users, roles: ['admin', 'manager'] },
  { to: '/import', label: 'nav.import', icon: Upload, roles: ['admin', 'manager'] },
  { to: '/settings', label: 'nav.settings', icon: Settings, roles: ['admin'] },
];

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function SidebarNav({
  onNavigate,
  stats,
}: {
  onNavigate?: () => void;
  stats: DashboardStats | undefined;
}) {
  const { t } = useTranslation();
  const { user, hasRole } = useAuthStore();

  const filteredNavItems = navItems.filter(
    (item) => !item.roles || (user && hasRole(item.roles)),
  );
  const filteredManagementItems = managementItems.filter(
    (item) => !item.roles || (user && hasRole(item.roles)),
  );

  return (
    <nav className="flex flex-col gap-1 px-3 py-2">
      {filteredNavItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )
          }
        >
          <item.icon className="h-4 w-4" />
          <span className="flex-1">{t(item.label)}</span>
          {item.badgeKey && stats && stats[item.badgeKey] ? (
            <Badge variant="secondary" className="ml-auto text-xs">
              {String(stats[item.badgeKey])}
            </Badge>
          ) : null}
        </NavLink>
      ))}

      {filteredManagementItems.length > 0 && (
        <>
          <Separator className="my-2" />
          {filteredManagementItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              <item.icon className="h-4 w-4" />
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
        </>
      )}
    </nav>
  );
}

export function AppLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const { data: stats } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const response = await apiClient.get<DashboardStats>(
        '/api/dashboard/stats',
      );
      return response.data;
    },
    staleTime: 60_000,
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center px-4">
          <span className="text-lg font-bold text-primary">DataPIM</span>
        </div>
        <Separator />
        <ScrollArea className="flex-1">
          <SidebarNav stats={stats} />
        </ScrollArea>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-14 items-center gap-4 border-b bg-card px-4">
          {/* Mobile hamburger */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger
              render={
                <Button variant="ghost" size="icon" className="md:hidden" />
              }
            >
              <Menu className="h-5 w-5" />
              <span className="sr-only">Menu</span>
            </SheetTrigger>
            <SheetContent side="left" className="w-60 p-0">
              <SheetTitle className="px-4 pt-4 text-lg font-bold text-primary">
                DataPIM
              </SheetTitle>
              <ScrollArea className="h-full">
                <SidebarNav
                  onNavigate={() => setMobileOpen(false)}
                  stats={stats}
                />
              </ScrollArea>
            </SheetContent>
          </Sheet>

          <span className="text-lg font-bold text-primary md:hidden">
            DataPIM
          </span>

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />

            {user && (
              <DropdownMenu>
                <DropdownMenuTrigger className="inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
                    {getInitials(user.name)}
                  </div>
                  <span className="hidden sm:inline-block">{user.name}</span>
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" sideOffset={8}>
                  <div className="flex flex-col px-2 py-1.5">
                    <span className="text-sm font-medium">{user.name}</span>
                    <span className="text-xs text-muted-foreground">{user.role}</span>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    Вийти
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
