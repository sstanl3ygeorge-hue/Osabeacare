import { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { InspectionModeProvider, useInspectionMode } from '../../context/InspectionModeContext';
import { InspectionBanner } from '../ui/inspection-banner';
import { Button } from '../ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import {
  LayoutDashboard, Users, GraduationCap,
  History, Settings, Menu, LogOut, ChevronDown, Bell, Search, UserPlus, ClipboardList, Building2, FileCheck, Shield, Heart, Eye, UserCheck, Calendar, UserCog, Upload
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/portal/dashboard', icon: LayoutDashboard },
  { name: 'Employees', href: '/portal/employees', icon: Users },
  { name: 'Recruitment', href: '/portal/recruitment', icon: UserCheck },
  { name: 'Bulk Import', href: '/portal/bulk-import', icon: Upload },
  { name: 'Service Users', href: '/portal/service-users', icon: Heart },
  // Templates hidden for Audit Mode - forms system hidden from UI
  // { name: 'Templates', href: '/portal/templates', icon: ClipboardList },
  { name: 'Compliance Centre', href: '/portal/compliance-centre', icon: Building2 },
  // Policy Assignments removed - consolidated into Compliance Centre
  { name: 'Training', href: '/portal/training', icon: GraduationCap },
  { name: 'DBS Register', href: '/portal/dbs-register', icon: Shield },
  { name: 'Scheduled Requests', href: '/portal/scheduled-requests', icon: Calendar },
  { name: 'Audit View', href: '/portal/audit', icon: History },
  { name: 'Admin Users', href: '/portal/admin-users', icon: UserCog },
  { name: 'Settings', href: '/portal/settings', icon: Settings },
];

export default function PortalLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout, isAuditor } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const filteredNavigation = isAuditor() 
    ? navigation.filter(item => ['Dashboard', 'Audit View'].includes(item.name))
    : navigation;

  const NavLinks = ({ onClick }) => (
    <nav className="flex-1 px-4 py-6 space-y-1">
      {filteredNavigation.map((item) => {
        const isActive = location.pathname === item.href || 
          (item.href === '/portal/employees' && location.pathname.startsWith('/portal/employees/')) ||
          (item.href === '/portal/recruitment' && location.pathname.startsWith('/portal/recruitment/')) ||
          (item.href === '/portal/service-users' && location.pathname.startsWith('/portal/service-users/'));
        return (
          <Link
            key={item.name}
            to={item.href}
            onClick={onClick}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
              isActive 
                ? 'bg-primary text-white' 
                : 'text-text-muted hover:bg-[#F8FAFA] hover:text-text-primary'
            }`}
            data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
          >
            <item.icon className="h-5 w-5" />
            {item.name}
          </Link>
        );
      })}
    </nav>
  );

  // Inner component that uses inspection mode context
  const PortalContent = () => {
    const { isInspectionMode, enableInspectionMode } = useInspectionMode();
    
    return (
    <div className="min-h-screen bg-[#F8FAFA]">
      {/* Inspection Banner - shows when in inspection mode */}
      <InspectionBanner />
      
      {/* Desktop Sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col sidebar">
        <div className="flex flex-col flex-grow bg-white border-r border-[#E4E8EB]">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 py-5 border-b border-[#E4E8EB]">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
              <span className="text-white font-heading font-bold text-xl">O</span>
            </div>
            <div>
              <span className="font-heading font-semibold text-text-primary">Osabea Healthcare</span>
              <p className="text-xs text-text-muted">Compliance Portal</p>
            </div>
          </div>

          <NavLinks />

          {/* User Section */}
          <div className="p-4 border-t border-[#E4E8EB]">
            <div className="flex items-center gap-3 px-3 py-2">
              <Avatar className="h-9 w-9">
                <AvatarImage src={user?.picture} />
                <AvatarFallback className="bg-primary text-white text-sm">
                  {user?.name?.charAt(0) || 'U'}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{user?.name}</p>
                <p className="text-xs text-text-muted truncate capitalize">{user?.role?.replace('_', ' ')}</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden sticky top-0 z-40 bg-white border-b border-[#E4E8EB]">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" data-testid="mobile-sidebar-btn">
                  <Menu className="h-6 w-6" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64 p-0 bg-white">
                <div className="flex items-center gap-3 px-6 py-5 border-b border-[#E4E8EB]">
                  <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                    <span className="text-white font-heading font-bold text-xl">O</span>
                  </div>
                  <span className="font-heading font-semibold text-text-primary">Osabea Healthcare</span>
                </div>
                <NavLinks onClick={() => setSidebarOpen(false)} />
              </SheetContent>
            </Sheet>
            <span className="font-heading font-semibold text-text-primary">Portal</span>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon">
              <Bell className="h-5 w-5 text-text-muted" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.picture} />
                    <AvatarFallback className="bg-primary text-white text-xs">
                      {user?.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="lg:pl-64">
        {/* Desktop Header */}
        <header className="hidden lg:flex sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-[#E4E8EB] px-8 py-4 items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search employees, documents..."
                className="pl-10 pr-4 py-2 w-80 bg-[#F8FAFA] border border-[#E4E8EB] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                data-testid="portal-search"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Inspection Mode Toggle - only show when NOT in inspection mode */}
            {!isInspectionMode && (
              <Button 
                variant="outline" 
                className="rounded-xl border-primary/30 text-primary hover:bg-primary/10"
                onClick={enableInspectionMode}
                data-testid="enter-inspection-mode-btn"
              >
                <Eye className="mr-2 h-4 w-4" />
                Inspection Mode
              </Button>
            )}
            
            {!isAuditor() && (
              <Link to="/portal/employees">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="add-employee-btn">
                  <UserPlus className="mr-2 h-4 w-4" />
                  Add Employee
                </Button>
              </Link>
            )}
            
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5 text-text-muted" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full"></span>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.picture} />
                    <AvatarFallback className="bg-primary text-white text-sm">
                      {user?.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium text-text-primary">{user?.name}</span>
                  <ChevronDown className="h-4 w-4 text-text-muted" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-3 py-2 border-b border-[#E4E8EB]">
                  <p className="text-sm font-medium text-text-primary">{user?.name}</p>
                  <p className="text-xs text-text-muted">{user?.email}</p>
                </div>
                <DropdownMenuItem asChild>
                  <Link to="/portal/settings">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-error">
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-4 lg:p-8 main-content">
          <Outlet />
        </main>
      </div>
    </div>
    );
  };

  // Wrap everything in InspectionModeProvider
  return (
    <InspectionModeProvider>
      <PortalContent />
    </InspectionModeProvider>
  );
}
