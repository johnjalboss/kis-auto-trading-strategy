"""
AI 스윙 트레이딩 봇 - 원클릭 통합 설정 마법사 (setup_wizard.py)
======================================================
초보자도 메모장 수정 없이 한투 API, 구글 Gemini, Finnhub, FRED, 텔레그램 토큰, 
구동 방식(로컬 PC / 원격 오라클 클라우드)을 안전하게 입력 및 배포할 수 있는 
고해상도(High-DPI) 프리미엄 GUI 설정 프로그램입니다.
"""

import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests

# Windows High-DPI 지원 활성화 (글자 흐림 및 잘림 현상 원천 방지)
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# SSH/SCP 원격 배포를 위한 paramiko 임포트
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

# ----------------------------------------------------
# 테마 및 색상 정의 (Nordic Clean Modern Theme)
# ----------------------------------------------------
BG_COLOR = "#f4f6f9"
SURFACE_COLOR = "#ffffff"
TEXT_COLOR = "#1e293b"
TEXT_MUTED = "#64748b"
ACCENT_BLUE = "#3b82f6"
ACCENT_BLUE_HOVER = "#2563eb"
ACCENT_GREEN = "#10b981"
ACCENT_GREEN_HOVER = "#059669"
ACCENT_PURPLE = "#8b5cf6"
BORDER_COLOR = "#e2e8f0"
ENTRY_BG = "#f8fafc"
HEADER_BG = "#1e293b"


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#1e293b", foreground="#ffffff", relief='flat',
                         font=("Malgun Gothic", 9, "normal"), padx=8, pady=5)
        label.pack()

    def hide(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class SetupWizardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🕊️ AI 스윙 트레이딩 봇 - 올인원 설정 마법사 [2026 Master Edition]")
        self.root.geometry("900x750")
        self.root.minsize(860, 700)
        self.root.resizable(True, True)
        self.root.configure(bg=BG_COLOR)
        
        # 윈도우 타이틀바 아이콘 등록
        if os.path.exists("trading_bot_logo.ico"):
            try:
                self.root.iconbitmap("trading_bot_logo.ico")
            except Exception:
                pass
        
        # 1. KIS 증권사 API 변수
        self.var_appkey = tk.StringVar()
        self.var_secret = tk.StringVar()
        self.var_cano = tk.StringVar()
        self.var_acnt_code = tk.StringVar(value="01")
        self.var_trading_env = tk.StringVar(value="PROD")  # PROD (실전) or VIRT (모의)
        
        # 2. AI & 퀀트 외부 API 변수
        self.var_gemini_key = tk.StringVar()
        self.var_finnhub_key = tk.StringVar()
        self.var_fred_key = tk.StringVar()
        
        # 3. 텔레그램 알림봇 변수
        self.var_tg_token = tk.StringVar()
        self.var_tg_chat_id = tk.StringVar()
        
        # 4. 구동 모드 & 서버 변수
        self.var_mode = tk.StringVar(value="LOCAL")  # LOCAL or SERVER
        self.var_server_host = tk.StringVar()
        self.var_server_user = tk.StringVar(value="ubuntu")
        self.var_server_key_path = tk.StringVar()
        
        # 5. 매매 조건 변수
        self.var_capital = tk.StringVar(value="2000")
        self.var_max_pos = tk.StringVar(value="3")
        self.var_min_score = tk.StringVar(value="60")
        self.var_stop_loss = tk.StringVar(value="3.8")
        self.var_screener_max_candidates = tk.StringVar(value="300")
        
        # 기존 .env 로드
        self.load_existing_config()
        
        self.setup_ui()
        
    def load_existing_config(self):
        """기존 .env 파일이 있으면 읽어서 입력폼에 채움"""
        if os.path.exists(".env"):
            try:
                with open(".env", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        
                        # KIS Keys
                        if k in ("KIS_APP_KEY", "KIS_APPKEY"): self.var_appkey.set(v)
                        elif k in ("KIS_APP_SECRET", "KIS_SECRET"): self.var_secret.set(v)
                        elif k == "KIS_CANO": self.var_cano.set(v)
                        elif k == "KIS_ACNT_PRDT_CD": self.var_acnt_code.set(v)
                        elif k == "TRADING_ENV": self.var_trading_env.set(v.upper())
                        elif k == "KIS_SANDBOX": self.var_trading_env.set("VIRT" if v.upper() == "TRUE" else "PROD")
                        
                        # External APIs
                        elif k == "GEMINI_API_KEY": self.var_gemini_key.set(v)
                        elif k == "FINNHUB_API_KEY": self.var_finnhub_key.set(v)
                        elif k == "FRED_API_KEY": self.var_fred_key.set(v)
                        
                        # Telegram
                        elif k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN"): self.var_tg_token.set(v)
                        elif k == "TELEGRAM_CHAT_ID": self.var_tg_chat_id.set(v)
                        
                        # Parameters
                        elif k == "INITIAL_CAPITAL": self.var_capital.set(v)
                        elif k == "MAX_POSITIONS": self.var_max_pos.set(v)
                        elif k == "MIN_ENTRY_SCORE": self.var_min_score.set(v)
                        elif k == "DAILY_STOP_LOSS_PCT": self.var_stop_loss.set(v)
                        elif k == "SCREENER_MAX_CANDIDATES": self.var_screener_max_candidates.set(v)
                        
                        # Remote Deploy
                        elif k == "RUN_MODE": self.var_mode.set(v)
                        elif k == "REMOTE_HOST": self.var_server_host.set(v)
                        elif k == "REMOTE_USER": self.var_server_user.set(v)
                        elif k == "REMOTE_KEY": self.var_server_key_path.set(v)
            except Exception as e:
                print("이전 설정 로드 오류:", e)

    def add_button_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda e: button.configure(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.configure(bg=normal_bg))

    def setup_ui(self):
        # 상단 모던 헤더
        header_frame = tk.Frame(self.root, bg=HEADER_BG, height=75)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="✨ AI SOTA 퀀트 스윙 트레이딩 봇", font=("Malgun Gothic", 15, "bold"), fg="#ffffff", bg=HEADER_BG)
        title_label.pack(anchor="w", padx=25, pady=(14, 0))
        
        subtitle_label = tk.Label(header_frame, text="초보자를 위한 원클릭 API 설정, 실시간 연결 검증 및 자동 매매 런처", font=("Malgun Gothic", 9), fg="#94a3b8", bg=HEADER_BG)
        subtitle_label.pack(anchor="w", padx=25, pady=(2, 0))
        
        # 하단 액션 버튼 바
        bottom_frame = tk.Frame(self.root, bg=SURFACE_COLOR, height=70, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        bottom_frame.pack_propagate(False)
        
        # 1. 연결 검증 버튼
        self.btn_test = tk.Button(
            bottom_frame, 
            text="🔌 5대 API 연결 검증 및 테스트", 
            font=("Malgun Gothic", 10, "bold"), 
            fg="#ffffff", 
            bg=ACCENT_GREEN, 
            activebackground=ACCENT_GREEN_HOVER, 
            borderwidth=0, 
            cursor="hand2", 
            padx=20, 
            pady=9, 
            command=self.run_connection_test
        )
        self.btn_test.pack(side=tk.LEFT, padx=20, pady=15)
        self.add_button_hover(self.btn_test, ACCENT_GREEN, ACCENT_GREEN_HOVER)
        
        # 2. 설정 저장 및 구동 시작 버튼
        self.btn_save = tk.Button(
            bottom_frame, 
            text="🚀 설정 저장 및 구동 시작", 
            font=("Malgun Gothic", 10, "bold"), 
            fg="#ffffff", 
            bg=ACCENT_BLUE, 
            activebackground=ACCENT_BLUE_HOVER, 
            borderwidth=0, 
            cursor="hand2", 
            padx=24, 
            pady=9, 
            command=self.save_and_execute
        )
        self.btn_save.pack(side=tk.RIGHT, padx=20, pady=15)
        self.add_button_hover(self.btn_save, ACCENT_BLUE, ACCENT_BLUE_HOVER)
        
        # 탭 노트북 스타일 커스텀
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=BG_COLOR, borderwidth=0)
        style.configure('TNotebook.Tab', background="#e2e8f0", foreground=TEXT_MUTED, borderwidth=0, padding=[16, 9], font=("Malgun Gothic", 10, "bold"))
        style.map('TNotebook.Tab', background=[('selected', SURFACE_COLOR)], foreground=[('selected', ACCENT_BLUE)])
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # 5대 탭 프레임 생성
        self.tab_kis = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_ai = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_tg = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_mode = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_opt = tk.Frame(self.notebook, bg=BG_COLOR)
        
        self.notebook.add(self.tab_kis, text=" 📈 1. 한투 증권 계좌 ")
        self.notebook.add(self.tab_ai, text=" 🧠 2. AI & 퀀트 API ")
        self.notebook.add(self.tab_tg, text=" 📱 3. 텔레그램 알림 ")
        self.notebook.add(self.tab_mode, text=" 🖥️ 4. 구동 및 서버 배포 ")
        self.notebook.add(self.tab_opt, text=" ⚙️ 5. 매매 세부 설정 ")
        
        self.build_kis_tab()
        self.build_ai_tab()
        self.build_tg_tab()
        self.build_mode_tab()
        self.build_opt_tab()

    # ----------------------------------------------------
    # 탭 1: 한국투자증권 계좌 탭
    # ----------------------------------------------------
    def build_kis_tab(self):
        container = tk.Frame(self.tab_kis, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_label_section(container, "한국투자증권(KIS) Open API 계정 설정", 
                                  "KIS Developers 개발자센터(apiportal.koreainvestment.com)에서 발급받은 키를 입력합니다.")
        
        self.create_input_row(container, "APP KEY", self.var_appkey, placeholder="한국투자증권에서 발급된 36자리 APP Key", show="*")
        self.create_input_row(container, "SECRET KEY", self.var_secret, placeholder="한국투자증권 Secret Key를 입력하세요", show="*")
        
        # 계좌번호 프레임
        account_frame = tk.Frame(container, bg=SURFACE_COLOR)
        account_frame.pack(fill=tk.X, padx=25, pady=8)
        
        tk.Label(account_frame, text="종합계좌번호", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=22, anchor="w").pack(side=tk.LEFT)
        
        cano_entry = tk.Entry(account_frame, textvariable=self.var_cano, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR, width=16)
        cano_entry.pack(side=tk.LEFT, ipady=3)
        ToolTip(cano_entry, "종합계좌번호 앞 8자리 숫자 (CANO)")
        
        tk.Label(account_frame, text="-", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, padx=6).pack(side=tk.LEFT)
        
        code_entry = tk.Entry(account_frame, textvariable=self.var_acnt_code, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR, width=6)
        code_entry.pack(side=tk.LEFT, ipady=3)
        ToolTip(code_entry, "계좌 상품코드 뒤 2자리 (보통 01)")
        
        # 실전 / 모의 라디오 버튼
        env_frame = tk.Frame(container, bg=SURFACE_COLOR)
        env_frame.pack(fill=tk.X, padx=25, pady=12)
        
        tk.Label(env_frame, text="투자 환경 선택", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=22, anchor="w").pack(side=tk.LEFT)
        
        r_prod = tk.Radiobutton(env_frame, text="실전투자 (Real Live PROD)", variable=self.var_trading_env, value="PROD", font=("Malgun Gothic", 10, "bold"), fg="#16a34a", bg=SURFACE_COLOR, activebackground=SURFACE_COLOR, cursor="hand2")
        r_prod.pack(side=tk.LEFT, padx=(0, 15))
        
        r_virt = tk.Radiobutton(env_frame, text="모의투자 (Mock Sandbox VIRT)", variable=self.var_trading_env, value="VIRT", font=("Malgun Gothic", 10), fg=TEXT_MUTED, bg=SURFACE_COLOR, activebackground=SURFACE_COLOR, cursor="hand2")
        r_virt.pack(side=tk.LEFT)

    # ----------------------------------------------------
    # 탭 2: AI & 퀀트 외부 API 탭 (Gemini, Finnhub, FRED)
    # ----------------------------------------------------
    def build_ai_tab(self):
        container = tk.Frame(self.tab_ai, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_label_section(container, "인공지능 & 거시경제 퀀트 API (100% 무료 발급)", 
                                  "뉴스 감성 분석, 기업 실적 발표(PEAD), 연준 거시경제 데이터를 실시간 수집합니다.")
        
        # 1. 구글 제미나이 AI 키
        self.create_input_row(container, "🌟 Google Gemini API", self.var_gemini_key, 
                              placeholder="Google AI Studio(aistudio.google.com)에서 발급된 무료 AIzaSy... 키", show="*")
        
        # 2. 핀허브 API 키
        self.create_input_row(container, "🏢 Finnhub API Key", self.var_finnhub_key, 
                              placeholder="Finnhub.io 대시보드에서 무료 발급된 API 키", show="*")
        
        # 3. FRED API 키
        self.create_input_row(container, "🏛️ FRED API Key", self.var_fred_key, 
                              placeholder="세인트루이스 연준(fred.stlouisfed.org)에서 무료 발급된 32자리 API 키", show="*")
        
        tip_frame = tk.Frame(container, bg=SURFACE_COLOR)
        tip_frame.pack(fill=tk.X, padx=25, pady=15)
        
        tip_text = (
            "💡 무료 API 발급 안내 (모두 가입 즉시 1분 컷 무료 발급):\n"
            "  1. Google Gemini AI: https://aistudio.google.com/ ➔ [Get API key] 클릭\n"
            "  2. Finnhub (기업 실적/내부자): https://finnhub.io/ ➔ 회원가입 후 대시보드 API Key 복사\n"
            "  3. FRED (연준 거시경제/금리): https://fred.stlouisfed.org/ ➔ My Account ➔ API Keys 발급"
        )
        tk.Label(tip_frame, text=tip_text, font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=SURFACE_COLOR, justify="left").pack(anchor="w")

    # ----------------------------------------------------
    # 탭 3: 텔레그램 알림 탭
    # ----------------------------------------------------
    def build_tg_tab(self):
        container = tk.Frame(self.tab_tg, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_label_section(container, "텔레그램 실시간 알림 & 32개 버튼 리모컨", 
                                  "거래 체결, 익절/손절 보고서 및 스마트폰 원격 제어를 위한 텔레그램 설정을 입력합니다.")
        
        self.create_input_row(container, "봇 토큰 (Bot Token)", self.var_tg_token, placeholder="7888401155:AAG0oSg...", show="*")
        self.create_input_row(container, "사용자 채팅 ID (Chat ID)", self.var_tg_chat_id, placeholder="@userinfobot 으로 조회한 숫자 아이디 (예: 6807414163)")
        
        tip_frame = tk.Frame(container, bg=SURFACE_COLOR)
        tip_frame.pack(fill=tk.X, padx=25, pady=15)
        
        tip_text = (
            "💡 텔레그램 연결 3단계:\n"
            "  1. 텔레그램 검색창에 '@BotFather' 검색 ➔ /newbot 입력 ➔ 봇 생성 후 'HTTP API Token' 복사\n"
            "  2. 텔레그램 검색창에 '@userinfobot' 검색 ➔ 아무 메시지나 전송 ➔ 숫자 'Id: 12345678' 복사\n"
            "  3. 내가 만든 봇 대화방 링크로 들어가 반드시 [시작] 버튼을 한 번 눌러주세요!"
        )
        tk.Label(tip_frame, text=tip_text, font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=SURFACE_COLOR, justify="left").pack(anchor="w")

    # ----------------------------------------------------
    # 탭 4: 구동 및 서버 배포 탭
    # ----------------------------------------------------
    def build_mode_tab(self):
        container = tk.Frame(self.tab_mode, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_label_section(container, "시스템 구동 및 클라우드 배포 모드", 
                                  "개인 윈도우 PC에서 직접 실행하거나, 오라클 클라우드 평생 무료 VPS(Linux)에 자동 배포합니다.")
        
        mode_frame = tk.Frame(container, bg=SURFACE_COLOR)
        mode_frame.pack(fill=tk.X, padx=25, pady=10)
        
        tk.Label(mode_frame, text="구동 환경 선택", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=22, anchor="w").pack(side=tk.LEFT)
        
        r_local = tk.Radiobutton(mode_frame, text="내 윈도우 PC 로컬 구동", variable=self.var_mode, value="LOCAL", font=("Malgun Gothic", 10), bg=SURFACE_COLOR, fg=TEXT_COLOR, activebackground=SURFACE_COLOR, command=self.toggle_mode_fields, cursor="hand2")
        r_local.pack(side=tk.LEFT, padx=(0, 15))
        
        r_server = tk.Radiobutton(mode_frame, text="오라클 클라우드 VPS 원격 자동 배포", variable=self.var_mode, value="SERVER", font=("Malgun Gothic", 10), bg=SURFACE_COLOR, fg=TEXT_COLOR, activebackground=SURFACE_COLOR, command=self.toggle_mode_fields, cursor="hand2")
        r_server.pack(side=tk.LEFT)
        
        self.server_info_frame = tk.LabelFrame(container, text="🔒 원격 클라우드 서버 접속 정보 (SSH)", font=("Malgun Gothic", 9, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.server_info_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)
        
        self.create_input_row(self.server_info_frame, "서버 공인 IP", self.var_server_host, placeholder="예: 141.148.172.12")
        self.create_input_row(self.server_info_frame, "SSH 계정명", self.var_server_user, placeholder="ubuntu, root 등")
        
        key_frame = tk.Frame(self.server_info_frame, bg=SURFACE_COLOR)
        key_frame.pack(fill=tk.X, padx=20, pady=6)
        
        tk.Label(key_frame, text="SSH 개인키 (Key)", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=20, anchor="w").pack(side=tk.LEFT)
        
        key_entry = tk.Entry(key_frame, textvariable=self.var_server_key_path, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR)
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        
        btn_key = tk.Button(key_frame, text="파일 찾기...", font=("Malgun Gothic", 9), fg=TEXT_COLOR, bg=BORDER_COLOR, bd=0, cursor="hand2", padx=10, pady=2, command=self.browse_key_file)
        btn_key.pack(side=tk.LEFT, padx=6)
        
        self.toggle_mode_fields()

    def browse_key_file(self):
        file_path = filedialog.askopenfilename(title="SSH Private Key 파일 선택 (oracle_key, id_rsa, pem)")
        if file_path:
            self.var_server_key_path.set(file_path)
            
    def toggle_mode_fields(self):
        mode = self.var_mode.get()
        state = 'disabled' if mode == "LOCAL" else 'normal'
        for child in self.server_info_frame.winfo_children():
            try:
                child.configure(state=state)
                for subchild in child.winfo_children():
                    subchild.configure(state=state)
            except Exception:
                pass

    # ----------------------------------------------------
    # 탭 5: 퀀트 매매 세부 설정 탭
    # ----------------------------------------------------
    def build_opt_tab(self):
        container = tk.Frame(self.tab_opt, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_label_section(container, "포지션 사이징 & 리스크 관리 수칙", 
                                  "계좌 집중 방지 및 원금 보존을 위한 포지션 한도와 손절 기준을 설정합니다.")
        
        self.create_input_row(container, "운용 자본금 ($)", self.var_capital, placeholder="예: 2000 달러")
        self.create_input_row(container, "최대 보유 종목 수", self.var_max_pos, placeholder="안전 분산을 위해 3개 ~ 5개 추천 (기본: 3개)")
        self.create_input_row(container, "최소 진입 점수", self.var_min_score, placeholder="60점(기본) ~ 80점(초우량 엄선)")
        self.create_input_row(container, "개별 손절 한도 (%)", self.var_stop_loss, placeholder="기본 3.8% (기계적 칼손절)")
        self.create_input_row(container, "스크리닝 후보 수", self.var_screener_max_candidates, placeholder="API 안정성을 위해 300개 권장")

    # ----------------------------------------------------
    # 공통 UI 컴포넌트 빌더
    # ----------------------------------------------------
    def create_label_section(self, parent, title, desc):
        frame = tk.Frame(parent, bg=SURFACE_COLOR)
        frame.pack(fill=tk.X, padx=25, pady=(15, 10))
        tk.Label(frame, text=title, font=("Malgun Gothic", 12, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w")
        tk.Label(frame, text=desc, font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 6))
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=25, pady=5)

    def create_input_row(self, parent, label_text, var, placeholder="", show=""):
        frame = tk.Frame(parent, bg=SURFACE_COLOR)
        frame.pack(fill=tk.X, padx=25, pady=6)
        
        tk.Label(frame, text=label_text, font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=22, anchor="w").pack(side=tk.LEFT)
        
        entry = tk.Entry(frame, textvariable=var, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR, show=show)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        
        entry.bind("<FocusIn>", lambda e: entry.configure(highlightbackground=ACCENT_BLUE, highlightcolor=ACCENT_BLUE))
        entry.bind("<FocusOut>", lambda e: entry.configure(highlightbackground=BORDER_COLOR, highlightcolor=BORDER_COLOR))
        
        if placeholder:
            ToolTip(entry, placeholder)
            
        return entry

    # ----------------------------------------------------
    # 연결 검증 로직 (KIS + Telegram + Gemini + Finnhub + FRED)
    # ----------------------------------------------------
    def run_connection_test(self):
        self.btn_test.configure(state="disabled", text="🔌 연결 검증 진행 중...")
        threading.Thread(target=self._connection_test_thread, daemon=True).start()
        
    def _connection_test_thread(self):
        appkey = self.var_appkey.get().strip()
        secret = self.var_secret.get().strip()
        env = self.var_trading_env.get().strip()
        
        # 1. KIS 인증
        kis_msg = "❌ 키 미입력"
        if appkey and secret:
            base_url = "https://openapivts.koreainvestment.com:29443" if env == "VIRT" else "https://openapi.koreainvestment.com:9443"
            try:
                res = requests.post(f"{base_url}/oauth2/tokenP", json={"grant_type": "client_credentials", "appkey": appkey, "secretkey": secret}, headers={"content-type": "application/json"}, timeout=8)
                if res.status_code == 200 and "access_token" in res.json():
                    kis_msg = f"✅ 성공 ({'모의투자' if env == 'VIRT' else '실전계좌'} 토큰 정상 발급)"
                else:
                    kis_msg = f"❌ 인증 실패 ({res.json().get('error_description', '키 불일치')})"
            except Exception as e:
                kis_msg = f"❌ 통신 에러 ({e})"
                
        # 2. 텔레그램
        tg_token = self.var_tg_token.get().strip()
        tg_chat_id = self.var_tg_chat_id.get().strip()
        tg_msg = "ℹ️ 정보 미입력 (생략)"
        if tg_token and tg_chat_id:
            try:
                res = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={"chat_id": tg_chat_id, "text": "🔌 [AI 스윙 봇] 5대 API 연결 검증 테스트에 성공했습니다! 🚀"}, timeout=8)
                if res.status_code == 200:
                    tg_msg = "✅ 전송 성공 (스마트폰 알림 확인)"
                else:
                    tg_msg = f"❌ 전송 실패 ({res.text})"
            except Exception as e:
                tg_msg = f"❌ 통신 에러 ({e})"
                
        # 3. Gemini AI
        gemini_key = self.var_gemini_key.get().strip()
        gemini_msg = "ℹ️ 미입력 (선택사항)"
        if gemini_key:
            try:
                res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}", timeout=8)
                gemini_msg = "✅ 정상 연동" if res.status_code == 200 else f"❌ 키 오류 (HTTP {res.status_code})"
            except Exception as e:
                gemini_msg = f"❌ 통신 에러 ({e})"
                
        # 4. Finnhub
        finnhub_key = self.var_finnhub_key.get().strip()
        finnhub_msg = "ℹ️ 미입력 (선택사항)"
        if finnhub_key:
            try:
                res = requests.get(f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={finnhub_key}", timeout=8)
                finnhub_msg = "✅ 정상 연동" if res.status_code == 200 else f"❌ 키 오류 (HTTP {res.status_code})"
            except Exception as e:
                finnhub_msg = f"❌ 통신 에러 ({e})"
                
        # 5. FRED
        fred_key = self.var_fred_key.get().strip()
        fred_msg = "ℹ️ 미입력 (선택사항)"
        if fred_key:
            try:
                res = requests.get(f"https://api.stlouisfed.org/fred/series?series_id=FEDFUNDS&api_key={fred_key}&file_type=json", timeout=8)
                fred_msg = "✅ 정상 연동" if res.status_code == 200 else f"❌ 키 오류 (HTTP {res.status_code})"
            except Exception as e:
                fred_msg = f"❌ 통신 에러 ({e})"
                
        result_text = (
            "=== 🔌 5대 API 연결 검증 결과 리포트 ===\n\n"
            f"1. 📈 한국투자증권(KIS) : {kis_msg}\n"
            f"2. 📱 텔레그램 알림봇    : {tg_msg}\n"
            f"3. 🌟 Google Gemini AI   : {gemini_msg}\n"
            f"4. 🏢 Finnhub 실적 API   : {finnhub_msg}\n"
            f"5. 🏛️ FRED 연준 거시경제 : {fred_msg}\n"
        )
        
        self.root.after(0, lambda: self.btn_test.configure(state="normal", text="🔌 5대 API 연결 검증 및 테스트"))
        self.root.after(0, lambda: messagebox.showinfo("연결 검증 리포트", result_text))

    # ----------------------------------------------------
    # .env 파일 생성 및 실행/배포
    # ----------------------------------------------------
    def save_and_execute(self):
        appkey = self.var_appkey.get().strip()
        secret = self.var_secret.get().strip()
        cano = self.var_cano.get().strip()
        
        if not appkey or not secret or not cano:
            messagebox.showerror("필수 항목 누락", "증권사 APP KEY, SECRET KEY 및 CANO 계좌번호는 필수입니다!")
            return
            
        env_content = f"""# ====================================================================
# AI SOTA 퀀트 스윙 트레이딩 봇 자동 생성 설정파일 (.env)
# ====================================================================

# ======================
# KIS API Configuration
# ======================
TRADING_ENV={self.var_trading_env.get().strip()}
KIS_APP_KEY={appkey}
KIS_APP_SECRET={secret}
KIS_CANO={cano}
KIS_ACNT_PRDT_CD={self.var_acnt_code.get().strip()}

# KIS Aliases
KIS_APPKEY={appkey}
KIS_SECRET={secret}
KIS_SANDBOX={'true' if self.var_trading_env.get() == 'VIRT' else 'false'}

# ======================
# External AI & Macro APIs
# ======================
GEMINI_API_KEY="{self.var_gemini_key.get().strip()}"
FINNHUB_API_KEY={self.var_finnhub_key.get().strip()}
FRED_API_KEY={self.var_fred_key.get().strip()}

# ======================
# Telegram Bot
# ======================
TELEGRAM_BOT_TOKEN={self.var_tg_token.get().strip()}
TELEGRAM_TOKEN={self.var_tg_token.get().strip()}
TELEGRAM_CHAT_ID={self.var_tg_chat_id.get().strip()}

# ======================
# Risk & Strategy Parameters
# ======================
INITIAL_CAPITAL={self.var_capital.get().strip()}
MAX_POSITIONS={self.var_max_pos.get().strip()}
MIN_ENTRY_SCORE={self.var_min_score.get().strip()}
DAILY_STOP_LOSS_PCT={self.var_stop_loss.get().strip()}
SCREENER_MAX_CANDIDATES={self.var_screener_max_candidates.get().strip()}
MACRO_BLIND_POLICY=PENALTY
DISABLE_YFINANCE_FALLBACK=true
DISABLE_OPTIONS_FLOW=false

# ======================
# Deployment Mode
# ======================
RUN_MODE={self.var_mode.get()}
REMOTE_HOST={self.var_server_host.get().strip()}
REMOTE_USER={self.var_server_user.get().strip()}
REMOTE_KEY={self.var_server_key_path.get().strip()}
"""
        try:
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
        except Exception as e:
            messagebox.showerror("저장 실패", f".env 파일 저장 중 오류 발생:\n{e}")
            return
            
        mode = self.var_mode.get()
        if mode == "LOCAL":
            confirm = messagebox.askyesno("설정 완료", "설정이 성공적으로 저장되었습니다!\n\n지금 바로 내 PC에서 봇을 구동하시겠습니까?")
            if confirm:
                self.root.destroy()
                os.system("start Start_Dashboard.bat")
        else:
            if not HAS_PARAMIKO:
                messagebox.showerror("배포 라이브러리 필요", "원격 자동 배포를 위해 'paramiko' 라이브러리가 필요합니다.\n명령창에 pip install paramiko 를 실행해 주세요.")
                return
            
            host = self.var_server_host.get().strip()
            user = self.var_server_user.get().strip()
            key_path = self.var_server_key_path.get().strip()
            
            if not host or not key_path:
                messagebox.showerror("입력값 누락", "클라우드 서버 IP 주소와 SSH 개인키 파일 경로를 입력해 주세요.")
                return
                
            confirm = messagebox.askyesno("배포 확인", f"원격 서버({host})로 봇 설정 및 코드를 업로드하고 자동 배포를 진행할까요?")
            if confirm:
                self.run_server_deployment(host, user, key_path)

    def run_server_deployment(self, host, user, key_path):
        deploy_win = tk.Toplevel(self.root)
        deploy_win.title("☁️ 클라우드 원클릭 자동 배포")
        deploy_win.geometry("520x400")
        deploy_win.configure(bg=BG_COLOR)
        
        tk.Label(deploy_win, text="☁️ 원격 서버 자동 배포 진행 상태", font=("Malgun Gothic", 12, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=12)
        
        log_txt = tk.Text(deploy_win, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Consolas", 9), bd=1, relief="solid")
        log_txt.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        def append_log(msg):
            log_txt.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            log_txt.see(tk.END)
            
        def _deploy_thread():
            try:
                self.root.after(0, lambda: append_log("1. SSH 개인키 로드 중..."))
                private_key = paramiko.RSAKey.from_private_key_file(key_path)
                
                self.root.after(0, lambda: append_log(f"2. {host} 서버에 접속하는 중..."))
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=host, username=user, pkey=private_key, timeout=15)
                
                self.root.after(0, lambda: append_log("3. SFTP로 최신 .env 파일 전송 중..."))
                sftp = ssh.open_sftp()
                sftp.put(".env", "/home/ubuntu/kis-auto-trading/.env")
                sftp.close()
                
                self.root.after(0, lambda: append_log("4. 원격 systemd 서비스 재시작 중..."))
                stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart kis-trading-bot")
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    self.root.after(0, lambda: append_log("✅ 24시간 백그라운드 서비스 재시작 성공!"))
                    self.root.after(0, lambda: append_log("🎉 클라우드 원클릭 자동 배포가 완료되었습니다."))
                else:
                    self.root.after(0, lambda: append_log(f"⚠️ 서비스 재시작 경고: {stderr.read().decode('utf-8')}"))
                
                ssh.close()
            except Exception as e:
                self.root.after(0, lambda: append_log(f"❌ 배포 중 오류 발생: {e}"))
                
        threading.Thread(target=_deploy_thread, daemon=True).start()


def main():
    root = tk.Tk()
    app = SetupWizardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
