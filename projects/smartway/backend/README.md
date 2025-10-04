# Smartway Analytics Backend

LangGraph 기반 버스 노선 분석 Agent with FastAPI

## Architecture

```
backend/
├── main.py                 # FastAPI entry point
├── config.py              # Configuration & LLM setup
├── requirements.txt       # Python dependencies
├── analytics/
│   ├── types/
│   │   └── state_types.py    # LangGraph State definition
│   ├── nodes/
│   │   ├── router.py         # Intent analysis (LLM-based)
│   │   ├── find_highlight.py # Find/Highlight path nodes
│   │   ├── analysis.py       # Analysis path nodes
│   │   └── fallback.py       # Fallback response
│   └── graph/
│       └── analytics_graph.py # LangGraph construction
└── api/
    └── routes/
        └── analytics.py      # FastAPI routes
```

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your API key
# UPSTAGE_API_KEY=your_actual_key
```

### 4. Run Server

```bash
python main.py
```

Server will start at `http://localhost:8000`

- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Usage

### API Example

```bash
# Test analytics endpoint
curl -X POST http://localhost:8000/api/analytics \
  -H "Content-Type: application/json" \
  -d '{"question": "가장 포화가 많은 노선은?"}'
```

### Response Format

**Find/Highlight Response:**
```json
{
  "intent_type": "find_highlight",
  "highlight_edge": {
    "id": "edge-id",
    "source": "source-node",
    "target": "target-node",
    "label": "노선명"
  },
  "analysis_result": "선택 이유 설명",
  "chart_data": null,
  "chart_type": null
}
```

**Analysis Response:**
```json
{
  "intent_type": "analysis",
  "highlight_edge": null,
  "chart_data": {
    "labels": ["노선1", "노선2", ...],
    "datasets": [...]
  },
  "analysis_result": "분석 결과 설명",
  "chart_type": "bar_chart"
}
```

## LangGraph Flow

```
START
  ↓
intent_analyzer (LLM-based)
  ↓
┌─────────────┬──────────────┐
↓             ↓              ↓
find_highlight  analysis   fallback
  ↓             ↓              ↓
get_graph_data get_bus_data  END
  ↓             ↓
select_edge   chart_type_selector
  ↓             ↓
 END        generate_analytic
                 ↓
                END
```

## Development

### Add New Node

1. Create node function in `analytics/nodes/`
2. Import in `analytics_graph.py`
3. Add to graph with `workflow.add_node()`
4. Connect with edges

### Modify Intent Classification

Edit system prompt in `analytics/nodes/router.py`:

```python
system_prompt = """
당신은 Intent Classifier입니다.
...
"""
```

## Troubleshooting

### Module Not Found Error

```bash
# Add backend to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
```

### API Key Error

Check `.env` file and ensure `UPSTAGE_API_KEY` is set correctly.

### Graph Build Error

Check all node imports in `analytics_graph.py` are correct.
