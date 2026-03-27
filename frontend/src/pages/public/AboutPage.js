import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Heart, Shield, Users, Award, Target, HandHeart, ArrowRight } from 'lucide-react';

const values = [
  { icon: Heart, title: 'Compassion', description: 'We put people at the heart of everything we do.' },
  { icon: Shield, title: 'Accountability', description: 'Clear records, transparent processes, reliable service.' },
  { icon: Users, title: 'Professionalism', description: 'High standards in recruitment and delivery.' },
  { icon: Award, title: 'Dignity', description: 'Respect for workers and those receiving care.' },
  { icon: Target, title: 'Safety', description: 'Structured compliance and safer recruitment.' },
  { icon: HandHeart, title: 'Reliability', description: 'Dependable staffing you can count on.' }
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero */}
      <section className="bg-white py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="font-heading text-4xl sm:text-5xl font-bold text-text-primary mb-6">
              About Osabea Care Solutions
            </h1>
            <p className="text-lg text-text-muted leading-relaxed">
              Osabea Care Solutions is committed to compassionate care, safer recruitment and organised workforce compliance. We support care delivery with a people-first approach backed by structured processes, clear documentation and professional standards.
            </p>
          </div>
        </div>
      </section>

      {/* Our Values */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Our Values
            </h2>
            <p className="text-lg text-text-muted">
              These principles guide how we work with candidates, clients and the communities we serve.
            </p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {values.map((value, idx) => (
              <div key={idx} className="card-public" data-testid={`value-card-${idx}`}>
                <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mb-6">
                  <value.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{value.title}</h3>
                <p className="text-text-muted">{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Our Approach */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Our Approach to Safer Recruitment
              </h2>
              <p className="text-lg text-text-muted mb-6">
                We believe quality care starts with quality recruitment. Our structured onboarding process ensures every care professional joining our team is thoroughly vetted, properly trained and ready to deliver excellent care.
              </p>
              <p className="text-text-muted mb-8">
                From initial application through to active placement, we maintain detailed compliance records, track training completion and ensure all regulatory requirements are met. This gives our clients confidence and our workers clear guidance.
              </p>
              <Link to="/compliance">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="learn-compliance-btn">
                  Learn about our compliance
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            <div className="relative">
              <img
                src="https://images.pexels.com/photos/6129589/pexels-photo-6129589.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Healthcare professionals discussing"
                className="rounded-3xl shadow-lg w-full object-cover aspect-[4/3]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 lg:py-28 bg-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-white mb-4">
            Ready to work with us?
          </h2>
          <p className="text-lg text-white/80 mb-8">
            Whether you need staffing support or want to join our team of care professionals, we'd love to hear from you.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/contact">
              <Button size="lg" className="bg-white text-secondary hover:bg-white/90 rounded-full px-8 h-14">
                Contact Us
              </Button>
            </Link>
            <Link to="/apply">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 rounded-full px-8 h-14">
                Apply Now
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
