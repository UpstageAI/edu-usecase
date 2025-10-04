import { RouteGraphData, RouteNode, RouteEdge, EnrichedEdge, StopNodeData } from '../types/route.types';

export async function loadRouteData(): Promise<RouteGraphData> {
  const response = await fetch('/reactflow_graph.json');
  if (!response.ok) {
    throw new Error(`Failed to fetch route data: ${response.status}`);
  }
  const data = await response.json();
  return data;
}

export function calculateCurrentPassengers(
  nodes: RouteNode[],
  edges: RouteEdge[]
): EnrichedEdge[] {
  const enrichedEdges: EnrichedEdge[] = [];

  // 노선별로 그룹화
  const routeGroups = new Map<string, RouteNode[]>();

  nodes.forEach((node) => {
    if (node.parentNode) {
      const route = node.parentNode;
      if (!routeGroups.has(route)) {
        routeGroups.set(route, []);
      }
      routeGroups.get(route)!.push(node);
    }
  });

  // 각 노선별로 누적 탑승 인원 계산
  routeGroups.forEach((routeNodes, routeName) => {
    // 노드를 순서대로 정렬 (id의 마지막 숫자로)
    const sortedNodes = routeNodes.sort((a, b) => {
      const aNum = parseInt(a.id.split('::')[1] || '0');
      const bNum = parseInt(b.id.split('::')[1] || '0');
      return aNum - bNum;
    });

    let currentPassengers = 0;

    sortedNodes.forEach((node, index) => {
      const nodeData = node.data as StopNodeData;

      // 승차/하차에 따라 현재 탑승 인원 업데이트
      if (nodeData.action === '승차') {
        currentPassengers += nodeData.count;
      } else if (nodeData.action === '하차') {
        currentPassengers -= nodeData.count;
      }

      // 다음 정류장으로 가는 엣지 찾기
      if (index < sortedNodes.length - 1) {
        const nextNode = sortedNodes[index + 1];
        const edge = edges.find(
          (e) => e.source === node.id && e.target === nextNode.id
        );

        if (edge) {
          enrichedEdges.push({
            ...edge,
            currentPassengers,
            label: `${currentPassengers}명`,
          });
        }
      }
    });
  });

  return enrichedEdges;
}

export function validateNodeEdges(data: RouteGraphData): boolean {
  const nodeIds = new Set(data.nodes.map((n) => n.id));

  for (const edge of data.edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      console.error('Invalid edge:', edge);
      return false;
    }
  }

  return true;
}
