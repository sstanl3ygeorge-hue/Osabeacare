import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Brain, Heart, Activity, Home, Clock, Moon, Smile, ArrowRight } from 'lucide-react';

const services = [
  {
    icon: Brain,
    title: 'Mental Health Support',
    description: 'Trained staff to support individuals with mental health conditions, providing compassionate and person-centred care in various settings.'
  },
  {
    icon: Heart,
    title: 'Learning Disabilities',
    description: 'Specialist support for individuals with learning disabilities, promoting independence and quality of life.'
  },
  {
    icon: Activity,
    title: 'Complex Care',
    description: 'Experienced professionals for individuals with complex medical or care needs, including clinical support requirements.'
  },
  {
    icon: Home,
    title: 'Supported Living',
    description: 'Staff to enable individuals to live as independently as possible in supported accommodation.'
  },
  {
    icon: Clock,
    title: 'Live-in Care',
    description: '24-hour care support in the client\'s own home, providing continuity and personalised attention.'
  },
  {
    icon: Smile,
    title: 'Hourly Care',
    description: 'Flexible domiciliary care visits to support daily living activities and personal care needs.'
  },
  {
    icon: Heart,
    title: 'Respite Care',
    description: 'Short-term care support to give family carers a well-deserved break while ensuring continuity of care.'
  },
  {
    icon: Moon,
    title: 'Waking & Overnight Care',
    description: 'Night-time support for those who need assistance during sleeping hours, including waking night and sleep-in options.'
  }
];

export default function ServicesPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero */}
      <section className="bg-white py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="font-heading text-4xl sm:text-5xl font-bold text-text-primary mb-6">
              Staffing and care support services
            </h1>
            <p className="text-lg text-text-muted leading-relaxed">
              We support providers and service users with dependable staffing solutions and a structured approach to recruitment and onboarding. Our care professionals are carefully selected, compliance-checked and ready to deliver quality care.
            </p>
          </div>
        </div>
      </section>

      {/* Services Grid */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {services.map((service, idx) => (
              <div key={idx} className="card-public" data-testid={`service-card-${idx}`}>
                <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mb-6">
                  <service.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{service.title}</h3>
                <p className="text-text-muted text-sm leading-relaxed">{service.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Quality Promise */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="relative">
              <img
                src="https://images.pexels.com/photos/6129442/pexels-photo-6129442.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Care team collaboration"
                className="rounded-3xl shadow-lg w-full object-cover aspect-[4/3]"
              />
            </div>
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Our Quality Promise
              </h2>
              <p className="text-lg text-text-muted mb-6">
                Every care professional we place has completed our structured onboarding process. This includes identity verification, right to work checks, DBS clearance, reference verification and mandatory training.
              </p>
              <p className="text-text-muted mb-8">
                We maintain detailed compliance records for each worker, making it easy for clients to have confidence in our staffing solutions and for auditors to verify our processes.
              </p>
              <Link to="/contact">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="request-staffing-btn">
                  Request staffing support
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 lg:py-28 bg-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-white mb-4">
            Looking for reliable care staffing?
          </h2>
          <p className="text-lg text-white/80 mb-8">
            Contact our team to discuss your staffing requirements. We'll work with you to find the right care professionals for your needs.
          </p>
          <Link to="/contact">
            <Button size="lg" className="bg-white text-secondary hover:bg-white/90 rounded-full px-8 h-14" data-testid="cta-contact-btn">
              Get in touch
            </Button>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
