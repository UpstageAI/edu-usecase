import torch
from datasets import load_dataset

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)
from peft import PeftModel
from trl import DPOTrainer, DPOConfig
import os

# ==============================================================================
# 0. QA 테스트를 위한 헬퍼 함수 정의
# ==============================================================================
def run_qa_test(model, tokenizer, question, context):
    """주어진 모델과 토크나이저로 QA 테스트를 실행하고 답변을 반환합니다."""
    
    # Llama-3의 프롬프트 형식에 맞게 테스트 입력을 구성합니다.
    prompt = (
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"심사 기준표에 맞춰 평가 코멘트를 작성하시오.\n[RFP 요구사항]\n{question}\n\n[제안서 내용]\n{context}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    # 토큰화 및 추론
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=256,
        temperature=0.1,
        do_sample=False,
        eos_token_id=tokenizer.eos_token_id
    )
    
    # 생성된 텍스트에서 답변 부분만 깔끔하게 추출
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    answer = generated_text.split('<|start_header_id|>assistant<|end_header_id|>')[-1].strip()
    
    return answer

# ==============================================================================
# 1. 환경 설정 및 경로 지정
# ==============================================================================
os.environ["CUDA_VISIBLE_DEVICES"] = "0" 
base_model_path = "NakJun/Llama-3.2-1B-Instruct-ko-QuAD"
sft_adapter_path = "./rfp-eval-lora-adapter"
output_dir = "./final-dpo-adapter"

# ==============================================================================
# 2. 토크나이저 로드 및 설정
# ==============================================================================
tokenizer = AutoTokenizer.from_pretrained(base_model_path)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
# tokenizer.padding_side = "left"

# ==============================================================================
# [Phase 1] DPO 학습 전 SFT 모델 성능 테스트
# ==============================================================================
print("="*60)
print("Phase 1: DPO 학습 전 SFT 모델 성능 테스트 시작")
print("="*60)

# SFT Phase 3와 완전히 동일한 방식으로 로드
base_model_for_test = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    dtype=torch.bfloat16,
    device_map="auto",
)

# SFT 어댑터 로드 및 병합 (SFT Phase 3와 동일)
sft_model = PeftModel.from_pretrained(base_model_for_test, sft_adapter_path)
sft_merged_model = sft_model.merge_and_unload()

test_question = "시스템은 최신 MSA(Microservice Architecture) 구조를 채택하여 서비스 간 독립성과 확장성을 보장해야 합니다."
test_context = "본 시스템은 모놀리식(Monolithic) 아키텍처를 기반으로 설계되었습니다. 이는 초기 개발 속도가 빠르다는 장점이 있으나, 향후 서비스 단위의 독립적인 배포 및 확장은 제한될 수 있습니다. 대신, 모듈화를 통해 결합도를 낮추는 전략을 사용합니다."

# 테스트 실행
before_dpo_answer = run_qa_test(sft_merged_model, tokenizer, test_question, test_context)

print(f"\n[Test Question]\nRFP 요구사항: {test_question}")
print(f"\n[Test Context]\n제안서 내용: {test_context}")
print("\n--------------------[Before DPO Training]--------------------")
print(f"SFT 모델의 답변:\n{before_dpo_answer}")
print("="*60)

# VRAM 확보
del base_model_for_test
del sft_model
del sft_merged_model
torch.cuda.empty_cache()

# ==============================================================================
# [Phase 2] DPO 학습 진행
# ==============================================================================
print("\n" + "="*60)
print("Phase 2: DPO 학습 시작")
print("="*60)

# DPO 학습을 위한 베이스 모델 및 SFT 어댑터 로드
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    dtype=torch.bfloat16,
    device_map="auto",
)
base_model.config.use_cache = False
base_model.config.pad_token_id = tokenizer.pad_token_id

# SFT 어댑터를 베이스 모델 위에 로드
model = PeftModel.from_pretrained(base_model, sft_adapter_path)

# DPO용 Preference 데이터셋 로드
try:
    train_dataset = load_dataset("json", data_files="preference_dataset.jsonl", split="train")
except FileNotFoundError:
    print("="*60)
    print("ERROR: 'preference_dataset.jsonl' 파일을 찾을 수 없습니다.")
    print("DPO 학습용 데이터셋을 스크립트와 동일한 폴더에 저장해주세요.")
    print("="*60)
    exit()

# DPO 학습 설정
training_args = DPOConfig(
    output_dir="./dpo_training_results",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=1,
    learning_rate=1e-5,
    bf16=True,
    logging_steps=10,
    save_strategy="epoch",
    report_to="tensorboard",
    beta=0.1,
    max_prompt_length=512,
    max_length=1024,
    padding_value=tokenizer.pad_token_id,
)

# DPOTrainer 설정 및 학습
dpo_trainer = DPOTrainer(
    model,
    args=training_args,
    train_dataset=train_dataset,
)

print(f"Pad token ID: {tokenizer.pad_token_id}")
print("DPO 학습을 시작합니다...")
print("="*60)

dpo_trainer.train()

# 최종 DPO 어댑터 저장
dpo_trainer.model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"\nDPO 어댑터가 '{output_dir}'에 저장되었습니다.")

# ==============================================================================
# [Phase 3] DPO 학습 후 모델 성능 테스트
# ==============================================================================
print("\n" + "="*60)
print("Phase 3: DPO 학습 후 모델 성능 테스트 시작")
print("="*60)
print("학습된 DPO 어댑터를 베이스 모델에 병합하고 새로 로드합니다...")

# VRAM 확보
del model
del dpo_trainer
torch.cuda.empty_cache()

# 1. 베이스 모델을 BFloat16 타입으로 새로 로드
base_model_final = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    dtype=torch.bfloat16,
    device_map="auto",
)

# 2. 먼저 SFT 어댑터 로드
sft_model_final = PeftModel.from_pretrained(base_model_final, sft_adapter_path)

# 3. SFT 어댑터 위에 DPO 어댑터 로드
dpo_model_final = PeftModel.from_pretrained(sft_model_final, output_dir)

# 4. 모든 어댑터를 병합
final_merged_model = dpo_model_final.merge_and_unload()
print("모델 병합 완료!")

# 5. 병합된 모델로 QA 테스트 실행
after_dpo_answer = run_qa_test(final_merged_model, tokenizer, test_question, test_context)

print(f"\n[Test Question]\nRFP 요구사항: {test_question}")
print(f"\n[Test Context]\n제안서 내용: {test_context}")
print("\n--------------------[After DPO Training]---------------------")
print(f"DPO 학습 후 모델의 답변:\n{after_dpo_answer}")
print("\n--------------------[Before DPO (for comparison)]---------------------")
print(f"SFT 모델의 답변:\n{before_dpo_answer}")
print("="*60)
print("\nDPO 학습이 완료되었습니다!")
print(f"최종 DPO 어댑터가 '{output_dir}'에 저장되었습니다.")
print("="*60)