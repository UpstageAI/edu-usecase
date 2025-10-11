#!/usr/bin/env python3
"""
Gmail OAuth token.json 생성 스크립트

이 스크립트는 Gmail API OAuth 인증을 수행하고 token.json 파일을 생성합니다.
"""

import os
import sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gmail API 권한 범위
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

def create_gmail_token():
    """Gmail OAuth token.json 생성"""
    
    # 환경 변수에서 경로 가져오기
    credentials_path = os.getenv('GMAIL_CREDENTIALS')
    token_path = os.getenv('GMAIL_TOKEN_PATH', 'token.json')
    
    if not credentials_path:
        print("❌ 오류: GMAIL_CREDENTIALS 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 다음을 추가하세요:")
        print("   GMAIL_CREDENTIALS=경로/client_secret_xxx.json")
        sys.exit(1)
    
    if not os.path.exists(credentials_path):
        print(f"❌ 오류: credentials 파일을 찾을 수 없습니다: {credentials_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("Gmail OAuth Token 생성")
    print("=" * 70)
    print(f"Credentials 파일: {credentials_path}")
    print(f"Token 저장 경로: {token_path}")
    print()
    
    creds = None
    
    # 기존 token.json이 있으면 로드
    if os.path.exists(token_path):
        print(f"ℹ️  기존 token.json 파일 발견: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print("✅ 기존 토큰 로드 성공")
        except Exception as e:
            print(f"⚠️  기존 토큰 로드 실패: {e}")
            print("   새로운 토큰을 생성합니다.")
    
    # 토큰이 없거나 유효하지 않으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 토큰 갱신 중...")
            try:
                creds.refresh(Request())
                print("✅ 토큰 갱신 성공")
            except Exception as e:
                print(f"⚠️  토큰 갱신 실패: {e}")
                print("   새로운 인증을 시작합니다.")
                creds = None
        
        if not creds:
            print("\n🔐 OAuth 인증 시작...")
            print("   브라우저가 자동으로 열립니다.")
            print("   Google 계정으로 로그인하고 권한을 승인해주세요.")
            print()
            
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, 
                SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("\n✅ 인증 완료!")
        
        # token.json 저장
        print(f"\n💾 토큰 저장 중: {token_path}")
        
        # 디렉토리가 없으면 생성
        token_dir = os.path.dirname(token_path)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        print(f"✅ token.json 파일이 생성되었습니다!")
        print(f"   위치: {os.path.abspath(token_path)}")
        
    else:
        print("✅ 유효한 토큰이 이미 존재합니다.")
    
    print("\n" + "=" * 70)
    print("완료!")
    print("=" * 70)
    print("\n이제 Daily Briefing을 실행할 수 있습니다.")
    print("Backoffice에서 'Trigger Now' 버튼을 클릭하세요.")
    print()

if __name__ == '__main__':
    try:
        create_gmail_token()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자가 취소했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

