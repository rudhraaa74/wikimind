import React, { useState } from 'react';
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
    <div className="relative min-h-screen text-space-text font-sans selection:bg-space-accent/30">
      {/* Pure CSS Starfield Background */}
      <div className="starfield-container">
        <div className="starfield"></div>
        <div className="starfield-2"></div>
        <div className="starfield-overlay"></div>
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
