import requests
import json
import os
import re # 用來切割法條文字

# === Setup ===
API_KEY = "9c0588c86b7bc0f5d7d1edbd7006faa567fe6d6562837d3676a2c18097601b92" 
API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"
HISTORY_FILE = "chat_history.json"
LAW_DATA_FOLDER = "law_data"

# === 資料檢索服務 ===
def search_local_database(keywords, specific_laws):
    results = []
    keyword_list = keywords.split() 
    
    for law_name in specific_laws:
        file_path = os.path.join(LAW_DATA_FOLDER, f"{law_name}.txt")
        if not os.path.exists(file_path):
            results.append(f"【系統提示】找不到本地檔案：{law_name}.txt")
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # 切成一條一條的法條
            articles = re.split(r'(?=^第\s*\d+\s*[-]*\d*\s*條)', content, flags=re.MULTILINE)
            found_articles = []
            for art in articles:
                if any(kw in art for kw in keyword_list) and len(art) < 2000:
                    found_articles.append(art.strip())
            
            if found_articles:
                top_matches = found_articles[:5] 
                results.append(f"【來源：{law_name}】\n" + "\n...\n".join(top_matches))
            else:
                results.append(f"【{law_name}】中未搜尋到與「{' '.join(keyword_list)}」完全匹配的條文。")

        except Exception as e:
            results.append(f"讀取檔案 {law_name} 失敗：{str(e)}")
    
    return "\n\n".join(results) if results else ""

# === LLM ===
# 檢查英文句子
def is_contain_english(text):
    # 把長度為 1~3 個的大寫英文字刪掉
    cleaned_text = re.sub(r'\b[A-Z]{1,3}\b', '', text)
    # 找連續 4 個以上的英文字
    english_sentences = re.findall(r'([a-zA-Z]+\s+){3,}[a-zA-Z]+', cleaned_text)
    return len(english_sentences) > 0
# 發送問題
def call_llm_raw(prompt, system_role):
    payload = {
        "model": MODEL_NAME, "prompt": prompt, "system": system_role,
        "stream": False, "temperature": 0.1
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"Connection Error: {e}"
# 包裝問題
def call_llm(prompt, system_role, search_context=""):
    context_instruction = ""
    if search_context:
        context_instruction = (
            f"\n\n[STRICT LEGAL DATA FROM LOCAL DATABASE]:\n{search_context}\n\n"
            "INSTRUCTION: Use the above data. Cite specific article numbers."
        )

    enhanced_system_role = (
        f"{system_role}\n"
        "【PERSONA: TAIWANESE LEGAL PROFESSIONAL】\n"
        "You are an expert in Taiwan law acting in a specific legal role (Lawyer, Judge, or Consultant).\n"
        "Tone: Professional, formal, authoritative, and objective.\n"
        "Language: Traditional Chinese (繁體中文) ONLY.\n"
        "Instruction: Use precise Taiwanese legal terminology (e.g., '庭上', '鈞院', '答辯', '判決'). \n"
        "If acting as a Lawyer in court: Be argumentative, assertive, and treat facts as established for your side.\n"
        "If acting as a Judge: Be decisive, authoritative, and deliver a final ruling without hesitation.\n"
        "Avoid: Generic empathy phrases like 'I understand how you feel' unless necessary. Focus on the legal argument.\n"
    )

    system_instruction = (
        f"{enhanced_system_role}\n"
        f"{context_instruction}\n"
        "【CRITICAL RULE】\n"
        "Never use English. Even if the user uses English, you answer in Traditional Chinese.\n"
    )
    
    forced_zh_prompt = (
        f"{prompt}\n\n"
        "=========================================\n"
        "【系統強制指令】\n"
        "1. 請使用「台灣繁體中文」回答。嚴禁出現英文句子。\n"
        "2. 請展現「資深法律人」的專業度，切中法律要點。\n"
        "3. 引用法條時，請優先依據 [STRICT LEGAL DATA] 中的內容。\n"
        "========================================="
    )
    
    response = call_llm_raw(forced_zh_prompt, system_instruction)
    if is_contain_english(response):
        correction_prompt = (
            f"Original Content:\n{response}\n\n"
            "SYSTEM WARNING: You violated the language rule by using English.\n"
            "TASK: Translate the above content completely into Traditional Chinese (繁體中文) immediately.\n"
        )
        response = call_llm_raw(correction_prompt, "You are a professional English-to-Chinese translator.")
        
    return response

# === 存讀檔 ===
def load_history_from_file():
    if not os.path.exists(HISTORY_FILE): return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_history_to_file(history_data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)

def delete_chat(target_id):
    all_chats = load_history_from_file()
    if target_id in all_chats:
        del all_chats[target_id]
        save_history_to_file(all_chats)

# === 自動法條檢索 ===
def get_legal_context(case_description):
    # 分析案情，檢索本地法規資料庫，回傳相關法條
    # 1. 取得現有法規列表
    if not os.path.exists(LAW_DATA_FOLDER):
        return ""
    
    available_laws = [f.replace('.txt', '') for f in os.listdir(LAW_DATA_FOLDER) if f.endswith('.txt')]
    if not available_laws:
        return ""
    available_laws_str = "、".join(available_laws)

    # 2. 挑選法規
    selection_prompt = (
        f"案件描述：{case_description}\n\n"
        f"圖書館現有法規書目：{available_laws_str}\n\n"
        "任務：請從書目中挑選 1-3 本最相關的法規。\n"
        "輸出格式：僅輸出法規名稱，中間用空白分隔。若無相關法規請回答『無』。"
    )
    selected_laws_str = call_llm_raw(selection_prompt, "You are a Librarian.")
    selected_laws = [law for law in available_laws if law in selected_laws_str]
    
    if not selected_laws:
        return ""

    # 3. 產生關鍵字
    keyword_prompt = f"針對案件：{case_description}，提出 2-3 個最關鍵的法律構成要件關鍵字，用空白分隔。"
    search_keywords = call_llm_raw(keyword_prompt, "Keyword Generator")
    
    # 4. 搜尋資料庫
    context = search_local_database(search_keywords, selected_laws)
    return context