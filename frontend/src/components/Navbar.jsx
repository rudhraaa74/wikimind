import React, { useState, useEffect } from 'react';
import { Telescope, Code } from 'lucide-react';

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${scrolled ? 'bg-space-900/80 backdrop-blur-md border-b border-space-border' : 'bg-transparent'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Telescope className="w-6 h-6 text-space-accent" />
          <span className="text-white font-bold tracking-[0.2em] text-lg mt-0.5">WIKIMIND</span>
        </div>
        <div>
          <a href="https://github.com/rudhraaa74/wikimind" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-space-muted hover:text-white transition-colors">
            <Code className="w-5 h-5" />
            <span className="font-medium text-sm hidden sm:inline-block">Source Code</span>
          </a>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
