export interface StopNodeData {
  label: string;
  route: string;
  stopName: string;
  action: '승차' | '하차';
  count: number;
  departTime: string;
  busNo: string;
  category: string;
}

export interface GroupNodeData {
  label: string;
}

export interface RouteNode {
  id: string;
  type?: string;
  data: StopNodeData | GroupNodeData;
  position: {
    x: number;
    y: number;
  };
  parentNode?: string;
}

export interface RouteEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  data?: {
    action: string;
    count: number;
  };
  type?: string;
  animated?: boolean;
  markerEnd?: {
    type: string;
  };
}

export interface RouteGraphData {
  nodes: RouteNode[];
  edges: RouteEdge[];
}

export interface EnrichedEdge extends RouteEdge {
  currentPassengers: number;
}
