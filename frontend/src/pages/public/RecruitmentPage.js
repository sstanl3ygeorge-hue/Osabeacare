import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  GraduationCap, Heart, Shield, Clock, Users, Award,
  FileCheck, BadgeCheck, CheckCircle, ArrowRight
} from 'lucide-react';

const benefits = [
  { icon: Shield, title: 'Structured onboarding', description: 'Clear guidance from application to active work' },
  { icon: GraduationCap, title: 'Training support', description: 'Mandatory training tracked and supported' },
  { icon: Clock, title: 'Flexible work', description: 'Various shift patterns and care settings' },
  { icon: Users, title: 'Supportive team', description: 'Responsive coordination and support' },
  { icon: Award, title: 'Professional growth', description: 'Development opportunities and progression' },
  { icon: Heart, title: 'Meaningful work', description: 'Make a real difference in people\'s lives' }
];

const documents = [
  'Proof of identity (passport, driving licence)',
  'Right to work evidence',
  'Employment references',
  'DBS information or certificate',
  'Employment history',
  'Health declaration',
  'Relevant training certificates'
];

export default function RecruitmentPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero */}
      <section className="bg-white py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="font-heading text-4xl sm:text-5xl font-bold text-text-primary mb-6">
                Join our care team
              </h1>
              <p className="text-lg text-text-muted leading-relaxed mb-6">
                We welcome compassionate professionals who want to work to a high standard and complete a structured onboarding process.
              </p>
              <p className="text-text-muted mb-8">
                Our recruitment and onboarding process is designed to support you from application through to active work, with clear guidance, training expectations and ongoing support.
              </p>
              <Link to="/apply">
                <Button size="lg" className="bg-primary hover:bg-primary-hover text-white rounded-full px-8 h-14" data-testid="apply-btn">
                  Start your application
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </div>
            <div className="relative">
              <img
                src="https://images.pexels.com/photos/6129442/pexels-photo-6129442.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Care team"
                className="rounded-3xl shadow-lg w-full object-cover aspect-[4/3]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Why Work With Us */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Why work with us
            </h2>
            <p className="text-lg text-text-muted">
              Join a team that values compassion, professionalism and high standards.
            </p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {benefits.map((benefit, idx) => (
              <div key={idx} className="card-public" data-testid={`benefit-card-${idx}`}>
                <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mb-6">
                  <benefit.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{benefit.title}</h3>
                <p className="text-text-muted">{benefit.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What to Expect */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                What to expect from recruitment
              </h2>
              <p className="text-text-muted mb-8">
                Our process is designed to be clear and thorough. We'll guide you through each step, from initial application to your first placement.
              </p>
              
              <div className="space-y-4">
                {[
                  { step: '1', title: 'Apply online', desc: 'Complete our application form with your details and experience' },
                  { step: '2', title: 'Document submission', desc: 'Upload required documents and references' },
                  { step: '3', title: 'Interview', desc: 'Meet with our team to discuss your experience and goals' },
                  { step: '4', title: 'Compliance checks', desc: 'DBS, right to work and reference verification' },
                  { step: '5', title: 'Training & induction', desc: 'Complete mandatory training and induction' },
                  { step: '6', title: 'Ready to work', desc: 'Once approved, you\'re ready for placement' }
                ].map((item, idx) => (
                  <div key={idx} className="flex gap-4">
                    <div className="w-10 h-10 bg-primary text-white rounded-xl flex items-center justify-center flex-shrink-0 font-heading font-semibold">
                      {item.step}
                    </div>
                    <div>
                      <h4 className="font-heading font-medium text-text-primary">{item.title}</h4>
                      <p className="text-sm text-text-muted">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Documents you may need
              </h2>
              <p className="text-text-muted mb-8">
                To complete our compliance process, you'll need to provide some or all of the following:
              </p>
              
              <div className="bg-[#F8FAFA] rounded-2xl p-6 border border-[#E4E8EB]">
                <ul className="space-y-3">
                  {documents.map((doc, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-success flex-shrink-0" />
                      <span className="text-text-primary">{doc}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <p className="text-sm text-text-muted mt-4">
                Don't worry if you don't have everything ready. We'll guide you through what's needed.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 lg:py-28 bg-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-white mb-4">
            Ready to make a difference?
          </h2>
          <p className="text-lg text-white/80 mb-8">
            Start your application today and join our team of dedicated care professionals.
          </p>
          <Link to="/apply">
            <Button size="lg" className="bg-white text-secondary hover:bg-white/90 rounded-full px-8 h-14" data-testid="cta-apply-btn">
              Apply Now
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
