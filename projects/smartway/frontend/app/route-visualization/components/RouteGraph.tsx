'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';

import CustomNode from './CustomNode';
import RouteStartNode from './RouteStartNode';
import { RouteEdge } from './RouteEdge';
import { loadRouteData, calculateCurrentPassengers } from '../utils/dataTransform';
import { RouteNode, EnrichedEdge } from '../types/route.types';

const nodeTypes = {
  default: CustomNode,
  routeStart: RouteStartNode,
};

const edgeTypes = {
  routeEdge: RouteEdge,
};

const RouteGraph: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await loadRouteData();

        // 그룹 노드와 일반 노드 분리
        const stopNodes = data.nodes.filter((node: RouteNode) => node.type !== 'group');
        const groupNodes = data.nodes.filter((node: RouteNode) => node.type === 'group');

        // 노선명 매핑
        const routeNameMap = new Map<string, string>();
        groupNodes.forEach((node: RouteNode) => {
          routeNameMap.set(node.id, (node.data as any).label);
        });

        // 노선별 첫 번째 정류장 위치 계산
        const routeFirstStopPositions = new Map<string, { x: number; y: number }>();
        stopNodes.forEach((node: RouteNode) => {
          if (node.parentNode && !routeFirstStopPositions.has(node.parentNode)) {
            routeFirstStopPositions.set(node.parentNode, node.position);
          }
        });

        // 시작 노드 생성 (노선명만 표시)
        const startNodes: Node[] = Array.from(routeNameMap.entries()).map(([routeId, routeName]) => {
          const firstStopPos = routeFirstStopPositions.get(routeId) || { x: 0, y: 0 };
          return {
            id: `start-${routeId}`,
            type: 'routeStart',
            data: {
              routeName,
            },
            position: {
              x: firstStopPos.x,
              y: firstStopPos.y - 100, // 첫 번째 정류장 위에 배치
            },
          };
        });

        // 정류장 노드 변환
        const stopNodesTransformed: Node[] = stopNodes.map((node: RouteNode) => ({
          id: node.id,
          type: 'default',
          data: node.data,
          position: node.position,
        }));

        const transformedNodes = [...startNodes, ...stopNodesTransformed];

        // 시작 노드와 첫 번째 정류장 연결 엣지 생성
        const startEdges: Edge[] = Array.from(routeNameMap.keys()).map((routeId) => {
          // 해당 노선의 첫 번째 정류장 찾기
          const firstStop = stopNodes.find((node) => node.parentNode === routeId);
          if (!firstStop) return null;

          return {
            id: `edge-start-${routeId}`,
            source: `start-${routeId}`,
            target: firstStop.id,
            type: 'routeEdge',
            animated: false,
            data: {
              currentPassengers: 0,
              isStartEdge: true,
            },
          };
        }).filter(Boolean) as Edge[];

        // 엣지 변환 및 현재 탑승 인원 계산
        const enrichedEdges = calculateCurrentPassengers(data.nodes, data.edges);

        const transformedEdges: Edge[] = [
          ...startEdges,
          ...enrichedEdges.map((edge: EnrichedEdge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            type: 'routeEdge',
            animated: true,
            data: {
              currentPassengers: edge.currentPassengers,
              isStartEdge: false,
            },
          })),
        ];

        setNodes(transformedNodes);
        setEdges(transformedEdges);
        setLoading(false);
      } catch (error) {
        console.error('Failed to load route data:', error);
        setLoading(false);
      }
    }

    fetchData();
  }, [setNodes, setEdges]);

  if (loading) {
    return (
      <div style={{ width: '100vw', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading route data...</div>
      </div>
    );
  }

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        attributionPosition="bottom-right"
        style={{ background: '#0f172a' }}
      >
        <Controls />
        <MiniMap zoomable pannable nodeColor="#1e293b" />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} color="#334155" />
      </ReactFlow>
    </div>
  );
};

export default RouteGraph;
