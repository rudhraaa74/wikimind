import React, { useState, useEffect } from 'react';
import { Search, ArrowRight } from 'lucide-react';

const HeroSearch = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleSetSearchQuery = (e) => {
      if (e.detail && typeof e.detail === 'string') {
        setQuery(e.detail);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    };
    window.addEventListener('setSearchQuery', handleSetSearchQuery);
    return () => window.removeEventListener('setSearchQuery', handleSetSearchQuery);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <div className="flex flex-col items-center justify-center pt-32 pb-12 px-4 text-center">
      <h1 
        className="text-4xl md:text-6xl lg:text-7xl font-extrabold text-white uppercase tracking-tight leading-[1.1] mb-2"
        style={{ textShadow: '0 0 40px rgba(0,0,0,0.8)' }}
      >
        EXPLORE THE UNIVERSE<br />
        <span className="text-space-muted">THROUGH CONNECTED KNOWLEDGE</span>
      </h1>
      
      <p className="mt-6 text-lg text-space-muted max-w-2xl mx-auto">
        Ask anything about space and astronomy. WikiMind builds a live knowledge graph to answer your question.
      </p>

      <div className="w-full max-w-2xl mt-12 relative group">
        <div className="absolute -inset-0.5 bg-white rounded-full blur opacity-10 group-focus-within:opacity-30 transition duration-500"></div>
        <form onSubmit={handleSubmit} className="relative flex items-center bg-[#1c1a2b]/90 backdrop-blur-md border border-[#2d2a45]/80 rounded-full p-2 focus-within:border-space-accent/50 focus-within:bg-[#1f1d33]/90 transition-colors duration-300">
          <div className="pl-4 pr-2 text-space-muted">
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            placeholder="How do supermassive black holes form?"
            className="flex-1 bg-transparent border-none outline-none text-white px-2 py-2 placeholder:text-space-muted/60"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="bg-white hover:bg-gray-200 text-black rounded-full p-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            ) : (
              <ArrowRight className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default HeroSearch;
