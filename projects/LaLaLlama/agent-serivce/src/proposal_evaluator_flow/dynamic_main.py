import os
import asyncio
import json
import glob
import torch
import chromadb
import requests
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from bs4 import BeautifulSoup
from functools import partial   ### 🔧 FIX: partial import (trace 저장시 회사명 전달)

# LangChain 관련 라이브러리 임포트
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

# =================================================================
# 1. RAG 파이프라인 설정 및 함수 정의
# =================================================================

# --- 경로 설정 ---
PROPOSAL_DIR = "./proposal"
RFP_PATH = "./RFP/수협_rfp.pdf"
OUTPUT_DIR = "./output"
EVALUATION_CRITERIA_PATH = "./standard/evaluation_criteria.md"
CHROMA_PERSIST_DIR = "./chroma_db_html_parsed"
INTERNAL_DATA_DIR = "./internal_data"  # 사내 정보 디렉토리 (기술스택, 담당자, 마이그레이션, 장애이력 등)
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

# --- 전역 변수 ---
unified_vectorstore = None
company_map = {}   # {"A사_제안서": "A사"} 형태
llm = None         ### 🔧 FIX: llm 전역변수 명시적으로 선언

# =================================================================
# HTML 청킹 함수 (RAG_pipeline.ipynb에서 가져옴)
# =================================================================

def split_text_by_length(text, max_length, overlap):
    """텍스트가 길 경우 지정된 크기로 분할합니다."""
    if len(text) <= max_length:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_length
        chunks.append(text[start:end])
        start += max_length - overlap
    return chunks

def chunk_html_recursively(html_content, proposal_id, max_chunk_size=1000, chunk_overlap=100):
    """HTML을 제목(h 태그) 계층 구조에 따라 안정적으로 분할합니다."""
    soup = BeautifulSoup(html_content, 'html.parser')
    chunks = []
    chunk_index = 0
    
    header_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    all_headers = soup.find_all(header_tags)

    # 헤더가 시작되기 전의 텍스트도 처리
    if all_headers:
        first_header = all_headers[0]
        text_before_first_header = ""
        for elem in first_header.find_previous_siblings():
            text_before_first_header = elem.get_text(separator=' ', strip=True) + " " + text_before_first_header
        
        if text_before_first_header.strip():
            text_chunks = split_text_by_length(text_before_first_header.strip(), max_chunk_size, chunk_overlap)
            for text_chunk in text_chunks:
                chunks.append({
                    "proposal_id": proposal_id,
                    "source_id": f"{proposal_id}_chunk_{chunk_index}",
                    "heading_context": "서문",
                    "original_text": text_chunk
                })
                chunk_index += 1

    # 헤더 기반으로 섹션 분할
    for i, header in enumerate(all_headers):
        section_text_parts = [header.get_text(separator=' ', strip=True)]
        
        for sibling in header.find_next_siblings():
            if sibling.name in header_tags:
                break
            section_text_parts.append(sibling.get_text(separator=' ', strip=True))

        full_section_text = ' '.join(filter(None, section_text_parts))
        if not full_section_text.strip():
            continue

        parent_headers = [h.get_text(strip=True) for h in header.find_parents(header_tags)]
        parent_headers.reverse()
        heading_context = parent_headers + [header.get_text(strip=True)]

        text_chunks = split_text_by_length(full_section_text, max_chunk_size, chunk_overlap)
        for text_chunk in text_chunks:
            chunks.append({
                "proposal_id": proposal_id,
                "source_id": f"{proposal_id}_chunk_{chunk_index}",
                "heading_context": " > ".join(heading_context),
                "original_text": text_chunk
            })
            chunk_index += 1
            
    # 헤더가 전혀 없는 경우 body 전체를 처리
    if not all_headers and soup.body:
        full_text = soup.body.get_text(separator=' ', strip=True)
        if full_text:
            text_chunks = split_text_by_length(full_text, max_chunk_size, chunk_overlap)
            for text_chunk in text_chunks:
                chunks.append({
                    "proposal_id": proposal_id,
                    "source_id": f"{proposal_id}_chunk_{chunk_index}",
                    "heading_context": "본문",
                    "original_text": text_chunk
                })
                chunk_index += 1
                
    return chunks

# =================================================================
# 사내 정보 로더 함수
# =================================================================

def load_all_internal_data_simple(internal_data_dir):
    """
    사내 정보 디렉토리의 모든 파일을 간단하게 로드하는 함수

    정형/비정형 구분 없이 모든 .txt 파일을 Document로 변환하여 로드합니다.
    각 파일은 통째로 하나의 Document가 되며, 파일명에서 문서 타입을 자동 추론합니다.

    Args:
        internal_data_dir (str): 사내 정보 디렉토리 경로

    Returns:
        list[Document]: 모든 사내 정보 Document 리스트
    """
    all_internal_docs = []

    if not os.path.exists(internal_data_dir):
        print(f"  ⚠ 사내 정보 디렉토리가 존재하지 않습니다: {internal_data_dir}")
        return all_internal_docs

    print(f"\n[사내 정보 로드 시작: {internal_data_dir}]")

    # 디렉토리 내 모든 .txt 파일 검색
    internal_files = glob.glob(os.path.join(internal_data_dir, "*.txt"))

    for file_path in internal_files:
        filename = os.path.basename(file_path)

        try:
            # 파일 내용 전체를 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 파일명에서 문서 타입 자동 분류
            if 'tech_stack' in filename.lower():
                doc_type = "사내_기술스택"
            elif 'contact' in filename.lower():
                doc_type = "사내_담당자"
            elif 'migration' in filename.lower():
                doc_type = "사내_마이그레이션"
            elif 'incident' in filename.lower():
                doc_type = "사내_장애이력"
            else:
                doc_type = "사내_기타"

            # Document 생성 (파일 전체를 하나의 Document로)
            doc = Document(
                page_content=content,
                metadata={
                    "doc_type": doc_type,
                    "source_file": filename
                }
            )
            all_internal_docs.append(doc)
            print(f"  ✓ [{doc_type}] {filename} 로드 완료 ({len(content)} 자)")

        except Exception as e:
            print(f"  ✗ {filename} 로드 실패: {e}")
            continue

    print(f"\n✅ 총 {len(all_internal_docs)}개의 사내 정보 파일 로드 완료\n")
    return all_internal_docs

# =================================================================
# RAG 초기화 함수
# =================================================================

def initialize_rag_components():
    """RAG에 필요한 임베딩 모델을 초기화합니다."""
    if torch.cuda.is_available():
        device = "cuda"
        torch.cuda.set_device(0)
        print(f"INFO: CUDA 사용 가능 - GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        print("WARNING: CUDA를 사용할 수 없습니다. CPU로 실행합니다.")
    
    print("INFO: 임베딩 모델을 로딩합니다...")
    embedding_model = HuggingFaceEmbeddings(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    print("INFO: 임베딩 모델 초기화 완료.")
    return embedding_model

def create_unified_vectorstore(proposal_files, rfp_path, embedding_model):
    """모든 제안서와 RFP 문서를 단일 벡터 스토어로 변환"""
    print(f"\n--- [RAG Setup] 통합 벡터스토어 생성을 시작합니다 ---")
    
    all_chunked_data = []
    
    # 1. RFP(PDF) 처리 - Upstage API 사용
    print("\n[RFP 처리]")
    try:
        rfp_id = os.path.splitext(os.path.basename(rfp_path))[0]
        url = "https://api.upstage.ai/v1/document-digitization"
        headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
        
        with open(rfp_path, "rb") as f:
            files = {"document": f}
            data = {"ocr": "force", "model": "document-parse"}
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            html_from_api = response.json().get("content", {}).get("html", "")
            
        if html_from_api:
            rfp_chunks = chunk_html_recursively(html_from_api, rfp_id)
            all_chunked_data.extend(rfp_chunks)
            print(f"  ✓ RFP '{rfp_id}' 처리 완료: {len(rfp_chunks)}개 청크 생성")
    except Exception as e:
        print(f"  ✗ RFP 처리 중 오류 발생: {e}")

    # 2. 제안서(HTML) 처리
    print("\n[제안서 처리]")
    for file_path in proposal_files:
        try:
            proposal_id = os.path.splitext(os.path.basename(file_path))[0]
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            proposal_chunks = chunk_html_recursively(html_content, proposal_id)
            all_chunked_data.extend(proposal_chunks)
            print(f"  ✓ 제안서 '{proposal_id}' 처리 완료: {len(proposal_chunks)}개 청크 생성")
        except Exception as e:
            print(f"  ✗ 제안서 '{os.path.basename(file_path)}' 처리 중 오류: {e}")

    # 3. 사내 정보 로드 (기술스택, 담당자, 마이그레이션 이력, 장애 이력 등)
    print("\n[사내 정보 처리]")
    internal_docs = load_all_internal_data_simple(INTERNAL_DATA_DIR)

    # 사내 정보를 청크 형태로 변환 (기존 구조와 통일)
    for idx, doc in enumerate(internal_docs):
        doc_type = doc.metadata.get("doc_type", "사내_기타")
        source_file = doc.metadata.get("source_file", "unknown")

        # 내용이 긴 경우 적절히 분할 (max 1000자)
        content = doc.page_content
        if len(content) > 1000:
            # 1000자 단위로 분할 (오버랩 100자)
            chunks = split_text_by_length(content, 1000, 100)
            for chunk_idx, chunk in enumerate(chunks):
                all_chunked_data.append({
                    "proposal_id": f"internal_{doc_type}",
                    "source_id": f"internal_{source_file}_{idx}_{chunk_idx}",
                    "heading_context": f"{doc_type} > {source_file}",
                    "original_text": chunk
                })
        else:
            all_chunked_data.append({
                "proposal_id": f"internal_{doc_type}",
                "source_id": f"internal_{source_file}_{idx}",
                "heading_context": f"{doc_type} > {source_file}",
                "original_text": content
            })

    print(f"  ✓ 사내 정보 {len(internal_docs)}개 파일을 청크로 변환 완료")

    if not all_chunked_data:
        print("\n벡터 DB에 저장할 데이터가 없습니다.")
        return None

    # 3. Document 객체로 변환
    documents = [
        Document(
            page_content=chunk["original_text"],
            metadata={
                "proposal_id": chunk["proposal_id"],
                "source_id": chunk["source_id"],
                "heading_context": chunk["heading_context"]
            }
        ) for chunk in all_chunked_data
    ]
    print(f"\n✓ 총 {len(documents)}개의 청크를 Document 객체로 변환했습니다.")

    # 4. 벡터 스토어 생성
    print("\n[벡터화 및 저장]")
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=CHROMA_PERSIST_DIR
    )
    print(f"  ✓ 통합 벡터 스토어 생성 및 저장 완료! ({CHROMA_PERSIST_DIR})")
    return vectorstore

def get_context_for_category(proposal_file, category_keywords):
    """대분류 관련 컨텍스트를 벡터스토어에서 검색합니다."""
    global unified_vectorstore
    if unified_vectorstore is None:
        return "오류: 벡터스토어가 초기화되지 않았습니다."

    print(f"INFO: RAG 검색 실행 -> 제안서: '{proposal_file}', 대분류: '{category_keywords}'")
    
    # 대분류 관련 내용을 더 많이 가져옴
    results = unified_vectorstore.similarity_search(
        query=category_keywords,
        k=10,  # 더 많은 청크를 검색 (제한 제거)
        filter={"proposal_id": proposal_file}
    )
    
    if not results:
        return "관련 내용을 찾을 수 없습니다."
        
    # 모든 검색 결과를 포함 (길이 제한 제거)
    context = "\n\n---\n\n".join([doc.page_content for doc in results])
    
    print(f"INFO: 총 {len(results)}개 청크, {len(context)}자의 컨텍스트를 가져왔습니다.")
    
    return context

def load_evaluation_criteria_as_text(criteria_path):
    """평가 기준표를 텍스트 그대로 로드합니다 (파싱 없음)."""
    if not os.path.exists(criteria_path):
        print(f"WARNING: 평가 기준표 파일이 없습니다: {criteria_path}")
        return ""
    
    print(f"INFO: 평가 기준표 로딩: {criteria_path}")
    
    with open(criteria_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"INFO: 평가 기준표를 텍스트로 로드했습니다 ({len(content)} 자)")
    return content

def save_evaluation_report(proposal_name, report_content):
    """제안서별 평가 보고서를 파일로 저장합니다."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    proposal_base_name = os.path.splitext(proposal_name)[0]
    filename = f"{proposal_base_name}_evaluation_report_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("제안서 평가 보고서\n")
        f.write("="*80 + "\n")
        f.write(f"제안서명: {proposal_name}\n")
        f.write(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("="*80 + "\n")
        f.write("최종 평가 보고서\n")
        f.write("="*80 + "\n")
        f.write(report_content)
        f.write("\n\n" + "="*80 + "\n")
        f.write("보고서 끝\n")
        f.write("="*80 + "\n")
    
    print(f"[SAVED] 평가 보고서가 저장되었습니다: {filepath}")
    return filepath

# =================================================================
# LLM 모델 가져오기
# =================================================================

def get_llm_model():
    """환경변수에 따라 LLM 모델을 선택합니다."""
    global llm
    if llm is not None:
        return llm

    model_type = os.getenv('LLM_TYPE', 'local').lower()
    
    if model_type == 'local':
        model_name = os.getenv('LOCAL_MODEL_NAME', 'llama-blossom')
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        print(f"INFO: 로컬 LLM 사용 - 모델: {model_name}, URL: {base_url}")
        return LLM(model=f"ollama/{model_name}", base_url=base_url)
    
    elif model_type == 'huggingface':
        model_name = os.getenv('HF_MODEL_NAME', 'meta-llama/Meta-Llama-3-8B-Instruct')
        api_key = os.getenv('HUGGINGFACEHUB_API_TOKEN')
        if not api_key:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN 환경변수가 필요합니다.")
        print(f"INFO: HuggingFace LLM 사용 - 모델: {model_name}")
        return LLM(model=f"huggingface/{model_name}", api_key=api_key)
    
    else:
        raise ValueError(f"지원하지 않는 LLM 타입입니다: {model_type}")
    
    return llm

async def main():
    print("## LLM 주도형 동적 Agent 생성 및 평가 프로세스를 시작합니다.")
    
    # RAG 파이프라인 초기화
    global unified_vectorstore, company_map
    proposal_files = glob.glob(os.path.join(PROPOSAL_DIR, "*.html"))
    
    if not proposal_files or not os.path.exists(RFP_PATH):
        print("오류: 제안서 또는 RFP 파일이 없습니다. 경로를 확인하세요.")
        return
    
    # 회사명 매핑 테이블 생성
    company_map = {}
    for file_path in proposal_files:
        proposal_name = os.path.splitext(os.path.basename(file_path))[0]
        # 파일명에서 회사명 추출 (예: "A사_제안서" -> "A사")
        if "_" in proposal_name:
            company_name = proposal_name.split("_")[0]
        else:
            company_name = proposal_name
        company_map[proposal_name] = company_name
        print(f"INFO: 회사 매핑 - {proposal_name} -> {company_name}")
    

    # 벡터스토어 로드 또는 생성
    if os.path.exists(CHROMA_PERSIST_DIR):
        print(f"\n기존 벡터 DB를 '{CHROMA_PERSIST_DIR}' 경로에서 불러옵니다...")
        embedding_model = initialize_rag_components()
        unified_vectorstore = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embedding_model
        )
        print("✓ DB 로드 완료!")
    else:
        embedding_model = initialize_rag_components()
        unified_vectorstore = create_unified_vectorstore(
            proposal_files, RFP_PATH, embedding_model
        )

    # 평가 기준표를 텍스트 그대로 로드 (파싱 없음)
    evaluation_criteria_text = load_evaluation_criteria_as_text(EVALUATION_CRITERIA_PATH)
    
    if not evaluation_criteria_text:
        print("ERROR: 평가 기준표를 로드할 수 없습니다.")
        return
    
    # LLM 초기화
    llm = get_llm_model()

    # =================================================================
    # Phase 1: Dispatcher가 마크다운을 분석하여 최상위 대분류만 추출
    # =================================================================
    print("\n--- [Phase 1] LLM이 평가 기준표에서 최상위 대분류(카테고리)만 추출합니다 ---")
    
    dispatcher_agent = Agent(
        role="평가 기준표 구조 분석 전문가",
        goal="마크다운 형식의 평가 기준표에서 최상위 대분류(메인 카테고리)만 추출",
        backstory="""당신은 복잡한 문서의 계층 구조를 파악하는 전문가입니다.
        평가 기준표에서 가장 큰 분류 체계만을 정확히 식별할 수 있습니다.""",
        llm=llm,
        verbose=True
    )

    dispatcher_task = Task(
        description=f"""아래 마크다운 형식의 평가 기준표를 분석하여 **최상위 대분류(메인 카테고리)**만 추출해주세요.

[평가 기준표]:
```markdown
{evaluation_criteria_text}
```

위 평가 기준표에서:
1. 가장 큰 분류 체계(최상위 대분류)만 찾아주세요
2. 하위 세부 항목들은 무시하고, 큰 카테고리의 이름만 추출하세요
3. 예를 들어 "가격 평가", "기술력 평가", "프로젝트 수행 능력" 같은 메인 카테고리들입니다

다음 JSON 형식으로 반환하세요:
{{
  "categories": [
    {{
      "name": "대분류1 이름",
      "description": "이 대분류에 대한 간단한 설명"
    }},
    {{
      "name": "대분류2 이름", 
      "description": "이 대분류에 대한 간단한 설명"
    }}
  ]
}}

주의사항:
- '소계', '이계', '합계' 같은 것은 제외하세요
- 오직 최상위 대분류만 추출하세요 (보통 3-5개 정도)
- 반드시 유효한 JSON 형식으로 반환하세요
""",
        expected_output="최상위 대분류의 이름과 설명을 포함한 JSON 배열",
        agent=dispatcher_agent
    )

    dispatcher_crew = Crew(
        agents=[dispatcher_agent], 
        tasks=[dispatcher_task], 
        verbose=False,
        task_callback=partial(task_callback, company="Dispatcher")
    )
    categorization_result = dispatcher_crew.kickoff()
    
    try:
        raw_result = str(categorization_result.raw)
        # JSON 추출
        if "```json" in raw_result:
            start_idx = raw_result.find("```json") + 7
            end_idx = raw_result.find("```", start_idx)
            json_string = raw_result[start_idx:end_idx].strip()
        elif "```" in raw_result:
            start_idx = raw_result.find("```") + 3
            end_idx = raw_result.find("```", start_idx)
            json_string = raw_result[start_idx:end_idx].strip()
        else:
            start_idx = raw_result.find('{')
            end_idx = raw_result.rfind('}') + 1
            json_string = raw_result[start_idx:end_idx]
        
        categories_data = json.loads(json_string)
        main_categories = categories_data.get('categories', [])
        
        print(f"[SUCCESS] LLM이 추출한 최상위 대분류 ({len(main_categories)}개):")
        for cat in main_categories:
            print(f"  - {cat['name']}: {cat.get('description', 'N/A')}")
            
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] 대분류 추출 실패: {e}")
        print(f"   - 원본 결과: {categorization_result.raw}")
        return

    # =================================================================
    # Phase 2: 최상위 대분류별로만 Agent 생성 (1개 대분류 = 1개 Agent)
    # =================================================================
    print(f"\n--- [Phase 2] 추출된 {len(main_categories)}개 대분류별로 전문가 Agent를 생성합니다 ---")
    
    # 모든 제안서 파일에 대해 평가를 반복합니다.
    for proposal_path in proposal_files:
        proposal_name = os.path.basename(proposal_path)
        print(f"\n\n{'='*20} [{proposal_name}] 평가 시작 {'='*20}")

        specialist_agents = []
        evaluation_tasks = []

        # 각 최상위 대분류마다 1개의 Agent와 1개의 Task 생성
        for category in main_categories:
            category_name = category['name']
            category_desc = category.get('description', '')
            
            # 대분류 전문가 Agent 생성
            specialist_agent = Agent(
                role=f"'{category_name}' 부문 전문 평가관",
                goal=f"'{proposal_name}' 제안서의 '{category_name}' 부문을 간결하게 평가 (1000자 이내 필수)",
                backstory=f"""당신은 '{category_name}' 분야의 최고 전문가입니다.
                {category_desc}
                
                **중요**: 당신의 보고서는 다른 시스템에 입력되므로 반드시 1000자 이내로 작성해야 합니다.
                간결하고 핵심만 담은 평가가 요구됩니다.""",
                llm=llm,
                verbose=True
            )
            specialist_agents.append(specialist_agent)
            
            # 해당 대분류 관련 컨텍스트를 RAG에서 검색 (간결하게)
            context = get_context_for_category(
                os.path.splitext(proposal_name)[0],
                f"{category_name} {category_desc}"
            )
            
            # 컨텍스트가 너무 길면 요약 (토큰 절약)
            if len(context) > 2000:
                context = context[:2000] + "\n...(이하 생략)"
                print(f"  ⚠️ '{category_name}' 컨텍스트를 2000자로 제한")
            
            # 대분류 전체를 평가하는 단일 Task 생성
            task = Task(
                description=f"""제안서 '{proposal_name}'의 '{category_name}' 부문을 평가하세요.

**평가 대분류**: {category_name}

**제안서 핵심 내용**:
{context}

**🚨🚨🚨 절대 규칙: 전체 응답은 반드시 1000자 이내로 작성하세요! 🚨🚨🚨**

다음 형식으로 **극도로 간결하게** 작성:

# {category_name} 부문

**배점/취득**: Y점 / Z점 (X%)

**주요 항목** (2-3개만):
- 항목1 (배점): 점수 - 1줄 평가
- 항목2 (배점): 점수 - 1줄 평가

**강점**: (2개, 각 1줄)
- 
- 

**약점**: (2개, 각 1줄)
- 
- 

**개선안**: (1개, 1줄)
- 

**절대 규칙**:
- 1000자 초과 시 응답 무효
- 불필요한 문장 일체 금지
- 항목은 최대 3개만
- 각 설명은 1줄만
""",
                expected_output=f"'{category_name}' 부문 평가 (1000자 이내 필수)",
                agent=specialist_agent
            )
            evaluation_tasks.append(task)
        
        if not evaluation_tasks:
            print("평가할 작업이 없습니다.")
            continue

        print(f"\n총 {len(specialist_agents)}개의 전문가 Agent가 생성되었습니다.")
        print(f"총 {len(evaluation_tasks)}개의 평가 Task가 생성되었습니다.")

        # 현재 회사명으로 task_callback 생성
        current_company = company_map.get(proposal_name, "Unknown")
        current_task_callback = partial(task_callback, company=current_company)
        
        evaluation_crew = Crew(
            agents=specialist_agents,
            tasks=evaluation_tasks,
            verbose=False,
            task_callback=current_task_callback
        )
        final_results = await evaluation_crew.kickoff_async()

        print(f"\n--- [Phase 3] [{proposal_name}] 최종 보고서를 작성합니다 ---")
        
        # kickoff_async()는 튜플을 반환할 수 있으므로 처리
        if isinstance(final_results, tuple):
            results_list = final_results[0] if final_results else []
        else:
            results_list = final_results
        
        # 부문별 보고서를 수집하고 강제로 길이 제한
        individual_reports = []
        for idx, result in enumerate(results_list):
            if hasattr(result, 'raw'):
                report_text = str(result.raw)
            else:
                report_text = str(result)
            
            # 강제로 1000자 제한 (LLM이 무시한 경우 대비)
            if len(report_text) > 1000:
                report_text = report_text[:1000] + "\n...(길이 제한으로 절삭)"
                print(f"  ⚠️ 부문 {idx+1} 보고서가 1000자를 초과하여 강제 절삭")
            
            individual_reports.append(report_text)
        
        individual_reports_text = "\n\n".join(individual_reports)
        
        # 토큰 수 확인을 위한 출력
        print(f"INFO: 부문별 보고서 총 길이: {len(individual_reports_text)}자")
        
        # 그래도 너무 길면 추가 경고
        if len(individual_reports_text) > 4000:
            print(f"  ⚠️⚠️ 경고: 부문별 보고서 총합이 {len(individual_reports_text)}자로 여전히 깁니다!")
            print(f"  → 각 부문을 500자로 추가 제한합니다.")
            individual_reports = [report[:500] + "..." for report in individual_reports]
        individual_reports_text = "\n\n".join(individual_reports)
        print(f"  → 최종 길이: {len(individual_reports_text)}자")

        reporting_agent = Agent(
            role="수석 평가 분석가",
            goal="부문별 평가를 종합하여 경영진이 의사결정에 활용할 수 있는 완성된 최종 보고서 작성",
            backstory="""당신은 20년 경력의 수석 분석가로, 핵심을 파악하고 전략적 인사이트를 
            제공하는 능력이 뛰어나며, 의사결정자들이 신뢰하는 분석가입니다.""",
            llm=get_llm_model(), 
            verbose=True
        )

        reporting_task = Task(
            description=f"""'{proposal_name}' 제안서에 대한 부문별 평가를 종합하여 
최종 평가 보고서를 작성하세요.

**부문별 평가 보고서들**:
{individual_reports_text}

**🚨 중요: 최종 보고서는 2000자 이내로 간결하게 작성하세요!**

다음 구조로 작성하세요:

# 제안서 평가 최종 보고서

## 1. Executive Summary (5줄 이내)
- 제안서: {proposal_name}
- 평가일: {datetime.now().strftime('%Y-%m-%d')}
- 총점: X/100점
- 등급: S/A/B/C/D
- 핵심 평가: (2줄 요약)

## 2. 부문별 결과 (표 형식)
| 부문 | 배점 | 취득 | 비율 | 평가 |
|------|------|------|------|------|
| 부문1 | XX | YY | ZZ% | 1줄 평가 |
| ... |
| 총점 | 100 | 총합 | 평균 | - |

## 3. 주요 발견사항
**강점 Top 3** (각 1줄):
1. 
2. 
3. 

**약점 Top 3** (각 1줄):
1. 
2. 
3. 

## 4. 권고사항
**우선 개선** (2개, 각 1줄):
- 
- 

**강점 유지** (2개, 각 1줄):
- 
- 

## 5. 최종 결론 (3줄 이내)
- 종합 의견:
- 선정 권고: (선정 추천/조건부/탈락)
- 근거:

**작성 규칙**:
- 전체 2000자 이내 엄수
- 표와 리스트 활용하여 간결하게
- 중복 내용 제거
- 핵심만 포함
""",
            expected_output="경영진 의사결정용 간결한 최종 평가 보고서 (2000자 이내)",
            agent=reporting_agent
        )
        
        # 현재 회사명으로 task_callback 생성
        current_company = company_map.get(proposal_name, "Unknown")
        current_task_callback = partial(task_callback, company=current_company)
        
        reporting_crew = Crew(
            agents=[reporting_agent], 
            tasks=[reporting_task], 
            verbose=False,
            task_callback=current_task_callback
        )
        final_comprehensive_report = reporting_crew.kickoff()

        print(f"\n\n[FINAL REPORT] [{proposal_name}] 최종 종합 평가 보고서")
        print("="*80)
        print(final_comprehensive_report.raw)
        print("="*80)
        
        # 평가 보고서를 파일로 저장
        save_evaluation_report(proposal_name, final_comprehensive_report.raw)


# =================================================================
# 6. 기업별 Trace 저장 함수
# =================================================================

def save_task_trace(company: str, task_info: dict):
    """기업별로 task trace를 저장합니다."""
    trace_dir = os.path.join("traces", company)
    os.makedirs(trace_dir, exist_ok=True)
    filepath = os.path.join(trace_dir, "task_log.ndjson")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(task_info, ensure_ascii=False) + "\n")

def task_callback(task_output, company="Unknown"):
    """각 작업 완료 시 결과를 로깅하는 콜백 (기업별 저장)"""
    global company_map
    
    task_info = {
        "type": "task_completed",
        "task_name": getattr(task_output, "name", None),
        "agent": str(getattr(task_output, "agent", None)),
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    # 기업별 trace 저장
    save_task_trace(company, task_info)

# =================================================================
# 7. 챗봇 관련 함수들 (main_jy.py에서 가져옴)
# =================================================================
def normalize_company_name(extracted: str) -> str:   ### 🔧 FIX: 중복 정의 제거 후 최종 버전
    """추출된 회사명을 proposal_id로 변환, 없으면 all"""
    if not extracted or extracted=="all":
        return "all"
    extracted_clean = extracted.replace(" ","")
    for pid, cname in company_map.items():
        if extracted_clean in cname.replace(" ",""):
            return pid
    return "all"


def classify_question(user_question: str) -> dict:
    router_agent = Agent(
        role="질문 분류 전문가",
        goal="사용자 질문을 정확히 분류하여 intent (회사 내부 정보, 평가 관련, 일반 질문) 결정, 회사명 추출출",
        backstory="당신은 질문을 분석하여 정확한 카테고리로 분류하는 전문가입니다. 회사 내부 정보, 평가 관련, 일반 질문을 정확히 구분할 수 있습니다.",
        llm=get_llm_model(),
        verbose=True
    )
    router_task = Task(
        description=f"""
다음 질문을 분석하여 정확한 카테고리로 분류하세요:

질문: "{user_question}"

분류 기준:
1. "company_db": 회사 내부 정보 (부서, 기술스택, 담당자, 조직도 등)
2. "evaluation": 제안서 평가 관련 (점수, 근거, 보고서, 평가 결과 등)
3. "other": 위 두 가지에 해당하지 않는 일반 질문

회사명 추출:
- 평가 관련 질문에서 회사명이 언급되면 추출
- 없으면 "all"

반드시 다음 JSON 형식으로만 답변하세요:
{{
  "intent": "company_db",
  "company": "A사"
}}
        """,
        expected_output="JSON 객체 (intent와 company 키 포함)",
        agent=router_agent
    )
    crew = Crew(agents=[router_agent],tasks=[router_task],verbose=False)
    result = crew.kickoff()
    try:
        # JSON 추출 및 파싱
        raw_text = str(result.raw)
        if "```json" in raw_text:
            start = raw_text.find("```json") + 7
            end = raw_text.find("```", start)
            json_text = raw_text[start:end].strip()
        elif "```" in raw_text:
            start = raw_text.find("```") + 3
            end = raw_text.find("```", start)
            json_text = raw_text[start:end].strip()
        else:
            start = raw_text.find('{')
            end = raw_text.rfind('}') + 1
            json_text = raw_text[start:end]
        
        parsed = json.loads(json_text)
        return parsed
    except Exception as e:
        print(f"JSON 파싱 오류: {e}")
        return {"intent":"other","company":"all"}


def search_company_db(user_question: str) -> str:
    """벡터스토어에서 사내 정보를 검색하여 답변합니다."""
    global unified_vectorstore

    if unified_vectorstore is None:
        return "오류: 벡터스토어가 초기화되지 않았습니다. 먼저 평가를 실행해주세요."

    # 벡터스토어에서 사내 정보 검색 (사내_로 시작하는 proposal_id 필터링)
    try:
        # 모든 사내 정보 타입에서 검색
        all_results = []
        internal_types = ["사내_기술스택", "사내_담당자", "사내_마이그레이션", "사내_장애이력", "사내_기타"]

        for doc_type in internal_types:
            results = unified_vectorstore.similarity_search(
                query=user_question,
                k=3,
                filter={"proposal_id": f"internal_{doc_type}"}
            )
            all_results.extend(results)

        if not all_results:
            return "관련된 사내 정보를 찾을 수 없습니다."

        # 검색 결과를 컨텍스트로 변환
        context = "\n\n".join([doc.page_content for doc in all_results[:5]])  # 상위 5개만 사용

        prompt = f"""
사용자 질문: "{user_question}"

회사 내부 정보:
{context}

위 정보를 바탕으로 정확하고 도움이 되는 답변을 해주세요.
- 구체적인 정보를 명시하세요
- 간결하고 명확하게 답변하세요
- 관련 없는 정보는 제외하세요
"""
        return get_llm_model().call(prompt)

    except Exception as e:
        return f"사내 정보 검색 중 오류 발생: {e}"

# ================================================================
# Evaluation 질문 처리
# ================================================================
def load_evaluation_trace(company: str):
    filepath = os.path.join("traces", company, "task_log.ndjson")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def answer_evaluation_question(user_question: str, company="all") -> str:
    if company == "all":
        companies = list(company_map.keys())
    else:
        companies = [company]
    
    context = ""
    for comp in companies:
        traces = load_evaluation_trace(comp)
        for t in traces[:5]:
            task_name = t.get('task_name', 'Unknown')
            status = t.get('status', 'Unknown')
            context += f"- {task_name}: {status}\n"
    
    if not context:
        return f"현재 {company} 회사의 평가 데이터가 없습니다. 먼저 제안서 평가를 실행해주세요."
    
    prompt = f"""
사용자 질문: "{user_question}"

평가 기록 데이터:
{context}

위 평가 기록을 바탕으로 정확하고 도움이 되는 답변을 해주세요.
- 실제 평가 결과를 인용하여 답변하세요
- 구체적인 점수나 근거가 있다면 명시하세요
- 간결하고 명확하게 답변하세요
"""
    return get_llm_model().call(prompt)

def answer_general_question(user_question: str) -> str:
    prompt = f"""
사용자 질문: "{user_question}"

위 질문에 대해 정확하고 도움이 되는 답변을 해주세요.
- 간결하고 명확하게 답변하세요
- 관련 없는 정보는 제외하세요
- 정확한 정보를 제공하세요
"""
    return get_llm_model().call(prompt)


def run_main():
    """동기적으로 main 함수를 실행합니다."""
    asyncio.run(main())

def run_chatbot_test():
    print("================================")
    print("ChatBot 테스트")
    print("================================")
    test_questions = [
        "우리 회사에서 Kafka 쓰는 부서가 있어?",
        "왜 A사의 기술 점수는 8점이야?", 
        "오늘 날씨 어때?",
        "개발팀에서 뭐 쓰고 있어?",
        "React 사용하는 팀이 어디야?",
        "A사의 기술 점수 근거를 알려줘",
    ]
    
    for q in test_questions:
        result = classify_question(q)
        intent, company = result.get("intent"), result.get("company", "all")
        print(f"\nQ: {q}\n분류: {result}")
        if intent == "company_db":
            print("A:", search_company_db(q))
        elif intent == "evaluation":
            comp_id = normalize_company_name(company)
            print("A:", answer_evaluation_question(q, comp_id))
        else:
            print("A:", answer_general_question(q))

if __name__ == '__main__':
    run_main()
    run_chatbot_test()