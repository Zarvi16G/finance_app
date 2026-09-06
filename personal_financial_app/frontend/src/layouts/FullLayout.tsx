/**
 * Shared dashboard shell: paper sidebar navigation, header with
 * theme toggle and user dropdown, mobile drawer, and the outlet
 * where routed pages render.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Icon } from '@iconify/react';
import SimpleBar from 'simplebar-react';
import { AMSidebar, AMMenu, AMMenuItem } from 'tailwind-sidebar';
import 'tailwind-sidebar/styles.css';
import LanguageToggle from '../components/shared/LanguageToggle';
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
 *  is going, then the account.
 *
 *  Routes stay in Spanish even in English mode — a URL is an address, not
 *  copy, and switching language must not invalidate a bookmark. Only `key`
 *  decides the label. */
const NAV_ITEMS = [
  { key: 'dashboard', icon: 'solar:widget-2-linear', url: '/' },
  { key: 'movements', icon: 'solar:list-linear', url: '/movimientos' },
  { key: 'statements', icon: 'solar:document-text-linear', url: '/extractos' },
  { key: 'debts', icon: 'solar:wallet-money-linear', url: '/deudas' },
  { key: 'goals', icon: 'solar:target-linear', url: '/metas' },
  { key: 'experiences', icon: 'solar:map-point-wave-linear', url: '/experiencias' },
  { key: 'patrimony', icon: 'solar:safe-square-linear', url: '/patrimonio' },
  { key: 'wealthness', icon: 'solar:heart-pulse-linear', url: '/wealthness' },
  { key: 'analysis', icon: 'solar:magic-stick-3-linear', url: '/analisis' },
  { key: 'profile', icon: 'solar:user-circle-linear', url: '/perfil' },
];

function sectionKey(pathname: string): string {
  const match = NAV_ITEMS.slice(1).find((item) => pathname.startsWith(item.url));
  return match?.key ?? 'dashboard';
}

function BrandLogo() {
  const { t } = useTranslation();
  return (
    <Link to="/" className="block px-6 py-5" aria-label={t('brand')}>
      <span className="fig text-[21px] font-medium text-sidebar-foreground">{t('brand')}</span>
    </Link>
  );
}

function SidebarContent({ onClose }: { onClose?: () => void }) {
  const { t } = useTranslation();
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
            subHeading={t('nav.sectionHeading')}
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
                  <span className="truncate flex-1">{t(`nav.${item.key}`)}</span>
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
  const { t } = useTranslation();
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
          <p className="eyebrow-sm">{t('nav.session')}</p>
          <p className="mt-1 text-sm font-semibold">{user?.username}</p>
          <p className="text-xs text-muted-foreground">{user?.email || '—'}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate('/perfil')}>
          <Icon icon="solar:user-circle-linear" className="mr-2 h-4 w-4" />
          {t('nav.profile')}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleLogout} className="text-error focus:text-error">
          <Icon icon="solar:logout-2-linear" className="mr-2 h-4 w-4" />
          {t('nav.logout')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function FullLayout() {
  const { t } = useTranslation();
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
                aria-label={t('nav.openNav')}
              >
                <Icon icon="solar:hamburger-menu-linear" height={18} width={18} />
              </Button>
              <p className="letterhead">
                <span className="fig font-semibold text-foreground">{t('brand')}</span>
                <span className="mx-2 text-border">/</span>
                {t(`nav.${sectionKey(pathname)}`)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <LanguageToggle />
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleMode}
                aria-label={t('nav.toggleTheme')}
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
                <VisuallyHidden>{t('nav.navigation')}</VisuallyHidden>
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
