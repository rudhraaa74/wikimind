import React, { useState, useEffect } from 'react';

const SkeletonLoader = () => {
  const [messageIndex, setMessageIndex] = useState(0);
  const messages = [
    "Searching Wikipedia...",
    "Building knowledge graph...",
    "Retrieving context...",
    "Generating answer..."
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [messages.length]);

  return (
    <div className="flex flex-col gap-8 w-full animate-pulse">
      {/* Answer Skeleton */}
      <div className="w-full bg-space-800 border border-space-border rounded-lg p-6 flex flex-col gap-4">
        <div className="h-4 bg-space-border rounded w-1/4 mb-4"></div>
        <div className="h-4 bg-space-border rounded w-full"></div>
        <div className="h-4 bg-space-border rounded w-5/6"></div>
        <div className="h-4 bg-space-border rounded w-full"></div>
        <div className="h-4 bg-space-border rounded w-4/5"></div>
        <div className="h-4 bg-space-border rounded w-full"></div>
        <div className="mt-8 h-4 bg-space-border rounded w-1/3"></div>
      </div>
      
      {/* Graph Skeleton */}
      <div className="w-full bg-space-800 border border-space-border rounded-lg p-6 flex flex-col items-center justify-center min-h-[520px]">
        <div className="w-16 h-16 border-4 border-space-accent border-t-transparent rounded-full animate-spin mb-6"></div>
        <p className="text-space-accent font-medium tracking-wide">
          {messages[messageIndex]}
        </p>
      </div>
    </div>
  );
};

export default SkeletonLoader;
