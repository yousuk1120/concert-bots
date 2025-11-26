import os
import json
import requests
import time
from apify_client import ApifyClient
from openai import OpenAI
from supabase import create_client, Client

# --- 환경 설정 (Github Actions Secrets에서 키를 읽도록 복구) ---
# 🚨 주의: 이 키 값들을 코드에 직접 적으면 안 됩니다. Secrets에 맡깁니다.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Supabase Rest API 주소
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1/concert_data"


# --- 로봇 초기화 및 주소 설정 ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
apify_client = ApifyClient(APIFY_API_TOKEN)

# Storage 접근용 Client 초기화 (GitHub Actions에서 Secret을 읽어오도록 설정)
try:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    # GitHub Actions 환경에서는 이 부분이 실행되지 않습니다.
    pass


# 수집할 인스타 계정들 (사용자님의 최종 리스트)
TARGET_ACCOUNTS = [
    "hongdaeff", "club_sharp", "subriot_hbc", "liveclubday",
    "jebidabang", "musinsagarage", "clubbang", "channel1969.seoul", "club_victim",
    "rollinghall", "prismhall", "greenflameboys_official", "galaxy_express_official",
    "chippostgang", "idiots.band", "meaningful_stone", "bandbyebyebadman"
]


# === 1. 수집 함수 (생략) ===
def get_instagram_posts(username):
    print(f"🕵️  '{username}' 글 읽으러 가는 중...")
    
    run_input = {
        "directUrls": [f"https://www.instagram.com/{username}/"], 
        "resultsLimit": 3, "resultsType": "posts", "searchType": "hashtag", "searchLimit": 1,
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

# === 2. 분석 함수 (생략) ===
def analyze_text_with_gpt(caption, venue_name):
    # ... (분석 로직은 그대로)
    if not caption or len(caption) < 10: return {}
    prompt = f"""
    이것은 '{venue_name}' 인스타그램 게시물의 텍스트(Caption)야. 내용: {caption}
    이 글을 읽고 공연 정보를 JSON으로 추출해줘. 1. title: 공연명 (없으면 라인업으로 대체) 2. date: 일시 (형식: YYYY.MM.DD (요일) HH:mm) - 년도 없으면 2025년 가정. 3. venue: 장소 (글에 없으면 '{venue_name}') 4. lineup: 출연진 (배열 형태)
    만약 공연 정보가 아닌 것 같으면(예: 공지사항, 단순 인사말) 빈 JSON {{}}을 줘. 오직 JSON 데이터만 뱉어.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "system", "content": "너는 공연 정보 추출 전문가야."}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {}

# === 3. ★ 이미지 영구 저장 함수 ★ ===
def upload_image_to_supabase_storage(image_url: str, post_link: str) -> str:
    """ 인스타그램 이미지 URL에서 파일을 다운로드하고, Supabase Storage(posters 버킷)에 업로드합니다. """
    if not image_url or not post_link: return ""

    try:
        unique_id = post_link.split('/p/')[1].strip('/').split('/')[0]
        file_name = f"{unique_id}.jpg"
    except: return ""

    # 이미지 다운로드
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status() 
        image_data = response.content
    except requests.exceptions.RequestException as e:
        return ""

    # Supabase Storage에 업로드 (Service Role이 필요함. GitHub Secrets에서 Key를 가져옴)
    try:
        # 이 시점에 supabase_client는 GitHub Actions의 Secrets로 초기화됩니다.
        supabase_client.storage.from_("posters").upload(
            file=image_data,
            path=file_name,
            file_options={"content-type": "image/jpeg"}
        )
        # 업로드된 파일의 공개 URL을 생성하여 반환
        new_public_url = supabase_client.storage.from_("posters").get_public_url(file_name)
        return new_public_url

    except Exception as e:
        # 이미 존재하는 파일일 경우 PASS 처리
        if "already exists" in str(e):
            new_public_url = supabase_client.storage.from_("posters").get_public_url(file_name)
            print(f"Storage: PASS: 이미 저장된 이미지. URL: {new_public_url}")
            return new_public_url
        else:
            print(f"Storage: 이미지 업로드 실패: {e}")
            return ""


# === 4. DB 저장 함수 (클라우드 환경용) ===
def save_to_supabase(data):
    print(f"💾 Supabase 저장 시도: {data.get('title')}")
    
    headers = {
        # GitHub Actions가 Key를 깨끗하게 넣어줄 것이므로, 그대로 사용합니다.
        "Authorization": f"Bearer {SUPABASE_KEY}", 
        "apikey": SUPABASE_KEY, 
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
    print("🚀 [최종 자동화] 로봇 가동!")
    
    time.sleep(2) 
    
    for account in TARGET_ACCOUNTS:
        print(f"\n--- [{account}] 처리 시작 ---")
        posts = get_instagram_posts(account)
        
        for post in posts:
            try:
                analyzed_data = analyze_text_with_gpt(post['caption'], account)
                
                if not analyzed_data or not analyzed_data.get("title"):
                    continue

                # 이미지 영구 저장
                permanent_url = upload_image_to_supabase_storage(post['url'], post['post_link'])

                concert_data = {
                    "title": analyzed_data.get("title", "정보 없음"),
                    "date": analyzed_data.get("date", ""),
                    "venue": analyzed_data.get("venue", ""),
                    "lineup": analyzed_data.get("lineup", []),
                    "poster_url": permanent_url or post['url'], # 영구 URL 사용
                    "post_link": post['post_link']
                }
                
                save_to_supabase(concert_data)
                
            except Exception as e:
                print(f"❌ 처리 중 에러: {e}")
            
    print("\n😴 모든 작업 완료. 로봇 퇴근합니다.")