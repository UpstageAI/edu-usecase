// flow-spec.ts (TS/React에서 그대로 import해서 사용)
// 요청하신 단계들을 JSON으로 정규화하고, Mermaid 코드로 변환합니다.

type NodeShape = "rect" | "stadium" | "round" | "circle" | "rhombus";
type NodeType = "normal" | "split" | "decision" | "start" | "end";

type FlowNode = {
  id: string; // 머메이드 노드 아이디 (문자 시작 권장)
  label: string; // 표시 라벨
  desc?: string; // 보조 설명 (줄바꿈으로 합쳐 표시)
  type?: NodeType;
  shape?: NodeShape;
};

type FlowEdge = [string, string, string?]; // [from, to, optional label]

type FlowSpec = {
  nodes: FlowNode[];
  edges: FlowEdge[];
};

export const flowSpec: FlowSpec = {
  nodes: [
    { id: "n1", label: "Document Upload", desc: "PDF 파일 수신", type: "start", shape: "stadium" },
    { id: "n2", label: "Format Detection", desc: "문서 형식 분석", type: "normal" },
    {
      id: "n3",
      label: "Layout Analysis",
      desc: "페이지 레이아웃 감지",
      type: "decision",
      shape: "rhombus",
    },

    { id: "n4", label: "Single Page", desc: "1페이지 구성", type: "normal" },
    { id: "n5", label: "Dual Page Detected", desc: "2페이지 가로 구성 감지", type: "split" },

    { id: "n6", label: "Page Splitting ✂️", desc: "페이지 반으로 분할", type: "normal" },
    { id: "n7", label: "OCR Processing", desc: "텍스트 추출 실행", type: "normal" },
    { id: "n8", label: "Quality Check", desc: "정확도 검증", type: "normal" },
    { id: "n9", label: "Output Generation", desc: "최종 결과 생성", type: "end", shape: "round" },
  ],
  edges: [
    ["n1", "n2"],
    ["n2", "n3"],
    ["n3", "n4", "단일 페이지"],
    ["n3", "n5", "가로 2면"],
    ["n4", "n7"],
    ["n5", "n6"],
    ["n6", "n7"],
    ["n7", "n8"],
    ["n8", "n9"],
  ],
};

export function toMermaid(spec: FlowSpec, direction: "TD" | "LR" = "TD"): string {
  const lines: string[] = [];
  lines.push(`flowchart ${direction}`);

  const toLabel = (n: FlowNode) => {
    const text = n.desc ? `${n.label}<br/>${n.desc}` : n.label;
    switch (
      n.shape ??
      (n.type === "start" || n.type === "end"
        ? "round"
        : n.type === "decision"
          ? "rhombus"
          : "rect")
    ) {
      case "stadium":
        return `${n.id}([${text}])`;
      case "round":
        return `${n.id}(${text})`;
      case "circle":
        return `${n.id}((${text}))`;
      case "rhombus":
        return `${n.id}{${text}}`;
      default:
        return `${n.id}[${text}]`;
    }
  };

  // 노드 선언
  for (const n of spec.nodes) {
    lines.push(`  ${toLabel(n)}`);
  }

  // 엣지 선언
  for (const [from, to, lbl] of spec.edges) {
    lines.push(lbl ? `  ${from} -- ${lbl} --> ${to}` : `  ${from} --> ${to}`);
  }

  // 스타일 (다크/라이트 모두 적당히 보이도록 클래스 정의)
  lines.push(
    `  classDef start fill:#e3f2fd,stroke:#90caf9,stroke-width:1px;`,
    `  classDef terminal fill:#e8f5e9,stroke:#a5d6a7,stroke-width:1px;`,
    `  classDef decision fill:#fff3e0,stroke:#ffb74d,stroke-width:1px;`,
    `  classDef split fill:#fce4ec,stroke:#f48fb1,stroke-width:1px;`,
    `  classDef normal fill:#f5f5f5,stroke:#bdbdbd,stroke-width:1px;`,
  );

  // 타입별 클래스 매핑
  for (const n of spec.nodes) {
    const cls =
      n.type === "start"
        ? "start"
        : n.type === "end"
          ? "terminal"
          : n.type === "decision"
            ? "decision"
            : n.type === "split"
              ? "split"
              : "normal";
    lines.push(`  class ${n.id} ${cls};`);
  }

  return lines.join("\n");
}

// Mermaid 문자열 생성 (예: LR로 가로 배치하고 싶으면 toMermaid(flowSpec, "LR"))
export const mermaidCode = toMermaid(flowSpec, "TD");
