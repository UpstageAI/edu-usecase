import torch
from datasets import load_dataset

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig
)
from peft import PeftModel, LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import os

# ==============================================================================
# 0. QA 테스트를 위한 헬퍼 함수 정의
# ==============================================================================
def run_qa_test(model, tokenizer, question, context):
    """주어진 모델과 토크나이저로 QA 테스트를 실행하고 답변을 반환합니다."""
    
    # Llama-3의 프롬프트 형식에 맞게 테스트 입력 구성
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
# 1. 기본 설정 및 모델/토크나이저 로드
# ==============================================================================
os.environ["CUDA_VISIBLE_DEVICES"] = "0" 

model_path = "NakJun/Llama-3.2-1B-Instruct-ko-QuAD"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=False,
)

# 파인튜닝 전 '원본' 모델 로드
original_model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto",
)
original_model.config.use_cache = False
original_model.config.pretraining_tp = 1

tokenizer = AutoTokenizer.from_pretrained(model_path)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# ==============================================================================
# [Phase 1] 파인튜닝 전 모델 성능 테스트
# ==============================================================================
print("="*60)
print("Phase 1: 파인튜닝 전 원본 모델 성능 테스트 시작")
print("="*60)

test_question = "시스템은 최신 MSA(Microservice Architecture) 구조를 채택하여 서비스 간 독립성과 확장성을 보장해야 합니다."
test_context = "본 시스템은 모놀리식(Monolithic) 아키텍처를 기반으로 설계되었습니다. 이는 초기 개발 속도가 빠르다는 장점이 있으나, 향후 서비스 단위의 독립적인 배포 및 확장은 제한될 수 있습니다. 대신, 모듈화를 통해 결합도를 낮추는 전략을 사용합니다."

before_answer = run_qa_test(original_model, tokenizer, test_question, test_context)

print(f"\n[Test Question]\nRFP 요구사항: {test_question}")
print(f"\n[Test Context]\n제안서 내용: {test_context}")
print("\n--------------------[Before Fine-tuning]--------------------")
print(f"원본 모델의 답변:\n{before_answer}")
print("="*60)

# ==============================================================================
# [Phase 2] LoRA 파인튜닝 진행
# ==============================================================================
print("\n" + "="*60)
print("Phase 2: LoRA 파인튜닝 시작")
print("="*60)

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# PEFT 모델 준비 (학습을 위해 원본 모델을 래핑)
peft_model = prepare_model_for_kbit_training(original_model)
peft_model = get_peft_model(peft_model, lora_config)
peft_model.print_trainable_parameters()

try:
    data = load_dataset("json", data_files="evaluation_dataset_temp_1000.jsonl", split="train")
except FileNotFoundError:
    print("ERROR: 'evaluation_dataset_temp_1000.jsonl' 파일을 찾을 수 없습니다.")
    exit()

def create_prompt(sample):
    instruction = sample['instruction']
    input_text = sample['input']
    output_text = sample['output']
    eos_token = tokenizer.eos_token
    prompt = (
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{instruction}\n{input_text}{eos_token}"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{output_text}{eos_token}"
    )
    return {"text": prompt}

processed_data = data.map(create_prompt)

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=1,
    optim="paged_adamw_32bit",
    save_steps=100,
    logging_steps=10,
    learning_rate=2e-5,
    bf16=True,
    report_to="tensorboard",
)

trainer = SFTTrainer(
    model=peft_model,
    train_dataset=processed_data,
    args=training_args,
)

trainer.train()

output_adapter_dir = "./rfp-eval-lora-adapter"
trainer.model.save_pretrained(output_adapter_dir)
print(f"\nLoRA 어댑터가 '{output_adapter_dir}'에 저장되었습니다.")

# ==============================================================================
# [Phase 3] 파인튜닝 후 모델 성능 테스트
# ==============================================================================
print("\n" + "="*60)
print("Phase 3: 파인튜닝 후 모델 성능 테스트 시작")
print("="*60)
print("학습된 LoRA 어댑터를 베이스 모델에 병합하고 새로 로드합니다...")

# VRAM 확보를 위해 이전 모델을 메모리에서 삭제
del original_model
del peft_model
del trainer
torch.cuda.empty_cache()

# 1. 베이스 모델을 BFloat16 타입으로 새로 로드 (양자화 없이)
base_model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16, # 학습 시 사용한 compute_dtype과 동일하게 설정
    device_map="auto",
)

# 2. 저장된 LoRA 어댑터를 베이스 모델에 로드
ft_model = PeftModel.from_pretrained(base_model, output_adapter_dir)

# 3. 어댑터를 베이스 모델에 병합하고, 어댑터는 언로드
merged_model = ft_model.merge_and_unload()
print("모델 병합 완료!")

# 4. 병합된 모델로 QA 테스트 실행
after_answer = run_qa_test(merged_model, tokenizer, test_question, test_context)

print(f"\n[Test Question]\nRFP 요구사항: {test_question}")
print(f"\n[Test Context]\n제안서 내용: {test_context}")
print("\n--------------------[After Fine-tuning]---------------------")
print(f"파인튜닝된 모델의 답변:\n{after_answer}")
print("\n--------------------[Before (for comparison)]---------------------")
print(f"원본 모델의 답변:\n{before_answer}")
print("="*60)