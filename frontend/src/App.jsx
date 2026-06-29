import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Navbar from './components/Navbar';
import HeroSearch from './components/HeroSearch';
import SuggestedQueries from './components/SuggestedQueries';
import ResultsSection from './components/ResultsSection';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

function App() {
  const [hasQueried, setHasQueried] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleQuery = async (queryText) => {
    setHasQueried(true);
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${BACKEND_URL}/query`, {
        query: queryText
      });
      
      setResult(response.data);
    } catch (err) {
      console.error("API Error:", err);
      setError("Something went wrong exploring the universe. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen text-space-text font-sans selection:bg-space-accent/30 overflow-x-hidden">
      {/* Pure CSS Starfield Background */}
      <div className="starfield-container">
        <div className="starfield"></div>
        <div className="starfield-2"></div>
        <div className="starfield-overlay"></div>
      </div>

      {/* Decorative Parallax Moon */}
      <div 
        className="fixed z-0 pointer-events-none"
        style={{ 
          bottom: '10%',
          right: '-15%',
          transform: `translateY(${-scrollY * 0.3}px)`,
          width: '750px',
          height: '750px',
          maskImage: 'radial-gradient(circle at center, black 40%, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(circle at center, black 40%, transparent 70%)'
        }}
      >
        <img 
          src="/moon.jpg" 
          alt="Moon background" 
          className="w-full h-full object-cover opacity-100 mix-blend-screen"
        />
      </div>

      <Navbar />

      <main className="relative z-10">
        <HeroSearch onSubmit={handleQuery} isLoading={isLoading} />
        
        {/* Only show suggested queries if we haven't queried yet */}
        {!hasQueried && (
          <SuggestedQueries onSelect={handleQuery} isLoading={isLoading} />
        )}

        {/* Results section fades in once a query has been made */}
        {hasQueried && (
          <ResultsSection loading={isLoading} result={result} error={error} />
        )}
      </main>
    </div>
  );
}

export default App;
