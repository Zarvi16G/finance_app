/**
 * Shared dashboard shell: paper sidebar navigation, header with
 * theme toggle and user dropdown, mobile drawer, and the outlet
 * where routed pages render.
 */
import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Icon } from '@iconify/react';
import SimpleBar from 'simplebar-react';
import { AMSidebar, AMMenu, AMMenuItem } from 'tailwind-sidebar';
import 'tailwind-sidebar/styles.css';
import { useTheme } from '../components/provider/theme-provider';
import { useAuth } from '../auth/AuthContext';
import { Button } from '../components/ui/button';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetTitle } from '../components/ui/sheet';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';

/** The order is the design's: what you have, then what you plan, then how it
 *  is going, then the account. */
const NAV_ITEMS = [
  { name: 'Dashboard', icon: 'solar:widget-2-linear', url: '/' },
  { name: 'Movimientos', icon: 'solar:list-linear', url: '/movimientos' },
  { name: 'Extractos', icon: 'solar:document-text-linear', url: '/extractos' },
  { name: 'Deudas', icon: 'solar:wallet-money-linear', url: '/deudas' },
  { name: 'Metas', icon: 'solar:target-linear', url: '/metas' },
  { name: 'Experiencias', icon: 'solar:map-point-wave-linear', url: '/experiencias' },
  { name: 'Patrimonio', icon: 'solar:safe-square-linear', url: '/patrimonio' },
  { name: 'Wealthness', icon: 'solar:heart-pulse-linear', url: '/wealthness' },
  { name: 'Análisis', icon: 'solar:magic-stick-3-linear', url: '/analisis' },
  { name: 'Perfil', icon: 'solar:user-circle-linear', url: '/perfil' },
];

function sectionLabel(pathname: string): string {
  const match = NAV_ITEMS.slice(1).find((item) => pathname.startsWith(item.url));
  return match?.name ?? 'Dashboard';
}

function BrandLogo() {
  return (
    <Link to="/" className="block px-6 py-5" aria-label="Patrimonio, ir al inicio">
      <span className="fig text-[21px] font-medium text-sidebar-foreground">Patrimonio</span>
    </Link>
  );
}

function SidebarContent({ onClose }: { onClose?: () => void }) {
  const { pathname } = useLocation();
  const { theme } = useTheme();
  const sidebarMode = theme === 'light' || theme === 'dark' ? theme : undefined;

  return (
    <AMSidebar
      collapsible="none"
      animation={true}
      showProfile={false}
      width={'264px'}
      showTrigger={false}
      mode={sidebarMode}
      className="fixed left-0 top-0 border-r border-border bg-sidebar dark:bg-sidebar z-10 h-screen"
    >
      <div className="border-b border-border bg-sidebar">
        <BrandLogo />
      </div>

      <SimpleBar className="h-[calc(100vh-90px)]">
        <div className="px-3 pt-4">
          <AMMenu
            subHeading="Tus finanzas"
            ClassName="hide-menu leading-21 text-[11px] uppercase tracking-[0.15em] text-muted-foreground"
          />
          {NAV_ITEMS.map((item) => {
            const isSelected =
              item.url === '/' ? pathname === '/' : pathname.startsWith(item.url);
            return (
              <div key={item.url} onClick={onClose}>
                <AMMenuItem
                  icon={<Icon icon={item.icon} height={17} width={17} />}
                  isSelected={isSelected}
                  link={item.url}
                  component={Link}
                  className="mt-0.5 text-sm text-sidebar-foreground dark:text-sidebar-foreground"
                >
                  <span className="truncate flex-1">{item.name}</span>
                </AMMenuItem>
              </div>
            );
          })}
        </div>
      </SimpleBar>
    </AMSidebar>
  );
}

function ProfileMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const initials = (user?.username || 'U').slice(0, 2).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-sm p-1 outline-none transition hover:bg-lightprimary">
          <Avatar className="h-9 w-9 rounded-sm">
            <AvatarFallback className="bg-lightprimary font-mono text-xs text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <p className="eyebrow-sm">Sesión</p>
          <p className="mt-1 text-sm font-semibold">{user?.username}</p>
          <p className="text-xs text-muted-foreground">{user?.email || '—'}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate('/perfil')}>
          <Icon icon="solar:user-circle-linear" className="mr-2 h-4 w-4" />
          Perfil
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleLogout} className="text-error focus:text-error">
          <Icon icon="solar:logout-2-linear" className="mr-2 h-4 w-4" />
          Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function FullLayout() {
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();

  const toggleMode = () => setTheme(theme === 'light' ? 'dark' : 'light');

  return (
    <div className="flex w-full min-h-screen">
      <div className="page-wrapper flex w-full">
        <div className="xl:block hidden">
          <SidebarContent />
        </div>

        <div className="body-wrapper min-w-0 flex-1 bg-background xl:ml-[264px]">
          {/* Top Header — the statement masthead strip */}
          <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur-sm px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="icon"
                className="xl:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation"
              >
                <Icon icon="solar:hamburger-menu-linear" height={18} width={18} />
              </Button>
              <p className="letterhead">
                <span className="fig font-semibold text-foreground">Patrimonio</span>
                <span className="mx-2 text-border">/</span>
                {sectionLabel(pathname)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleMode}
                aria-label="Toggle theme"
                className="text-muted-foreground hover:text-foreground"
              >
                <Icon
                  icon={theme === 'dark' ? 'solar:sun-linear' : 'solar:moon-linear'}
                  height={18}
                  width={18}
                />
              </Button>
              <ProfileMenu />
            </div>
          </header>

          {/* Mobile drawer */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetContent side="left" className="p-0 w-[264px]">
              <SheetTitle>
                <VisuallyHidden>Navigation</VisuallyHidden>
              </SheetTitle>
              <SidebarContent onClose={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>

          {/* Body Content */}
          <div className="mx-auto w-full max-w-[1240px] px-6 py-8">
            <main className="grow">
              <Outlet />
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}

export { NAV_ITEMS };
