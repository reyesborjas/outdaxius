// src/components/home/CTASection.jsx
import React from "react";
import { Link } from "react-router-dom";

export default function CTASection() {
  return (
    <div className="text-center text-white">
      <h3 className="display-6 fw-bold mb-2">Ready to grow your outdoor business?</h3>
      <p className="mb-4 opacity-75">Create itineraries, manage bookings and scale with confidence.</p>
      <div className="d-flex gap-2 justify-content-center">
        <Link to="/register" className="btn btn-light btn-lg">Start Free</Link>
        <Link to="/contact" className="btn btn-outline-light btn-lg">Schedule a Demo</Link>
      </div>
    </div>
  );
}
