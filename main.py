import os
import json
import requests
import time
from apify_client import ApifyClient
from openai import OpenAI
from supabase import create_client, Client # Storage 접근용으로 필요

# [main.py, 환경 설정 섹션]

# 🚨🚨🚨 이 4줄로 덮어써서 비밀번호를 숨깁니다 🚨🚨🚨
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# ... (나머지 코드는 그대로 둡니다) ...


# --- 로봇 초기화 및 주소 설정 ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
apify_client = ApifyClient(APIFY_API_TOKEN)

# ★ 오류 해결 ★: Storage 접근용 Client 초기화 (최상단에서 정의)
try:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    pass

# Supabase Rest API 주소 (저장 시 캐시 우회를 위한 직접 요청 주소)
SUPABASE_REST_URL = f"{SUPABASE_URL.strip()}/rest/v1/concert_data"


# 수집할 인스타 계정들 (사용자님의 최종 리스트)
TARGET_ACCOUNTS = [
    "hongdaeff", "club_sharp", "subriot_hbc", "liveclubday",
    "jebidabang", "musinsagarage", "clubbang", "channel1969.seoul", "club_victim",
    "rollinghall", "prismhall", "greenflameboys_official", "galaxy_express_official",
    "chippostgang", "idiots.band", "meaningful_stone", "bandbyebyebadman"
]

# === 1. 수집 함수 ===
def get_instagram_posts(username):
    print(f"🕵️  '{username}' 글 읽으러 가는 중...")
    
    run_input = {
        "directUrls": [f"https://www.instagram.com/{username}/"], 
        "resultsLimit": 3, "resultsType": "posts","searchType": "hashtag", "searchLimit": 1,
    }
    
    try:
        run = apify_client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            if item.get("caption", ""): 
                posts.append({"url": item.get("displayUrl", ""), "caption": item.get("caption", ""), "post_link": f"https://www.instagram.com/p/{item.get('code')}"})
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
            model="gpt-4o", messages=[{"role": "system", "content": "너는 공연 정보 추출 전문가야."}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ GPT 분석 실패: {e}")
        return {}

# === 3. 이미지 영구 저장 함수 (Storage는 이 단계에서 제외하고 DB 저장만 진행합니다) ===
# 이 단계는 GitHub Actions 성공 후, 별도로 진행해야 합니다.


# === 4. DB 저장 함수 (최종 저장 로직) ===
def save_to_supabase(data):
    print(f"💾 Supabase 저장 시도: {data.get('title')}")
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY.strip()}", 
        "apikey": SUPABASE_KEY.strip(), 
        "Content-Type": "application/json",
        "Prefer": "resolution=prefer-response-schema", 
    }
    
    try:
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
    
    time.sleep(2) 
    
    for account in TARGET_ACCOUNTS:
        print(f"\n--- [{account}] 처리 시작 ---")
        posts = get_instagram_posts(account)
        
        for post in posts:
            try:
                analyzed_data = analyze_text_with_gpt(post['caption'], account)
                
                if not analyzed_data or not analyzed_data.get("title"):
                    continue

                # ★ Storage 로직은 GitHub Actions 성공 후 진행합니다. (현재는 링크 그대로 사용)
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