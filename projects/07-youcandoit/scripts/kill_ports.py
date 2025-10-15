#!/usr/bin/env python3
"""
특정 포트를 사용하는 프로세스를 종료하는 Python 스크립트
사용법: python kill_ports.py
"""

import subprocess
import sys
import re
from typing import List, Tuple, Optional


def find_process_by_port_windows(port: int) -> List[Tuple[int, str]]:
    """
    Windows에서 특정 포트를 사용하는 프로세스 찾기
    
    Args:
        port: 검색할 포트 번호
        
    Returns:
        (PID, 프로세스명) 튜플의 리스트
    """
    try:
        # netstat으로 포트를 사용하는 프로세스의 PID 찾기
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=True
        )
        
        processes = []
        for line in result.stdout.split('\n'):
            # LISTENING 상태이고 해당 포트를 사용하는 라인만 확인
            if f':{port}' in line and 'LISTENING' in line:
                # PID는 마지막 컬럼
                parts = line.strip().split()
                if parts:
                    pid_str = parts[-1]
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        # 프로세스 이름 가져오기
                        process_name = get_process_name(pid)
                        if process_name:
                            processes.append((pid, process_name))
        
        return processes
    
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] netstat 실행 실패: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] 포트 {port} 검색 중 오류: {e}")
        return []


def get_process_name(pid: int) -> Optional[str]:
    """
    PID로 프로세스 이름 가져오기
    
    Args:
        pid: 프로세스 ID
        
    Returns:
        프로세스 이름 또는 None
    """
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/NH', '/FO', 'CSV'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # CSV 형식에서 프로세스 이름 추출
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            # 첫 번째 필드(프로세스 이름)를 따옴표 제거하고 반환
            parts = lines[0].split(',')
            if parts:
                return parts[0].strip('"')
        
        return None
    
    except Exception:
        return None


def kill_process(pid: int, process_name: str) -> bool:
    """
    프로세스를 강제 종료
    
    Args:
        pid: 프로세스 ID
        process_name: 프로세스 이름 (로깅용)
        
    Returns:
        성공 여부
    """
    try:
        subprocess.run(
            ['taskkill', '/PID', str(pid), '/F'],
            capture_output=True,
            check=True
        )
        print(f"  >> [SUCCESS] 종료 완료: '{process_name}' (PID: {pid})")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"  >> [ERROR] 종료 실패: PID {pid} - {e}")
        return False


def main():
    """메인 함수"""
    # 종료할 포트 목록
    ports = [8001, 8002, 8003]
    
    print("=" * 50)
    print("포트 프로세스 종료 스크립트 (Python)")
    print("=" * 50)
    print()
    
    # Windows 여부 확인
    if sys.platform != 'win32':
        print("[ERROR] 이 스크립트는 Windows 전용입니다.")
        print("Linux/macOS에서는 psutil 버전을 사용하세요: kill_ports_psutil.py")
        sys.exit(1)
    
    total_killed = 0
    
    for port in ports:
        print(f"[INFO] 포트 {port} 확인 중...")
        
        processes = find_process_by_port_windows(port)
        
        if not processes:
            print(f"  >> 포트 {port}을(를) 사용하는 프로세스가 없습니다.")
        else:
            for pid, process_name in processes:
                print(f"  >> [FOUND] 프로세스 '{process_name}' (PID: {pid})")
                if kill_process(pid, process_name):
                    total_killed += 1
        
        print()
    
    print("=" * 50)
    print(f"[DONE] 작업 완료: 총 {total_killed}개 프로세스 종료")
    print("=" * 50)


if __name__ == "__main__":
    main()
