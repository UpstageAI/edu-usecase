# Route Visualization Frontend

Next.js 기반 노선(버스 경로) 시각화 애플리케이션

## 기술 스택

- **Framework**: Next.js 15
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Graph Visualization**: React Flow 11
- **Runtime**: Node.js

## 프로젝트 구조

```
frontend/
├── app/
│   ├── route-visualization/
│   │   ├── components/
│   │   │   ├── CustomNode.tsx        # 정류장 노드 컴포넌트
│   │   │   ├── CustomGroupNode.tsx   # 노선 그룹 컴포넌트
│   │   │   └── RouteGraph.tsx        # React Flow 메인 컴포넌트
│   │   ├── utils/
│   │   │   ├── dataTransform.ts      # 데이터 변환 로직
│   │   │   └── styleConfig.ts        # 스타일 설정
│   │   ├── types/
│   │   │   └── route.types.ts        # TypeScript 타입 정의
│   │   └── page.tsx                  # 시각화 페이지
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx                      # 홈 페이지
├── public/
│   └── reactflow_graph.json          # 노선 데이터
└── package.json
```

## 설치 및 실행

### 1. 의존성 설치

```bash
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 http://localhost:3000 접속

### 3. 프로덕션 빌드

```bash
npm run build
npm start
```

## 주요 기능

### 1. 노선 시각화
- 7개 노선 (출근 4개, 퇴근 3개) 그래프 형태로 표시
- 48개 정류장 노드 시각화
- 노선별 그룹화 및 색상 구분

### 2. 정류장 노드
- 정류장명 및 순번 표시
- 승하차 정보 표시 (↑ +3명 / ↓ -2명)
- 출발 시간 표시
- 승차: 파란색, 하차: 빨간색 텍스트

### 3. 엣지 (연결선)
- 현재 탑승 인원 표시 (누적 계산)
- Animated 효과
- 화살표로 방향 표시

### 4. 인터랙티브 기능
- Zoom / Pan 컨트롤
- MiniMap 네비게이션
- Background grid
- Fit view (전체 화면에 맞춤)

## 데이터 구조

### Node Data
```typescript
{
  label: string;          // 순번 + 정류장명
  stopName: string;       // 정류장명
  action: '승차' | '하차';
  count: number;          // 승하차 인원
  departTime: string;     // 출발 시간
  busNo: string;          // 버스 번호
  category: string;       // 카테고리
}
```

### Edge Data
```typescript
{
  currentPassengers: number;  // 현재 탑승 인원 (계산됨)
  label: string;              // "{count}명"
}
```

## 스타일링

### 노드
- 배경색: 흰색
- Border: 회색 (#e5e7eb)
- Border radius: 8px
- Shadow: 가벼운 그림자 효과

### 그룹 노드
- 출근 노선: 연한 파란색 배경 (#e0f2fe)
- 퇴근 노선: 연한 주황색 배경 (#fed7aa)

### 엣지
- 색상: 회색 (#9ca3af)
- Width: 2px
- Animated: true

## 개발 가이드

### 새로운 노드 타입 추가

1. `types/route.types.ts`에 타입 정의 추가
2. `components/` 에 새로운 컴포넌트 생성
3. `RouteGraph.tsx`의 `nodeTypes`에 등록

### 데이터 변환 로직 수정

`utils/dataTransform.ts`의 `calculateCurrentPassengers` 함수 수정

### 스타일 커스터마이징

`utils/styleConfig.ts` 파일에서 색상 및 스타일 변경

## 트러블슈팅

### React Flow 스타일이 적용되지 않을 때
```tsx
import 'reactflow/dist/style.css';  // RouteGraph.tsx에 추가
```

### JSON 데이터를 찾을 수 없을 때
- `public/reactflow_graph.json` 파일 존재 확인
- 경로가 `/reactflow_graph.json`으로 시작하는지 확인

## 라이선스

MIT
