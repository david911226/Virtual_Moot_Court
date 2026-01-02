import re

# CSS 樣式表
MAIN_CSS = """
<style>
    .stApp { background-color: #131314; color: #E3E3E3; }
    [data-testid="stSidebar"] { background-color: #1E1F20; border-right: 1px solid #333; }
    
    [data-testid="stHeaderAction"] { display: none !important; }
    [data-testid="stMarkdownContainer"] h1 > a, [data-testid="stMarkdownContainer"] h2 > a { display: none !important; pointer-events: none; }
    
    [data-testid="stSidebar"] button { border-radius: 20px !important; border: none !important; text-align: left !important; padding-left: 15px !important; }
    [data-testid="stSidebar"] button[kind="secondary"] { background-color: transparent !important; color: #C4C7C5 !important; }
    [data-testid="stSidebar"] button[kind="secondary"]:hover { background-color: #303134 !important; }
    [data-testid="stSidebar"] button[kind="primary"] { background-color: #004A77 !important; color: #FFFFFF !important; font-weight: 500 !important; }
    
    .stTextArea textarea, .stTextInput input { background-color: #1E1F20; color: #E3E3E3; border: 1px solid #444746; border-radius: 10px; }
    .stChatInputContainer { padding-bottom: 20px; }
    
    /* === 1. 寬度控制與對齊：800px + 置中 === */
    [data-testid="stChatInput"] { max-width: 800px !important; margin: 0 auto !important; }
    .stMarkdown { max-width: 800px; margin: 0 auto; }
    
    /* === 強制修正 Spinner (思考中) 的對齊問題 === */
    .stSpinner {
        max-width: 800px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    div[data-testid="stSpinner"] { 
        max-width: 800px !important; 
        margin-left: auto !important; 
        margin-right: auto !important;
        width: 100% !important;
        /* 使用 flex 佈局確保內容靠左，但容器本身置中 */
        display: flex;
        justify-content: flex-start;
        padding-left: 15px !important; /* 增加內距以對齊對話氣泡文字 */
    }

    /* === 修正 st.info / st.success / st.error (Alerts) 的對齊問題 === */
    div[data-testid="stAlert"] {
        max-width: 800px !important; 
        margin-left: auto !important; 
        margin-right: auto !important;
    }

    .stVerticalBlock > div > div > div > div.stButton {
        display: flex;
        justify-content: center;
    }
    
    header[data-testid="stHeader"] { background-color: transparent; }
    
    .chat-row { 
        display: flex; 
        margin-bottom: 20px; 
        width: 100%; 
        max-width: 800px; 
        margin-left: auto; 
        margin-right: auto; 
    }
    .chat-row.user { justify-content: flex-end; }
    .chat-row.assistant { justify-content: flex-start; }
    
    .chat-bubble { padding: 12px 18px; border-radius: 18px; max-width: 85%; line-height: 1.5; font-size: 16px; }
    .chat-bubble.user { background-color: #282A2C; color: #ECECF1; border-radius: 18px 18px 4px 18px; }
    .chat-bubble.assistant { background-color: transparent; color: #ECECF1; padding-left: 0; }
    
    .chat-bubble.report {
        background-color: rgba(28, 131, 225, 0.1); 
        border: 1px solid rgba(28, 131, 225, 0.4);
        color: #e8f0fe;
        border-radius: 10px;
        padding: 20px;
        width: 100%; 
        max-width: 100%;
    }
    
    .ai-icon { margin-right: 10px; font-size: 24px; display: flex; align-items: flex-start; padding-top: 5px; }

    /* === 2. 懸浮按鈕：使用【嚴格】錨點定位法 === */
    .element-container:has(#float_anchor) + .element-container .stButton {
        position: fixed;
        top: 80px;
        right: 40px;
        z-index: 99999;
        width: auto !important;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.5);
        background-color: #131314;
        border-radius: 8px;
    }
    .element-container:has(#float_anchor) + .element-container .stButton button {
        width: auto !important;
        padding-left: 20px !important;
        padding-right: 20px !important;
    }
</style>
"""

# UI 輔助 functions

def format_message(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = text.replace('\n', '<br>')
    return text

def get_avatar(stage):
    """根據當前階段決定預設頭像"""
    if stage in ["INPUT", "DIAGNOSE"]:
        return "⚙️"
    elif stage in ["CONSULTATION", "ADVICE_REPORT"]:
        return "👩‍💼"
    else:
        return "🧑‍⚖️"