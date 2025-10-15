#!/usr/bin/env python3
"""
Daily Briefing 환경변수 설정 도우미

이 스크립트는 Gmail, Slack, Notion 설정을 쉽게 할 수 있도록 도와줍니다:
1. 필요한 설정 페이지를 브라우저에서 자동으로 엽니다
2. 사용자 입력을 받아 .env 파일을 생성합니다
3. 입력값을 검증합니다
"""

import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional

# 색상 출력을 위한 ANSI 코드
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}\n")

def print_step(step: int, text: str):
    print(f"{Colors.BOLD}{Colors.GREEN}[단계 {step}]{Colors.ENDC} {text}")

def print_info(text: str):
    print(f"{Colors.CYAN}i{Colors.ENDC} {text}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}!{Colors.ENDC} {text}")

def print_error(text: str):
    print(f"{Colors.RED}x{Colors.ENDC} {text}")

def print_success(text: str):
    print(f"{Colors.GREEN}v{Colors.ENDC} {text}")

def get_input(prompt: str, default: str = "", required: bool = True) -> str:
    """사용자 입력을 받습니다."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        value = input(full_prompt).strip()
        
        if not value and default:
            return default
        
        if not value and required:
            print_error("이 값은 필수입니다. 다시 입력해주세요.")
            continue
        
        return value

def open_browser(url: str, description: str):
    """브라우저에서 URL을 엽니다."""
    print_info(f"{description} 페이지를 브라우저에서 엽니다...")
    print_info(f"URL: {url}")
    try:
        webbrowser.open(url)
        print_success("브라우저가 열렸습니다.")
    except Exception as e:
        print_warning(f"브라우저를 자동으로 열 수 없습니다: {e}")
        print_info(f"수동으로 다음 URL을 열어주세요: {url}")

def setup_llm_provider() -> dict:
    """LLM Provider 설정"""
    print_header("1. LLM Provider 설정")
    
    print("Daily Briefing에 사용할 LLM을 선택하세요:")
    print("  1) upstage - Upstage Solar (한국어 최적화, 클라우드)")
    print("  2) llama   - Meta LLaMA (로컬, 무료)")
    print("  3) openai  - OpenAI GPT (범용, 클라우드)")
    
    choice = get_input("선택 (1-3)", "1", required=True)
    
    config = {}
    
    if choice == "1":
        config["LLM_PROVIDER"] = "upstage"
        print_info("\nUpstage API Key가 필요합니다.")
        print_info("API Key 발급: https://console.upstage.ai/")
        
        if get_input("브라우저에서 페이지를 열까요? (y/n)", "y").lower() == "y":
            open_browser("https://console.upstage.ai/", "Upstage Console")
        
        config["UPSTAGE_API_KEY"] = get_input("Upstage API Key (up-로 시작)", required=True)
        config["UPSTAGE_MODEL"] = get_input("모델 이름", "solar-pro2", required=False)
        config["UPSTAGE_BASE_URL"] = get_input("Base URL", "https://api.upstage.ai/v1/solar", required=False)
        
    elif choice == "2":
        config["LLM_PROVIDER"] = "llama"
        config["LLAMA_MODEL_PATH"] = get_input("LLaMA 모델 경로", "meta-llama/Llama-3.2-3B-Instruct", required=False)
        print_success("LLaMA는 첫 실행 시 자동으로 다운로드됩니다.")
        
    elif choice == "3":
        config["LLM_PROVIDER"] = "openai"
        print_info("\nOpenAI API Key가 필요합니다.")
        print_info("API Key 발급: https://platform.openai.com/api-keys")
        
        if get_input("브라우저에서 페이지를 열까요? (y/n)", "y").lower() == "y":
            open_browser("https://platform.openai.com/api-keys", "OpenAI API Keys")
        
        config["OPENAI_API_KEY"] = get_input("OpenAI API Key (sk-로 시작)", required=True)
        config["OPENAI_MODEL"] = get_input("모델 이름", "gpt-4-turbo-preview", required=False)
    
    print_success("LLM Provider 설정 완료!\n")
    return config
def setup_gmail() -> dict:
    """Gmail 설정 - 상세 가이드"""
    print_header("2. Gmail 설정")
    
    print("Gmail OAuth 인증이 필요합니다.")
    print_info("Google Cloud Console에서 OAuth 클라이언트 ID를 생성해야 합니다.")
    
    if get_input("\nGmail 설정을 진행할까요? (y/n)", "y").lower() != "y":
        print_warning("Gmail 설정을 건너뜁니다.")
        return {}
    
    print("\n" + "="*70)
    print("Gmail OAuth 설정 단계별 가이드")
    print("="*70)
    
    print("\n[1단계] Google Cloud 프로젝트 생성")
    print("  1. Google Cloud Console 접속")
    print("  2. 상단의 프로젝트 선택 드롭다운 클릭")
    print("  3. 'NEW PROJECT' 클릭")
    print("  4. 프로젝트 이름 입력 (예: my-daily-briefing)")
    print("  5. 'CREATE' 클릭")
    
    if get_input("\n프로젝트 생성 페이지를 열까요? (y/n)", "y").lower() == "y":
        open_browser("https://console.cloud.google.com/projectcreate", "Google Cloud Project Create")
        print_info("프로젝트를 생성하고 Enter를 누르세요...")
        input()
    
    print("\n[2단계] Gmail API 활성화")
    print("  1. 좌측 메뉴 -> 'APIs & Services' -> 'Library'")
    print("  2. 검색창에 'Gmail API' 입력")
    print("  3. 'Gmail API' 클릭")
    print("  4. 'ENABLE' 버튼 클릭")
    
    if get_input("\nGmail API 활성화 페이지를 열까요? (y/n)", "y").lower() == "y":
        open_browser("https://console.cloud.google.com/apis/library/gmail.googleapis.com", "Gmail API Library")
        print_info("Gmail API를 활성화하고 Enter를 누르세요...")
        input()
    
    print("\n[3단계] OAuth 동의 화면 설정")
    print("  1. 'APIs & Services' -> 'OAuth consent screen'")
    print("  2. User Type: 'External' 선택")
    print("  3. 'CREATE' 클릭")
    print("  4. App name 입력 (예: My Daily Briefing)")
    print("  5. User support email: 본인 이메일 선택")
    print("  6. Developer contact: 본인 이메일 입력")
    print("  7. 'SAVE AND CONTINUE' 클릭")
    print("  8. Scopes 단계: 'SAVE AND CONTINUE' 클릭 (기본값 사용)")
    print("  9. Test users 단계: 'SAVE AND CONTINUE' 클릭")
    
    if get_input("\nOAuth 동의 화면 설정 페이지를 열까요? (y/n)", "y").lower() == "y":
        open_browser("https://console.cloud.google.com/apis/credentials/consent", "OAuth Consent Screen")
        print_info("OAuth 동의 화면을 설정하고 Enter를 누르세요...")
        input()
    
    print("\n[4단계] OAuth 클라이언트 ID 생성")
    print("  1. 'APIs & Services' -> 'Credentials'")
    print("  2. 상단의 '+ CREATE CREDENTIALS' 클릭")
    print("  3. 'OAuth client ID' 선택")
    print("  4. Application type: 'Desktop app' 선택")
    print("  5. Name 입력 (예: Daily Briefing Desktop)")
    print("  6. 'CREATE' 클릭")
    
    if get_input("\nCredentials 생성 페이지를 열까요? (y/n)", "y").lower() == "y":
        open_browser("https://console.cloud.google.com/apis/credentials", "Google Cloud Credentials")
        print_info("OAuth 클라이언트 ID를 생성하고 Enter를 누르세요...")
        input()
    
    print("\n[5단계] credentials.json 다운로드")
    print("  1. 생성된 OAuth 클라이언트 ID 우측의 다운로드 아이콘 클릭")
    print("  2. JSON 파일 다운로드")
    print("  3. 다운로드한 JSON 파일 경로를 다음 단계에서 입력")
    
    print_warning("\n중요: credentials.json은 절대 Git에 커밋하지 마세요!")
    
    config = {}
    
    print("\n" + "="*70)
    cred_path = get_input("\n다운로드한 JSON 파일의 전체 경로를 입력하세요", required=False)
    
    if cred_path:
        # Windows 경로 처리
        cred_path = cred_path.replace("\\", "/").strip('"').strip("'")
        
        # 파일 존재 확인
        if not Path(cred_path).exists():
            print_error(f"파일을 찾을 수 없습니다: {cred_path}")
            print_warning("경로를 확인하고 다시 실행하세요.")
            return {}
        
        # Gmail MCP 서버를 위한 디렉토리 생성 및 파일 복사
        import shutil
        gmail_mcp_dir = Path.home() / ".gmail-mcp"
        gmail_mcp_dir.mkdir(exist_ok=True)
        
        oauth_keys_path = gmail_mcp_dir / "gcp-oauth.keys.json"
        shutil.copy2(cred_path, oauth_keys_path)
        
        print_success(f"Gmail MCP 디렉토리 생성: {gmail_mcp_dir}")
        print_success(f"인증 파일 복사: {oauth_keys_path}")
        
        # .env 파일에는 원본 경로 저장 (호환성 유지)
        config["GMAIL_CREDENTIALS"] = str(oauth_keys_path)
        config["GMAIL_TOKEN_PATH"] = str(gmail_mcp_dir / "token.json")
        
        # OAuth 인증 수행
        print("\n" + "="*70)
        print("OAuth 인증 수행")
        print("="*70)
        
        if get_input("\n지금 OAuth 인증을 진행할까요? (y/n)", "y").lower() == "y":
            import subprocess
            print_info("OAuth 인증을 시작합니다...")
            print_info("브라우저가 열리면 Google 계정으로 로그인하고 권한을 승인하세요.")
            
            try:
                result = subprocess.run(
                    ["npx", "-y", "@gongrzhe/server-gmail-autoauth-mcp", "auth"],
                    capture_output=False,
                    text=True
                )
                
                if result.returncode == 0:
                    print_success("OAuth 인증이 완료되었습니다!")
                    credentials_json = gmail_mcp_dir / "credentials.json"
                    if credentials_json.exists():
                        print_success(f"인증 토큰 저장됨: {credentials_json}")
                else:
                    print_error("OAuth 인증에 실패했습니다.")
                    print_info("나중에 수동으로 다음 명령어를 실행하세요:")
                    print_info("  npx -y @gongrzhe/server-gmail-autoauth-mcp auth")
            except FileNotFoundError:
                print_error("npx를 찾을 수 없습니다. Node.js가 설치되어 있는지 확인하세요.")
                print_info("Node.js 설치 후 다음 명령어를 실행하세요:")
                print_info("  npx -y @gongrzhe/server-gmail-autoauth-mcp auth")
            except Exception as e:
                print_error(f"인증 중 오류 발생: {e}")
                print_info("나중에 수동으로 다음 명령어를 실행하세요:")
                print_info("  npx -y @gongrzhe/server-gmail-autoauth-mcp auth")
        else:
            print_info("나중에 다음 명령어로 OAuth 인증을 수행하세요:")
            print_info("  npx -y @gongrzhe/server-gmail-autoauth-mcp auth")
    else:
        print_warning("Gmail 설정을 나중에 수동으로 완료하세요.")
    
    return config

def setup_slack() -> dict:
    """Slack 설정"""
    print_header("3. Slack 설정")
    
    print("Slack User Token이 필요합니다.")
    print_info("Slack App을 생성하고 User Token (xoxp-)을 발급받아야 합니다.")
    
    if get_input("\nSlack 설정을 진행할까요? (y/n)", "y").lower() != "y":
        print_warning("Slack 설정을 건너뜁니다.")
        return {}
    
    print("\n[Slack App 생성 방법]")
    print("1. Slack API 페이지 접속")
    print("2. 'Create New App' -> 'From scratch'")
    print("3. OAuth & Permissions에서 User Token Scopes 추가:")
    print("   - channels:history, channels:read")
    print("   - groups:history, im:history")
    print("   - search:read, users:read")
    print("4. 'Install to Workspace' 클릭")
    print("5. User OAuth Token (xoxp-로 시작) 복사")
    
    if get_input("\nSlack API 페이지를 열까요? (y/n)", "y").lower() == "y":
        open_browser("https://api.slack.com/apps", "Slack API Apps")
    
    config = {}
    token = get_input("\nSlack User Token (xoxp-로 시작)", required=False)
    
    if token:
        if not token.startswith("xoxp-"):
            print_warning("User Token은 'xoxp-'로 시작해야 합니다.")
            print_warning("Bot Token (xoxb-)은 사용할 수 없습니다.")
        else:
            config["SLACK_MCP_XOXP_TOKEN"] = token
            print_success("Slack Token 설정 완료!")
    
    return config
def setup_notion() -> dict:
    """Notion 설정"""
    print_header("4. Notion 설정")
    
    print("Notion Integration이 필요합니다.")
    print_info("Integration을 생성하고 Token을 발급받아야 합니다.")
    
    if get_input("\nNotion 설정을 진행할까요? (y/n)", "y").lower() != "y":
        print_warning("Notion 설정을 건너뜁니다.")
        return {}
    
    print("\n[Notion Integration 생성 방법]")
    print("1. Notion Integrations 페이지 접속")
    print("2. New integration 클릭")
    print("3. Integration Token (secret_로 시작) 복사")
    print("4. Notion 페이지/데이터베이스에 Integration 연결")
    
    if get_input("\nNotion Integrations 페이지를 열까요? (y/n)", "y").lower() == "y":
        open_browser("https://www.notion.so/my-integrations", "Notion Integrations")
    
    config = {}
    
    api_key = get_input("\nNotion Integration Token (secret_로 시작)", required=False)
    if api_key:
        config["NOTION_API_KEY"] = api_key
        print_success("Notion API Key 설정 완료!")
        
        print("\n[페이지 ID 찾는 방법]")
        print("Notion 페이지 URL에서 ID를 찾을 수 있습니다:")
        print("https://notion.so/workspace/페이지제목-{이부분이ID}?v=...")
        
        parent_page = get_input("Daily Briefing을 생성할 부모 페이지 ID", required=False)
        if parent_page:
            if "notion.so" in parent_page:
                parts = parent_page.split("/")[-1].split("-")
                if len(parts) > 0:
                    parent_page = parts[-1].split("?")[0]
            config["NOTION_PARENT_PAGE_ID"] = parent_page
            print_success(f"부모 페이지 ID: {parent_page}")
        
        database_id = get_input("Tasks 데이터베이스 ID (선택사항)", required=False)
        if database_id:
            if "notion.so" in database_id:
                parts = database_id.split("/")[-1].split("-")
                if len(parts) > 0:
                    database_id = parts[-1].split("?")[0]
            config["NOTION_DATABASE_ID"] = database_id
            print_success(f"데이터베이스 ID: {database_id}")
    
    return config

def generate_env_file(config: dict, env_path: Path):
    """환경변수 파일 생성"""
    print_header("5. .env 파일 생성")
    
    if env_path.exists():
        backup_path = env_path.with_suffix(".env.backup")
        print_warning(f"기존 .env 파일을 {backup_path.name}으로 백업합니다.")
        env_path.rename(backup_path)
    
    lines = [
        "# ===========================================",
        "# AI Agent Orchestrator - 환경 변수",
        "# 자동 생성됨 (setup_env.py)",
        "# ===========================================\n",
    ]
    
    lines.extend([
        "# LLM Provider 설정",
        f"LLM_PROVIDER={config.get('LLM_PROVIDER', 'llama')}\n",
    ])
    
    if config.get("UPSTAGE_API_KEY"):
        lines.append(f"UPSTAGE_API_KEY={config['UPSTAGE_API_KEY']}")
        lines.append(f"UPSTAGE_MODEL={config.get('UPSTAGE_MODEL', 'solar-pro2')}")
        lines.append(f"UPSTAGE_BASE_URL={config.get('UPSTAGE_BASE_URL', 'https://api.upstage.ai/v1/solar')}\n")
    
    if config.get("LLAMA_MODEL_PATH"):
        lines.append(f"LLAMA_MODEL_PATH={config['LLAMA_MODEL_PATH']}\n")
    
    if config.get("OPENAI_API_KEY"):
        lines.append(f"OPENAI_API_KEY={config['OPENAI_API_KEY']}")
        lines.append(f"OPENAI_MODEL={config.get('OPENAI_MODEL', 'gpt-4-turbo-preview')}\n")
    
    if config.get("GMAIL_CREDENTIALS"):
        lines.extend([
            "# Gmail 설정",
            f"GMAIL_CREDENTIALS={config['GMAIL_CREDENTIALS']}",
            f"GMAIL_TOKEN_PATH={config['GMAIL_TOKEN_PATH']}\n",
        ])
    
    if config.get("SLACK_MCP_XOXP_TOKEN"):
        lines.extend([
            "# Slack 설정",
            f"SLACK_MCP_XOXP_TOKEN={config['SLACK_MCP_XOXP_TOKEN']}\n",
        ])
    
    if config.get("NOTION_API_KEY"):
        lines.append("# Notion 설정")
        lines.append(f"NOTION_API_KEY={config['NOTION_API_KEY']}")
        if config.get("NOTION_PARENT_PAGE_ID"):
            lines.append(f"NOTION_PARENT_PAGE_ID={config['NOTION_PARENT_PAGE_ID']}")
        if config.get("NOTION_DATABASE_ID"):
            lines.append(f"NOTION_DATABASE_ID={config['NOTION_DATABASE_ID']}")
        lines.append("")
    
    env_path.write_text("\n".join(lines), encoding="utf-8")
    
    print_success(f".env 파일이 생성되었습니다: {env_path}")
    print_info(f"총 {len([k for k in config.keys() if config[k]])}개의 환경변수가 설정되었습니다.")

def main():
    """메인 함수"""
    print_header("Daily Briefing 환경변수 설정 도우미")
    
    print("이 스크립트는 Daily Briefing에 필요한 환경변수를 설정합니다.")
    print_info("각 단계에서 브라우저가 자동으로 열립니다.")
    print_warning("보안상의 이유로 Token/Key는 직접 발급받아야 합니다.\n")
    
    if get_input("계속 진행할까요? (y/n)", "y").lower() != "y":
        print("설정을 취소합니다.")
        return
    
    config = {}
    config.update(setup_llm_provider())
    config.update(setup_gmail())
    config.update(setup_slack())
    config.update(setup_notion())
    
    env_path = Path(__file__).parent.parent / ".env"
    generate_env_file(config, env_path)
    
    print_header("설정 완료!")
    
    print("다음 단계:")
    print("  1. Gmail OAuth 인증 (설정한 경우):")
    print("     npx -y @gongrzhe/server-gmail-autoauth-mcp auth")
    print()
    print("  2. Daily Briefing 데이터 수집 테스트:")
    print("     uv run python mcp_server/daily_briefing_collector.py")
    print()
    print("  3. Backoffice에서 수동 실행:")
    print("     http://localhost:8003")
    print()
    
    print_success("설정이 완료되었습니다!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n설정을 취소합니다.")
        sys.exit(0)
    except Exception as e:
        print_error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)