import streamlit as st
import uuid
import os
import backend
import ui

# === 介面 Init ===
st.set_page_config(page_title="Virtual Moot Court", page_icon="⚖️", layout="wide")
st.markdown(ui.MAIN_CSS, unsafe_allow_html=True)

# === Session State Init ===
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = str(uuid.uuid4())
if "stage" not in st.session_state: st.session_state.stage = "INPUT"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "full_case_context" not in st.session_state: st.session_state.full_case_context = ""
if "consult_step" not in st.session_state: st.session_state.consult_step = 0
if "strategy" not in st.session_state: st.session_state.strategy = ""
if "court_done" not in st.session_state: st.session_state.court_done = False
if "court_step" not in st.session_state: st.session_state.court_step = 0 
if "court_logs" not in st.session_state: st.session_state.court_logs = {}

# === 流程控制 ===
def auto_save(title=None):
    try:
        # 讀取目前所有的舊紀錄
        all_chats = backend.load_history_from_file()
        # 決定標題
        current_title = all_chats.get(st.session_state.current_chat_id, {}).get("title", "新案件")
        if title: current_title = title
        
        # 準備存檔資料
        chat_data = {
            "title": current_title, "stage": st.session_state.stage,
            "chat_history": st.session_state.chat_history, "full_case_context": st.session_state.full_case_context,
            "strategy": st.session_state.strategy, "consult_step": st.session_state.consult_step,
            "court_done": st.session_state.court_done, "court_step": st.session_state.court_step,
            "court_logs": st.session_state.court_logs
        }
        # 存檔
        backend.save_history_to_file({**all_chats, st.session_state.current_chat_id: chat_data})
    except Exception as e:
        st.error(f"存檔失敗：{e}")

def start_new_chat():
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.stage = "INPUT"
    st.session_state.chat_history = []
    st.session_state.full_case_context = ""
    st.session_state.strategy = ""
    st.session_state.consult_step = 0
    st.session_state.court_done = False
    st.session_state.court_step = 0
    st.session_state.court_logs = {}

def add_message(role, content, avatar=None):
    msg_data = {"role": role, "content": content}
    if role == "assistant":
        # 若未指定頭像，則使用 ui 模組根據當前 stage 判斷
        msg_data["avatar"] = avatar if avatar else ui.get_avatar(st.session_state.stage)
    st.session_state.chat_history.append(msg_data)

@st.dialog("為此案件命名") # 彈出視窗
def naming_dialog(case_desc):
    st.write("請輸入一個標題，方便日後在側邊欄查找。")
    with st.form("naming_form"):
        raw_title = st.text_input("案件標題", value="", placeholder="新案件", key=f"title_input_{st.session_state.current_chat_id}")
        submitted = st.form_submit_button("確認", type="primary")
        if submitted:
            final_title = raw_title.strip() if raw_title.strip() else "新案件"
            # 存入使用者的案情描述
            st.session_state.full_case_context = f"當事人初步描述：{case_desc}"
            # 寫入第一組對話
            if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != case_desc:
                add_message("user", case_desc)
                add_message("assistant", f"了解。為了進一步評估，請問您手邊有任何**證據**嗎？例如照片、影片、錄音、報警紀錄或是證人？")
            # 準備進入 DIAGNOSE
            st.session_state.consult_step = 1
            st.session_state.stage = "DIAGNOSE"
            # 存檔並重整頁面
            auto_save(title=final_title)
            st.rerun()

# Sidebar
with st.sidebar:
    if st.button("＋ 新增諮詢", use_container_width=True, type="secondary"):
        start_new_chat()
        st.rerun()
    # 顯示標題
    st.markdown("<div style='margin-top: 20px; color: #888; font-size: 0.8em; padding-left: 10px;'>對話紀錄</div>", unsafe_allow_html=True)
    # 讀取歷史紀錄
    all_chats = backend.load_history_from_file()
    chat_ids = list(reversed(list(all_chats.keys())))
    # 畫出每一個案件按鈕
    for chat_id in chat_ids:
        chat_data = all_chats[chat_id]
        title = chat_data.get("title", "未命名案件")
        is_active = (chat_id == st.session_state.current_chat_id) # 判斷這個按鈕是不是當前案件
        btn_type = "primary" if is_active else "secondary"
        col1, col2 = st.columns([0.85, 0.15], gap="small", vertical_alignment="center")
        with col1:
            if st.button(title, key=f"load_{chat_id}", type=btn_type, use_container_width=True):
                st.session_state.current_chat_id = chat_id
                st.session_state.stage = chat_data["stage"]
                st.session_state.chat_history = chat_data["chat_history"]
                st.session_state.full_case_context = chat_data["full_case_context"]
                st.session_state.strategy = chat_data["strategy"]
                st.session_state.consult_step = chat_data.get("consult_step", 0)
                st.session_state.court_done = chat_data.get("court_done", False)
                st.session_state.court_step = chat_data.get("court_step", 0)
                st.session_state.court_logs = chat_data.get("court_logs", {})
                st.rerun()
        with col2:
            with st.popover(" ", use_container_width=True):
                st.caption(f"管理：{title}")
                with st.form(key=f"rename_form_{chat_id}", border=False):
                    new_name = st.text_input("修改名稱", value=title)
                    if st.form_submit_button("確認"): 
                        all_chats[chat_id]["title"] = new_name
                        backend.save_history_to_file(all_chats)
                        st.rerun()
                if st.button("刪除", key=f"del_btn_{chat_id}", type="primary"):
                    backend.delete_chat(chat_id)
                    st.rerun()

# 主畫面 UI 渲染
if not st.session_state.chat_history and st.session_state.stage == "INPUT":
    st.markdown("""
        <div style="text-align: center; margin-bottom: 40px; max-width: 800px; margin-left: auto; margin-right: auto;">
            <h1 style="background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5em;">
                ⚖️ Virtual Moot Court
            </h1>
            <h3 style="color: #666;">輸入案情，開始模擬法庭攻防</h3>
        </div>
    """, unsafe_allow_html=True)
else:
    st.caption("Virtual Moot Court")

# 對話紀錄顯示
for msg in st.session_state.chat_history:
    role = msg["role"]
    content = msg["content"]
    formatted_content = ui.format_message(content)
    
    if role == "user":
        # 如果是使用者，畫在右邊
        st.markdown(f"""<div class="chat-row user"><div class="chat-bubble user">{formatted_content}</div></div>""", unsafe_allow_html=True)
    else:
        # 如果是 AI，畫在左邊
        saved_avatar = msg.get("avatar", "🤖")
        # 特殊的藍底樣式
        if any(keyword in content for keyword in ["【律師分析報告】", "【原告律師】", "【被告律師】", "【法官判決】", "【結案分析】"]):
             st.markdown(f"""
                <div class="chat-row assistant">
                    <div class="ai-icon">{saved_avatar}</div>
                    <div class="chat-bubble report">{formatted_content}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-row assistant">
                    <div class="ai-icon">{saved_avatar}</div>
                    <div class="chat-bubble assistant">{formatted_content}</div>
                </div>
            """, unsafe_allow_html=True)

# === State Machine ===
if st.session_state.stage == "INPUT":
    if not st.session_state.chat_history:
        user_input = st.chat_input("請簡述案情")
        if user_input: naming_dialog(user_input)

elif st.session_state.stage == "DIAGNOSE":
    if st.session_state.chat_history[-1]["role"] == "assistant":
        user_reply = st.chat_input("請輸入回答...")
        if user_reply:
            add_message("user", user_reply)
            st.session_state.full_case_context += f"\n補充資訊：{user_reply}"
            if st.session_state.consult_step == 1:
                add_message("assistant", "收到。最後想請問您的**具體訴求**是什麼？是希望對方賠償金額、公開道歉，還是只要停止行為即可？")
                st.session_state.consult_step = 2
                auto_save()
                st.rerun()
            elif st.session_state.consult_step == 2:
                st.session_state.consult_step = 3
                auto_save()
                st.rerun()

    if st.session_state.consult_step == 3:
        st.markdown("---")
        st.write("已蒐集完基本訊息，請選擇下一步：")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("👩‍⚖️ 進入深入法律諮詢", use_container_width=True):
                    st.session_state.stage = "CONSULTATION"
                    auto_save()
                    st.rerun()
            with col_b:
                if st.button("🏛️ 直接進入模擬法庭", use_container_width=True, type="primary"):
                    st.session_state.stage = "STRATEGY"
                    auto_save()
                    st.rerun()

elif st.session_state.stage == "CONSULTATION":
    st.markdown('<div id="float_anchor"></div>', unsafe_allow_html=True)
    if st.button("資訊已充足，生成分析報告", type="primary"):
        st.session_state.stage = "ADVICE_REPORT"
        auto_save()
        st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        with st.spinner("AI 律師正在思考法律爭點（並翻閱法條）..."):
            # 法條檢索
            legal_context = backend.get_legal_context(st.session_state.full_case_context)
            prompt = f"案件全貌：{st.session_state.full_case_context}\n使用者最新發言：{st.session_state.chat_history[-1]['content']}\n任務：請扮演專業台灣律師。針對使用者的事實陳述，追問具有法律意義的細節（例如證據能力、具體損失、因果關係）。不要說廢話。"
            ai_reply = backend.call_llm(prompt, "你是專業的台灣資深律師。", search_context=legal_context)
            add_message("assistant", ai_reply)
        auto_save()
        st.rerun()
    
    user_reply = st.chat_input("請回答律師的問題，或提出您的疑問...")
    if user_reply:
        add_message("user", user_reply)
        st.session_state.full_case_context += f"\n補充資訊：{user_reply}"
        auto_save()
        st.rerun()

elif st.session_state.stage == "ADVICE_REPORT":
    st.markdown("#### 👩‍⚖️ 法律顧問分析報告")
    
    if not any("律師分析報告" in str(msg) for msg in st.session_state.chat_history):
        available_laws = []
        if os.path.exists(backend.LAW_DATA_FOLDER):
            available_laws = [f.replace('.txt', '') for f in os.listdir(backend.LAW_DATA_FOLDER) if f.endswith('.txt')]
        if not available_laws:
            st.error(f"❌ 找不到本地法規檔案！請將 .txt 檔案放入 `{backend.LAW_DATA_FOLDER}` 資料夾中。")
            st.stop()
        available_laws_str = "、".join(available_laws)

        with st.spinner("Step 1: 分析案情，調閱法典中..."):
            selection_prompt = (
                f"案件描述：{st.session_state.full_case_context}\n\n"
                f"圖書館現有法規書目：{available_laws_str}\n\n"
                "任務：請從書目中挑選 1-3 本最相關的法規。"
            )
            selected_laws_str = backend.call_llm(selection_prompt, "You are a Librarian.")
            selected_laws = [law for law in available_laws if law in selected_laws_str]
            if not selected_laws and available_laws: selected_laws = [] 
            st.caption(f"已選定參考法典：{'、'.join(selected_laws) if selected_laws else '無'}")

        with st.spinner(f"Step 2: 檢索關鍵條文..."):
            keyword_prompt = f"針對案件：{st.session_state.full_case_context}，提出 2-3 個最關鍵的法律構成要件關鍵字，用空白分隔。"
            search_keywords = backend.call_llm(keyword_prompt, "Keyword Generator")
            final_context = ""
            if selected_laws:
                final_context = backend.search_local_database(search_keywords, selected_laws)
            
        with st.spinner("Step 3: 撰寫正式法律意見書..."):
            advice = backend.call_llm(
                f"案件全貌：{st.session_state.full_case_context}\n請撰寫一份專業的法律分析報告，包含：\n"
                f"1. **法律觀點與涵攝**：引用上述提供的真實法條，並說明本案事實如何適用該條文。\n"
                f"2. **勝訴率評估**：客觀分析。\n"
                f"3. **具體行動建議**。\n"
                f"4. **證據蒐集指南**：針對本案缺少的證據提出建議。\n\n"
                f"請注意：必須優先依據【本地資料庫】中的精確條文文字，嚴禁編造法條。",
                "你是專業律師。語氣專業、客觀。",
                search_context=final_context 
            )
            
            add_message("assistant", f"【律師分析報告】\n(參考資料：{', '.join(selected_laws)}、{search_keywords})\n{advice}")
            auto_save()
            st.rerun() 
    else:
        st.info("（分析報告已生成，請見上方對話紀錄最後一則）")

    st.markdown("---")
    st.write("看完分析後，您可以選擇進入模擬法庭，觀看雙方律師與法官的攻防。")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🏛️ 進入模擬法庭", type="primary", use_container_width=True):
            st.session_state.stage = "STRATEGY"
            auto_save()
            st.rerun()

elif st.session_state.stage == "STRATEGY":
    st.markdown("#### 🤔 選擇被告辯護策略")
    
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        col1, col2, col3 = st.columns(3)
        def set_strategy(strat_text):
            st.session_state.strategy = strat_text
            st.session_state.stage = "COURT"
            # 重置 Court 狀態
            st.session_state.court_step = 0 
            st.session_state.court_done = False
            st.session_state.court_logs = {}
            auto_save()
            st.rerun()
        with col1:
            if st.button("強硬否認", use_container_width=True): set_strategy("強硬否認，主張證據不足。")
        with col2:
            if st.button("減輕責任", use_container_width=True): set_strategy("承認部分事實，請求輕判。")
        with col3:
            if st.button("AI 自動判定", use_container_width=True): set_strategy("請自動選擇最有利策略。")

elif st.session_state.stage == "COURT":
    st.markdown("#### 🏛️ 虛擬法庭開庭")
    
    if not st.session_state.court_done:
        if st.session_state.court_step == 0:
            with st.spinner("原告律師正在陳述..."):
                # 法條檢索
                legal_context = backend.get_legal_context(st.session_state.full_case_context)
                p_opening = backend.call_llm(
                    f"案件：{st.session_state.full_case_context}", 
                    "你是法庭上的原告律師。請進行【法庭開場陳述】。面對法官（稱呼『庭上』或『鈞院』），語氣必須堅定、具攻擊性。請依據案情主張被告已構成侵權或犯罪，並引用台灣法律條文，具體提出訴訟請求（如賠償或刑責）。請把案情當作『既定事實』來陳述，不要說『可能』或『需要調查』。目標是說服法官判決勝訴。",
                    search_context=legal_context
                )
                st.session_state.court_logs["p_opening"] = p_opening
                add_message("assistant", f"**【原告律師】**\n\n{p_opening}", avatar="⚔️")
                st.session_state.court_step = 1
                auto_save()
                st.rerun()

        elif st.session_state.court_step == 1:
            with st.spinner("被告律師正在反駁..."):
                # 加入法條檢索
                legal_context = backend.get_legal_context(st.session_state.full_case_context)
                p_prev = st.session_state.court_logs.get("p_opening", "")
                d_opening = backend.call_llm(
                    f"原告說：{p_prev}\n請反駁。", 
                    f"你是法庭上的被告律師。請進行【法庭答辯】。面對法官，語氣強硬。針對原告的指控進行反駁，主張被告無過失或無罪。請引用法律條文支持你的論點。策略：{st.session_state.strategy}。",
                    search_context=legal_context
                )
                st.session_state.court_logs["d_opening"] = d_opening
                add_message("assistant", f"**【被告律師】**\n\n{d_opening}", avatar="🛡️")
                st.session_state.court_step = 2
                auto_save()
                st.rerun()

        elif st.session_state.court_step == 2:
            with st.spinner("法官正在撰寫判決書..."):
                # 加入法條檢索
                legal_context = backend.get_legal_context(st.session_state.full_case_context)
                p_prev = st.session_state.court_logs.get("p_opening", "")
                d_prev = st.session_state.court_logs.get("d_opening", "")
                verdict = backend.call_llm(
                    f"案件：{st.session_state.full_case_context}\n辯論：{p_prev}\n{d_prev}", 
                    "你是台灣法院法官。請進行【宣判】。語氣必須權威、果斷。請綜合雙方陳述，引用相關法律條文（如民法、刑法），直接給出判決結果（主文）。不要說『初步認為』或『建議繼續調查』，請基於現有資訊做出最終判決。",
                    search_context=legal_context
                )
                st.session_state.court_logs["verdict"] = verdict
                add_message("assistant", f"**【法官判決】**\n\n{verdict}", avatar="👨‍⚖️")
                st.session_state.court_step = 3
                auto_save()
                st.rerun()

        elif st.session_state.court_step == 3:
            with st.spinner("AI 顧問正在分析勝訴率..."):
                # 加入法條檢索
                legal_context = backend.get_legal_context(st.session_state.full_case_context)
                logs = st.session_state.court_logs
                analysis = backend.call_llm(
                    f"基於模擬法庭結果（判決：{logs.get('verdict')}），請以 AI 法律顧問的角度，為使用者進行總結分析。\n"
                    f"1. **勝訴機率評估** (以百分比表示)\n"
                    f"2. **推薦的解決方法** (如和解、訴訟技巧)\n"
                    "語氣：專業、客觀、友善。", 
                    "你是法律顧問。",
                    search_context=legal_context
                )
                st.session_state.court_logs["analysis"] = analysis
                add_message("assistant", f"**【結案分析】**\n\n{analysis}", avatar="🤖")
                st.session_state.stage = "CASE_CLOSED"
                auto_save()
                st.rerun()

elif st.session_state.stage == "CASE_CLOSED":
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.caption("👨‍⚖️ 本次模擬法庭已結束。")
        if st.button("＋ 開始新的法律諮詢", type="primary", use_container_width=True):
            start_new_chat()
            st.rerun()