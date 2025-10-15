from multiprocessing import context
import os
import pandas as pd
import numpy as np
import json
from tqdm.notebook import tqdm 
tqdm.pandas()
import warnings
warnings.filterwarnings("ignore")
import re
from typing import List, Dict, Any

from huggingface_hub import login
from datasets import load_dataset
import faiss

from openai import OpenAI
from datasets import Dataset

# Config
CONFIG_PATH = "../config.json"
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)
UPSTAGE_API = config["UPSTAGE_API"]
TAVILY_API_KEY = config["TAVILY_API_KEY"]
HUGGING_FACE_TOKEN = config["HUGGING_FACE_TOKEN"]
login(token=HUGGING_FACE_TOKEN)

# Config: Model
SOLAR_MODEL = 'solar-pro2'
LLAMA_MODEL = 'meta-llama/Llama-3.2-3B-Instruct'

# Config: Data
# Config: Data
def select_dataset_config(dataset_name: str) -> Dict[str, str]:
    if dataset_name == "FINANCE":
        return {
            "QA_PATH": config["FINANCE_QA_PATH"],
            "BENCHMARK_PATH": config["FINANCE_BENCHMARK_PATH"],
            "BENCHMARK_VALID_PATH": config["FINANCE_BENCHMARK_VALID_PATH"],
            "BENCHMARK_VALID_FILTERING_PATH": config["FINANCE_BENCHMARK_VALID_FILTERING_PATH"],
        }
    elif dataset_name == "PIT":
        return {
            "QA_PATH": config["PIT_QA_PATH"],
            "BENCHMARK_PATH": config["PIT_BENCHMARK_PATH"],
            "BENCHMARK_RAG_PATH": config["PIT_BENCHMARK_RAG_PATH"],
            "BENCHMARK_VALID_PATH": config["PIT_BENCHMARK_VALID_PATH"],
            "BENCHMARK_VALID_FILTERING_PATH": config["PIT_BENCHMARK_VALID_FILTERING_PATH"],
        }
    elif dataset_name == "REPORT":
        return {
            "QA_PATH": config["REPORT_QA_PATH"],
            "BENCHMARK_PATH": config["REPORT_BENCHMARK_PATH"],
            "BENCHMARK_RAG_PATH": config["REPORT_BENCHMARK_RAG_PATH"],
            "BENCHMARK_VALID_PATH": config["REPORT_BENCHMARK_VALID_PATH"],
            "BENCHMARK_VALID_FILTERING_PATH": config["REPORT_BENCHMARK_VALID_FILTERING_PATH"],
        }
    elif dataset_name == "KRX":
        return {
            "QA_PATH": config["KRX_QA_PATH"],
            "BENCHMARK_PATH": config["KRX_BENCHMARK_PATH"],
            "BENCHMARK_RAG_PATH": config["KRX_BENCHMARK_RAG_PATH"],
            "BENCHMARK_VALID_PATH": config["KRX_BENCHMARK_VALID_PATH"],
            "BENCHMARK_VALID_FILTERING_PATH": config["KRX_BENCHMARK_VALID_FILTERING_PATH"],
        }
    else:
        raise ValueError(f"Unknown dataset name: {dataset_name}")

# Config: Prompt
GENERATE_QA_PROMPT_PATH = config["GENERATE_QA_PROMPT_PATH"]
EVAL_DOMAIN_PROMPT_PATH = config["EVAL_DOMAIN_PROMPT_PATH"]
EVAL_QUALITY_PROMPT_PATH = config["EVAL_QUALITY_PROMPT_PATH"]
EVAL_DIFFICULTY_PROMPT_PATH = config["EVAL_DIFFICULTY_PROMPT_PATH"]


### Process Data ###
def load_prompt(path) -> str:
    """
    프롬프트 파일을 읽어오는 함수.

    Parameters:
        path (str): 프롬프트 파일 경로)
    Returns:
        str: 프롬프트 내용    
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
def chunk_text(text: str, chunk_size: int = 5, chunk_overlap: int = 100) -> List[str]:
    """
    긴 텍스트를 일정 길이(chunk_size) 단위로 나누는 함수.
    각 청크 사이에 일정 부분(chunk_overlap)을 겹치게 하여 문맥 유지를 돕는다.
    
    Parameters:
        text (str): 나눌 전체 입력 텍스트
        chunk_size (int): 각 청크의 최대 토큰 단위 길이 (기본값=5)
        chunk_overlap (int): 청크 간 겹치는 토큰 수 (기본값=100)
    
    Returns:
        List[str]: 분리된 텍스트 청크 리스트
    """
    tokens = re.findall(r"\S+\s*", text)
    out = []
    i = 0
    while i < len(tokens):
        chunk = "".join(tokens[i:i+chunk_size]).strip()
        if chunk:
            out.append(chunk)
        if i + chunk_size >= len(tokens):
            break
        i += max(1, chunk_size - chunk_overlap)
    return out or [text]


### Generate Benchmark ###
def generate_for_contexts(
    contexts: List[str],
    api_key: str,
    save_path: str,
    model: str = SOLAR_MODEL
) -> List[dict]:
    """
    각 context에 대해 단 하나의 Q-A 쌍을 생성하고
    Context, Question, Answer 필드만 포함된 JSON 객체 리스트로 반환.
    """

    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    sys_prompt = load_prompt(GENERATE_QA_PROMPT_PATH)

    results = []
    for context in contexts:
        prompt = f"[CONTEXT]\n{context}\n\n위 컨텍스트로부터 한 개의 질문과 정답을 생성하라."

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "qa_pair",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "Context": {"type": "string"},
                        "Question": {"type": "string"},
                        "Answer": {"type": "string"},
                    },
                    "required": ["Context", "Question", "Answer"],
                },
            },
        }

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            stream=False,
            response_format=response_format
        )

        result = json.loads(response.choices[0].message.content)
        results.append(result)

    # 데이터 저장
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


### Top-k Similar Docs Retrieval for RAG ###
def get_embeddings(client: OpenAI, texts: List[str], mode: str = "query") -> List[List[float]]:
    """Get embeddings using Solar embedding model.
    
    Args:
        client: OpenAI client configured for Upstage API
        texts: List of input strings
        mode: "query" or "passage"
        
    Returns:
        List of embedding vectors
    """
    if mode == "query":
        model = "embedding-query"
    elif mode == "passage":
        model = "embedding-passage"
    else:
        raise ValueError("mode must be 'query' or 'passage'")
    
    response = client.embeddings.create(
        model=model,
        input=texts
    )
    return [embedding.embedding for embedding in response.data]

def add_similar_docs_to_benchmark(benchmark, all_contexts, client, get_embeddings, k=3) -> List[Dict[str, Any]]:
    """
    Question에 대해 유사 문서를 검색하여 benchmark에 추가하는 함수

    Parameters:
        benchmark: 질문/문맥 dict 리스트
        all_contexts: 인덱스에 들어갈 전체 문서 리스트
        client, get_embeddings: 임베딩 생성에 필요한 객체/함수
        k: Top-K 유사 문서 개수
    Returns:
        benchmark: 질문/문맥 dict 리스트
    """
    # 1. 전체 문서 임베딩 (매개변수로 받은 all_contexts 사용)
    embeddings = get_embeddings(client, all_contexts, mode="passage")
    document_embeddings = np.array(embeddings).astype(np.float32)

    # 2. 벡터 인덱스 생성 (코사인 유사도)
    dimension = document_embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(document_embeddings)
    index.add(document_embeddings)

    # 3. 각 질문별로 유사 문서 검색 및 benchmark에 추가
    for item in benchmark:
        question = item['Question']
        question_embedding = get_embeddings(client, [question], mode="query")[0]
        question_embedding = np.array(question_embedding).astype(np.float32)
        question_embedding = question_embedding.reshape(1, -1)
        faiss.normalize_L2(question_embedding)
        similarity_scores, indices = index.search(question_embedding, k)
        retrieved_contexts = [all_contexts[idx] for idx in indices[0]]
        item['Context_RAG'] = retrieved_contexts
    return benchmark


def detect_domain_generate_judge_prompt(
    qa_data: List[str],
    api_key: str,
) -> List[dict]:
    """
    각 context에 대해 도메인을 자동 판별하고,
    판별된 도메인을 기반으로 Question이 도메인에 적합한지 평가하는 Prompt를 생성
    """

    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    sys_prompt = load_prompt(EVAL_DOMAIN_PROMPT_PATH)

    results = []
    for qa in qa_data:
        context = qa['Context_RAG']
        question = qa['Question']
        answer = qa['Answer']
        prompt = f"도메인을 자동 판별하고, Question이 도메인에 적합한지 평가하는 Prompt를 작성하라.\n\nContext: {context}\nQuestion: {question}\nAnswer: {answer}"

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "domain_prompt",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "Domain": {"type": "string"},
                        "Domain_Prompt": {"type": "string"},
                    },
                    "required": ["Domain", "Domain_Prompt"],
                },
            },
        }

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=SOLAR_MODEL,
            messages=messages,
            temperature=0.2,
            stream=False,
            response_format=response_format
        )

        result = json.loads(response.choices[0].message.content)
        results.append(result)
    return results

def evaluate_domain_validity(
    qa_data: List[str],
    domain_info: List[str],
    api_key: str,
) -> List[dict]:
    """
    도메인 평가 Prompt에 따라 Question/Answer 쌍이 도메인에 적합한지 평가
    """

    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")

    results = []
    for i in range(len(qa_data)):
        question = qa_data[i]['Question']
        answer = qa_data[i]['Answer']
        domain = domain_info[i]['Domain']
        domain_prompt = domain_info[i]['Domain_Prompt']
        prompt = f"Question/Answer 쌍이 도메인에 적합한지 평가하라.\n\nQuestion: {question}\nAnswer: {answer}"

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "evaluate_domain_prompt",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "Domain": {"type": "string"},
                        "Domain_Validity": {"type": "integer"},
                        "Domain_Validity_Reason": {"type": "string"},
                    },
                    "required": ["Domain", "Domain_Validity", "Domain_Validity_Reason"],
                },
            },
        }

        messages = [
            {"role": "system", "content": domain_prompt},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=SOLAR_MODEL,
            messages=messages,
            temperature=0.2,
            stream=False,
            response_format=response_format
        )

        result = json.loads(response.choices[0].message.content)
        results.append(result)
        
    return results

def evaluate_quality(
    qa_data: List[str],
    api_key: str,
) -> List[dict]:
    """
    QA 데이터의 품질을 평가
    **평가 기준**
    1. Context와 Question의 관련성
    2. Question의 명확성과 구체성
    3. Answer의 정확성과 완성도
    4. 전체적인 논리적 일관성
    5. 정보의 유용성과 가치
    """

    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    sys_prompt = load_prompt(EVAL_QUALITY_PROMPT_PATH)

    results = []
    for i in range(len(qa_data)):
        context = qa_data[i]['Context_RAG']
        question = qa_data[i]['Question']
        answer = qa_data[i]['Answer']
        prompt = f"Question/Answer 쌍의 품질을 평가하라.\n\nContext: {context}\nQuestion: {question}\nAnswer: {answer}"

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "evaluate_quality",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "Quality_Score": {"type": "integer"},
                        "Quality_Reason": {"type": "string"},
                    },
                    "required": ["Quality_Score", "Quality_Reason"],
                },
            },
        }

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=SOLAR_MODEL,
            messages=messages,
            temperature=0.2,
            stream=False,
            response_format=response_format
        )

        result = json.loads(response.choices[0].message.content)
        results.append(result)
        
    return results

def evaluate_difficulty(
    qa_data: List[str],
    api_key: str,
) -> List[dict]:
    """
    QA 데이터의 난이도를 평가
    **평가 기준**:
    1점: very easy 
    2점: easy 
    3점: medium 
    4점: hard 
    5점: very hard 
    """

    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    sys_prompt = load_prompt(EVAL_DIFFICULTY_PROMPT_PATH)

    results = []
    for i in range(len(qa_data)):
        question = qa_data[i]['Question']
        answer = qa_data[i]['Answer']
        prompt = f"Question/Answer 쌍의 난이도를 평가하라.\n\nQuestion: {question}\nAnswer: {answer}"

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "evaluate_difficulty",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "Difficulty": {"type": "integer"},
                        "Difficulty_Reason": {"type": "string"},
                    },
                    "required": ["Difficulty", "Difficulty_Reason"],
                },
            },
        }

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=SOLAR_MODEL,
            messages=messages,
            temperature=0.2,
            stream=False,
            response_format=response_format
        )

        result = json.loads(response.choices[0].message.content)
        results.append(result)
        
    return results

def qa_evaluate(qa_data: List[str], api_key: str, save_path: str) -> Dict[str, Any]:
    """
    QA 데이터를 평가하는 함수: 도메인 적합성, 품질, 난이도 
    """
    domain_info = detect_domain_generate_judge_prompt(qa_data, api_key=api_key)
    print('finish domain_info')
    domain_results = evaluate_domain_validity(qa_data, domain_info, api_key=api_key)
    print('finish domain_results')
    quality_results = evaluate_quality(qa_data, api_key=api_key)
    print('finish quality_results')
    difficulty_results = evaluate_difficulty(qa_data, api_key=api_key)
    print('finish difficulty_results')

    combined_results = []
    for i in range(len(qa_data)):
        combined_results.append({
            "Context": qa_data[i]['Context'],
            "Context_RAG": qa_data[i]['Context_RAG'],
            "Question": qa_data[i]['Question'],
            "Answer": qa_data[i]['Answer'],
            "Domain": domain_results[i]['Domain'],
            "Domain_Validity": domain_results[i]['Domain_Validity'],
            "Domain_Validity_Reason": domain_results[i]['Domain_Validity_Reason'],
            "Quality_Score": quality_results[i]['Quality_Score'],
            "Quality_Reason": quality_results[i]['Quality_Reason'],
            "Difficulty": difficulty_results[i]['Difficulty'],
            "Difficulty_Reason": difficulty_results[i]['Difficulty_Reason']
        })

    # JSON 파일로 저장
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(combined_results, f, ensure_ascii=False, indent=4)
    return combined_results

### Benchmark Filtering ###
def filter_benchmark_data(
    data: List[Dict],
    domain_threshold: int = 2,
    quality_threshold: int = 2,
    difficulty_threshold: int = 2,
    save_path: str = None
) -> List[Dict]:
    """
    벤치마크 데이터를 필터링하는 함수
    기존 딕셔너리 구조를 유지하고, 기준을 만족하지 않는 항목들만 제거
    
    필터링 조건:
    - 도메인 타당성 > threshold점
    - 퀄리티 > threshold점  
    - 난이도 > threshold점
    
    Parameters:
        data (List[Dict]): 평가된 QA 데이터 리스트
        domain_threshold (int): 도메인 타당성 임계값 (기본값: 3)
        quality_threshold (int): 품질 임계값 (기본값: 3)
        difficulty_threshold (int): 난이도 임계값 (기본값: 3)
        save_path (str): 필터링된 결과 저장 경로
    
    Returns:
        List[Dict]: 필터링된 QA 데이터 리스트 (기존 구조 유지)
    """
    
    original_count = len(data)
    filtered_data = []
    
    # 통계 정보
    filter_stats = {
        "domain_passed": 0,
        "quality_passed": 0, 
        "difficulty_passed": 0,
        "all_criteria_passed": 0
    }
    
    for item in data:
        # 각 기준 점수 추출
        domain_score = item.get('Domain_Validity', 0)
        quality_score = item.get('Quality_Score', 0)
        difficulty_score = item.get('Difficulty', 0)
        
        # 개별 기준 통과 여부
        domain_pass = domain_score > domain_threshold
        quality_pass = quality_score > quality_threshold
        difficulty_pass = difficulty_score > difficulty_threshold
        
        # 통계 업데이트
        if domain_pass:
            filter_stats["domain_passed"] += 1
        if quality_pass:
            filter_stats["quality_passed"] += 1
        if difficulty_pass:
            filter_stats["difficulty_passed"] += 1
        
        # 모든 기준을 통과한 경우만 필터링된 데이터에 추가
        if domain_pass and quality_pass and difficulty_pass:
            filter_stats["all_criteria_passed"] += 1
            filtered_data.append(item)  # 기존 딕셔너리 구조 그대로 유지
    
    # 결과 저장
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
    
    # 필터링 결과 출력
    filtered_count = len(filtered_data)
    retention_rate = (filtered_count / original_count * 100) if original_count > 0 else 0
    
    print("=" * 50)
    print("🔍 벤치마크 필터링 결과 요약")
    print("=" * 50)
    print(f"📊 원본 샘플 수: {original_count}개")
    print(f"✅ 필터링 후 샘플 수: {filtered_count}개")
    print(f"📈 보존율: {retention_rate:.1f}%")
    
    print(f"\n🎯 필터링 기준")
    print(f"   • 도메인 타당성 임계값: {domain_threshold}점 초과")
    print(f"   • 품질 임계값: {quality_threshold}점 초과")
    print(f"   • 난이도 임계값: {difficulty_threshold}점 초과")
    
    print(f"\n📋 개별 기준 통과율")
    print(f"   • 도메인 타당성: {filter_stats['domain_passed']}/{original_count} ({filter_stats['domain_passed']/original_count*100:.1f}%)")
    print(f"   • 품질 기준: {filter_stats['quality_passed']}/{original_count} ({filter_stats['quality_passed']/original_count*100:.1f}%)")
    print(f"   • 난이도 기준: {filter_stats['difficulty_passed']}/{original_count} ({filter_stats['difficulty_passed']/original_count*100:.1f}%)")
    print(f"   • 모든 기준: {filter_stats['all_criteria_passed']}/{original_count} ({filter_stats['all_criteria_passed']/original_count*100:.1f}%)")
    print("=" * 50)
    
    return filtered_data

### Main Process ###

def main():
    choices = ["FINANCE", "PIT", "REPORT", "KRX"]
    print("데이터셋을 선택하세요:")
    for idx, choice in enumerate(choices, 1):
        print(f"{idx}. {choice}")
    selection = int(input("번호 선택: "))
    DATA_NAME = choices[selection - 1]
    dataset_config = select_dataset_config(DATA_NAME)

#데이터 로드
    if DATA_NAME == "PIT":
        dfs = load_dataset("ohsuz/PII_text_dataset")
        df = pd.DataFrame(dfs['train'])
        contexts = [i for i in df['text']][:30]
    else:
        contexts = pd.read_csv(dataset_config["QA_PATH"])
        contexts = [i for i in contexts['Context']]

    # 모델 로드
    client = OpenAI(
        api_key=UPSTAGE_API,
        base_url="https://api.upstage.ai/v1"
    )

    # QA 벤치마크 생성
    save_path = dataset_config["BENCHMARK_PATH"]
    benchmark = generate_for_contexts(contexts, api_key=UPSTAGE_API, save_path=save_path)

    # 전체 문서
    all_contexts = []
    for item in benchmark:
        all_contexts.append(item['Context'])

    # RAG 벤치마크 생성
    rag_benchmark = add_similar_docs_to_benchmark(
        benchmark, all_contexts, client, get_embeddings, k=3
    )
    # RAG 벤치마크 저장
    with open(dataset_config["BENCHMARK_RAG_PATH"], "w", encoding="utf-8") as f:
        json.dump(rag_benchmark, f, ensure_ascii=False, indent=4)

    # 데이터 타당성 확보
    save_path = dataset_config["BENCHMARK_VALID_PATH"]
    benchmark_valid = qa_evaluate(rag_benchmark, api_key=UPSTAGE_API, save_path=save_path)

    # 벤치마크 데이터 필터링 실행
    filter_save_path = dataset_config["BENCHMARK_VALID_FILTERING_PATH"]
    benchmark_valid_filter = filter_benchmark_data(
        data=benchmark_valid,
        domain_threshold=2,
        quality_threshold=2, 
        difficulty_threshold=2,
        save_path=filter_save_path
    )

    print(f"\n💾 필터링된 데이터: {len(benchmark_valid_filter)}개 샘플")


    # 데이터 허깅페이스 업로드
    # 벤치마크 데이터
    with open(dataset_config["BENCHMARK_VALID_PATH"], "r", encoding="utf-8") as f:
        benchmark_valid = json.load(f)
    benchmark_valid_df = pd.DataFrame(benchmark_valid)
    dataset = Dataset.from_pandas(benchmark_valid_df)
    dataset = dataset.add_column("FILE_NAME", [DATA_NAME] * len(dataset))
    benchmark_id = f"GAYOEN/DOC_RAG_{DATA_NAME}_BENCHMARK"
    dataset.push_to_hub(benchmark_id, token=HUGGING_FACE_TOKEN)
    
    # print('✅ Upload to Huggingface Hub Done! - ', benchmark_id)

    # 벤치마크 필터링 데이터
    with open(dataset_config["BENCHMARK_VALID_FILTERING_PATH"], "r", encoding="utf-8") as f:
        benchmark_valid_filter = json.load(f)
    benchmark_valid_filter_df = pd.DataFrame(benchmark_valid_filter)
    dataset = Dataset.from_pandas(benchmark_valid_filter_df)
    dataset = dataset.add_column("FILE_NAME", [DATA_NAME] * len(dataset))
    benchmark_filter_id = f"GAYOEN/DOC_RAG_{DATA_NAME}_BENCHMARK_FILTERED"
    dataset.push_to_hub(benchmark_filter_id, token=HUGGING_FACE_TOKEN)
    # print('✅ Upload to Huggingface Hub Done! - Filtered', benchmark_filter_id)

    # 링크 반환
    benchmark_link = f"https://huggingface.co/datasets/{benchmark_id}"
    benchmark_filter_link = f"https://huggingface.co/datasets/{benchmark_filter_id}"
    print(f"🔗 벤치마크 링크: {benchmark_link}")
    print(f"🔗 필터링된 벤치마크 링크: {benchmark_filter_link}")
    return {
        "benchmark_link": benchmark_link,
        "benchmark_filter_link": benchmark_filter_link
    }
    
if __name__ == "__main__":
    main()