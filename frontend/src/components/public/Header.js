import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from '../ui/button';
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet';
import { Menu, X } from 'lucide-react';

const navLinks = [
  { href: '/', label: 'Home' },
  { href: '/services', label: 'Services' },
  { href: '/recruitment', label: 'Recruitment' },
  { href: '/compliance', label: 'Compliance' },
  { href: '/about', label: 'About' },
  { href: '/contact', label: 'Contact' },
];

export default function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-[#E4E8EB]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3" data-testid="header-logo">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
              <span className="text-white font-heading font-bold text-xl">O</span>
            </div>
            <span className="font-heading font-semibold text-xl text-text-primary hidden sm:block">
              Osabea Healthcare
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  location.pathname === link.href ? 'text-primary' : 'text-text-muted'
                }`}
                data-testid={`nav-${link.label.toLowerCase()}`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden lg:flex items-center gap-3">
            <Link to="/login">
              <Button 
                variant="ghost" 
                className="text-text-primary hover:bg-[#F8FAFA]"
                data-testid="staff-login-btn"
              >
                Staff Login
              </Button>
            </Link>
            <Link to="/apply">
              <Button 
                className="bg-primary hover:bg-primary-hover text-white rounded-full px-6"
                data-testid="apply-now-btn"
              >
                Apply Now
              </Button>
            </Link>
          </div>

          {/* Mobile Menu */}
          <div className="lg:hidden flex items-center gap-2">
            <Link to="/apply">
              <Button 
                size="sm" 
                className="bg-primary hover:bg-primary-hover text-white rounded-full"
                data-testid="mobile-apply-btn"
              >
                Apply
              </Button>
            </Link>
            <Sheet open={isOpen} onOpenChange={setIsOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" data-testid="mobile-menu-btn">
                  <Menu className="h-6 w-6" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-[300px] bg-white">
                <div className="flex flex-col gap-6 mt-8">
                  {navLinks.map((link) => (
                    <Link
                      key={link.href}
                      to={link.href}
                      onClick={() => setIsOpen(false)}
                      className={`text-lg font-medium transition-colors hover:text-primary ${
                        location.pathname === link.href ? 'text-primary' : 'text-text-primary'
                      }`}
                    >
                      {link.label}
                    </Link>
                  ))}
                  <hr className="border-[#E4E8EB]" />
                  <Link to="/login" onClick={() => setIsOpen(false)}>
                    <Button variant="outline" className="w-full rounded-xl">
                      Staff Login
                    </Button>
                  </Link>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  );
}
