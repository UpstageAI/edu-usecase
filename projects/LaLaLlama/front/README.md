# Decision SaaS Frontend

내부용 의사결정 SaaS 프론트엔드 애플리케이션

## 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행 (Mock 모드)
npm run dev

# 개발 서버 실행 (API 모드)
# Windows (PowerShell)
$env:VITE_DATA_SOURCE="api"; npm run dev

# Linux/Mac
VITE_DATA_SOURCE=api npm run dev

# 빌드
npm run build
```

## 환경변수

- `VITE_DATA_SOURCE`: `mock` (기본값) 또는 `api`
  - `mock`: public/mock/*.json 파일에서 데이터 로드 (20초 로딩 연출)
  - `api`: 실제 API 서버 호출
  
`.env` 파일을 생성하여 환경변수를 설정할 수도 있습니다:
```
VITE_DATA_SOURCE=mock
```

## 라우트

- `/#/upload`: 파일 업로드 페이지 (기본 진입점)
- `/#/report/:proposalId`: 제안서 보고서 상세 페이지

## 기술 스택

- React 18
- Vite
- 순수 CSS (외부 UI 라이브러리 없음)

## 주요 기능

- **파일 업로드**: RFP, 심사표, 제안서 파일 선택 (v1은 실제 업로드 없음)
- **평가 리포트**: 제안서별 상세 평가 결과 확인
- **챗봇 Q&A**: 각 제안서에 대한 질문-응답 (Drawer UI)
- **20초 로딩 연출**: Mock 모드에서 모든 주요 화면이 20초 스켈레톤 표시
- **해시 라우팅**: `/#/upload`, `/#/report/:proposalId`

## 디렉토리 구조

```
front/
├── public/
│   └── mock/                      # Mock JSON 데이터
│       ├── evaluation.create.json
│       ├── report-p-abc.json
│       ├── report-p-def.json
│       ├── report-p-ghi.json
│       ├── chat.send-p-abc.json
│       ├── chat.send-p-def.json
│       └── chat.send-p-ghi.json
├── src/
│   ├── components/                # 재사용 컴포넌트
│   │   ├── Accordion.jsx
│   │   ├── Banner.jsx
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── ChatDrawer.jsx
│   │   ├── Chip.jsx
│   │   ├── Drawer.jsx
│   │   ├── MultiFileUpload.jsx
│   │   ├── ProgressBar.jsx
│   │   ├── SingleFileUpload.jsx
│   │   └── Skeleton.jsx
│   ├── lib/
│   │   └── api.js                 # API/Mock 데이터 레이어
│   ├── pages/
│   │   ├── UploadPage.jsx
│   │   └── ReportPage.jsx
│   ├── App.jsx                    # 메인 앱
│   ├── main.jsx                   # 진입점
│   ├── router.js                  # 해시 라우터
│   ├── state.js                   # 전역 상태
│   └── index.css                  # 디자인 토큰 & 글로벌 스타일
├── index.html
├── package.json
└── vite.config.js
```

## 디자인 시스템

### 컬러 팔레트
- **배경**: `#FAFBFC` (연한 회색 배경)
- **패널**: `#FFFFFF` (카드/패널)
- **브랜드**: `#4F46E5` (인디고 블루)
- **상태색**: Info(`#2563EB`), Success(`#059669`), Danger(`#DC2626`)

### 타이포그래피
- **H1**: 22px / 30px, Semibold
- **H2**: 18px / 26px, Semibold
- **Body**: 14px / 22px
- **Caption**: 12px / 18px

### 레이아웃
- 최대 너비: 1280px
- 섹션 간격: 32px
- 카드 패딩: 24px
- 카드 라운드: 14px

## Mock 데이터 명세

모든 Mock JSON 파일은 `public/mock/` 디렉토리에 위치하며, 명명 규칙을 따릅니다:

- **평가 생성**: `evaluation.create.json` → batchId 반환
- **보고서 조회**: `report-{proposalId}.json` → 제안서별 평가 결과
- **챗 전송**: `chat.send-{proposalId}.json` → 챗봇 응답

## 채팅 기능

채팅 시스템은 질문 순서에 따라 다른 답변을 제공합니다:

1. **첫 번째 질문**: `chat.send-p-abc.json` 답변 사용
2. **두 번째 질문**: `chat.send-p-def.json` 답변 사용  
3. **세 번째 질문 이후**: `chat.send-p-ghi.json` 답변 사용
