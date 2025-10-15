#!/usr/bin/env python3
"""
Llama Model Loader
Provides load_model() function for loading Llama models with transformers
"""

import os
import logging
import torch
from pathlib import Path

logger = logging.getLogger(__name__)


def load_model(model_name: str = "meta-llama/Llama-3.2-3B-Instruct"):
    """
    Load Llama model and tokenizer

    Args:
        model_name: HuggingFace model name or local path

    Returns:
        tuple: (tokenizer, model)
    """
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        raise ImportError(
            "transformers package not installed. Run: uv add transformers torch"
        )

    logger.info(f"Loading Llama model: {model_name}")

    # Check if CUDA is available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Set pad token if not set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        low_cpu_mem_usage=True
    )

    if device == "cpu":
        model = model.to(device)

    logger.info(f"Model loaded successfully on {device}")

    return tokenizer, model


def generate_text(
    tokenizer,
    model,
    prompt: str,
    max_new_tokens: int = 1500,
    temperature: float = 0.3,
    top_p: float = 0.9,
    do_sample: bool = True,
    repetition_penalty: float = 1.1
) -> str:
    """
    Generate text using Llama model

    Args:
        tokenizer: Tokenizer instance
        model: Model instance
        prompt: Input prompt
        max_new_tokens: Maximum number of new tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        do_sample: Whether to use sampling
        repetition_penalty: Penalty for repetition

    Returns:
        str: Generated text
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=repetition_penalty
        )

    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Remove the prompt from the output
    generated_text = full_text[len(prompt):].strip()

    return generated_text
