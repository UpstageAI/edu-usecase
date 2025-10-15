# src/graph/router_prompt.py
def build_router_prompt(query: str) -> str:
    return f"""
You are a router. Choose ONE tool for the user query.

Allowed tools: "retrieve", "web", "answer"
- retrieve: patent/tech RAG search needed
- web: open web search needed
- answer: you can answer directly without retrieval

Return STRICT JSON only (no code fences, no explanation):
{{"tool": "<retrieve|web|answer>", "confidence": <0..1>, "extra": {{}}}}

Query: {query}
"""
