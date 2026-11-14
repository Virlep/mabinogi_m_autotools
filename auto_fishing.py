import sys
import threading
import time
import random
import json
import os
from datetime import datetime
import cv2
import numpy as np
import mss
import pyautogui
import customtkinter as ctk
import keyboard
import pygetwindow as gw  # 在執行緒內動態引入視窗管理庫
from PIL import Image

VERSION = "v0.4.2"  # 🟢 增加這一行，定義當前腳本版本

# 設定 GUI 主題
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# 🟢 修正點：嚴謹判斷目前是執行 Python 原始碼還是編譯後的 EXE
if getattr(sys, 'frozen', False):
    # 如果是 EXE 版本，sys.executable 會精準指向 ".exe" 的路徑
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 如果是 Python 原始碼執行 (.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ICON_PATH = os.path.join(BASE_DIR, "fish_icon.png")

class FishingBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mabinogi Mobile 釣魚助手")
        self.geometry("480x780")  # 調整高度以容納新增的 PIXEL_BUFFER 設定項
        self.attributes("-topmost", True)  # 讓視窗保持在最上層

        # 核心參數變數
        self.game_zone = None  
        self.button_pos = None  
        self.is_running = False
        self.bot_thread = None

        # --- UI 介面配置 ---
        self.title_label = ctk.CTkLabel(self, text="🎣 瑪奇 Mobile 自動釣魚設定", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=15)

        # 0. 視窗標題測試區塊 (新功能)
        self.win_test_frame = ctk.CTkFrame(self)
        self.win_test_frame.pack(pady=5, fill="x", padx=20)

        self.lbl_win_title = ctk.CTkLabel(self.win_test_frame, text="遊戲視窗標題:", font=ctk.CTkFont(size=12))
        self.lbl_win_title.pack(side="left", padx=10, pady=10)

        self.entry_win_title = ctk.CTkEntry(self.win_test_frame, width=140)
        self.entry_win_title.insert(0, "瑪奇 Mobile")  # 預設值
        self.entry_win_title.pack(side="left", padx=5, pady=10)

        self.btn_test_win = ctk.CTkButton(self.win_test_frame, text="測試切換", width=80, fg_color="#e67e22", hover_color="#d35400", command=self.test_window_focus)
        self.btn_test_win.pack(side="right", padx=10, pady=10)

        # 1. 區域設定區塊
        self.zone_frame = ctk.CTkFrame(self)
        self.zone_frame.pack(pady=5, fill="x", padx=20)

        self.btn_select_zone = ctk.CTkButton(self.zone_frame, text="1. 設定釣魚辨識區域", command=self.select_game_zone)
        self.btn_select_zone.pack(side="left", padx=10, pady=10, expand=True)
        
        self.lbl_zone_status = ctk.CTkLabel(self.zone_frame, text="未設定", text_color="red", font=ctk.CTkFont(weight="bold"))
        self.lbl_zone_status.pack(side="right", padx=20)

        # 1.5 圖示範本擷取區塊 (新功能)
        self.icon_frame = ctk.CTkFrame(self)
        self.icon_frame.pack(pady=5, fill="x", padx=20)

        self.btn_capture_icon = ctk.CTkButton(self.icon_frame, text="1.5 擷取開始釣魚圖示範本", command=self.capture_icon_template, fg_color="#1f538d")
        self.btn_capture_icon.pack(side="left", padx=10, pady=10, expand=True)
        
        self.lbl_icon_status = ctk.CTkLabel(self.icon_frame, text="未設定", text_color="red", font=ctk.CTkFont(weight="bold"))
        self.lbl_icon_status.pack(side="right", padx=20)

        # 按鈕座標設定區塊
        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.pack(pady=5, fill="x", padx=20)

        self.btn_select_pos = ctk.CTkButton(self.btn_frame, text="2. 設定收線按鈕位置", command=self.select_button_pos)
        self.btn_select_pos.pack(side="left", padx=10, pady=10, expand=True)

        self.lbl_pos_status = ctk.CTkLabel(self.btn_frame, text="未設定", text_color="red", font=ctk.CTkFont(weight="bold"))
        self.lbl_pos_status.pack(side="right", padx=20)

        # --- 轉折緩衝量 (PIXEL_BUFFER) 設定區塊 ---
        self.buffer_frame = ctk.CTkFrame(self)
        self.buffer_frame.pack(pady=5, fill="x", padx=20)
        
        self.lbl_buffer = ctk.CTkLabel(self.buffer_frame, text="3. 轉折緩衝門檻 (PIXEL_BUFFER):", font=ctk.CTkFont(size=12))
        self.lbl_buffer.pack(side="left", padx=10, pady=10)
        
        self.entry_buffer = ctk.CTkEntry(self.buffer_frame, width=60)
        self.entry_buffer.insert(0, "15")  # 預設預設值為 15
        self.entry_buffer.pack(side="left", padx=5, pady=10)
        
        self.btn_save_buffer = ctk.CTkButton(self.buffer_frame, text="儲存設定", width=80, command=self.save_config)
        self.btn_save_buffer.pack(side="right", padx=10, pady=10)

        # --- 測試模式設定區塊 ---
        self.test_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.test_frame.pack(pady=5, fill="x", padx=40)
        
        self.disable_click_var = ctk.StringVar(value="off")
        self.chk_disable_click = ctk.CTkCheckBox(self.test_frame, text="停用點擊動作（僅測試辨識日誌）", 
                                                 variable=self.disable_click_var, onvalue="on", offvalue="off",
                                                 text_color="orange", font=ctk.CTkFont(weight="bold"))
        self.chk_disable_click.pack(anchor="w")

        # 控制開關
        self.btn_toggle = ctk.CTkButton(self, text="▶ 啟動腳本", fg_color="green", hover_color="darkgreen", 
                                         font=ctk.CTkFont(size=16, weight="bold"), command=self.toggle_bot)
        self.btn_toggle.pack(pady=15, fill="x", padx=40)

        # 快捷鍵提示標籤
        self.shortcut_label = ctk.CTkLabel(self, text="💡 提示：在任何時候按 [Ctrl+Alt+Q] 可緊急停止", text_color="gray")
        self.shortcut_label.pack(pady=2)

        # --- Action Log 區塊 ---
        self.log_label = ctk.CTkLabel(self, text="📋 執行日誌 (Action Log):", font=ctk.CTkFont(size=12, weight="bold"))
        self.log_label.pack(anchor="w", padx=20, pady=(10, 2))

        self.log_box = ctk.CTkTextbox(self, height=200, state="disabled", font=ctk.CTkFont(family="Courier", size=12))
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # 狀態列
        self.status_bar = ctk.CTkLabel(self, text="系統就緒。", anchor="w")
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=5)

        # ----------------------------------------------------
        # 🟢 增加以下這段：在右下角建立獨立的版本號顯示元件
        self.lbl_version = ctk.CTkLabel(
            self.win_test_frame.master, # 掛載在主視窗底部
            text=f"Version: {VERSION}", 
            text_color="gray", 
            font=ctk.CTkFont(size=10)
        )
        # 利用 place 座標法將它固定在視窗的最右下角
        self.lbl_version.place(relx=1.0, rely=1.0, x=-15, y=-22, anchor="se")

        # 註冊全域快捷鍵
        keyboard.add_hotkey("ctrl+alt+q", self.hotkey_stop)
        
        # 讀取歷史設定檔案
        self.load_config()

    def log(self, text):
        self.status_bar.configure(text=str(text))
        current_time = datetime.now().strftime("[%H:%M:%S]")
        log_message = f"{current_time} {text}\n"
        
        self.log_box.configure(state="normal")
        self.log_box.insert("end", log_message)
        self.log_box.see("end")  
        self.log_box.configure(state="disabled")

    def log_error(self, source, e):
        import traceback

        self.log(f"❌ [{source}] {type(e).__name__}: {e}")

        for line in traceback.format_exc().splitlines():
            self.log(line)

    def test_window_focus(self):
        target_title = self.entry_win_title.get().strip()

        self.log(f"🔍 正在測試尋找視窗: 「{target_title}」...")

        try:
            all_windows = gw.getWindowsWithTitle(target_title)

            win = None

            for w in all_windows:
                if w.title == target_title:
                    win = w
                    break

            if not win and all_windows:
                win = all_windows[0]

            if win:
                if win.isMinimized:
                    win.restore()

                win.activate()

                self.log(
                    f"✅ 成功聚焦視窗！標題為: 「{win.title}」"
                )

                self.save_config()

            else:
                self.log(
                    f"❌ 找不到視窗「{target_title}」"
                )

        except Exception as e:
            self.log_error("test_window_focus", e)

    def load_config(self):
        try:
            if not os.path.exists(CONFIG_FILE):
                return

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                config = json.load(f)

            if "game_zone" in config and config["game_zone"]:
                self.game_zone = config["game_zone"]

                self.lbl_zone_status.configure(
                    text="已載入 ✔",
                    text_color="green"
                )

            if "button_pos" in config and config["button_pos"]:
                self.button_pos = tuple(config["button_pos"])

                self.lbl_pos_status.configure(
                    text=f"X:{self.button_pos[0]}, Y:{self.button_pos[1]} ✔",
                    text_color="green"
                )

            if "pixel_buffer" in config:
                self.entry_buffer.delete(0, "end")
                self.entry_buffer.insert(
                    0,
                    str(config["pixel_buffer"])
                )

            if "window_title" in config:
                self.entry_win_title.delete(0, "end")
                self.entry_win_title.insert(
                    0,
                    str(config["window_title"])
                )

            if os.path.exists(ICON_PATH):
                self.has_icon = True

                self.lbl_icon_status.configure(
                    text="已載入 ✔",
                    text_color="green"
                )

            self.log("成功從 config.json 載入歷史設定值。")

        except Exception as e:
            self.log_error("load_config", e)

    def save_config(self):
        try:
            buffer_val = int(
                self.entry_buffer.get().strip()
            )

        except ValueError:
            self.log(
                "❌ 錯誤：PIXEL_BUFFER 必須輸入整數數字！"
            )
            return

        config_data = {
            "window_title": self.entry_win_title.get().strip(),
            "game_zone": self.game_zone,
            "button_pos": self.button_pos,
            "pixel_buffer": buffer_val
        }

        try:
            with open(
                CONFIG_FILE,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    config_data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            self.log("💾 設定檔已成功儲存！")

        except Exception as e:
            self.log_error("save_config", e)
            
    def select_game_zone(self):
        try:
            self.log(
                "請在全螢幕畫面上框選「釣魚進度條」，完成後按 ENTER"
            )

            self.withdraw()

            time.sleep(0.3)

            with mss.mss() as sct:
                monitor = sct.monitors[1]

                self.log(f"[DEBUG] Monitor={monitor}")

                screen_img = np.array(
                    sct.grab(monitor)
                )

                screen_bgr = cv2.cvtColor(
                    screen_img,
                    cv2.COLOR_BGRA2BGR
                )

                cv2.namedWindow(
                    "Select_Zone",
                    cv2.WND_PROP_FULLSCREEN
                )

                cv2.setWindowProperty(
                    "Select_Zone",
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN
                )

                roi = cv2.selectROI(
                    "Select_Zone",
                    screen_bgr,
                    showCrosshair=True,
                    fromCenter=False
                )

                cv2.destroyAllWindows()

            self.deiconify()

            if roi[2] > 0 and roi[3] > 0:

                self.game_zone = {
                    "left": int(roi[0] + monitor["left"]),
                    "top": int(roi[1] + monitor["top"]),
                    "width": int(roi[2]),
                    "height": int(roi[3])
                }

                self.lbl_zone_status.configure(
                    text="已設定 ✔",
                    text_color="green"
                )

                self.log(
                    f"區域設定成功 -> "
                    f"W:{self.game_zone['width']} "
                    f"H:{self.game_zone['height']}"
                )

                self.save_config()

            else:
                self.log("取消區域選取。")

        except Exception as e:

            try:
                cv2.destroyAllWindows()
            except:
                pass

            self.deiconify()

            self.log_error(
                "select_game_zone",
                e
            )

    def select_button_pos(self):

        self.log(
            "請將滑鼠移到遊戲的「收線按鈕」上..."
        )

        def get_pos():

            try:

                for i in range(3, 0, -1):

                    self.log(
                        f"請瞄準按鈕... 倒數 {i} 秒"
                    )

                    time.sleep(1)

                x, y = pyautogui.position()

                self.button_pos = (x, y)

                self.lbl_pos_status.configure(
                    text=f"X:{x}, Y:{y} ✔",
                    text_color="green"
                )

                self.log(
                    f"按鈕座標已鎖定：({x}, {y})"
                )

                self.save_config()

            except Exception as e:

                self.after(
                    0,
                    lambda err=e:
                    self.log_error(
                        "select_button_pos",
                        err
                    )
                )

        threading.Thread(
            target=get_pos,
            daemon=True
        ).start()

    def capture_icon_template(self):

        try:

            self.log(
                "請在全螢幕畫面上，精準框選遊戲彈出的開始釣魚圖示"
            )

            self.withdraw()

            time.sleep(0.3)

            with mss.mss() as sct:

                monitor = sct.monitors[1]

                self.log(
                    f"[DEBUG] Monitor={monitor}"
                )

                screen_img = np.array(
                    sct.grab(monitor)
                )

                screen_bgr = cv2.cvtColor(
                    screen_img,
                    cv2.COLOR_BGRA2BGR
                )

                cv2.namedWindow(
                    "Capture_Icon",
                    cv2.WND_PROP_FULLSCREEN
                )

                cv2.setWindowProperty(
                    "Capture_Icon",
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN
                )

                roi = cv2.selectROI(
                    "Capture_Icon",
                    screen_bgr,
                    showCrosshair=True,
                    fromCenter=False
                )

                cv2.destroyAllWindows()

            self.deiconify()

            if roi[2] > 0 and roi[3] > 0:

                x, y, w, h = (
                    int(roi[0]),
                    int(roi[1]),
                    int(roi[2]),
                    int(roi[3])
                )

                cropped_icon = screen_bgr[
                    y:y+h,
                    x:x+w
                ]

                try:
                    self.log(f"[DEBUG] Save Path={ICON_PATH}")
                    self.log(f"[DEBUG] Shape={cropped_icon.shape}")
                    self.log(f"[DEBUG] Size={cropped_icon.size}")

                    if cropped_icon.size == 0:
                        raise ValueError("cropped_icon 為空")

                    img = Image.fromarray(
                        cv2.cvtColor(
                            cropped_icon,
                            cv2.COLOR_BGR2RGB
                        )
                    )

                    img.save(
                        ICON_PATH,
                        format="PNG"
                    )

                    self.log("✅ Pillow 儲存成功")
                
                    result=True

                except Exception as e:
                    self.log_error(
                        "PIL.Image.save",
                        e
                    )

                    result=False

                self.log(
                    f"[DEBUG] Save Result={result}"
                )

                self.has_icon = True

                self.lbl_icon_status.configure(
                    text="已設定 ✔",
                    text_color="green"
                )

                self.log(
                    "💾 圖示範本已成功擷取並儲存"
                )

                self.save_config()

            else:

                self.log("取消圖示擷取。")

        except Exception as e:

            try:
                cv2.destroyAllWindows()
            except:
                pass

            self.deiconify()

            self.log_error(
                "capture_icon_template",
                e
            )

    def toggle_bot(self):
        if self.is_running:
            self.stop_bot()
        else:
            if not self.game_zone or not self.button_pos:
                self.log("❌ 錯誤：請先設定辨識區域與按鈕位置！")
                return
            
            self.is_running = True
            self.btn_toggle.configure(text="🔕 停止腳本", fg_color="red", hover_color="darkred")
            
            if self.disable_click_var.get() == "on":
                self.log("🚀 自動辨識啟動中（🔧 測試模式：已停用實體點擊）...")
            else:
                self.log("🚀 自動釣魚啟動中（正常模式）...")
            
            self.bot_thread = threading.Thread(target=self.fishing_logic, daemon=True)
            self.bot_thread.start()

    def stop_bot(self):
        if self.is_running:
            self.is_running = False
            self.btn_toggle.configure(text="▶ 啟動腳本", fg_color="green", hover_color="darkgreen")
            self.log("🛑 腳本已安全停止。")
            pyautogui.mouseUp()

    def hotkey_stop(self):
        if self.is_running:
            self.after(0, lambda: self.log("⌨ 偵測到快捷鍵 [Ctrl+Alt+Q]"))
            self.after(0, self.stop_bot)

    def fishing_logic(self):
        """核心辨識邏輯：包含客製化圖示、綠條轉折、滑鼠點擊歸位，以及 30 秒閒置重置視窗機制"""
        import pygetwindow as gw  # 動態引入視窗管理庫

        prev_green_pixels = 0
        is_shrinking = False  
        
        # 初始化閒置計時器
        idle_start_time = time.time()

        # 根據剛剛 user 裁剪的實體檔案讀取圖示範本
        template = None
        if self.has_icon and os.path.exists(ICON_PATH):
            # 🟢 更改點：改為彩色讀取範本
            template = cv2.imread(ICON_PATH, cv2.IMREAD_COLOR)
            self.after(0, lambda: self.log("ℹ️ 背景已成功加載客製化圖示範本 (彩色模式)。"))
        else:
            self.after(0, lambda: self.log("⚠️ 提示：未設定圖示範本，將僅使用綠條轉折機制。"))

        with mss.mss() as sct:
            monitor_full = sct.monitors[1]

            while self.is_running:
                try:
                    pixel_buffer = int(self.entry_buffer.get().strip())
                except ValueError:
                    pixel_buffer = 15  

                # 📌 每次循環先記錄當前滑鼠位置，供後續點擊或重置後歸位使用
                current_mouse_x, current_mouse_y = pyautogui.position()
                
                # 判定當前是否有觸發任何辨識動作（有動作就代表不閒置）
                action_triggered = False

                # 1. 擷取畫面
                zone_img = np.array(sct.grab(self.game_zone))
                zone_bgr = cv2.cvtColor(zone_img, cv2.COLOR_BGRA2BGR)
                zone_hsv = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2HSV)

                # --- 機制 A：客製化圖示偵測 ---
                if template is not None:
                    # 🟢 更改點：移除 full_gray，直接使用 full_bgr 進行彩色匹配
                    full_img = np.array(sct.grab(monitor_full))
                    full_bgr = cv2.cvtColor(full_img, cv2.COLOR_BGRA2BGR)
                    
                    h_img, w_img = full_bgr.shape[:2]
                    h_tpl, w_tpl = template.shape[:2]
                    
                    if h_img >= h_tpl and w_img >= w_tpl:
                        # 🟢 更改點：使用彩色矩陣傳入
                        res = cv2.matchTemplate(full_bgr, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        
                        # 因為彩色比對更精準，信心度門檻可以維持 0.85 
                        if max_val > 0.85:
                            action_triggered = True  
                            if self.disable_click_var.get() == "on":
                                self.after(0, lambda v=max_val: self.log(f"🔬 [測試] 全域偵測到開始釣魚圖示！(信心度:{v:.2f}) -> ⚠️ 跳過點擊"))
                            else:
                                self.after(0, lambda v=max_val: self.log(f"🎯 [正常] 全域偵測到開始釣魚圖示 (信心度:{v:.2f}) -> 立刻開始釣魚"))
                                pyautogui.click(self.button_pos)
                                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                                
                            time.sleep(0.8)
                            prev_green_pixels = 0
                            is_shrinking = False
                            idle_start_time = time.time()  
                            continue

                # --- 機制 B：精確綠色條轉折偵測 ---
                lower_green = np.array([50, 200, 180])   
                upper_green = np.array([70, 255, 255]) 
                mask = cv2.inRange(zone_hsv, lower_green, upper_green)
                current_green_pixels = cv2.countNonZero(mask)

                if current_green_pixels > 50:
                    action_triggered = True  # 有辨識到綠條，重置閒置狀態
                    if current_green_pixels < (prev_green_pixels - 5):
                        if not is_shrinking:
                            is_shrinking = True
                            self.after(0, lambda: self.log("📉 綠色條正在向左縮短..."))
                            
                    elif current_green_pixels > (prev_green_pixels + pixel_buffer):
                        if is_shrinking:
                            is_shrinking = False
                            
                            reaction_delay = random.uniform(0.10, 0.50)
                            if self.disable_click_var.get() == "on":
                                self.after(0, lambda d=reaction_delay: self.log(
                                    f"🔬 [測試] 偵測到轉折！預計延遲 {d:.2f} 秒 -> ⚠️ 點擊已跳過"
                                ))
                            else:
                                self.after(0, lambda d=reaction_delay: self.log(
                                    f"🎯 [正常] 偵測到轉折！等待真人反應 {d:.2f} 秒後收線..."
                                ))
                                time.sleep(reaction_delay)
                                # 🟢 點擊並立刻讓滑鼠游標歸位
                                pyautogui.click(self.button_pos)
                                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                            
                    if not is_shrinking or current_green_pixels < prev_green_pixels:
                        prev_green_pixels = current_green_pixels
                else:
                    is_shrinking = False
                    prev_green_pixels = 0

                # --- ⏳ 30秒閒置防斷線重置機制 ---
                if action_triggered:
                    idle_start_time = time.time()  
                else:
                    elapsed_idle_time = time.time() - idle_start_time
                    if elapsed_idle_time > 30.0:  
                        self.after(0, lambda: self.log("⏰ 系統已閒置超過 30 秒，執行防斷線/喚醒機制..."))
                        
                        try:
                            # 🟢 修正點：在這裡重新獲取最新輸入框的視窗標題
                            target_window_title = self.entry_win_title.get().strip()

                            # 改用完全匹配尋找視窗
                            all_windows = gw.getWindowsWithTitle(target_window_title)
                            win = None
                            for w in all_windows:
                                if w.title == target_window_title:
                                    win = w
                                    break
                            if not win and all_windows:
                                win = all_windows

                            if win:
                                if win.isMinimized:
                                    win.restore()  
                                win.activate()     
                                time.sleep(0.5)    
                                
                                self.after(0, lambda: self.log("⌨️ 已聚焦視窗，自動按下 [W] 鍵。"))
                                pyautogui.press('w')
                                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                            else:
                                # 🟢 修正點：將這裡的變數改為與上面一致的局部變數 t
                                self.after(0, lambda t=target_window_title: self.log(f"❌ 找不到視窗「{t}」，請檢查上方標題欄。"))
                        except Exception as e:
                            self.after(
                                0,
                                lambda err=e:
                                self.log_error(
                                    "fishing_logic",
                                    err
                                )
                            )
                        
                        idle_start_time = time.time()# --- ⏳ 30秒閒置防斷線重置機制 ---
                if action_triggered:
                    idle_start_time = time.time()  
                else:
                    elapsed_idle_time = time.time() - idle_start_time
                    if elapsed_idle_time > 30.0:  
                        self.after(0, lambda: self.log("⏰ 系統已閒置超過 30 秒，執行防斷線/喚醒機制..."))
                        
                        try:
                            # 🟢 修正點：在這裡重新獲取最新輸入框的視窗標題
                            target_window_title = self.entry_win_title.get().strip()

                            # 改用完全匹配尋找視窗
                            all_windows = gw.getWindowsWithTitle(target_window_title)
                            win = None
                            for w in all_windows:
                                if w.title == target_window_title:
                                    win = w
                                    break
                            if not win and all_windows:
                                win = all_windows

                            if win:
                                if win.isMinimized:
                                    win.restore()  
                                win.activate()     
                                time.sleep(0.5)    
                                
                                self.after(0, lambda: self.log("⌨️ 已聚焦視窗，自動按下 [W] 鍵。"))
                                pyautogui.press('w')
                                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                            else:
                                # 🟢 修正點：將這裡的變數改為與上面一致的局部變數 t
                                self.after(0, lambda t=target_window_title: self.log(f"❌ 找不到視窗「{t}」，請檢查上方標題欄。"))
                        except Exception as e:
                            self.after(0, lambda e=str(e): self.log(f"⚠️ 視窗切換失敗: {e}"))
                        
                        idle_start_time = time.time()

                # 稍微放慢畫面採樣率，降至約每秒 20 次，降低 CPU 負擔
                time.sleep(0.3)
            
            pyautogui.mouseUp()

if __name__ == "__main__":
    app = FishingBotGUI()
    app.mainloop()
