import { Link } from 'react-router-dom';
import { Phone, Mail, MapPin } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-[#17324D] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          {/* Brand */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center">
                <span className="text-primary font-heading font-bold text-xl">O</span>
              </div>
              <span className="font-heading font-semibold text-xl">Osabea Care</span>
            </div>
            <p className="text-white/70 text-sm leading-relaxed mb-6">
              Recruiting compassionate care professionals with a safer, structured and people-first approach.
            </p>
            <div className="flex flex-col gap-3">
              <a href="tel:+441onal" className="flex items-center gap-3 text-white/70 hover:text-white transition-colors text-sm">
                <Phone className="h-4 w-4" />
                <span>0800 123 4567</span>
              </a>
              <a href="mailto:info@osabea.care" className="flex items-center gap-3 text-white/70 hover:text-white transition-colors text-sm">
                <Mail className="h-4 w-4" />
                <span>info@osabea.care</span>
              </a>
              <div className="flex items-start gap-3 text-white/70 text-sm">
                <MapPin className="h-4 w-4 mt-0.5" />
                <span>123 Care Street, London, UK</span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-heading font-semibold text-lg mb-6">Quick Links</h4>
            <ul className="space-y-3">
              {[
                { href: '/about', label: 'About Us' },
                { href: '/services', label: 'Our Services' },
                { href: '/recruitment', label: 'Join Our Team' },
                { href: '/compliance', label: 'Compliance' },
                { href: '/contact', label: 'Contact Us' },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    to={link.href}
                    className="text-white/70 hover:text-white transition-colors text-sm"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Services */}
          <div>
            <h4 className="font-heading font-semibold text-lg mb-6">Care Services</h4>
            <ul className="space-y-3">
              {[
                'Domiciliary Care',
                'Live-in Care',
                'Complex Care',
                'Mental Health Support',
                'Learning Disabilities',
              ].map((service) => (
                <li key={service}>
                  <span className="text-white/70 text-sm">{service}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* For Candidates */}
          <div>
            <h4 className="font-heading font-semibold text-lg mb-6">For Candidates</h4>
            <ul className="space-y-3">
              {[
                { href: '/apply', label: 'Apply Now' },
                { href: '/recruitment', label: 'Why Work With Us' },
                { href: '/compliance', label: 'Our Standards' },
                { href: '/login', label: 'Staff Portal Login' },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    to={link.href}
                    className="text-white/70 hover:text-white transition-colors text-sm"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <hr className="border-white/10 my-12" />

        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-white/50 text-sm">
            © {new Date().getFullYear()} Osabea Care Solutions. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <Link to="/privacy" className="text-white/50 hover:text-white/70 text-sm transition-colors">
              Privacy Policy
            </Link>
            <Link to="/terms" className="text-white/50 hover:text-white/70 text-sm transition-colors">
              Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
