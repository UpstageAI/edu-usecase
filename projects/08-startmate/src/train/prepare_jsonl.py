# src/train/prepare_all.py
# 원본 (messages/response) 형식 JSONL 2개를 변환하여 새 경로에 저장

import json
from pathlib import Path

def convert_line(ex: dict) -> dict:
    system_msg = next((m["content"] for m in ex.get("messages", []) if m.get("role") == "system"), "")
    user_msg   = next((m["content"] for m in ex.get("messages", []) if m.get("role") == "user"), "")
    response   = ex.get("response", "")
    return {
        "instruction": f"{system_msg}\n\n{user_msg}".strip(),
        "output": response
    }

def convert_file(in_path: Path, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except Exception as e:
                print(f"[WARN] {in_path.name} invalid JSON: {e}")
                continue
            new_ex = convert_line(ex)
            fout.write(json.dumps(new_ex, ensure_ascii=False) + "\n")
    print(f"✅ {in_path.name} → {out_path}")

def main():
    base_in  = Path("/patent-llama/data/sft")
    base_out = Path("/patent-llama/data/sft_prepared")

    files = ["train_mixed.jsonl", "val.jsonl"]
    for f in files:
        in_path  = base_in / f
        out_path = base_out / f
        if in_path.exists():
            convert_file(in_path, out_path)
        else:
            print(f"⚠️ {in_path} not found")

if __name__ == "__main__":
    main()
