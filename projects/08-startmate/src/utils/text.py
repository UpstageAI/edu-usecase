from __future__ import annotations

def join_hits_for_ctx(docs: list[dict], budget_chars: int = 4000) -> str:
    parts: list[str] = []
    used = 0
    for i, d in enumerate(docs, start=1):
        t = d.get("text","").strip()
        if not t: continue
        piece = f"[#{i}] {t}\n"
        if used + len(piece) > budget_chars:
            break
        parts.append(piece)
        used += len(piece)
    return "".join(parts) if parts else "(no context)"
