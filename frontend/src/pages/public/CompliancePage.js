import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  BadgeCheck, FileCheck, GraduationCap, Shield, 
  ClipboardList, History, CheckCircle, ArrowRight
} from 'lucide-react';

const complianceAreas = [
  {
    icon: BadgeCheck,
    title: 'Recruitment Checks',
    description: 'Identity verification, right to work, employment history and gap analysis for every candidate.'
  },
  {
    icon: Shield,
    title: 'DBS & References',
    description: 'Enhanced DBS checks and thorough reference verification from previous employers.'
  },
  {
    icon: GraduationCap,
    title: 'Training & Induction',
    description: 'Mandatory training completion tracked and certificates stored before active work.'
  },
  {
    icon: FileCheck,
    title: 'Policy Acknowledgement',
    description: 'Key policies issued and acknowledged, with timestamps and versions recorded.'
  },
  {
    icon: ClipboardList,
    title: 'Document Management',
    description: 'All compliance documents stored digitally with expiry tracking and review status.'
  },
  {
    icon: History,
    title: 'Audit Trail',
    description: 'Complete audit log of all compliance actions, uploads and approvals.'
  }
];

const checklistItems = [
  'Application form and employment history',
  'Proof of identity and right to work',
  'References from recent employers',
  'Enhanced DBS certificate or update service',
  'Health declaration and screening',
  'Mandatory training certificates',
  'Induction completion and shadowing',
  'Policy acknowledgements',
  'Contract and handbook receipt'
];

export default function CompliancePage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero */}
      <section className="bg-white py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="font-heading text-4xl sm:text-5xl font-bold text-text-primary mb-6">
              Our approach to safer recruitment and compliance
            </h1>
            <p className="text-lg text-text-muted leading-relaxed">
              Quality care begins with safe recruitment, organised onboarding and visible standards. Our compliance approach is built to support accountability, documentation and readiness for review.
            </p>
          </div>
        </div>
      </section>

      {/* Compliance Areas */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              What our compliance process covers
            </h2>
            <p className="text-lg text-text-muted">
              A structured approach to ensure every care professional meets our standards.
            </p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {complianceAreas.map((area, idx) => (
              <div key={idx} className="card-public" data-testid={`compliance-card-${idx}`}>
                <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mb-6">
                  <area.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{area.title}</h3>
                <p className="text-text-muted">{area.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Compliance Checklist */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Every worker has a complete compliance file
              </h2>
              <p className="text-lg text-text-muted mb-8">
                Before any worker is placed, we ensure their compliance file is complete. This includes all required checks, documents and training records.
              </p>
              
              <div className="bg-[#F8FAFA] rounded-2xl p-6 border border-[#E4E8EB]">
                <h4 className="font-heading font-medium text-text-primary mb-4">Compliance checklist includes:</h4>
                <ul className="space-y-3">
                  {checklistItems.map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-success flex-shrink-0" />
                      <span className="text-text-primary text-sm">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute -top-4 -right-4 w-32 h-32 bg-accent rounded-full blur-2xl opacity-60"></div>
              <img
                src="https://images.pexels.com/photos/7511751/pexels-photo-7511751.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Organised compliance records"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-square"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Audit Ready */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-3xl border border-[#E4E8EB] p-8 lg:p-12">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <h2 className="font-heading text-3xl font-semibold text-text-primary mb-6">
                  Audit-ready at all times
                </h2>
                <p className="text-text-muted mb-6">
                  Our digital compliance system means we can demonstrate our recruitment and onboarding standards at any time. Whether it's a routine review or an external audit, our records are organised and accessible.
                </p>
                <ul className="space-y-3">
                  {[
                    'Complete digital employee files',
                    'Document approval and review status',
                    'Expiry date monitoring',
                    'Policy acknowledgement tracking',
                    'Full audit trail of all actions'
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <div className="w-6 h-6 bg-support-accent rounded-full flex items-center justify-center flex-shrink-0">
                        <CheckCircle className="h-4 w-4 text-success" />
                      </div>
                      <span className="text-text-primary">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="text-center lg:text-left">
                <p className="text-lg text-text-muted mb-6">
                  Want to learn more about our compliance approach or discuss your staffing needs?
                </p>
                <Link to="/contact">
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="contact-compliance-btn">
                    Speak to our team
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
