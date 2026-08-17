/**
 * Shared dashboard shell: sidebar navigation, header with
theme toggle and user dropdown, mobile drawer, and the
outlet where routed pages render.
 */
import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Icon } from '@iconify/react';
import SimpleBar from 'simplebar-react';
import { AMSidebar, AMMenu, AMMenuItem } from 'tailwind-sidebar';
import 'tailwind-sidebar/styles.css';
import logo from '../assets/logo.svg';
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

const NAV_ITEMS = [
  { name: 'Dashboard', icon: 'solar:widget-2-linear', url: '/' },
  { name: 'Statements', icon: 'solar:document-text-linear', url: '/statements' },
  { name: 'Debts', icon: 'solar:wallet-money-linear', url: '/debts' },
  { name: 'Goals', icon: 'solar:target-linear', url: '/goals' },
  { name: 'AI Analysis', icon: 'solar:magic-stick-3-linear', url: '/analysis' },
  { name: 'Profile', icon: 'solar:user-circle-linear', url: '/profile' },
];

function BrandLogo() {
  return (
    <Link to="/" className="flex items-center gap-2 px-4 py-4">
      <img src={logo} alt="FinanceApp logo" className="h-9 w-9" />
      <span className="text-xl font-semibold text-sidebar-foreground">FinanceApp</span>
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
      width={'270px'}
      showTrigger={false}
      mode={sidebarMode}
      className="fixed left-0 top-0 border border-border dark:border-border bg-sidebar dark:bg-sidebar z-10 h-screen"
    >
      <div className="px-6 flex items-center brand-logo overflow-hidden bg-white dark:bg-dark">
        <BrandLogo />
      </div>

      <SimpleBar className="h-[calc(100vh-76px)]">
        <div className="px-6">
          <AMMenu
            subHeading="MENU"
            ClassName="hide-menu leading-21 text-sidebar-foreground font-bold uppercase text-xs dark:text-sidebar-foreground"
          />
          {NAV_ITEMS.map((item) => {
            const isSelected =
              item.url === '/' ? pathname === '/' : pathname.startsWith(item.url);
            return (
              <div key={item.url} onClick={onClose}>
                <AMMenuItem
                  icon={<Icon icon={item.icon} height={21} width={21} />}
                  isSelected={isSelected}
                  link={item.url}
                  component={Link}
                  className="mt-0.5 text-sidebar-foreground dark:text-sidebar-foreground"
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
        <button className="flex items-center gap-2 rounded-full p-1 outline-none transition hover:bg-muted">
          <Avatar className="h-9 w-9">
            <AvatarFallback className="bg-lightprimary text-primary">{initials}</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <p className="text-sm font-semibold">{user?.username}</p>
          <p className="text-xs text-muted-foreground">{user?.email || '—'}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate('/profile')}>
          <Icon icon="solar:user-circle-linear" className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleLogout} className="text-error focus:text-error">
          <Icon icon="solar:logout-2-linear" className="mr-2 h-4 w-4" />
          Logout
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function FullLayout() {
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleMode = () => setTheme(theme === 'light' ? 'dark' : 'light');

  return (
    <div className="flex w-full min-h-screen">
      <div className="page-wrapper flex w-full">
        <div className="xl:block hidden">
          <SidebarContent />
        </div>

        <div className="body-wrapper w-full bg-white dark:bg-dark">
          {/* Top Header */}
          <header className="sticky top-0 z-20 border-b border-border bg-white dark:bg-dark px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="icon"
                className="xl:hidden"
                onClick={() => setMobileOpen(true)}
              >
                <Icon icon="solar:hamburger-menu-linear" height={20} width={20} />
              </Button>
              <h1 className="text-xl font-semibold text-foreground">FinanceApp</h1>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" onClick={toggleMode} aria-label="Toggle theme">
                <Icon
                  icon={theme === 'dark' ? 'solar:sun-linear' : 'solar:moon-linear'}
                  height={20}
                  width={20}
                />
              </Button>
              <ProfileMenu />
            </div>
          </header>

          {/* Mobile drawer */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetContent side="left" className="p-0 w-[270px]">
              <SheetTitle>
                <VisuallyHidden>Navigation</VisuallyHidden>
              </SheetTitle>
              <SidebarContent onClose={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>

          {/* Body Content */}
          <div className="container mx-auto px-6 py-8">
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