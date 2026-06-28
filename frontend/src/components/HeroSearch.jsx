import React, { useState } from 'react';
import { Search, ArrowRight } from 'lucide-react';

const HeroSearch = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <div className="flex flex-col items-center justify-center pt-32 pb-12 px-4 text-center">
      <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold text-white uppercase tracking-tight leading-[1.1] mb-2">
        EXPLORE THE UNIVERSE<br />
        <span className="text-space-muted">THROUGH CONNECTED KNOWLEDGE</span>
      </h1>
      
      <p className="mt-6 text-lg text-space-muted max-w-2xl mx-auto">
        Ask anything about space and astronomy. WikiMind builds a live knowledge graph to answer your question.
      </p>

      <div className="w-full max-w-2xl mt-12 relative group">
        <div className="absolute -inset-0.5 bg-space-accent rounded-full blur opacity-30 group-focus-within:opacity-70 transition duration-500"></div>
        <form onSubmit={handleSubmit} className="relative flex items-center bg-space-800/80 backdrop-blur-sm border border-space-border rounded-full p-2 focus-within:border-space-accent transition-colors">
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
            className="bg-space-accent hover:bg-space-accent-hover text-white rounded-full p-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
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
