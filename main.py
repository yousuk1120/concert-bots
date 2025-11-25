import os
import json
import base64
import requests 
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client
from openai import OpenAI

# --- 환경 설정 ---
load_dotenv()

# [.env] 파일에서 키를 가져오거나, 여기에 직접 문자열로 넣으셔도 됩니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# --- 로봇 초기화 ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
apify_client = ApifyClient(APIFY_API_TOKEN)

# 수집할 계정 ID
TARGET_USERNAME = "rollinghall" 

def get_instagram_posts():
    print(f"🕵️  '{TARGET_USERNAME}' 인스타그램 주소 확보 중...")
    
    # Apify에게 '주소(Direct URL)'를 줘서 정확도를 높임
    run_input = {
        "directUrls": [f"https://www.instagram.com/{TARGET_USERNAME}/"], 
        "resultsLimit": 3,
        "resultsType": "posts",
        "searchType": "hashtag",
        "searchLimit": 1,
    }
    
    run = apify_client.actor("apify/instagram-scraper").call(run_input=run_input)
    
    posts = []
    # 결과 데이터 정리
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        if "displayUrl" in item:
            posts.append({
                "url": item["displayUrl"],
                "caption": item.get("caption", ""),
                "post_link": f"https://www.instagram.com/p/{item.get('code')}"
            })
    print(f"✅ {len(posts)}개의 게시물 발견!")
    return posts

# [핵심] 이미지를 다운받아서 GPT에게 직접 전송하는 함수
def analyze_image_with_gpt(image_url, caption):
    print("🧠 (신규 기능) 로봇이 이미지를 직접 다운로드해서 GPT에게 건네주는 중...")
    
    # 1. 파이썬이 먼저 이미지를 다운로드
    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            print("⚠️ 이미지 다운로드 실패 (인터넷 문제 등)")
            return {}
    except Exception as e:
        print(f"⚠️ 이미지 다운로드 중 에러: {e}")
        return {}
        
    # 2. 이미지를 문자열(Base64)로 변환 (GPT가 읽을 수 있게)
    base64_image = base64.b64encode(response.content).decode('utf-8')
    
    prompt = f"""
    이것은 공연 포스터 이미지와 인스타그램 캡션이야.
    캡션: {caption}
    
    아래 정보를 JSON 형식으로 추출해줘. 없는 정보는 빈 문자열로 둬.
    1. title: 공연명 (없으면 라인업으로)
    2. date: 일시 (형식: YYYY.MM.DD (요일) HH:mm) - 년도가 없으면 2025년으로 가정해.
    3. venue: 장소 (포스터에 없으면 '{TARGET_USERNAME}'라고 적어)
    4. lineup: 출연진 (배열 형태 ["가수1", "가수2"])
    
    오직 JSON 데이터만 뱉어줘.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}" # <--- 여기가 핵심! 주소 대신 이미지를 줌
                        }
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
    )
    
    return json.loads(response.choices[0].message.content)

def save_to_supabase(data):
    print(f"💾 Supabase에 저장 시도: {data.get('title')}")
    try:
        response = supabase.table("concerts").insert(data).execute()
        print("🎉 저장 성공!")
    except Exception as e:
        print(f"⚠️ 저장 실패 (또는 이미 존재함): {e}")

# === 메인 실행 ===
if __name__ == "__main__":
    print("🚀 [업데이트된 로봇] 공연 정보 수집 시작!")
    
    posts = get_instagram_posts()
    
    for post in posts:
        try:
            analyzed_data = analyze_image_with_gpt(post['url'], post['caption'])
            
            if not analyzed_data:
                continue

            concert_data = {
                "title": analyzed_data.get("title", "정보 없음"),
                "date": analyzed_data.get("date", ""),
                "venue": analyzed_data.get("venue", ""),
                "lineup": analyzed_data.get("lineup", []),
                "poster_url": post['url'], 
            }
            
            save_to_supabase(concert_data)
            
        except Exception as e:
            print(f"❌ 처리 중 에러 발생: {e}")
            
    print("😴 모든 작업 완료. 로봇 퇴근합니다.")