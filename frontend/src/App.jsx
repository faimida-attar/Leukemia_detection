import React, { useState } from 'react';
import Navbar from './components/Navbar';
import ImageAnalysis from './pages/ImageAnalysis';
import Results from './pages/Results';
import ModelPerformance from './pages/ModelPerformance';

export default function App() {
  const [activeTab, setActiveTab] = useState('analysis');
  const [analysisData, setAnalysisData] = useState(null);

  const renderActivePage = () => {
    switch (activeTab) {
      case 'analysis':
        return (
          <ImageAnalysis
            setActiveTab={setActiveTab}
            setAnalysisData={setAnalysisData}
          />
        );
      case 'comparison':
        return (
          <ModelPerformance
            setActiveTab={setActiveTab}
            analysisData={analysisData}
          />
        );
      case 'results':
        return (
          <Results
            setActiveTab={setActiveTab}
            analysisData={analysisData}
          />
        );
      default:
        return (
          <ImageAnalysis
            setActiveTab={setActiveTab}
            setAnalysisData={setAnalysisData}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased selection:bg-sky-500 selection:text-white">
      {/* Top Header Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1">
        {renderActivePage()}
      </main>
    </div>
  );
}
