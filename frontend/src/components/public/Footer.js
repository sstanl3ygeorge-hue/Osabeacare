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
              <span className="font-heading font-semibold text-xl">Osabea Healthcare</span>
            </div>
            <p className="text-white/70 text-sm leading-relaxed mb-6">
              CQC-compliant care staffing for care homes and supported living services across the UK.
            </p>
            <div className="flex flex-col gap-3">
              <a href="tel:01634306000" className="flex items-center gap-3 text-white/70 hover:text-white transition-colors text-sm">
                <Phone className="h-4 w-4" />
                <span>01634 306 000</span>
              </a>
              <a href="mailto:info@osabea.care" className="flex items-center gap-3 text-white/70 hover:text-white transition-colors text-sm">
                <Mail className="h-4 w-4" />
                <span>info@osabea.care</span>
              </a>
              <div className="flex items-start gap-3 text-white/70 text-sm">
                <MapPin className="h-4 w-4 mt-0.5" />
                <span>Kent, UK</span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-heading font-semibold text-lg mb-6">For Care Homes</h4>
            <ul className="space-y-3">
              {[
                { href: '/contact', label: 'Request Staffing Support' },
                { href: '/services', label: 'Our Services' },
                { href: '/compliance', label: 'Compliance Standards' },
                { href: '/about', label: 'About Us' },
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
            <h4 className="font-heading font-semibold text-lg mb-6">Looking for Work?</h4>
            <ul className="space-y-3">
              {[
                { href: '/apply', label: 'Apply to Join Our Team' },
                { href: '/recruitment', label: 'Why Work With Us' },
                { href: '/worker/login', label: 'Applicant Portal' },
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
            © {new Date().getFullYear()} Osabea Healthcare Solutions. All rights reserved.
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
