# finetune_qlora_router_ko.py
# QLoRA 기반 한국어 라우터 전용 SFT (RTX 4070 8GB 안전 기본값)
# - assistant 구간만 손실에 기여(라벨 마스킹)
# - 한국어 시스템 프롬프트 고정, EOS 종료 토큰 강제
# - 중단/재개 지원(get_last_checkpoint)
# - 4bit NF4 + paged optimizer
# - TensorBoard logging_dir .env와 일치 가능

import os
import argparse
import json
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
    set_seed,
    default_data_collator,
)
from transformers.trainer_utils import get_last_checkpoint
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
import bitsandbytes as bnb  # noqa: F401  (확실히 로드 여부 확인용)

# ---------------------------
# Argparse / ENV
# ---------------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base_model",   default=os.getenv("BASE_MODEL", "/workspace/models/base"))
    p.add_argument("--output_dir",   default=os.getenv("OUTPUT_DIR", "/workspace/models/lora"))
    p.add_argument("--train_file",   default=os.getenv("TRAIN_FILE", "/workspace/data/sft/train_mixed.jsonl"))
    p.add_argument("--val_file",     default=os.getenv("VAL_FILE",   "/workspace/data/sft/val.jsonl"))
    p.add_argument("--seq_len",      type=int,   default=int(os.getenv("SEQ_LEN", 1024)))
    p.add_argument("--micro_bsz",    type=int,   default=int(os.getenv("MICRO_BSZ", 1)))
    p.add_argument("--grad_acc",     type=int,   default=int(os.getenv("GRAD_ACC", 16)))
    p.add_argument("--epochs",       type=float, default=float(os.getenv("EPOCHS", 1.0)))
    p.add_argument("--lr",           type=float, default=float(os.getenv("LR", 2e-4)))
    p.add_argument("--eval_steps",   type=int,   default=int(os.getenv("EVAL_STEPS", 200)))
    p.add_argument("--save_steps",   type=int,   default=int(os.getenv("SAVE_STEPS", 200)))
    p.add_argument("--bf16",         type=str,   default=os.getenv("BF16", "true"))  # "true"/"false"
    p.add_argument("--lora_r",       type=int,   default=int(os.getenv("LORA_R", 8)))
    p.add_argument("--lora_alpha",   type=int,   default=int(os.getenv("LORA_ALPHA", 16)))
    p.add_argument("--lora_dropout", type=float, default=float(os.getenv("LORA_DROPOUT", 0.05)))
    p.add_argument("--weight_decay", type=float, default=float(os.getenv("WEIGHT_DECAY", 0.01)))
    p.add_argument("--seed",         type=int,   default=int(os.getenv("SEED", 42)))
    p.add_argument("--resume",       type=str,   default=os.getenv("RESUME", "true"))  # "true"/"false"
    p.add_argument("--logging_dir",  type=str,   default=os.getenv("TB_LOGDIR", None))
    p.add_argument("--target_modules", type=str, default=os.getenv("TARGET_MODULES", ""))  # "", "all-linear" 등
    return p.parse_args()


def get_bnb_config():
    return BitsAndBytesConfig(
        load_in_4bit=True,                  # 4bit 로드
        bnb_4bit_quant_type="nf4",          # QLoRA 표준: NF4
        bnb_4bit_compute_dtype=torch.bfloat16,  # 4070은 bf16 지원
        bnb_4bit_use_double_quant=True      # 권장(메모리 절약)
    )


def build_prompt(instruction: str, inctx: str | None, output: str | None = None, for_labels: bool = True) -> str:
    """한국어 라우터 목적에 고정된 SFT 템플릿.
    ※ EOS는 tok_map에서 토큰 단위로 보장합니다.
    """
    sys = (
        "당신은 IP/특허 비서의 라우팅 모델입니다. 반드시 JSON만 출력합니다. "
        '키는 {"intent","action","jurisdiction","confidence"} 입니다. '
        '불확실하거나 증거가 필요하면 action="retrieve" 를 선택하세요.'
    )
    u = instruction or ""
    if inctx:
        u = u + "\n" + inctx
    a = (output or "") if for_labels else ""
    return (
        f"<|system|>{sys}</|system|>\n"
        f"<|user|>{u}</|user|>\n"
        f"<|assistant|>{a}</|assistant|>"
    )


def resolve_target_modules(arg_str: str):
    # 기본값: Llama 계열 권장 모듈
    default = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    if not arg_str:
        return default
    key = arg_str.strip().lower()
    if key in ("all-linear", "all_linear", "all"):
        # 필요 시 lm_head 포함 여부 선택 가능
        return default + ["lm_head"]
    # 쉼표 분리 지정 지원: TARGET_MODULES="q_proj,k_proj,v_proj"
    if "," in key:
        return [x.strip() for x in key.split(",") if x.strip()]
    return default


def main():
    args = parse_args()
    set_seed(args.seed)

    # 성능 스위치(속도 개선)
    torch.backends.cuda.matmul.allow_tf32 = True

    print("==== Args ====")
    print(json.dumps(vars(args), indent=2, ensure_ascii=False))

    print("Loading model/tokenizer...")
    bnb_config = get_bnb_config()

    # 4bit 로드
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        device_map="auto",
        trust_remote_code=True,
        quantization_config=bnb_config,
    )

    # k-bit 학습 준비
    model = prepare_model_for_kbit_training(model)

    # gradient checkpointing
    model.gradient_checkpointing_enable()
    # 특정 환경에서 reentrant 관련 경고가 뜨면 아래로 교체
    # model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

    # 일부 모델은 use_cache=True면 ckpt와 충돌 경고
    if hasattr(model, "config"):
        try:
            model.config.use_cache = False
        except Exception:
            pass

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    tokenizer.padding_side = "right"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    if hasattr(model, "config"):
        model.config.pad_token_id = tokenizer.pad_token_id

    # LoRA 설정
    targets = resolve_target_modules(args.target_modules)
    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=targets,
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    print("Loading dataset...")
    ds = load_dataset("json", data_files={
        "train": args.train_file,
        "validation": args.val_file
    })

    # JSONL 필수 키 빠른 검증
    for split in ("train", "validation"):
        if split not in ds:
            continue
        bad = 0
        sample_n = min(100, len(ds[split]))
        if sample_n == 0:
            print(f"[WARN] {split}: empty dataset")
            continue
        for ex in ds[split].select(range(sample_n)):
            if not {"instruction", "output"}.issubset(ex.keys()):
                bad += 1
        if bad > 0:
            print(f"[WARN] {split}: malformed {bad} / {sample_n} (instruction/output 키 누락 가능)")

    eos_id = tokenizer.eos_token_id

    def tok_map(ex):
        instr = ex.get("instruction") or ""
        inctx = ex.get("input") or ex.get("context") or None
        out   = ex.get("output") or ex.get("answer") or ex.get("summary") or ""

        # (A) 어시 전까지
        prompt_in  = build_prompt(instr, inctx, output=None, for_labels=False)
        # (B) 어시 포함 전체
        prompt_out = build_prompt(instr, inctx, output=out,   for_labels=True)

        in_ids = tokenizer(
            prompt_in,
            max_length=args.seq_len,
            truncation=True,
            padding=False,
            add_special_tokens=False,
        )["input_ids"]

        full_ids = tokenizer(
            prompt_out,
            max_length=args.seq_len,
            truncation=True,
            padding=False,
            add_special_tokens=False,
        )["input_ids"]

        # 어시스턴트 끝에 EOS 강제(잘린 경우엔 이미 truncation됨)
        if len(full_ids) < args.seq_len and (len(full_ids) == 0 or full_ids[-1] != eos_id):
            full_ids = full_ids + [eos_id]

        # assistant 구간만 라벨 활성화
        labels = [-100] * len(in_ids) + full_ids[len(in_ids):]
        # 길이 정합(이상 케이스 방어)
        if len(labels) > len(full_ids):
            labels = labels[:len(full_ids)]
        elif len(labels) < len(full_ids):
            labels = labels + [-100] * (len(full_ids) - len(labels))

        return {"input_ids": full_ids, "labels": labels}

    train_ds = ds["train"].map(tok_map, remove_columns=ds["train"].column_names, desc="Tokenizing train")
    val_ds   = ds["validation"].map(tok_map, remove_columns=ds["validation"].column_names, desc="Tokenizing val")

    # collator: 우리가 labels를 만들었으니 기본 collator가 안전
    collator = default_data_collator

    # logging_dir 결정
    logging_dir = args.logging_dir if args.logging_dir else os.path.join(args.output_dir, "runs")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        logging_dir=logging_dir,
        per_device_train_batch_size=args.micro_bsz,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_acc,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=25,
        evaluation_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=(args.bf16.lower() == "true"),
        report_to=["tensorboard"],
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        gradient_checkpointing=True,   # enable + kwargs는 위에서 처리
        save_safetensors=True,
        weight_decay=args.weight_decay,
        optim="paged_adamw_8bit",      # bitsandbytes 옵티마이저
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
    )

    # ===== 재개 로직 =====
    resume_flag = (args.resume.lower() == "true")
    last_ckpt = None
    if resume_flag and os.path.isdir(args.output_dir):
        try:
            last_ckpt = get_last_checkpoint(args.output_dir)
        except Exception:
            last_ckpt = None
    if last_ckpt:
        print(f"[INFO] Resuming from checkpoint: {last_ckpt}")
    else:
        print("[INFO] Starting fresh training run")

    print("Starting training...")
    trainer.train(resume_from_checkpoint=last_ckpt)

    print("Saving LoRA adapter to", args.output_dir)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
