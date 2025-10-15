import os
import time
import csv
import psutil
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainerCallback,
    set_seed,
)
from peft import LoraConfig, prepare_model_for_kbit_training, PeftModel
from sklearn.model_selection import train_test_split
from trl import SFTTrainer, SFTConfig
import random
import numpy as np

os.environ["TOKENIZERS_PARALLELISM"] = "false"
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
set_seed(SEED)

eval_ds = None
# =========================
# 콜백: 런타임 로그
# =========================
class MemoryTimingCallback(TrainerCallback):
    def __init__(self, output_dir, log_every=50):
        self.output_dir = output_dir
        self.log_every = log_every
        self.proc = psutil.Process(os.getpid())
        self.csv_path = os.path.join(output_dir, "train_runtime_metrics.csv")
        self.wall_start = None
        self.cpu_peak_rss = 0
        self.max_cuda_ms = 0.0
        self.max_gpu_mem = 0
        self.step_start = None
        self.cuda_start = None
        self.gpu_available = torch.cuda.is_available()
        if self.gpu_available:
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        os.makedirs(output_dir, exist_ok=True)
        with open(self.csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "global_step", "wall_step_sec", "cuda_step_ms",
                "gpu_mem_allocated_mb", "gpu_mem_reserved_mb", "cpu_rss_mb"
            ])
    def on_train_begin(self, args, state, control, **kwargs):
        self.wall_start = time.perf_counter()
    def on_step_begin(self, args, state, control, **kwargs):
        self.step_start = time.perf_counter()
        if self.gpu_available:
            self.cuda_start = torch.cuda.Event(enable_timing=True)
            self.cuda_end = torch.cuda.Event(enable_timing=True)
            self.cuda_start.record()
    def on_step_end(self, args, state, control, **kwargs):
        wall_step_sec = time.perf_counter() - self.step_start if self.step_start else 0.0
        cuda_step_ms = 0.0
        if self.gpu_available:
            self.cuda_end.record()
            torch.cuda.synchronize()
            cuda_step_ms = self.cuda_start.elapsed_time(self.cuda_end)
            gpu_alloc = torch.cuda.max_memory_allocated() / (1024**2)
            gpu_resvd = torch.cuda.max_memory_reserved() / (1024**2)
            torch.cuda.reset_peak_memory_stats()
        else:
            gpu_alloc = gpu_resvd = 0.0
        cpu_rss_mb = self.proc.memory_info().rss / (1024**2)
        self.cpu_peak_rss = max(self.cpu_peak_rss, cpu_rss_mb)
        self.max_cuda_ms = max(self.max_cuda_ms, cuda_step_ms)
        self.max_gpu_mem = max(self.max_gpu_mem, gpu_resvd)
        if state.global_step % self.log_every == 0 or state.global_step == state.max_steps:
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    state.global_step, round(wall_step_sec, 6), round(cuda_step_ms, 3),
                    round(gpu_alloc, 2), round(gpu_resvd, 2), round(cpu_rss_mb, 2)
                ])
    def on_train_end(self, args, state, control, **kwargs):
        total_wall = time.perf_counter() - self.wall_start if self.wall_start else 0.0
        print("\n=== [RUNTIME SUMMARY] ===")
        print(f"Total wall time (sec): {total_wall:.2f}")
        print(f"Peak CPU RSS (MB): {self.cpu_peak_rss:.2f}")
        print(f"Peak GPU reserved (MB): {self.max_gpu_mem:.2f}")
        print(f"Max per-step CUDA (ms): {self.max_cuda_ms:.2f}")
        print(f"CSV saved to: {self.csv_path}")

class TimeBudgetCallback(TrainerCallback):
    def __init__(self, max_minutes=25):
        self.max_sec = max_minutes * 60
        self.t0 = None
    def on_train_begin(self, args, state, control, **kwargs):
        self.t0 = time.perf_counter()
    def on_step_end(self, args, state, control, **kwargs):
        if time.perf_counter() - self.t0 > self.max_sec:
            control.should_training_stop = True
            print(f"\n[TimeBudgetCallback] Reached {self.max_sec/60:.1f} min. Stopping training.")

# =========================
# 경로 설정
# =========================
model_name = "./llama-3.2-1B-Instruct"  # 로컬 모델 경로
output_dir = "./llama-3.2-1B-Instruct-vuln-lora"  # 학습 결과 저장
lora_adapter_dir = f"{output_dir}/lora-adapter"
os.makedirs(output_dir, exist_ok=True)

# =========================
# 데이터셋 로드 및 SFT용 전처리 (secure_programming_dpo_test.json)
# =========================
print("1) 데이터셋 로드: secure_programming_dpo.json ...")
dataset = load_dataset('json', data_files="./data/Code_Vuln_DPO/secure_programming_dpo.json")
dataset = load_dataset('json', data_files="./data/Code_Vuln_DPO/secure_programming_dpo_flat.json")

# 2. Train/Test 분할 (80:20)
# split_dataset = dataset['train'].train_test_split(test_size=0.1, seed=42)
# 3. Test를 Validation/Test로 재분할 (각 10%)
# test_valid = split_dataset['test'].train_test_split(test_size=0.5, seed=42)

# 4. 최종 데이터셋 구성
# train_dataset = split_dataset['train']  # 80%
# valid_dataset = test_valid['train']     # 10%/
# test_dataset = test_valid['test']       # 10%


# print(f"Train: {len(train_dataset)} samples")
# print(f"Validation: {len(valid_dataset)} samples")  
# print(f"Test: {len(test_dataset)} samples")


# def formatting_func(examples):
#     texts = []
#    for q, vuln, chosen in zip(examples["question"], examples["vulnerability"], examples["chosen"]):
#        prompt = f"보안 전문가의 입장에서, 다음 문제를 보고 취약점이 있다면 설명과 함께 안전한 코드를 작성하라.\n문제: {q}\n취약점 유형: {vuln}"
#        response = chosen.strip()
#        texts.append(prompt + '\n' + response)
#    return {"text": texts}


# def formatting_func(examples):
#     texts = []
#     for vuln, rejected, chosen in zip(examples["vulnerability"], examples["rejected"], examples["chosen"]):
#         # Sample 1: Vulnerable code → Vulnerability description
#         prompt1 = f"Analyze the security vulnerabilities in the following code.\n\n{rejected.strip()}"
#         response1 = vuln.strip()
#         texts.append(prompt1 + '\n\nAnalysis:\n' + response1)
        
#         # Sample 2: Safe code → Safety confirmation
#         prompt2 = f"Analyze the security vulnerabilities in the following code.\n\n{chosen.strip()}"
#         response2 = "No vulnerabilities detected. This code follows security best practices."
#         texts.append(prompt2 + '\n\nAnalysis:\n' + response2)
    
#     return {"text": texts}

def formatting_func(examples):
    texts = []
    for prompt, response in zip(examples['code'], examples['desc']):
        texts.append(f"Analyze the security vulnerabilities in the following code.\n\n{prompt}\n\nAnalysis:\n{response}")
    return {"text": texts}


# def formatting_func(example):
#     prompt = f"Analyze the security vulnerabilities in the following code.\n\n{example['code']}"
#     response = example['desc']
#     return {"text": prompt + "\n\nAnalysis:\n" + response}


train_dataset = dataset["train"].map(formatting_func, batched=True)
print(f"총 샘플 수: {len(train_dataset)}")

# =========================
# 모델/토크나이저 로드 (QLoRA)
# =========================
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=False,
)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model.config.use_cache = False
model.config.pretraining_tp = 1
try: model.config.attn_implementation = "sdpa"
except Exception: pass
model = prepare_model_for_kbit_training(model)
model.gradient_checkpointing_enable()
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# =========================
# LoRA 설정
# =========================
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

# =========================
# 데이터 서브샘플링
# =========================
MAX_TRAIN_SAMPLES = 5000
if len(train_dataset) > MAX_TRAIN_SAMPLES:
    train_dataset = train_dataset.shuffle(seed=42).select(range(MAX_TRAIN_SAMPLES))

MAX_SEQ_LENGTH = 1024
if hasattr(tokenizer, "model_max_length"):
    MAX_SEQ_LENGTH = min(MAX_SEQ_LENGTH, tokenizer.model_max_length)

# =========================
# 학습 설정
# =========================
training_arguments = SFTConfig(
    output_dir=output_dir,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    optim="paged_adamw_8bit",
    # fp16=False,
    # bf16=True,
    fp16=True,
    bf16=False,
    max_steps=240,
    num_train_epochs=1,
    logging_steps=50,
    # save_strategy="steps",
    save_strategy="no",
    save_steps=250,
    eval_strategy="no",
    report_to="none",
    lr_scheduler_type="cosine",
    learning_rate=2e-4,
    warmup_ratio=0.03,
    # dataloader_num_workers=2,           # for ubunut/
    dataloader_num_workers=0,           # for windows
    remove_unused_columns=False,
    # packing=True,                       # for ubuntu
    packing=False,                      # for windows
    # max_length=MAX_SEQ_LENGTH,
    # max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",
    seed=SEED,
    data_seed=SEED,
)

# =========================
# 학습 시작
# =========================
metrics_cb = MemoryTimingCallback(output_dir=output_dir, log_every=50)
time_cb = TimeBudgetCallback(max_minutes=30)

trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_ds,      # ← None으로 지정
    peft_config=peft_config,
    args=training_arguments,
    callbacks=[metrics_cb, time_cb],
)
trainer.train()

# =========================
# LoRA 어댑터 저장 및 병합
# =========================
os.makedirs(lora_adapter_dir, exist_ok=True)
trainer.save_model(lora_adapter_dir)
tokenizer.save_pretrained(output_dir)
base = AutoModelForCausalLM.from_pretrained(
    model_name, torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True
)

model_with_lora = PeftModel.from_pretrained(base, lora_adapter_dir)
merged = model_with_lora.merge_and_unload()
merged.save_pretrained("./merged-vuln-detector", safe_serialization=True)
tokenizer.save_pretrained("./merged-vuln-detector")
print("학습 및 모델 병합 완료")
