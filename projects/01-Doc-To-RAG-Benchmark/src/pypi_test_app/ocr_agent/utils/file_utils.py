"""
파일 유틸리티
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from .. import config


def load_pages_text(jsonl_path: str) -> List[Dict]:
    """
    pages_text.jsonl 파일 로드
    
    Args:
        jsonl_path: JSONL 파일 경로
        
    Returns:
        페이지 데이터 리스트
    """
    
    pages = []
    
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    page = json.loads(line)
                    pages.append(page)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {jsonl_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parsing error: {str(e)}")
        return []
    
    return pages


def save_pages_text(pages: List[Dict], output_path: str) -> None:
    """
    pages_text.jsonl 파일 저장
    
    Args:
        pages: 페이지 데이터 리스트
        output_path: 출력 파일 경로
    """
    
    # 디렉토리 생성
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for page in pages:
            f.write(json.dumps(page, ensure_ascii=False) + '\n')


def save_error_log(state: Dict[str, Any]) -> None:
    """
    에러 로그 저장
    
    Args:
        state: 문서 상태
    """
    
    if not state.get("error_log"):
        return
    
    log_path = config.REPORTS_DIR / f"{state['document_name']}_error_log.json"
    
    error_data = {
        "document_name": state["document_name"],
        "document_path": state["document_path"],
        "timestamp": datetime.now().isoformat(),
        "errors": state["error_log"]
    }
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, ensure_ascii=False, indent=2)
    
    print(f"[LOG] Error log saved: {log_path}")


def ensure_directories() -> None:
    """필요한 모든 디렉토리 생성"""
    
    directories = [
        config.INPUT_DIR,
        config.OUTPUT_DIR,
        config.TEMP_DIR,
        config.REPORTS_DIR,
        config.TABLES_DIR,
        config.EXTRACTED_DIR,
        config.VALIDATED_DIR,
        config.JUDGED_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_input_files(input_path: str = None) -> List[Path]:
    """
    입력 파일 목록 가져오기
    
    Args:
        input_path: 입력 경로 (파일 또는 디렉토리)
        
    Returns:
        PDF/HWP 파일 경로 리스트
    """
    
    if input_path:
        path = Path(input_path)
    else:
        path = config.INPUT_DIR
    
    files = []
    
    if path.is_file():
        # 단일 파일
        if path.suffix in config.SUPPORTED_FORMATS:
            files.append(path)
    elif path.is_dir():
        # 디렉토리
        for ext in config.SUPPORTED_FORMATS:
            files.extend(path.glob(f"*{ext}"))
    
    return sorted(files)


def cleanup_temp_files(keep_latest: int = 5) -> None:
    """
    임시 파일 정리
    
    Args:
        keep_latest: 최근 N개 보관
    """
    
    # 각 임시 디렉토리의 오래된 파일 삭제
    temp_dirs = [config.EXTRACTED_DIR, config.VALIDATED_DIR, config.JUDGED_DIR]
    
    for temp_dir in temp_dirs:
        if not temp_dir.exists():
            continue
        
        # 하위 디렉토리들 (문서별)
        subdirs = sorted(
            [d for d in temp_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True
        )
        
        # 오래된 것들 삭제
        for old_dir in subdirs[keep_latest:]:
            try:
                import shutil
                shutil.rmtree(old_dir)
                print(f"[DELETE] Removed: {old_dir}")
            except Exception as e:
                print(f"[WARNING] Delete failed: {old_dir} - {str(e)}")


if __name__ == "__main__":
    # 테스트
    ensure_directories()
    print("[OK] Directories created")
    
    input_files = get_input_files()
    print(f"[INFO] Input files: {len(input_files)} files")

