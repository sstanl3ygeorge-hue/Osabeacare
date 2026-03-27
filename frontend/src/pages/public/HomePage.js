import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  BadgeCheck, GraduationCap, FileCheck, HeartHandshake, 
  UserPlus, ShieldCheck, ClipboardList, BriefcaseMedical,
  ArrowRight, CheckCircle
} from 'lucide-react';

const whyChooseUs = [
  {
    icon: BadgeCheck,
    title: 'Safer recruitment',
    description: 'Identity, right-to-work, references and DBS requirements are tracked through a structured process.'
  },
  {
    icon: GraduationCap,
    title: 'Training-led onboarding',
    description: 'Mandatory training, induction and readiness checks are recorded before active placement.'
  },
  {
    icon: FileCheck,
    title: 'Clear compliance records',
    description: 'Every employee has a digital file with organised documents, policy acknowledgements and review status.'
  },
  {
    icon: HeartHandshake,
    title: 'People-first support',
    description: 'We care about quality, dignity and professionalism for workers, clients and the people receiving care.'
  }
];

const services = [
  'Mental Health Support',
  'Learning Disabilities',
  'Complex Care',
  'Supported Living',
  'Live-in Care',
  'Hourly Care',
  'Respite Care',
  'Waking & Overnight Care'
];

const recruitmentSteps = [
  { icon: UserPlus, title: 'Apply and screen', description: 'We review applications, experience and role suitability.' },
  { icon: BadgeCheck, title: 'Verify identity', description: 'Required identity and eligibility documents are collected and checked.' },
  { icon: ShieldCheck, title: 'DBS and references', description: 'Background checks and references are logged and reviewed.' },
  { icon: ClipboardList, title: 'Interview', description: 'Interviews, assessments and competency notes are captured clearly.' },
  { icon: GraduationCap, title: 'Training', description: 'Mandatory learning and onboarding steps are tracked before placement.' },
  { icon: FileCheck, title: 'Compliance approval', description: 'The compliance file is reviewed for completeness and readiness.' },
  { icon: BriefcaseMedical, title: 'Placement ready', description: 'Once approved, the worker is ready to be deployed safely.' }
];

const complianceChecklist = [
  'Digital employee compliance files',
  'Document approval and review statuses',
  'Policy acknowledgement tracking',
  'Training and expiry monitoring',
  'Read-only auditor visibility'
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div>
                <span className="inline-block px-4 py-2 bg-accent text-primary text-sm font-medium rounded-full mb-6">
                  Trusted care recruitment and staffing support
                </span>
                <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary tracking-tight leading-tight">
                  Safer recruitment. Better care. <span className="text-primary">Fully accountable</span> staffing.
                </h1>
              </div>
              <p className="text-lg text-text-muted leading-relaxed max-w-xl">
                Osabea Care Solutions connects care providers with compassionate, compliant and carefully screened professionals through a structured recruitment, onboarding and compliance process.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/apply">
                  <Button size="lg" className="bg-primary hover:bg-primary-hover text-white rounded-full px-8 h-14 text-base" data-testid="hero-apply-btn">
                    Apply Now
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Link to="/contact">
                  <Button size="lg" variant="outline" className="border-[#E4E8EB] hover:bg-[#F8FAFA] rounded-full px-8 h-14 text-base" data-testid="hero-contact-btn">
                    Speak to Our Team
                  </Button>
                </Link>
              </div>
              
              {/* Trust badges */}
              <div className="flex flex-wrap gap-4 pt-4">
                {['Structured onboarding', 'Compliance checks', 'Training tracked', 'Audit-ready'].map((badge) => (
                  <div key={badge} className="flex items-center gap-2 text-sm text-text-muted">
                    <CheckCircle className="h-4 w-4 text-success" />
                    <span>{badge}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute -top-8 -right-8 w-64 h-64 bg-accent rounded-full blur-3xl opacity-50"></div>
              <div className="absolute -bottom-8 -left-8 w-48 h-48 bg-support-accent rounded-full blur-3xl opacity-50"></div>
              <img
                src="https://images.pexels.com/photos/6129442/pexels-photo-6129442.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Care professionals working together"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-[4/3]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Why Choose Us */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Why providers and candidates choose Osabea
            </h2>
            <p className="text-lg text-text-muted">
              We combine people-first recruitment with a strong operational process, so every placement is supported by clear checks, organised records and accountable onboarding.
            </p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {whyChooseUs.map((item, idx) => (
              <div key={idx} className="card-public group" data-testid={`why-card-${idx}`}>
                <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mb-6 group-hover:bg-primary transition-colors">
                  <item.icon className="h-7 w-7 text-primary group-hover:text-white transition-colors" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{item.title}</h3>
                <p className="text-text-muted leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
                Care services and staffing support
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We support a range of care settings with dependable staffing and a recruitment process designed for quality, safety and continuity.
              </p>
              <Link to="/services">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="view-services-btn">
                  View all services
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            
            <div className="grid sm:grid-cols-2 gap-4">
              {services.map((service, idx) => (
                <div key={idx} className="bg-[#F8FAFA] rounded-2xl p-5 border border-[#E4E8EB] hover:border-primary/30 transition-colors">
                  <h3 className="font-heading font-medium text-text-primary">{service}</h3>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Recruitment Process */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Our recruitment and onboarding process
            </h2>
            <p className="text-lg text-text-muted">
              We follow a structured pathway so every candidate is reviewed, documented and prepared with the right checks and onboarding steps.
            </p>
          </div>
          
          <div className="relative">
            {/* Timeline line */}
            <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-[#E4E8EB] -translate-y-1/2"></div>
            
            <div className="grid sm:grid-cols-2 lg:grid-cols-7 gap-6 lg:gap-4">
              {recruitmentSteps.map((step, idx) => (
                <div key={idx} className="relative text-center group">
                  <div className="lg:absolute lg:left-1/2 lg:-translate-x-1/2 bg-white w-16 h-16 rounded-2xl border-2 border-[#E4E8EB] flex items-center justify-center mb-4 mx-auto group-hover:border-primary transition-colors">
                    <step.icon className="h-7 w-7 text-primary" />
                  </div>
                  <div className="lg:pt-24">
                    <h3 className="font-heading font-medium text-text-primary mb-2">{step.title}</h3>
                    <p className="text-sm text-text-muted">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Compliance Section */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Built around safe recruitment and audit-ready compliance
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We do not rely on disconnected folders or manual follow-up alone. Our process is designed to keep recruitment, onboarding, policies and employee records organised, visible and reviewable.
              </p>
              
              <ul className="space-y-4 mb-8">
                {complianceChecklist.map((item, idx) => (
                  <li key={idx} className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-support-accent rounded-full flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="h-4 w-4 text-success" />
                    </div>
                    <span className="text-text-primary">{item}</span>
                  </li>
                ))}
              </ul>
              
              <Link to="/contact">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="compliance-cta-btn">
                  Speak to our team
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            
            <div className="relative">
              <div className="absolute -top-4 -left-4 w-32 h-32 bg-support-accent rounded-full blur-2xl opacity-60"></div>
              <img
                src="https://images.pexels.com/photos/7511751/pexels-photo-7511751.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Modern office environment"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-square"
              />
            </div>
          </div>
        </div>
      </section>

      {/* CTA Band */}
      <section className="py-20 lg:py-28 bg-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-white mb-4">
            Need staffing support or looking to join our team?
          </h2>
          <p className="text-lg text-white/80 mb-8">
            Whether you need dependable care professionals or want to apply for care work, our team is here to help.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/contact">
              <Button size="lg" className="bg-white text-secondary hover:bg-white/90 rounded-full px-8 h-14" data-testid="cta-staffing-btn">
                Request Staffing Support
              </Button>
            </Link>
            <Link to="/apply">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 rounded-full px-8 h-14" data-testid="cta-apply-btn">
                Start Application
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
