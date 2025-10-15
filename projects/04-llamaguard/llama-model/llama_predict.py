import os
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

def parse_args():
    p = argparse.ArgumentParser(description="코드 취약점 진단 LLAMA 추론")
    p.add_argument("--model", type=str, required=True, help="병합된 모델 경로 (예시: ./merged-vuln-detector)")
    p.add_argument("--code", type=str, help="직접 입력한 코드(선택)")
    p.add_argument("--code_file", type=str, help="추론할 함수 코드 파일 경로(선택)")
    p.add_argument("--max_new_tokens", type=int, default=512)
    p.add_argument("--dtype", type=str, default="fp16", choices=["fp32", "fp16", "bf16"])
    return p.parse_args()


def resolve_dtype(dtype_flag):
    if dtype_flag == "fp32":
        return torch.float32
    if dtype_flag in ["fp16", "auto"]:
        return torch.float16 if torch.cuda.is_available() else torch.float32
    if dtype_flag == "bf16":
        return torch.bfloat16 if torch.cuda.is_available() else torch.float32
    return torch.float32

def build_prompt(code):
    # 학습과 동일하게 보안 전문가 스타일 프롬프트 생성
    return (
        "Analyze the security vulnerabilities in the following code.\n"
        + code
        + "\n\nAnalysis:\n"
    )

def main():
    args = parse_args()
    dtype = resolve_dtype(args.dtype)

    # 모델/토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=dtype,
        device_map="auto"
    )
    model.eval()

    # 입력 코드 받기
    if args.code:
        test_code = args.code
        print("[직접 입력 코드 사용]")
    elif args.code_file and os.path.exists(args.code_file):
        with open(args.code_file, "r", encoding="utf-8") as f:
            test_code = f.read()
        print(f"[코드 파일 로드] {args.code_file}")
    else:
        # 예시 코드 (취약점 포함 예)
        test_code = (
            "def login(username, password):\n"
            "    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n"
            "    cursor.execute(query)\n"
            "    return cursor.fetchone()\n"
        )
        print("[기본 예시 코드 사용]")

    print("="*50)
    print(test_code)
    print("="*50)

    prompt = build_prompt(test_code)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    gen_cfg = GenerationConfig(
        max_new_tokens=args.max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    with torch.inference_mode():
        output = model.generate(**inputs, generation_config=gen_cfg)

    input_len = inputs.input_ids.shape[1]
    generated_ids = output[0, input_len:]
    result = tokenizer.decode(generated_ids, skip_special_tokens=True)

    print("[취약점 진단 결과]")
    print(result.strip())
    print("="*50)

if __name__ == "__main__":
    main()
