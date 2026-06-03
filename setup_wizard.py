"""
AI 스윙 트레이딩 봇 - 원클릭 설정 마법사 (setup_wizard.py)
======================================================
초보자도 메모장 수정 없이 API 키, 계좌번호, 텔레그램 토큰, 
구동 방식(로컬 PC / 원격 오라클 클라우드)을 안전하게 입력 및 배포할 수 있는 
프리미엄 다크테마 GUI 설정 프로그램입니다.
"""

import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests

# SSH/SCP 원격 배포를 위한 라이브러리 임포트 (paramiko가 설치되어 있을 경우 사용)
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

# ----------------------------------------------------
# 테마 및 색상 정의 (Nordic Pastel Elegant Theme)
# ----------------------------------------------------
BG_COLOR = "#f4f6f8"        # 북유럽풍 아주 밝은 쿨 그레이
SURFACE_COLOR = "#ffffff"   # 순백색 (컨테이너 카드 배경)
TEXT_COLOR = "#2b2d42"      # 세련된 딥 차콜 (가독성 높은 텍스트)
TEXT_MUTED = "#7f8c8d"      # 소프트 더스티 그레이 (보조 텍스트)
ACCENT_BLUE = "#8ea8bd"     # 파스텔 더스티 블루 (주요 실행 버튼)
ACCENT_GREEN = "#8fa89b"    # 소프트 세이지 그린 (연결 검증 / 성공)
ACCENT_RED = "#e07a5f"      # 따뜻한 테라코타 오렌지 (경고 / 에러 / 취소)
BORDER_COLOR = "#e1e5eb"    # 소프트 실버 그레이 (경계선)
ENTRY_BG = "#fafbfd"        # 입력창 연한 배경


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Malgun Gothic", 9, "normal"))
        label.pack(ipadx=5, ipady=3)

    def hide(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class SetupWizardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🕊️ AI 스윙 트레이딩 봇 - 설정 마법사 [Golden Bird Nordic Edition]")
        self.root.geometry("840x700") # 더욱 시원해진 창 크기
        self.root.resizable(True, True) # 창 크기 동적 조절 가능하게 설정!
        self.root.configure(bg=BG_COLOR)
        
        # 윈도우 타이틀바 아이콘 등록
        if os.path.exists("trading_bot_logo.ico"):
            try:
                self.root.iconbitmap("trading_bot_logo.ico")
            except Exception as e:
                print("아이콘 로드 오류:", e)
        
        # 기본 입력 변수들
        self.var_appkey = tk.StringVar()
        self.var_secret = tk.StringVar()
        self.var_cano = tk.StringVar()
        self.var_acnt_code = tk.StringVar(value="01")
        self.var_is_sandbox = tk.BooleanVar(value=True)
        
        self.var_tg_token = tk.StringVar()
        self.var_tg_chat_id = tk.StringVar()
        self.var_finnhub_key = tk.StringVar()
        
        self.var_mode = tk.StringVar(value="LOCAL") # LOCAL or SERVER
        self.var_server_host = tk.StringVar()
        self.var_server_user = tk.StringVar(value="ubuntu")
        self.var_server_key_path = tk.StringVar()
        
        self.var_capital = tk.StringVar(value="1000") # 기본 $1,000 기준
        self.var_max_pos = tk.StringVar(value="5") # 기본 최대 5개 종목
        
        # 설정 로드
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
                        
                        if k == "KIS_APPKEY": self.var_appkey.set(v)
                        elif k == "KIS_SECRET": self.var_secret.set(v)
                        elif k == "KIS_CANO": self.var_cano.set(v)
                        elif k == "KIS_ACNT_PRDT_CD": self.var_acnt_code.set(v)
                        elif k == "KIS_SANDBOX": self.var_is_sandbox.set(v.upper() == "TRUE")
                        elif k == "TELEGRAM_TOKEN": self.var_tg_token.set(v)
                        elif k == "TELEGRAM_CHAT_ID": self.var_tg_chat_id.set(v)
                        elif k == "FINNHUB_API_KEY": self.var_finnhub_key.set(v)
                        elif k == "INITIAL_CAPITAL": self.var_capital.set(v)
                        elif k == "MAX_POSITIONS": self.var_max_pos.set(v)
                        elif k == "RUN_MODE": self.var_mode.set(v)
                        elif k == "REMOTE_HOST": self.var_server_host.set(v)
                        elif k == "REMOTE_USER": self.var_server_user.set(v)
                        elif k == "REMOTE_KEY": self.var_server_key_path.set(v)
            except Exception as e:
                print("이전 설정 로드 오류:", e)

    def add_button_hover(self, button, normal_bg, hover_bg):
        """버튼에 마우스 진입/퇴출 시 부드러운 하이라이트 애니메이션 적용"""
        button.bind("<Enter>", lambda e: button.configure(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.configure(bg=normal_bg))

    def setup_ui(self):
        # 스타일 커스텀
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=BG_COLOR, borderwidth=0)
        style.configure('TNotebook.Tab', background=SURFACE_COLOR, foreground=TEXT_MUTED, borderwidth=1, bordercolor=BORDER_COLOR, padding=[18, 10], font=("Malgun Gothic", 10, "bold"))
        style.map('TNotebook.Tab', background=[('selected', ACCENT_BLUE)], foreground=[('selected', '#ffffff')]) # 선택된 탭은 부드러운 더스티 블루 배경에 화이트 텍스트
        
        # 헤더
        header_frame = tk.Frame(self.root, bg=BG_COLOR, height=75)
        header_frame.pack(fill=tk.X, padx=24, pady=12)
        
        # 타이틀 컨테이너 (좌우 정렬로 구성하여 아이콘과 텍스트를 따로 배색)
        title_container = tk.Frame(header_frame, bg=BG_COLOR)
        title_container.pack(anchor="w")
        
        # 북유럽풍 미니멀 골드 스파클 엠블럼 (✦)
        icon_lbl = tk.Label(title_container, text="✦", font=("Segoe UI", 20, "bold"), fg="#d0b48c", bg=BG_COLOR)
        icon_lbl.pack(side=tk.LEFT)
        
        title_lbl = tk.Label(title_container, text=" AI 스윙 트레이딩 봇 설정 마법사", font=("Malgun Gothic", 18, "bold"), fg="#3d5a80", bg=BG_COLOR) # 북유럽 딥 블루 테마 타이틀
        title_lbl.pack(side=tk.LEFT)
        
        desc_lbl = tk.Label(header_frame, text="Golden Bird Nordic Edition - 깔끔하고 직관적인 화면에서 개인 계좌 및 알림 정보를 연동하고 무인 가동을 시작합니다.", font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=BG_COLOR)
        desc_lbl.pack(anchor="w", pady=4)
        
        # 메인 컨테이너 (Notebook / Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=24, pady=12)
        
        # 탭 정의
        self.tab_kis = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_tg = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_mode = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_opt = tk.Frame(self.notebook, bg=BG_COLOR)
        
        self.notebook.add(self.tab_kis, text="   • KIS 증권 계좌   ")
        self.notebook.add(self.tab_tg, text="   • 텔레그램 알림   ")
        self.notebook.add(self.tab_mode, text="   • 구동 및 배포 방식   ")
        self.notebook.add(self.tab_opt, text="   • 세부 거래 조건   ")
        
        # 탭 구현들
        self.build_kis_tab()
        self.build_tg_tab()
        self.build_mode_tab()
        self.build_opt_tab()
        
        # 하단 조작 바
        bottom_frame = tk.Frame(self.root, bg=BG_COLOR, height=65)
        bottom_frame.pack(fill=tk.X, padx=24, pady=15)
        
        # 연결 검증 버튼 (소프트 세이지 그린 + 호버 액션 + 화이트 텍스트)
        self.btn_test = tk.Button(bottom_frame, text="🔌 연결 검증 및 테스트", font=("Malgun Gothic", 10, "bold"), fg="#ffffff", bg=ACCENT_GREEN, activebackground="#7a9385", borderwidth=0, cursor="hand2", padx=22, pady=10, command=self.run_connection_test)
        self.btn_test.pack(side=tk.LEFT)
        self.add_button_hover(self.btn_test, ACCENT_GREEN, "#7a9385")
        
        # 설정 저장 및 구동 시작 버튼 (소프트 더스티 블루 + 호버 액션 + 화이트 텍스트)
        self.btn_save = tk.Button(bottom_frame, text="🚀 설정 저장 및 구동 시작", font=("Malgun Gothic", 10, "bold"), fg="#ffffff", bg=ACCENT_BLUE, activebackground="#7792a8", borderwidth=0, cursor="hand2", padx=28, pady=10, command=self.save_and_execute)
        self.btn_save.pack(side=tk.RIGHT)
        self.add_button_hover(self.btn_save, ACCENT_BLUE, "#7792a8")
        
    # ----------------------------------------------------
    # KIS 증권 계좌 탭 구성
    # ----------------------------------------------------
    def build_kis_tab(self):
        container = tk.Frame(self.tab_kis, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_label_section(container, "한국투자증권 Open API 설정", "증권사 개발자 센터에서 발급받은 실전 또는 모의투자 Key를 입력합니다.")
        
        # 앱키
        self.create_input_row(container, "APP KEY", self.var_appkey, placeholder="한국투자증권 APP Key를 입력하세요", show="*")
        
        # 시크릿
        self.create_input_row(container, "SECRET KEY", self.var_secret, placeholder="한국투자증권 Secret Key를 입력하세요", show="*")
        
        # 핀허브 API 키 (yfinance 차단방지 Fallback)
        self.create_input_row(container, "Finnhub API KEY (선택)", self.var_finnhub_key, placeholder="yfinance 차단 우회용 Finnhub API Key를 입력하세요 (선택)", show="*")
        
        # 계좌번호
        account_frame = tk.Frame(container, bg=SURFACE_COLOR)
        account_frame.pack(fill=tk.X, padx=20, pady=8)
        
        tk.Label(account_frame, text="종합계좌번호 (CANO)", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=18, anchor="w").pack(side=tk.LEFT)
        
        cano_entry = tk.Entry(account_frame, textvariable=self.var_cano, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR, width=15)
        cano_entry.pack(side=tk.LEFT)
        cano_entry.bind("<FocusIn>", lambda e: cano_entry.configure(highlightbackground=ACCENT_BLUE, highlightcolor=ACCENT_BLUE))
        cano_entry.bind("<FocusOut>", lambda e: cano_entry.configure(highlightbackground=BORDER_COLOR, highlightcolor=BORDER_COLOR))
        cano_tooltip = ToolTip(cano_entry, "앞 8자리 숫자만 입력합니다.")
        
        tk.Label(account_frame, text="-", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, padx=5).pack(side=tk.LEFT)
        
        code_entry = tk.Entry(account_frame, textvariable=self.var_acnt_code, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR, width=5)
        code_entry.pack(side=tk.LEFT)
        code_entry.bind("<FocusIn>", lambda e: code_entry.configure(highlightbackground=ACCENT_BLUE, highlightcolor=ACCENT_BLUE))
        code_entry.bind("<FocusOut>", lambda e: code_entry.configure(highlightbackground=BORDER_COLOR, highlightcolor=BORDER_COLOR))
        code_tooltip = ToolTip(code_entry, "계좌번호 뒤 2자리 (보통 01 등)를 입력합니다.")
        
        # 모의투자 여부
        sandbox_frame = tk.Frame(container, bg=SURFACE_COLOR)
        sandbox_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(sandbox_frame, text="투자 환경 선택", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=18, anchor="w").pack(side=tk.LEFT)
        
        chk_sandbox = tk.Checkbutton(sandbox_frame, text="모의투자 계좌 (Sandbox)", variable=self.var_is_sandbox, font=("Malgun Gothic", 10), bg=SURFACE_COLOR, fg=TEXT_COLOR, activebackground=SURFACE_COLOR, activeforeground=TEXT_COLOR, selectcolor="#ffffff", cursor="hand2")
        chk_sandbox.pack(side=tk.LEFT)
        
    # ----------------------------------------------------
    # 텔레그램 알림 탭 구성
    # ----------------------------------------------------
    def build_tg_tab(self):
        container = tk.Frame(self.tab_tg, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_label_section(container, "텔레그램 실시간 리포트 설정", "거래 시작, 체결 내역, 익절/손절 알림 및 실시간 차트를 전송받을 텔레그램 설정을 입력합니다.")
        
        # 봇 토큰
        self.create_input_row(container, "봇 토큰 (Token)", self.var_tg_token, placeholder="7489501...:AAH_...", show="*")
        
        # 채팅 ID
        self.create_input_row(container, "사용자 채팅 ID", self.var_tg_chat_id, placeholder="아이디 찾기 봇으로 조회한 Chat ID (예: 123456789)")
        
        tip_frame = tk.Frame(container, bg=SURFACE_COLOR)
        tip_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tip_text = (
            "💡 텔레그램 알림 연결 방법:\n"
            "  1. 텔레그램에서 '@BotFather'를 검색하여 채팅방에 들어간 뒤 /newbot 을 입력하여 봇을 생성합니다.\n"
            "  2. 생성 완료 시 발급받은 'HTTP API Token'을 위의 [봇 토큰] 란에 복사해 붙여넣습니다.\n"
            "  3. 텔레그램에서 '@userinfobot'을 검색하여 들어가 메시지를 보내면 본인의 고유 [채팅 ID]를 알려줍니다."
        )
        tk.Label(tip_frame, text=tip_text, font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=SURFACE_COLOR, justify="left").pack(anchor="w")

    # ----------------------------------------------------
    # 구동 및 배포 방식 탭 구성
    # ----------------------------------------------------
    def build_mode_tab(self):
        container = tk.Frame(self.tab_mode, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_label_section(container, "시스템 구동 및 서버 배포 방식", "봇을 개인 윈도우 PC에서 직접 실행하거나, 오라클 등 외부 가상 서버(Linux)에 원격 설치합니다.")
        
        # 구동 모드 라디오 버튼
        mode_frame = tk.Frame(container, bg=SURFACE_COLOR)
        mode_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(mode_frame, text="구동 시스템", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=18, anchor="w").pack(side=tk.LEFT)
        
        r_local = tk.Radiobutton(mode_frame, text="개인 PC (Windows) 로컬 구동", variable=self.var_mode, value="LOCAL", font=("Malgun Gothic", 10), bg=SURFACE_COLOR, fg=TEXT_COLOR, activebackground=SURFACE_COLOR, selectcolor="#ffffff", command=self.toggle_mode_fields, cursor="hand2")
        r_local.pack(side=tk.LEFT, padx=10)
        
        r_server = tk.Radiobutton(mode_frame, text="원격 클라우드 서버 (Linux) 자동 배포", variable=self.var_mode, value="SERVER", font=("Malgun Gothic", 10), bg=SURFACE_COLOR, fg=TEXT_COLOR, activebackground=SURFACE_COLOR, selectcolor="#ffffff", command=self.toggle_mode_fields, cursor="hand2")
        r_server.pack(side=tk.LEFT, padx=10)
        
        # 서버 상세 정보 프레임
        self.server_info_frame = tk.LabelFrame(container, text="🔒 원격 클라우드 서버 접속 정보 (SSH)", font=("Malgun Gothic", 9, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.server_info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # IP 주소
        self.create_input_row(self.server_info_frame, "서버 IP 주소", self.var_server_host, placeholder="예: 141.148.172.12")
        
        # SSH 계정
        self.create_input_row(self.server_info_frame, "SSH 계정명", self.var_server_user, placeholder="ubuntu, root 등")
        
        # SSH Private Key 파일 선택
        key_frame = tk.Frame(self.server_info_frame, bg=SURFACE_COLOR)
        key_frame.pack(fill=tk.X, padx=20, pady=8)
        
        tk.Label(key_frame, text="SSH 개인키 (id_rsa)", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=18, anchor="w").pack(side=tk.LEFT)
        
        key_entry = tk.Entry(key_frame, textvariable=self.var_server_key_path, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR)
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        key_entry.bind("<FocusIn>", lambda e: key_entry.configure(highlightbackground=ACCENT_BLUE, highlightcolor=ACCENT_BLUE))
        key_entry.bind("<FocusOut>", lambda e: key_entry.configure(highlightbackground=BORDER_COLOR, highlightcolor=BORDER_COLOR))
        
        btn_key = tk.Button(key_frame, text="찾아보기...", font=("Malgun Gothic", 9), fg=TEXT_COLOR, bg=BORDER_COLOR, bd=0, cursor="hand2", command=self.browse_key_file)
        btn_key.pack(side=tk.LEFT, padx=5)
        self.add_button_hover(btn_key, BORDER_COLOR, "#d1d5db")
        
        # 상태 토글 초기화
        self.toggle_mode_fields()
        
    def browse_key_file(self):
        file_path = filedialog.askopenfilename(title="SSH Private Key 파일 선택 (id_rsa, pem)")
        if file_path:
            self.var_server_key_path.set(file_path)
            
    def toggle_mode_fields(self):
        """LOCAL 선택 시 서버 입력창을 비활성화하고, SERVER 선택 시 활성화"""
        mode = self.var_mode.get()
        if mode == "LOCAL":
            for child in self.server_info_frame.winfo_children():
                try:
                    child.configure(state='disabled')
                    for subchild in child.winfo_children():
                        subchild.configure(state='disabled')
                except:
                    pass
            self.server_info_frame.configure(fg=TEXT_MUTED)
        else:
            for child in self.server_info_frame.winfo_children():
                try:
                    child.configure(state='normal')
                    for subchild in child.winfo_children():
                        subchild.configure(state='normal')
                except:
                    pass
            self.server_info_frame.configure(fg=TEXT_COLOR)

    # ----------------------------------------------------
    # 세부 거래 조건 탭 구성
    # ----------------------------------------------------
    def build_opt_tab(self):
        container = tk.Frame(self.tab_opt, bg=SURFACE_COLOR, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_label_section(container, "안전한 자본 배분 및 한도 설정", "사용자의 투자 규모에 맞는 포지션 사이징을 규격화하여, 집중 리스크를 방지합니다.")
        
        # 운용 자본금
        self.create_input_row(container, "총 투자 자본금 ($)", self.var_capital, placeholder="예: 777달러 혹은 10000달러")
        
        # 최대 보유 종목 수
        self.create_input_row(container, "최대 보유 종목 수 (개)", self.var_max_pos, placeholder="안전 분산을 위해 3개 ~ 7개 추천")
        
        tip_frame = tk.Frame(container, bg=SURFACE_COLOR)
        tip_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tip_text = (
            "🛡️ 보안 및 안전장치 안내:\n"
            "  - 설정 마법사는 30% 주가 집중 차단 룰을 활성화하여 어떤 종목도 자본금의 30%를 넘지 못하게 제어합니다.\n"
            "  - 사용자가 입력한 모든 비밀 키(APP KEY, SECRET KEY)는 본인의 로컬 PC 내에만 안전하게 텍스트로 보관됩니다.\n"
            "  - 외부의 해커나 타사 서버로 민감한 키가 전송되는 경로가 전혀 없으므로 안심하고 안전하게 구동하십시오."
        )
        tk.Label(tip_frame, text=tip_text, font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=SURFACE_COLOR, justify="left").pack(anchor="w")

    # ----------------------------------------------------
    # UI 빌더 유틸리티 함수들
    # ----------------------------------------------------
    def create_label_section(self, parent, title, desc):
        frame = tk.Frame(parent, bg=SURFACE_COLOR)
        frame.pack(fill=tk.X, padx=20, pady=15)
        tk.Label(frame, text=title, font=("Malgun Gothic", 12, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w")
        tk.Label(frame, text=desc, font=("Malgun Gothic", 9), fg=TEXT_MUTED, bg=SURFACE_COLOR).pack(anchor="w", pady=2)
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=20, pady=5)
        
    def create_input_row(self, parent, label_text, var, placeholder="", show=""):
        frame = tk.Frame(parent, bg=SURFACE_COLOR)
        frame.pack(fill=tk.X, padx=20, pady=8)
        
        tk.Label(frame, text=label_text, font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=SURFACE_COLOR, width=18, anchor="w").pack(side=tk.LEFT)
        
        entry = tk.Entry(frame, textvariable=var, font=("Malgun Gothic", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR, show=show)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 포커스 이동 시 테두리 색상 글로우 변화 (Aesthetic enhancement)
        entry.bind("<FocusIn>", lambda e: entry.configure(highlightbackground=ACCENT_BLUE, highlightcolor=ACCENT_BLUE))
        entry.bind("<FocusOut>", lambda e: entry.configure(highlightbackground=BORDER_COLOR, highlightcolor=BORDER_COLOR))
        
        if placeholder:
            tooltip = ToolTip(entry, placeholder)
            
        return entry

    # ----------------------------------------------------
    # 비즈니스 로직: 연결 검증 테스트
    # ----------------------------------------------------
    def run_connection_test(self):
        """스레드를 띄워 증권사 API 및 텔레그램 연동 상태를 확인"""
        self.btn_test.configure(state="disabled", text="🔌 연결 검증 중...")
        threading.Thread(target=self._connection_test_thread, daemon=True).start()
        
    def _connection_test_thread(self):
        appkey = self.var_appkey.get().strip()
        secret = self.var_secret.get().strip()
        is_sandbox = self.var_is_sandbox.get()
        
        token_success = False
        token_msg = ""
        
        # 1. KIS 인증 테스트
        if not appkey or not secret:
            token_msg = "❌ KIS APP KEY와 SECRET KEY를 먼저 입력해 주세요."
        else:
            base_url = "https://openapivts.koreainvestment.com:29443" if is_sandbox else "https://openapi.koreainvestment.com:9443"
            url = f"{base_url}/oauth2/tokenP"
            headers = {"content-type": "application/json"}
            payload = {
                "grant_type": "client_credentials",
                "appkey": appkey,
                "secretkey": secret
            }
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=8)
                if res.status_code == 200:
                    res_data = res.json()
                    if "access_token" in res_data:
                        token_success = True
                        token_msg = "✅ KIS API 인증 성공! 임시 토큰 발급 완료."
                    else:
                        token_msg = f"❌ KIS 인증 실패: {res_data.get('error_description', '알 수 없는 오류')}"
                else:
                    token_msg = f"❌ KIS 인증 실패 (HTTP {res.status_code}): {res.text}"
            except Exception as e:
                token_msg = f"❌ KIS API 통신 에러: {e}"
                
        # 2. 텔레그램 전송 테스트
        tg_token = self.var_tg_token.get().strip()
        tg_chat_id = self.var_tg_chat_id.get().strip()
        tg_success = False
        tg_msg = ""
        
        if not tg_token or not tg_chat_id:
            tg_msg = "ℹ️ 텔레그램 정보가 비어 있어 테스트를 생략합니다."
        else:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {
                "chat_id": tg_chat_id,
                "text": "🔌 [AI 스윙 봇] 설정 마법사 연동 테스트에 성공했습니다! 🚀"
            }
            try:
                res = requests.post(url, json=payload, timeout=8)
                if res.status_code == 200:
                    tg_success = True
                    tg_msg = "✅ 텔레그램 메시지 전송 성공! (휴대폰 확인)"
                else:
                    tg_msg = f"❌ 텔레그램 전송 실패: {res.text}"
            except Exception as e:
                tg_msg = f"❌ 텔레그램 API 통신 에러: {e}"
                
        # 결과 대화상자 출력
        result_text = f"=== 🔌 연결 검증 결과 ===\n\n1. [증권사 인증]\n{token_msg}\n\n2. [텔레그램 알림]\n{tg_msg}"
        
        # 버튼 상태 복구
        self.root.after(0, lambda: self.btn_test.configure(state="normal", text="🔌 연결 검증 및 테스트"))
        self.root.after(0, lambda: messagebox.showinfo("연결 검증 리포트", result_text))

    # ----------------------------------------------------
    # 비즈니스 로직: 설정 저장 및 구동/배포
    # ----------------------------------------------------
    def save_and_execute(self):
        """입력 값을 기반으로 .env 파일을 생성하고 구동/배포 수행"""
        appkey = self.var_appkey.get().strip()
        secret = self.var_secret.get().strip()
        cano = self.var_cano.get().strip()
        
        if not appkey or not secret or not cano:
            messagebox.showerror("입력값 에러", "증권사 APP KEY, SECRET KEY 및 CANO 계좌번호는 필수 항목입니다!")
            return
            
        # .env 내용 작성
        env_content = f"""# ====================================================================
# AI 스윙 트레이딩 봇 자동 생성 설정파일 (.env)
# ====================================================================

# 🔑 KIS 증권사 API Key
KIS_APPKEY={appkey}
KIS_SECRET={secret}
KIS_CANO={cano}
KIS_ACNT_PRDT_CD={self.var_acnt_code.get().strip()}
KIS_SANDBOX={'true' if self.var_is_sandbox.get() else 'false'}

# 🔑 Finnhub API Key (yfinance Fallback)
FINNHUB_API_KEY={self.var_finnhub_key.get().strip()}

# 📢 텔레그램 알림봇 설정
TELEGRAM_TOKEN={self.var_tg_token.get().strip()}
TELEGRAM_CHAT_ID={self.var_tg_chat_id.get().strip()}

# ⚙️ 리스크 및 매매 조건
INITIAL_CAPITAL={self.var_capital.get().strip()}
MAX_POSITIONS={self.var_max_pos.get().strip()}

# ☁️ 구동 및 배포 설정
RUN_MODE={self.var_mode.get()}
REMOTE_HOST={self.var_server_host.get().strip()}
REMOTE_USER={self.var_server_user.get().strip()}
REMOTE_KEY={self.var_server_key_path.get().strip()}
"""
        try:
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
        except Exception as e:
            messagebox.showerror("저장 실패", f"로컬 .env 파일을 작성하는 도중 오류가 발생했습니다:\n{e}")
            return
            
        # 구동 모드 분기
        mode = self.var_mode.get()
        if mode == "LOCAL":
            # 로컬 실행
            confirm = messagebox.askyesno("설정 완료", "설정이 안전하게 저장되었습니다!\n\n지금 이 컴퓨터(로컬 PC)에서 AI 스윙 봇을 구동할까요?")
            if confirm:
                self.root.destroy()
                # main.py 실행 호출
                os.system("python main.py")
        else:
            # 원격 서버 배포 시작
            if not HAS_PARAMIKO:
                messagebox.showerror("배포 차단", "서버 원스톱 배포를 위해서는 'paramiko' 라이브러리가 필요합니다!\n명령창에 'pip install paramiko'를 실행하시거나 로컬 봇을 실행하십시오.")
                return
            
            host = self.var_server_host.get().strip()
            user = self.var_server_user.get().strip()
            key_path = self.var_server_key_path.get().strip()
            
            if not host or not key_path:
                messagebox.showerror("입력값 에러", "클라우드 서버 IP 주소와 SSH 개인키 파일 경로가 필요합니다!")
                return
                
            confirm = messagebox.askyesno("배포 확인", f"원격 클라우드 서버 ({host}) 로 모든 봇 코드를 전송하고 패치 배포를 자동 실행할까요?")
            if confirm:
                # 배포 전용 진행 윈도우 생성
                self.run_server_deployment(host, user, key_path)

    # ----------------------------------------------------
    # 고급 기능: 원스톱 클라우드 자동 배포 (paramiko)
    # ----------------------------------------------------
    def run_server_deployment(self, host, user, key_path):
        deploy_win = tk.Toplevel(self.root)
        deploy_win.title("☁️ 클라우드 원클릭 자동 배포 상태")
        deploy_win.geometry("500x380")
        deploy_win.configure(bg=BG_COLOR)
        deploy_win.resizable(False, False)
        
        if os.path.exists("trading_bot_logo.ico"):
            try:
                deploy_win.iconbitmap("trading_bot_logo.ico")
            except:
                pass
        
        tk.Label(deploy_win, text="☁️ 원격 서버 자동 배포 진행 상황", font=("Malgun Gothic", 12, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=15)
        
        # 로그 출력 창
        log_txt = tk.Text(deploy_win, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Consolas", 9), bd=1, relief="solid", highlightthickness=1, highlightbackground=BORDER_COLOR)
        log_txt.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        def append_log(msg):
            log_txt.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            log_txt.see(tk.END)
            
        def _deploy_thread():
            try:
                self.root.after(0, lambda: append_log("1. 원격 SSH 개인키를 로드하는 중..."))
                private_key = paramiko.RSAKey.from_private_key_file(key_path)
                
                self.root.after(0, lambda: append_log(f"2. {host} 원격 서버 접속을 시도 중..."))
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=host, username=user, pkey=private_key, timeout=10)
                
                self.root.after(0, lambda: append_log("3. 원격 서버 접속 성공! 폴더 구조 생성 중..."))
                ssh.exec_command("mkdir -p /home/ubuntu/kis-auto-trading")
                
                self.root.after(0, lambda: append_log("4. SFTP 채널 개설 후 봇 소스코드 업로드 시작..."))
                sftp = ssh.open_sftp()
                
                # 전송할 파일 목록 필터링
                exclude_files = {".git", ".idea", ".vscode", "trades.db", "check_db.py", "inspect_db.py", "query_bottom_trades.py", "perf_analysis.py"}
                
                local_dir = os.getcwd()
                files = [f for f in os.listdir(local_dir) if os.path.isfile(os.path.join(local_dir, f))]
                
                total_transferred = 0
                for f in files:
                    if f in exclude_files or f.endswith(".log") or f.endswith(".db"):
                        continue
                    local_path = os.path.join(local_dir, f)
                    remote_path = f"/home/ubuntu/kis-auto-trading/{f}"
                    
                    self.root.after(0, lambda name=f: append_log(f"   -> {name} 업로드 중..."))
                    sftp.put(local_path, remote_path)
                    total_transferred += 1
                    
                sftp.close()
                self.root.after(0, lambda cnt=total_transferred: append_log(f"5. 총 {cnt}개 핵심 파일 업로드 완료!"))
                
                # 원격 서버 환경 세팅 및 실행 명령어
                self.root.after(0, lambda: append_log("6. 원격 서버 내 필수 라이브러리 및 패키지 설치 중 (시간 소요)..."))
                cmd_setup = "pip3 install --no-cache-dir -r /home/ubuntu/kis-auto-trading/requirements.txt"
                stdin, stdout, stderr = ssh.exec_command(cmd_setup)
                stdout.channel.recv_exit_status() # 완료 대기
                
                self.root.after(0, lambda: append_log("7. systemd 백그라운드 서비스(kis-trading) 등록 중..."))
                
                # kis-trading.service 파일 동적 원격 생성
                service_file_content = """[Unit]
Description=KIS Auto-Trading Swing Bot Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/kis-auto-trading
ExecStart=/usr/bin/python3 /home/ubuntu/kis-auto-trading/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
                # SFTP를 통해 서비스 파일 업로드
                sftp_serv = ssh.open_sftp()
                with sftp_serv.file("/home/ubuntu/kis-auto-trading/kis-trading.service", "w") as f:
                    f.write(service_file_content)
                sftp_serv.close()
                
                # 서비스 파일 복사 및 데몬 리로드
                cmd_srv = (
                    "sudo cp /home/ubuntu/kis-auto-trading/kis-trading.service /etc/systemd/system/kis-trading.service && "
                    "sudo systemctl daemon-reload && "
                    "sudo systemctl enable kis-trading && "
                    "sudo systemctl restart kis-trading"
                )
                stdin, stdout, stderr = ssh.exec_command(cmd_srv)
                stdout.channel.recv_exit_status()
                
                # 상태 확인
                stdin, stdout, stderr = ssh.exec_command("systemctl is-active kis-trading")
                status = stdout.read().decode().strip()
                
                ssh.close()
                
                if status == "active":
                    self.root.after(0, lambda: append_log("🎉 배포 및 가동 완벽 성공! 실서버 24시간 가동 중!"))
                    self.root.after(0, lambda: messagebox.showinfo("배포 성공", f"원격 클라우드 서버 ({host}) 에 AI 스윙 봇 배포 및 systemd 서비스 등록이 완료되었으며, 현재 정상 가동(active) 중입니다!"))
                else:
                    self.root.after(0, lambda: append_log("⚠️ 주의: 배포는 완료되었으나 서비스 구동에 실패했습니다. 로그를 검토하십시오."))
                    self.root.after(0, lambda: messagebox.showwarning("배포 검토", f"배포는 완료되었으나 원격 서비스 상태가 '{status}' 입니다. SSH로 직접 로그인해 systemctl status kis-trading을 확인하십시오."))
                
            except Exception as e:
                self.root.after(0, lambda err=e: append_log(f"❌ 배포 실패: {err}"))
                self.root.after(0, lambda err=e: messagebox.showerror("원격 배포 실패", f"원격 클라우드 자동 배포 도중 에러가 발생했습니다:\n{err}"))
                
        threading.Thread(target=_deploy_thread, daemon=True).start()


if __name__ == "__main__":
    # 고해상도 모니터 폰트 흐림 현상 방지
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    root = tk.Tk()
    app = SetupWizardApp(root)
    root.mainloop()
