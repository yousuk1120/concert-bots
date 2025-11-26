import os
import json
import requests 
from apify_client import ApifyClient
from openai import OpenAI

# --- 환경 설정 (키 값을 직접 입력하여 .env 파일 로드 실패 문제를 완전히 우회함) ---
# 🚨 주의: 이 키 값들은 사용자님의 실제 키입니다. 보안을 위해 노출되지 않도록 주의하세요.

# [Lines 11-14 Replacement Block]
# 🚨🚨🚨 이 4줄로 덮어쓰세요 🚨🚨🚨

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 그리고 기존의 11줄부터 20줄까지의 불필요한 주석과 코드는 싹 지우고 이 4줄만 남겨주세요.

# --- 로봇 초기화 및 주소 설정 ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
apify_client = ApifyClient(APIFY_API_TOKEN)
# Supabase Rest API 주소 (저장 시 캐시 우회를 위한 직접 요청 주소)
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1/concert_data"


# 수집할 인스타 계정들
TARGET_ACCOUNTS = [
    "hongdaeff", "club_sharp", "subriot_hbc", "liveclubday",
    "jebidabang", "musinsagarage", "clubbang", "channel1969.seoul", "club_victim",
    "rollinghall", "prismhall"
]

# === 1. 수집 함수 ===
def get_instagram_posts(username):
    print(f"🕵️  '{username}' 글 읽으러 가는 중...")
    
    run_input = {
        "directUrls": [f"https://www.instagram.com/{username}/"], 
        "resultsLimit": 3, 
        "resultsType": "posts",
        "searchType": "hashtag",
        "searchLimit": 1,
    }
    
    try:
        run = apify_client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            if item.get("caption", ""):
                posts.append({
                    "url": item.get("displayUrl", ""),
                    "caption": item.get("caption", ""),
                    "post_link": f"https://www.instagram.com/p/{item.get('code')}"
                })
        print(f"✅ {len(posts)}개의 게시물 발견!")
        return posts
    except Exception as e:
        print(f"⚠️ {username} 수집 중 에러: {e}")
        return []

# === 2. 분석 함수 (텍스트 전용) ===
def analyze_text_with_gpt(caption, venue_name):
    print(f"🧠 GPT-4o가 '{venue_name}'의 게시글을 읽는 중...")
    
    if not caption or len(caption) < 10:
        return {}
    
    prompt = f"""
    이것은 '{venue_name}' 인스타그램 게시물의 텍스트(Caption)야.
    내용: {caption}
    
    이 글을 읽고 공연 정보를 JSON으로 추출해줘.
    1. title: 공연명 (없으면 라인업으로 대체)
    2. date: 일시 (형식: YYYY.MM.DD (요일) HH:mm) - 년도 없으면 2025년 가정.
    3. venue: 장소 (글에 없으면 '{venue_name}')
    4. lineup: 출연진 (배열 형태)
    
    만약 공연 정보가 아닌 것 같으면(예: 공지사항, 단순 인사말) 빈 JSON {{}}을 줘.
    오직 JSON 데이터만 뱉어.
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": "너는 공연 정보 추출 전문가야."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ GPT 분석 실패: {e}")
        return {}

# === 3. 저장 함수 (401 에러 우회 로직) ===
# [main.py, save_to_supabase 함수 내부 수정]

def save_to_supabase(data):
    # ...
    
    # 캐시 우회를 위한 요청 헤더
    headers = {
        # 1. Bearer Authorization (기존)
        "Authorization": f"Bearer {SUPABASE_KEY.strip()}", 
        
        # 2. 🚨🚨 에러 힌트에 따라 apikey 헤더 추가 (이것이 핵심입니다!)
        "apikey": SUPABASE_KEY.strip(), 
        
        "Content-Type": "application/json",
        "Prefer": "resolution=prefer-response-schema", 
    }
    
    # ... (나머지 코드는 동일) ...
    
    try:
        # requests로 Supabase API에 직접 요청
        response = requests.post(SUPABASE_REST_URL, headers=headers, json=data)

        if response.status_code == 201:
            print("🎉 저장 성공!")
        elif response.status_code == 409:
            print(f"PASS: 이미 저장된 공연 (링크 중복)")
        else:
            print(f"⚠️ 저장 실패 (HTTP {response.status_code}, {response.text})")
            
    except Exception as e:
        print(f"❌ 최종 에러 발생: {e}")

# === 메인 실행 ===
if __name__ == "__main__":
    print("🚀 [최종 통합] 로봇 가동!")
    
    # 🚨🚨 로봇 실행 전, 잠시 wait time을 줍니다 (이전 실행 프로세스가 완전히 종료되도록)
    import time
    time.sleep(2) 
    
    for account in TARGET_ACCOUNTS:
        print(f"\n--- [{account}] 처리 시작 ---")
        posts = get_instagram_posts(account)
        
        for post in posts:
            try:
                analyzed_data = analyze_text_with_gpt(post['caption'], account)
                
                if not analyzed_data or not analyzed_data.get("title"):
                    continue

                concert_data = {
                    "title": analyzed_data.get("title", "정보 없음"),
                    "date": analyzed_data.get("date", ""),
                    "venue": analyzed_data.get("venue", ""),
                    "lineup": analyzed_data.get("lineup", []),
                    "poster_url": post['url'],
                    "post_link": post['post_link']
                }
                
                save_to_supabase(concert_data)
                
            except Exception as e:
                print(f"❌ 처리 중 에러: {e}")
            
    print("\n😴 모든 작업 완료. 로봇 퇴근합니다.")