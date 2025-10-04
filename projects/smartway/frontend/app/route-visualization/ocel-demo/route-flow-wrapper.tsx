'use client';

import { ReactFlowProvider } from 'reactflow';
import { RouteFlow } from './route-flow';
import { RouteGraphData, EnrichedEdge } from '../types/route.types';

interface RouteFlowWrapperProps {
  routeData: RouteGraphData;
  enrichedEdges: EnrichedEdge[];
  highlightedEdge?: any;
}

export const RouteFlowWrapper: React.FC<RouteFlowWrapperProps> = ({ routeData, enrichedEdges, highlightedEdge }) => {
  return (
    <ReactFlowProvider>
      <RouteFlow routeData={routeData} enrichedEdges={enrichedEdges} highlightedEdge={highlightedEdge} />
    </ReactFlowProvider>
  );
};
