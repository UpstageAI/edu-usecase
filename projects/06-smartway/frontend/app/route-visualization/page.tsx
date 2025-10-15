'use client';

import { useEffect, useState } from 'react';
import { RouteFlowWrapper } from './ocel-demo/route-flow-wrapper';
import { RightPanel } from './components/RightPanel';
import { loadRouteData, calculateCurrentPassengers } from './utils/dataTransform';
import { RouteGraphData, EnrichedEdge } from './types/route.types';

export default function RouteVisualizationPage() {
  const [routeData, setRouteData] = useState<RouteGraphData | null>(null);
  const [enrichedEdges, setEnrichedEdges] = useState<EnrichedEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [highlightedEdge, setHighlightedEdge] = useState<any>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await loadRouteData();
        const edges = calculateCurrentPassengers(data.nodes, data.edges);

        setRouteData(data);
        setEnrichedEdges(edges);
        setLoading(false);
      } catch (error) {
        console.error('Failed to load route data:', error);
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const handleHighlightEdge = (edge: any) => {
    console.log('Highlighting edge:', edge);
    setHighlightedEdge(edge);
  };

  if (loading) {
    return (
      <div style={{ width: '100vw', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a', color: 'white' }}>
        <div>Loading route data...</div>
      </div>
    );
  }

  if (!routeData) {
    return (
      <div style={{ width: '100vw', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a', color: 'white' }}>
        <div>Failed to load route data</div>
      </div>
    );
  }

  return (
    <main style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      <div style={{ flex: 1 }}>
        <RouteFlowWrapper
          routeData={routeData}
          enrichedEdges={enrichedEdges}
          highlightedEdge={highlightedEdge}
        />
      </div>
      <div style={{
        width: '400px',
        background: '#1e293b',
        borderLeft: '1px solid #334155'
      }}>
        <RightPanel onHighlightEdge={handleHighlightEdge} />
      </div>
    </main>
  );
}
