"""
MediScan AI — FastAPI Backend
처방약 AI 관리 앱 백엔드 서버

실행: uvicorn main:app --reload --port 8000
"""

import os
import json
import uuid
import base64
from datetime import datetime, date
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── App ───
app = FastAPI(
    title="MediScan AI",
    description="처방약 AI 관리 앱 백엔드",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 정적 파일 / 프론트엔드 ───
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DB_DIR = Path(__file__).parent / "db"
DB_DIR.mkdir(exist_ok=True)


# ================================================================
# HIRA 의약품 공공데이터 (ATC코드, 성분, 약효분류, DUR)
# 실제 서비스에서는 HIRA OpenAPI 또는 DB로 교체
# ================================================================
HIRA_DRUG_DB = {
    "노바스크": {
        "name": "노바스크정 5mg",
        "ingredient": "Amlodipine",
        "atc": "C08CA01",
        "category": "혈압약",
        "desc": "혈관을 이완시켜 혈압을 낮추는 칼슘채널차단제입니다. "
                "다른 혈압약과 함께 복용 중이면 어지러움이나 저혈압 증상을 확인해야 합니다.",
        "food": "과음은 어지러움과 저혈압 위험을 높일 수 있습니다.",
        "dur_alerts": ["저혈압 주의", "자몽주스 병용 시 약효 변화 가능"],
        "usage_stats": {"annual_prescriptions": 8_420_000, "rank_in_category": 1},
    },
    "리피토": {
        "name": "리피토정 10mg",
        "ingredient": "Atorvastatin",
        "atc": "C10AA05",
        "category": "지질저하제",
        "desc": "콜레스테롤 합성을 낮추는 스타틴 계열 약입니다. "
                "근육통, 무기력감, 간 수치 이상 병력이 있으면 정기 검사가 권장됩니다.",
        "food": "자몽·자몽주스와 음주는 주의가 필요합니다.",
        "dur_alerts": ["근육통/횡문근융해증 모니터링", "간기능 정기 검사 권장"],
        "usage_stats": {"annual_prescriptions": 6_150_000, "rank_in_category": 1},
    },
    "아스피린": {
        "name": "아스피린프로텍트정 100mg",
        "ingredient": "Aspirin",
        "atc": "B01AC06",
        "category": "항혈소판제",
        "desc": "혈소판 응집을 억제해 혈전 생성을 줄이는 약입니다. "
                "위장 출혈 병력, 멍, 검은 변이 있으면 상담이 필요합니다.",
        "food": "음주는 위장 출혈 위험을 높일 수 있습니다.",
        "dur_alerts": ["위장 출혈 위험", "수술 전 7일 중단 권장"],
        "usage_stats": {"annual_prescriptions": 5_890_000, "rank_in_category": 2},
    },
    "메트포르민": {
        "name": "메트포르민정 500mg",
        "ingredient": "Metformin",
        "atc": "A10BA02",
        "category": "당뇨병약",
        "desc": "간에서 포도당 생성을 억제하고 인슐린 감수성을 높이는 약입니다. "
                "신장 기능이 저하된 경우 용량 조절이 필요합니다.",
        "food": "과도한 음주는 유산산증 위험을 높입니다. 식사와 함께 복용하세요.",
        "dur_alerts": ["신기능 정기 모니터링", "조영제 검사 전후 중단"],
        "usage_stats": {"annual_prescriptions": 7_320_000, "rank_in_category": 1},
    },
    "타이레놀": {
        "name": "타이레놀정 500mg",
        "ingredient": "Acetaminophen",
        "atc": "N02BE01",
        "category": "해열진통제",
        "desc": "통증과 열을 낮추는 해열진통제입니다. "
                "하루 4g 이상 복용하면 간 손상 위험이 있습니다.",
        "food": "음주 시 간 독성 위험이 증가합니다. 복용 중 음주를 피하세요.",
        "dur_alerts": ["간기능 저하 시 감량", "하루 4g 초과 금지"],
        "usage_stats": {"annual_prescriptions": 12_500_000, "rank_in_category": 1},
    },
    "로사르탄": {
        "name": "코자정 50mg",
        "ingredient": "Losartan",
        "atc": "C09CA01",
        "category": "혈압약",
        "desc": "안지오텐신 II 수용체를 차단하여 혈압을 낮추는 약입니다. "
                "임산부에게는 금기이며 칼륨 수치를 정기적으로 확인해야 합니다.",
        "food": "칼륨이 많은 음식(바나나, 오렌지, 시금치)과 함께 과량 섭취 시 고칼륨혈증 주의.",
        "dur_alerts": ["임부 금기", "혈중 칼륨 모니터링", "신기능 확인"],
        "usage_stats": {"annual_prescriptions": 4_780_000, "rank_in_category": 3},
    },
    "오메프라졸": {
        "name": "오메프라졸캡슐 20mg",
        "ingredient": "Omeprazole",
        "atc": "A02BC01",
        "category": "위산분비억제제",
        "desc": "위산 분비를 강력히 억제하는 프로톤펌프억제제(PPI)입니다. "
                "장기 복용 시 마그네슘, 비타민B12 결핍 위험이 있습니다.",
        "food": "식사 30분 전 공복에 복용하는 것이 가장 효과적입니다.",
        "dur_alerts": ["장기복용 시 골절 위험 증가", "마그네슘 수치 모니터링"],
        "usage_stats": {"annual_prescriptions": 6_890_000, "rank_in_category": 2},
    },
}

# ─── 음식-약물 상호작용 DB ───
FOOD_DRUG_INTERACTIONS = {
    "자몽": ["Atorvastatin", "Amlodipine"],
    "그레이프프루트": ["Atorvastatin", "Amlodipine"],
    "술": ["Aspirin", "Acetaminophen", "Metformin"],
    "소주": ["Aspirin", "Acetaminophen", "Metformin"],
    "맥주": ["Aspirin", "Acetaminophen", "Metformin"],
    "와인": ["Aspirin", "Acetaminophen", "Metformin"],
    "막걸리": ["Aspirin", "Acetaminophen", "Metformin"],
    "바나나": ["Losartan"],
    "오렌지": ["Losartan"],
    "시금치": ["Losartan"],
    "우유": ["Metformin"],
    "라면": ["__HIGH_SODIUM__"],
    "찌개": ["__HIGH_SODIUM__"],
    "짬뽕": ["__HIGH_SODIUM__"],
    "피자": ["__HIGH_SODIUM__"],
    "햄버거": ["__HIGH_SODIUM__"],
    "치킨": ["__HIGH_SODIUM__"],
    "젓갈": ["__HIGH_SODIUM__"],
}

# ─── 가족력-질환 위험 DB ───
FAMILY_RISK_DB = {
    "고혈압": {
        "risk_multiplier": 2.5,
        "related_drugs": ["혈압약"],
        "dietary_warnings": ["나트륨 하루 2000mg 이하 권장", "짠 국물, 가공식품, 절임류 줄이기"],
        "screening": "매년 혈압 측정 권장",
    },
    "당뇨병": {
        "risk_multiplier": 3.0,
        "related_drugs": ["당뇨병약"],
        "dietary_warnings": ["정제 탄수화물(백미, 빵, 면류) 조절", "당분 섭취 제한"],
        "screening": "연 1회 공복혈당 + HbA1c 검사 권장",
    },
    "고지혈증": {
        "risk_multiplier": 2.0,
        "related_drugs": ["지질저하제"],
        "dietary_warnings": ["포화지방(삼겹살, 버터, 치즈) 줄이기", "트랜스지방 회피"],
        "screening": "연 1회 지질 검사 권장",
    },
    "심장질환": {
        "risk_multiplier": 2.8,
        "related_drugs": ["항혈소판제", "혈압약"],
        "dietary_warnings": ["포화지방 제한", "오메가3 섭취 권장"],
        "screening": "40세 이후 심전도 정기 검사",
    },
    "뇌졸중": {
        "risk_multiplier": 2.5,
        "related_drugs": ["항혈소판제", "혈압약"],
        "dietary_warnings": ["나트륨 제한", "규칙적 운동"],
        "screening": "혈압, 혈당, 지질 정기 검사",
    },
}


# ================================================================
# Pydantic Models
# ================================================================
class DrugInput(BaseModel):
    name: str

class ManualDrugInput(BaseModel):
    name: str
    ingredient: str = ""
    atc: str = ""
    category: str = ""
    food: str = ""

class MealInput(BaseModel):
    meal_type: str          # 아침/점심/저녁/간식
    foods: str = ""         # 먹은 음식 텍스트
    calories: int = 0
    sodium: int = 0

class ProfileInput(BaseModel):
    height: float = 170
    weight: float = 70
    exercise_freq: int = 0      # 0~4
    exercise_intensity: int = 0  # 0~3

class BodyStatusInput(BaseModel):
    condition: str
    memo: str = ""

class FamilyHistoryInput(BaseModel):
    disease: str
    relation: str
    memo: str = ""

class ReminderInput(BaseModel):
    drug_id: str
    time: str = "아침 식후"
    dose: str = "1정"
    cycle: str = "매일"


# ================================================================
# 간단 파일 기반 사용자 DB (실제 서비스에서는 PostgreSQL 등 사용)
# ================================================================
def get_user_db(user_id: str = "default") -> dict:
    db_path = DB_DIR / f"{user_id}.json"
    if db_path.exists():
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "user_id": user_id,
        "medicines": [],
        "profile": {"height": 170, "weight": 70, "exercise_freq": 0, "exercise_intensity": 0},
        "meal_logs": [],
        "body_logs": [],
        "family_history": [],
        "no_meds_mode": False,
        "nhis_data": None,
    }

def save_user_db(data: dict, user_id: str = "default"):
    db_path = DB_DIR / f"{user_id}.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================================================================
# 프론트엔드 서빙
# ================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>MediScan AI</h1><p>static/index.html 파일을 배치하세요.</p>")


# ================================================================
# 1. OCR + 약 분석 API
# ================================================================
@app.post("/api/scan")
async def scan_prescription(file: UploadFile = File(...)):
    """
    처방전/약 봉투 이미지 업로드 -> OCR -> HIRA DB 매칭 -> AI 설명 생성
    실제 서비스에서는:
    - Google Cloud Vision / Tesseract OCR로 텍스트 추출
    - 추출된 약 이름을 HIRA ATC코드 DB와 매칭
    - LLM(Claude API)으로 개인화 설명 생성
    """
    # 파일 저장
    file_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    ext = Path(file.filename).suffix or ".jpg"
    save_path = UPLOAD_DIR / f"{file_id}{ext}"
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # ── OCR 시뮬레이션 (실제: Google Vision API / Tesseract) ──
    # 실제 구현 시:
    # from google.cloud import vision
    # client = vision.ImageAnnotatorClient()
    # image = vision.Image(content=content)
    # response = client.text_detection(image=image)
    # ocr_text = response.text_annotations[0].description

    ocr_text = "노바스크정 5mg, 리피토정 10mg, 아스피린프로텍트정 100mg"

    # ── HIRA DB 매칭 ──
    matched_drugs = []
    for keyword, drug_info in HIRA_DRUG_DB.items():
        if keyword in ocr_text:
            matched_drugs.append({
                "id": drug_info["atc"].lower() + "_" + uuid.uuid4().hex[:4],
                **drug_info,
                "time": "아침 식후",
                "dose": "1정",
                "cycle": "매일",
            })

    # ── AI 설명 생성 (실제: Claude API) ──
    # 실제 구현 시:
    # import anthropic
    # client = anthropic.Anthropic()
    # message = client.messages.create(
    #     model="claude-sonnet-4-20250514",
    #     messages=[{"role": "user", "content": f"다음 약에 대해 설명: {matched_drugs}"}]
    # )

    return {
        "success": True,
        "ocr_text": ocr_text,
        "image_path": str(save_path),
        "matched_drugs": matched_drugs,
        "drug_count": len(matched_drugs),
        "analysis_source": "HIRA ATC코드·성분 사용실적·DUR 점검 현황",
    }


# ================================================================
# 2. 약 이름 검색 API (HIRA DB 조회)
# ================================================================
@app.post("/api/drug/search")
async def search_drug(data: DrugInput):
    """약 이름으로 HIRA DB 검색"""
    results = []
    for keyword, info in HIRA_DRUG_DB.items():
        if (data.name.lower() in keyword.lower()
            or data.name.lower() in info["name"].lower()
            or data.name.lower() in info["ingredient"].lower()):
            results.append({
                "id": info["atc"].lower() + "_match",
                **info,
                "time": "아침 식후",
                "dose": "1정",
                "cycle": "매일",
            })
    return {"success": True, "results": results, "query": data.name}


# ================================================================
# 3. 식사 분석 API
# ================================================================
@app.post("/api/food/analyze")
async def analyze_food(data: MealInput, user_id: str = "default"):
    """
    식사 내용 분석 -> 복용 약물과 교차 분석 -> 주의 음식 경고
    실제 서비스에서는:
    - 음식 이미지: Claude Vision API로 음식 인식
    - 텍스트: NLP로 음식 추출 + 영양정보 DB 매칭
    """
    db = get_user_db(user_id)
    medicines = db["medicines"]
    family_history = db["family_history"]
    user_ingredients = [m.get("ingredient", "") for m in medicines]
    user_categories = [m.get("category", "") for m in medicines]

    alerts = []
    foods_text = data.foods.lower()

    # ── 약물-음식 상호작용 분석 ──
    for food_keyword, interacting_ingredients in FOOD_DRUG_INTERACTIONS.items():
        if food_keyword in foods_text:
            if "__HIGH_SODIUM__" in interacting_ingredients:
                # 고나트륨 음식 + 혈압약
                if "혈압약" in user_categories:
                    alerts.append({
                        "type": "danger",
                        "title": f"고나트륨 식사 감지 — 혈압약 복용 중",
                        "desc": f"입력하신 식사에 '{food_keyword}'이 포함되어 있습니다. "
                                f"혈압약 복용 중에는 나트륨이 높은 음식 섭취를 줄이세요.",
                        "source": "HIRA 약효분류군 사용실적 기반",
                    })
            else:
                for ingredient in interacting_ingredients:
                    if ingredient in user_ingredients:
                        drug = next((m for m in medicines if m.get("ingredient") == ingredient), None)
                        alerts.append({
                            "type": "danger",
                            "title": f"'{food_keyword}' 섭취 감지 — {drug['name'] if drug else ingredient} 주의",
                            "desc": f"입력하신 식사에 '{food_keyword}'이 포함되어 있습니다. "
                                    f"{ingredient} 복용 중 상호작용 위험이 있습니다.",
                            "source": f"HIRA DUR 점검 현황 / ATC {drug.get('atc', '')} 기반",
                        })

    # ── 가족력 기반 식이 경고 ──
    family_diseases = [f.get("disease", "") for f in family_history]
    for disease in family_diseases:
        if disease in FAMILY_RISK_DB:
            risk_info = FAMILY_RISK_DB[disease]
            for warning in risk_info["dietary_warnings"]:
                alerts.append({
                    "type": "info",
                    "title": f"{disease} 가족력 — 식이 주의",
                    "desc": warning,
                    "source": "HIRA 질병별 의약품 통계 기반",
                })

    # ── 칼로리/나트륨 누적 계산 ──
    today = date.today().isoformat()
    today_meals = [m for m in db["meal_logs"] if m.get("date") == today]
    total_cal = sum(m.get("calories", 0) for m in today_meals) + data.calories
    total_sodium = sum(m.get("sodium", 0) for m in today_meals) + data.sodium

    profile = db["profile"]
    cal_goal = _calc_calorie_goal(profile)
    sodium_goal = 2000

    if total_cal > cal_goal:
        alerts.append({
            "type": "warning",
            "title": "오늘 칼로리 기준 초과",
            "desc": f"누적 {total_cal} kcal. 개인 권장 기준 {cal_goal} kcal를 넘었습니다.",
            "source": "개인 프로필 기반 계산",
        })
    if total_sodium > sodium_goal:
        alerts.append({
            "type": "warning",
            "title": "오늘 나트륨 기준 초과",
            "desc": f"누적 {total_sodium} mg. 권장 기준 {sodium_goal} mg을 넘었습니다.",
            "source": "WHO 나트륨 섭취 기준",
        })

    # ── 식사 기록 저장 ──
    meal_record = {
        "id": str(uuid.uuid4().hex[:12]),
        "type": data.meal_type,
        "foods": data.foods,
        "calories": data.calories,
        "sodium": data.sodium,
        "date": today,
        "time": datetime.now().strftime("%H:%M"),
        "created_at": datetime.now().isoformat(),
    }
    db["meal_logs"].insert(0, meal_record)
    save_user_db(db, user_id)

    return {
        "success": True,
        "meal": meal_record,
        "alerts": alerts,
        "totals": {"calories": total_cal, "sodium": total_sodium},
        "goals": {"calories": cal_goal, "sodium": sodium_goal},
    }


# ================================================================
# 4. 사용자 약력 CRUD
# ================================================================
@app.get("/api/medicines")
async def get_medicines(user_id: str = "default"):
    db = get_user_db(user_id)
    return {"medicines": db["medicines"], "count": len(db["medicines"])}

@app.post("/api/medicines/add")
async def add_medicine(data: dict, user_id: str = "default"):
    db = get_user_db(user_id)
    # 중복 확인 (성분 기준)
    existing = [m.get("ingredient") for m in db["medicines"]]
    if data.get("ingredient") in existing:
        return {"success": False, "message": "이미 동일 성분이 등록되어 있습니다."}
    data["id"] = data.get("id", f"med_{uuid.uuid4().hex[:8]}")
    data["taken"] = False
    db["medicines"].append(data)
    db["no_meds_mode"] = False
    save_user_db(db, user_id)
    return {"success": True, "medicine": data}

@app.delete("/api/medicines/{med_id}")
async def remove_medicine(med_id: str, user_id: str = "default"):
    db = get_user_db(user_id)
    db["medicines"] = [m for m in db["medicines"] if m.get("id") != med_id]
    save_user_db(db, user_id)
    return {"success": True}


# ================================================================
# 5. 프로필 / 몸상태 / 가족력
# ================================================================
@app.get("/api/profile")
async def get_profile(user_id: str = "default"):
    db = get_user_db(user_id)
    profile = db["profile"]
    bmi = _calc_bmi(profile)
    cal_goal = _calc_calorie_goal(profile)
    return {"profile": profile, "bmi": bmi, "calorie_goal": cal_goal}

@app.post("/api/profile")
async def save_profile(data: ProfileInput, user_id: str = "default"):
    db = get_user_db(user_id)
    db["profile"] = data.dict()
    save_user_db(db, user_id)
    bmi = _calc_bmi(data.dict())
    cal_goal = _calc_calorie_goal(data.dict())
    return {"success": True, "bmi": bmi, "calorie_goal": cal_goal}

@app.post("/api/body-status")
async def save_body_status(data: BodyStatusInput, user_id: str = "default"):
    db = get_user_db(user_id)
    record = {
        "id": uuid.uuid4().hex[:12],
        "condition": data.condition,
        "memo": data.memo or "메모 없음",
        "time": datetime.now().strftime("%m/%d %H:%M"),
        "created_at": datetime.now().isoformat(),
    }
    db["body_logs"].insert(0, record)
    save_user_db(db, user_id)
    return {"success": True, "record": record}

@app.get("/api/family-history")
async def get_family_history(user_id: str = "default"):
    db = get_user_db(user_id)
    return {"family_history": db["family_history"]}

@app.post("/api/family-history")
async def add_family_history(data: FamilyHistoryInput, user_id: str = "default"):
    db = get_user_db(user_id)
    record = {
        "id": uuid.uuid4().hex[:12],
        "disease": data.disease,
        "relation": data.relation,
        "memo": data.memo,
        "created_at": datetime.now().isoformat(),
    }
    db["family_history"].append(record)
    save_user_db(db, user_id)

    # 가족력 기반 AI 위험 분석
    risk_info = FAMILY_RISK_DB.get(data.disease)
    risk_alert = None
    if risk_info:
        medicines = db["medicines"]
        user_categories = [m.get("category", "") for m in medicines]
        drug_overlap = any(cat in risk_info["related_drugs"] for cat in user_categories)
        risk_alert = {
            "disease": data.disease,
            "risk_multiplier": risk_info["risk_multiplier"],
            "drug_overlap": drug_overlap,
            "screening": risk_info["screening"],
            "dietary_warnings": risk_info["dietary_warnings"],
        }

    return {"success": True, "record": record, "risk_alert": risk_alert}

@app.delete("/api/family-history/{record_id}")
async def delete_family_history(record_id: str, user_id: str = "default"):
    db = get_user_db(user_id)
    db["family_history"] = [f for f in db["family_history"] if f.get("id") != record_id]
    save_user_db(db, user_id)
    return {"success": True}


# ================================================================
# 6. AI 위험 점검 API
# ================================================================
@app.get("/api/risk-assessment")
async def risk_assessment(user_id: str = "default"):
    """
    약력 + 가족력 + 몸상태 -> AI 종합 위험 점검
    실제 서비스: LLM이 모든 데이터를 교차 분석해 개인화 리포트 생성
    """
    db = get_user_db(user_id)
    medicines = db["medicines"]
    family_history = db["family_history"]
    body_logs = db["body_logs"]
    alerts = []

    # ── 동일 성분 중복 감지 ──
    ingredients = [m.get("ingredient", "") for m in medicines]
    duplicates = len(ingredients) - len(set(ingredients))
    if duplicates > 0:
        alerts.append({
            "type": "danger",
            "title": "동일 성분 중복 가능성",
            "desc": f"동일 성분이 {duplicates}건 반복 등록. HIRA DUR 점검 현황 기준, 중복 처방은 부작용 발생률을 높입니다.",
        })
    else:
        alerts.append({
            "type": "safe",
            "title": "동일 성분 중복 처방 없음",
            "desc": "현재 약력 기준 동일 주성분 반복 등록은 없습니다.",
        })

    # ── 가족력 교차 분석 ──
    for fam in family_history:
        disease = fam.get("disease", "")
        risk_info = FAMILY_RISK_DB.get(disease)
        if not risk_info:
            continue
        user_categories = [m.get("category", "") for m in medicines]
        overlap = any(cat in risk_info["related_drugs"] for cat in user_categories)
        if overlap:
            alerts.append({
                "type": "danger",
                "title": f"가족력({disease}) + 관련 약물 복용 중",
                "desc": f"HIRA 질병별 의약품 통계 기준, {disease} 가족력 환자군은 "
                        f"관련 약물 복용 시 모니터링 빈도가 높습니다. {risk_info['screening']}",
            })
        else:
            alerts.append({
                "type": "info",
                "title": f"{disease} 가족력 감지",
                "desc": f"발병 확률이 약 {risk_info['risk_multiplier']}배 높습니다. "
                        f"{risk_info['screening']}",
            })

    # ── 위험 점수 계산 ──
    score = min(95, 12 + len(medicines) * 8 + duplicates * 18 + len(family_history) * 5)
    if score >= 60:
        level = "높은 위험"
    elif score >= 35:
        level = "중간 위험"
    else:
        level = "낮은 위험"

    return {
        "score": score,
        "level": level,
        "medicine_count": len(medicines),
        "family_history_count": len(family_history),
        "alerts": alerts,
    }


# ================================================================
# 7. NHIS (국민건강보험) 연동 API
# ================================================================
@app.post("/api/nhis/connect")
async def connect_nhis(user_id: str = "default"):
    """
    국민건강보험공단 건강정보 연동
    실제 서비스에서는:
    - NHIS 마이데이터 API 또는 공공 마이데이터 포털 연동
    - 사용자 본인인증(PASS, 공동인증서) 후 데이터 수신
    - https://www.nhis.or.kr 건강검진 결과 조회 API 활용
    """
    # ── 시뮬레이션 데이터 (실제: NHIS API 응답) ──
    nhis_data = {
        "connected": True,
        "name": "사용자",
        "checkup_date": "2025-12-15",
        "items": [
            {"type": "질환", "label": "고혈압 (I10)", "detail": "2023년 진단, 현재 투약 중"},
            {"type": "질환", "label": "고지혈증 (E78.0)", "detail": "2024년 진단, 스타틴 처방"},
            {"type": "검진결과", "label": "혈압: 138/88 mmHg", "detail": "경계 고혈압 (최근 검진 기준)"},
            {"type": "검진결과", "label": "공복혈당: 108 mg/dL", "detail": "공복혈당장애 (정상 범위 초과)"},
            {"type": "검진결과", "label": "총콜레스테롤: 242 mg/dL", "detail": "높음 (200 이하 권장)"},
            {"type": "검진결과", "label": "BMI: 26.1", "detail": "과체중 (23~25 정상)"},
            {"type": "가족력", "label": "부 — 고혈압", "detail": "55세 진단"},
            {"type": "가족력", "label": "모 — 당뇨병", "detail": "62세 진단"},
            {"type": "투약이력", "label": "노바스크정 5mg (Amlodipine)", "detail": "2023.03~ 현재, 매일 1회"},
            {"type": "투약이력", "label": "리피토정 10mg (Atorvastatin)", "detail": "2024.06~ 현재, 매일 1회"},
        ],
    }

    db = get_user_db(user_id)
    db["nhis_data"] = nhis_data
    save_user_db(db, user_id)

    return {"success": True, "data": nhis_data}

@app.post("/api/nhis/apply")
async def apply_nhis_data(user_id: str = "default"):
    """NHIS에서 불러온 데이터를 약력/가족력에 반영"""
    db = get_user_db(user_id)
    nhis = db.get("nhis_data")
    if not nhis or not nhis.get("connected"):
        raise HTTPException(400, "NHIS 데이터가 없습니다. 먼저 연동하세요.")

    added_meds = 0
    added_family = 0

    for item in nhis.get("items", []):
        if item["type"] == "가족력":
            parts = item["label"].split("—")
            if len(parts) == 2:
                relation = parts[0].strip()
                disease = parts[1].strip()
                existing = [f for f in db["family_history"]
                           if f.get("disease") == disease and f.get("relation") == relation]
                if not existing:
                    db["family_history"].append({
                        "id": uuid.uuid4().hex[:12],
                        "disease": disease,
                        "relation": relation,
                        "memo": f"NHIS 연동: {item['detail']}",
                    })
                    added_family += 1

        if item["type"] == "투약이력":
            import re
            match = re.match(r"^(.+?)\s*\((.+?)\)$", item["label"])
            if match:
                med_name = match.group(1).strip()
                ingredient = match.group(2).strip()
                existing = [m for m in db["medicines"] if m.get("ingredient") == ingredient]
                if not existing:
                    # HIRA DB에서 찾기
                    found = None
                    for _, info in HIRA_DRUG_DB.items():
                        if info["ingredient"] == ingredient:
                            found = info
                            break
                    if found:
                        db["medicines"].append({
                            "id": f"nhis_{uuid.uuid4().hex[:8]}",
                            **found,
                            "time": "아침 식후",
                            "dose": "1정",
                            "cycle": "매일",
                            "taken": False,
                        })
                    else:
                        db["medicines"].append({
                            "id": f"nhis_{uuid.uuid4().hex[:8]}",
                            "name": med_name,
                            "ingredient": ingredient,
                            "atc": "NHIS",
                            "category": "NHIS 연동 약",
                            "desc": "국민건강보험공단 투약 이력에서 불러온 약입니다.",
                            "food": "상세 정보는 전문가 상담을 권장합니다.",
                            "time": "아침 식후",
                            "dose": "1정",
                            "cycle": "매일",
                            "taken": False,
                        })
                    added_meds += 1

    if added_meds or added_family:
        db["no_meds_mode"] = False
    save_user_db(db, user_id)

    return {
        "success": True,
        "added_medicines": added_meds,
        "added_family_history": added_family,
    }


# ================================================================
# 8. 복용 알림
# ================================================================
@app.post("/api/reminder")
async def save_reminder(data: ReminderInput, user_id: str = "default"):
    db = get_user_db(user_id)
    for m in db["medicines"]:
        if m.get("id") == data.drug_id:
            m["time"] = data.time
            m["dose"] = data.dose
            m["cycle"] = data.cycle
            break
    save_user_db(db, user_id)
    return {"success": True}

@app.post("/api/reminder/toggle/{drug_id}")
async def toggle_taken(drug_id: str, user_id: str = "default"):
    db = get_user_db(user_id)
    for m in db["medicines"]:
        if m.get("id") == drug_id:
            m["taken"] = not m.get("taken", False)
            break
    save_user_db(db, user_id)
    return {"success": True}


# ================================================================
# 9. 전체 사용자 데이터 조회 (프론트엔드 초기 로딩용)
# ================================================================
@app.get("/api/user-data")
async def get_all_user_data(user_id: str = "default"):
    """프론트엔드 초기 로딩 시 전체 데이터를 한 번에 반환"""
    db = get_user_db(user_id)
    profile = db["profile"]
    return {
        "medicines": db["medicines"],
        "profile": profile,
        "meal_logs": db["meal_logs"],
        "body_logs": db["body_logs"],
        "family_history": db["family_history"],
        "no_meds_mode": db["no_meds_mode"],
        "nhis_data": db.get("nhis_data"),
        "computed": {
            "bmi": _calc_bmi(profile),
            "calorie_goal": _calc_calorie_goal(profile),
            "sodium_goal": 2000,
        },
    }


# ================================================================
# Helper 함수
# ================================================================
def _calc_bmi(profile: dict) -> float:
    h = float(profile.get("height", 170)) / 100
    w = float(profile.get("weight", 70))
    if h <= 0:
        return 0
    return round(w / (h * h), 1)

def _calc_calorie_goal(profile: dict) -> int:
    freq = int(profile.get("exercise_freq", 0))
    intensity = int(profile.get("exercise_intensity", 0))
    weight = float(profile.get("weight", 70))

    factor = 1.2
    if freq == 0 or intensity == 0:
        factor = 1.2
    elif freq <= 1 and intensity <= 1:
        factor = 1.3
    elif freq <= 1 and intensity <= 2:
        factor = 1.375
    elif freq <= 1:
        factor = 1.4
    elif freq <= 2 and intensity <= 1:
        factor = 1.4
    elif freq <= 2 and intensity <= 2:
        factor = 1.55
    elif freq <= 2:
        factor = 1.6
    elif freq <= 3 and intensity <= 1:
        factor = 1.5
    elif freq <= 3 and intensity <= 2:
        factor = 1.65
    elif freq <= 3:
        factor = 1.725
    elif freq >= 4 and intensity <= 1:
        factor = 1.6
    elif freq >= 4 and intensity <= 2:
        factor = 1.75
    else:
        factor = 1.9

    return round(weight * 24 * factor)


# ================================================================
# 서버 직접 실행
# ================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
