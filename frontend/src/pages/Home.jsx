// src/pages/Home.jsx
import React from "react";
import HeroCarousel from "../components/home/HeroCarousel";
import FeaturedCompanies from "../components/home/FeaturedCompanies";
import ActivitiesGrid from "../components/home/ActivitiesGrid";
import ProgramsGrid from "../components/home/ProgramsGrid";
import LocationsMap from "../components/LocationsMap";
import PlatformFeatures from "../components/home/PlatformFeatures";
import CTASection from "../components/home/CTASection";


export default function Home() {
  return (
    <div className="min-vh-100 d-flex flex-column bg-surface-snow">
      <main className="flex-grow-1">
        {/* Hero Section */}
        <section className="container-lg px-3 px-md-4 py-4">
          <HeroCarousel />
        </section>

        {/* Value Proposition */}
        <section className="container-lg px-3 px-md-4 py-4">
          <div className="text-center mb-5">
            <h2 className="fw-bold display-6 text-role-admin mb-3">
              Empowering Tourism Companies & Adventure Guides
            </h2>
            <p className="lead text-state-neutral fs-5 mx-auto" style={{maxWidth: '800px'}}>
              Manage itineraries, bookings, and client engagement in one powerful platform. 
              From small agencies to certified guides - scale your outdoor business with confidence.
            </p>
          </div>
        </section>

        {/* Platform Features */}
        <section className="bg-white py-5">
          <div className="container-lg px-3 px-md-4">
            <h3 className="h2 text-center mb-4 fw-bold">Everything You Need to Grow</h3>
            <PlatformFeatures />
          </div>
        </section>

        {/* Featured Companies & Guides */}
        <section className="container-lg px-3 px-md-4 py-5">
          <h3 className="h2 mb-4 fw-bold text-center">
            Trusted by Tourism Companies & Guides Worldwide
          </h3>
          <p className="text-center text-state-neutral mb-4">
            From small adventure companies to certified outdoor instructors
          </p>
          <FeaturedCompanies />
        </section>

        {/* Popular Activities */}
        <section className="bg-light py-5">
        <div className="container-lg px-3 px-md-4">
     <ActivitiesGrid asCarousel />
   </div>
 </section>

        {/* Featured Programs */}
         <section className="container-lg px-3 px-md-4 py-5">
         <ProgramsGrid asCarousel />
        </section>

        {/* Global Reach */}
        <section className="bg-white py-5">
          <div className="container-lg px-3 px-md-4">
            <h3 className="h2 mb-4 fw-bold text-center">Operating Across the Globe</h3>
            <p className="text-center text-state-neutral mb-4">
              Our platform connects travelers with local experts in dozens of destinations
            </p>
            <LocationsMap />
          </div>
        </section>

        {/* Call to Action */}
        <section className="bg-primary py-5">
          <div className="container-lg px-3 px-md-4">
            <CTASection />
          </div>
        </section>
      </main>

      {/* Enhanced Footer */}
      <footer className="border-top bg-surface-snow py-4">
        <div className="container-lg px-3 px-md-4">
          <div className="row">
            <div className="col-md-8">
              <div className="d-flex flex-wrap gap-4 mb-3">
                <a href="/about" className="text-decoration-none text-state-neutral">About</a>
                <a href="/features" className="text-decoration-none text-state-neutral">Features</a>
                <a href="/pricing" className="text-decoration-none text-state-neutral">Pricing</a>
                <a href="/support" className="text-decoration-none text-state-neutral">Support</a>
                <a href="/privacy" className="text-decoration-none text-state-neutral">Privacy</a>
              </div>
            </div>
            <div className="col-md-4 text-md-end">
              <p className="text-small text-state-neutral mb-0">
                © {new Date().getFullYear()} Outdaxius - Tourism Management Platform
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}