import tkinter as tk
from tkinter import ttk, Menu, messagebox
import os
import sys
import re
import requests
from getword import get_random_word, get_word_by_rank
from pystray import Icon, Menu as TrayMenu, MenuItem
from PIL import Image, ImageDraw
import json

class CustomPopup:
    def __init__(self, root):
        self.root = root
        self.root.title("单词默写助手")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.97)
        self.root.attributes("-topmost", True)

        self.transparent_color = "#00ff00"
        self.root.attributes("-transparentcolor", self.transparent_color)
        
        self.word = tk.StringVar(value="单词")
        self.pos = tk.StringVar(value="词性")
        self.definition = tk.StringVar(value="释义")
        self.example = tk.StringVar(value="例句")
        self.daily_saying = tk.StringVar(value="加载每日一言中...")
        self.current_word = ""
        self.current_word_rank = ""
        self.current_raw_sentences = []
        
        self.appdata_dir = os.path.join(os.environ.get('APPDATA'), "WordHelper")  
        os.makedirs(self.appdata_dir, exist_ok=True)
        self.learned_file = os.path.join(self.appdata_dir, "_user_.txt")
        self.corner_radius = 20
        
        self.bg_color = "#ffffff"
        self.border_color = "#dddddd"
        self.text_color = "#333333"
        
        self.canvas = tk.Canvas(
            self.root, 
            bg=self.transparent_color,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.frame = ttk.Frame(self.canvas, style="Transparent.TFrame")
        self.frame_id = self.canvas.create_window(
            self.corner_radius//2, self.corner_radius//2,
            window=self.frame, 
            anchor="nw"
        )
        
        self.create_widgets()
        self.draw_rounded_background()
        
        self.canvas.bind("<Configure>", self.on_resize)
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<Button-3>", self.show_right_click_menu)
        
        self.create_right_click_menu()
        
        self.root.geometry(f"{840 + self.corner_radius//5}x{350 + self.corner_radius//5}+500+300")
        
        self.create_tray_icon()
        

        self.refresh_word()
        self.fetch_daily_saying()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("Word.TLabel", font=("楷体", 20, "bold"), background=self.bg_color)
        style.configure("Pos.TLabel", font=("楷体", 14, "italic"), background=self.bg_color, foreground="#666")
        style.configure("Definition.TLabel", font=("楷体", 12), background=self.bg_color, wraplength=800)
        style.configure("Example.TLabel", font=("楷体", 12), background=self.bg_color, foreground="#555", wraplength=800)
        style.configure("Saying.TLabel", font=("楷体", 10, "italic"), background=self.bg_color, foreground="#888", wraplength=800)
        style.configure("Transparent.TFrame", background=self.bg_color)

        ttk.Label(self.frame, textvariable=self.daily_saying, style="Saying.TLabel").pack(pady=(5, 5), padx=10, anchor=tk.W)
        ttk.Label(self.frame, textvariable=self.word, style="Word.TLabel").pack(pady=(5, 5), anchor=tk.CENTER)
        ttk.Label(self.frame, textvariable=self.pos, style="Pos.TLabel").pack(pady=(0, 10), anchor=tk.CENTER)
        ttk.Label(self.frame, textvariable=self.definition, style="Definition.TLabel").pack(pady=(0, 10), padx=10, anchor=tk.W, fill=tk.X)
        ttk.Label(self.frame, textvariable=self.example, style="Example.TLabel").pack(padx=10, anchor=tk.W, fill=tk.X)

    def fetch_daily_saying(self):
        try:
            user_key = requests.post(
                'https://luckycola.com.cn/ai/getColaKey',
                data={'uid': 'YOUR__UID', "appKey":"YOUR_APP_KEY"},
                timeout=5
            )
            user_key = user_key.json()
            Cola = user_key.get('data', {}).get('cola_key', 'empty')
            response = requests.post(
                'https://luckycola.com.cn/tools/yiyan',
                data={'ColaKey': Cola},
                timeout=5
            )
            response.raise_for_status()
            response_json = response.json()
            note_content = response_json.get('data', {}).get('note', '今日暂无一言')
            self.daily_saying.set(f"每日一言：{note_content}")
        except requests.exceptions.RequestException:
            self.daily_saying.set(f"每日一言加载失败：网络错误")
        except json.JSONDecodeError:
            self.daily_saying.set(f"每日一言加载失败：数据格式错误")
        except Exception as e:
            self.daily_saying.set(f"每日一言加载失败：{Cola}")

    def delete_cache(self):
        if not os.path.exists(self.learned_file):
            messagebox.showinfo("提示", "暂无缓存（已背诵记录为空）")
            return
        confirm = messagebox.askyesno("确认删除", "是否删除所有已背诵记录？此操作不可恢复！")
        if not confirm:
            return
        try:
            os.remove(self.learned_file)
            messagebox.showinfo("成功", "已删除所有已背诵记录")
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{str(e)}")

    def create_right_click_menu(self):
        self.right_click_menu = Menu(self.root, tearoff=0)
        self.right_click_menu.add_command(label="换一个单词", command=self.refresh_word)
        self.right_click_menu.add_command(label="默写已背单词", command=self.open_recite_window)
        self.right_click_menu.add_command(label="我已背诵", command=self.mark_as_learned)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="删除缓存（已背诵记录）", command=self.delete_cache)  # 新增选项
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="切换置顶", command=self.toggle_topmost)
        self.right_click_menu.add_command(label="关闭", command=self.close_all)

    def mark_as_learned(self):
        if not self.current_word or not self.current_word_rank:
            messagebox.showinfo("提示", "没有可标记的单词或单词信息不完整")
            return
        
        learned_words = {}
        if os.path.exists(self.learned_file):
            try:
                with open(self.learned_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "," in line:
                            word, rank = line.split(",", 1)
                            learned_words[word] = rank
            except Exception as e:
                messagebox.showerror("错误", f"读取背诵记录失败：{str(e)}")
                return
        
        if self.current_word in learned_words:
            messagebox.showinfo("提示", f"{self.current_word}已在背诵列表中")
            return
        
        try:
            with open(self.learned_file, "a", encoding="utf-8") as f:
                f.write(f"{self.current_word},{self.current_word_rank}\n")
            messagebox.showinfo("成功", f"已添加{self.current_word}到背诵列表（存储于AppData）")
            self.refresh_word()
        except Exception as e:
            messagebox.showerror("错误", f"写入失败：{str(e)}")

    def open_recite_window(self):
        if not os.path.exists(self.learned_file):
            messagebox.showinfo("提示", "请先标记单词为“已背诵”")
            return
        
        learned_words = {}
        try:
            with open(self.learned_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "," in line:
                        word, rank = line.split(",", 1)
                        learned_words[word] = rank
        except Exception as e:
            messagebox.showerror("错误", f"读取背诵记录失败：{str(e)}")
            return
        
        if not learned_words:
            messagebox.showinfo("提示", "背诵列表为空，请先标记单词")
            return
        
        import random
        selected_word, selected_rank = random.choice(list(learned_words.items()))
        
        try:
            word_info = get_word_by_rank(selected_rank)
        except Exception as e:
            messagebox.showerror("错误", f"获取单词数据失败：{str(e)}")
            return
        
        target_word = selected_word.lower()
        valid_sentences = []
        for s in word_info["raw_sentences"]:
            eng_sentence = s.get("sContent", "").lower()
            if re.search(rf"\b{re.escape(target_word)}\b", eng_sentence):
                valid_sentences.append(s)
        
        if not valid_sentences:
            messagebox.showinfo("提示", f"未找到包含 {selected_word} 的例句，无法默写")
            return
        
        ReciteWindow(self.root, selected_word, valid_sentences)

    def show_right_click_menu(self, event):
        self.right_click_menu.post(event.x_root, event.y_root)
        
    def draw_rounded_background(self):
        self.canvas.delete("background")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width <= 0 or height <= 0:
            return
        r = min(self.corner_radius, width//2, height//2)
        
        points = [
            r, 0, width - r, 0,
            width, 0, width, r,
            width, height - r, width, height, width - r, height,
            r, height, 0, height, 0, height - r,
            0, r, 0, 0, r, 0
        ]
        
        self.canvas.create_polygon(
            [p+0.5 for p in points],
            fill=self.bg_color, outline="", smooth=True, splinesteps=48, tags="background"
        )
        self.canvas.create_polygon(
            points, fill="", outline=self.border_color, smooth=True, splinesteps=48, width=1.5, tags="background"
        )
        self.canvas.tag_lower("background")

    def toggle_topmost(self):
        current = self.root.attributes("-topmost")
        self.root.attributes("-topmost", not current)

    def on_resize(self, event):
        padding = self.corner_radius
        self.canvas.itemconfig(self.frame_id, width=event.width - padding, height=event.height - padding)
        self.draw_rounded_background()

    def start_drag(self, event):
        self.x, self.y = event.x, event.y

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self.x
        y = self.root.winfo_y() + event.y - self.y
        self.root.geometry(f"+{x}+{y}")

    def refresh_word(self):
        try:
            word_info = get_random_word()
            self.current_word = word_info["word"]
            self.current_word_rank = word_info["word_rank"]
            self.current_raw_sentences = word_info["raw_sentences"]
            self.word.set(word_info["word"])
            self.pos.set(word_info["pos"])
            self.definition.set(word_info["definition"])
            self.example.set(word_info["example"])
        except Exception as e:
            self.definition.set(f"错误：{str(e)}")
            self.current_word = ""
            self.current_word_rank = ""
            self.current_raw_sentences = []

    def create_tray_icon(self):
        image = Image.new("RGB", (128, 128), color="white")
        draw = ImageDraw.Draw(image)
        draw.text((30, 40), "词", font_size=60, fill="black")
        
        tray_menu = TrayMenu(
            MenuItem("显示窗口", self.show_window),
            MenuItem("隐藏窗口", self.hide_window),
            MenuItem("退出", self.close_all)
        )
        
        self.tray = Icon("单词助手", image, "单词助手", tray_menu)
        import threading
        threading.Thread(target=self.tray.run, daemon=True).start()

    def show_window(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def hide_window(self):
        self.root.iconify()

    def close_all(self):
        self.tray.stop()
        self.root.destroy()


class ReciteWindow(tk.Toplevel):
    def __init__(self, parent, target_word, sentences):
        super().__init__(parent)
        self.title("默写已背单词")
        self.geometry("650x300")
        self.resizable(False, False)
        self.target_word = target_word
        self.target_word_lower = target_word.lower()
        self.sentence = self._select_and_process_sentence(sentences)
        self.user_input = tk.StringVar()
        self.create_ui()

    def _select_and_process_sentence(self, sentences):
        import random
        selected = random.choice(sentences)
        eng = selected["sContent"]
        cn = selected["sCn"]
        pattern = re.compile(rf"\b{re.escape(self.target_word_lower)}\b", re.IGNORECASE)
        masked_eng = pattern.sub("______", eng)
        return {"original_eng": eng, "masked_eng": masked_eng, "cn": cn}

    def create_ui(self):
        ttk.Label(
            self,
            text="请根据例句填写缺失的单词（已背单词）：",
            font=("楷体", 12, "bold")
        ).pack(pady=(15, 10), anchor=tk.W, padx=20)
        
        ttk.Label(
            self,
            text=self.sentence["masked_eng"],
            font=("楷体", 14),
            wraplength=600,
            foreground="#2c3e50"
        ).pack(pady=(0, 20), anchor=tk.W, padx=20)
        
        input_frame = ttk.Frame(self)
        input_frame.pack(pady=(0, 20), padx=20, fill=tk.X)
        
        ttk.Label(input_frame, text="单词：", font=("楷体", 12)).pack(side=tk.LEFT, padx=5)
        ttk.Entry(
            input_frame,
            textvariable=self.user_input,
            font=("楷体", 14),
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            self,
            text="提交",
            command=self.check_answer
        ).pack(pady=10)

    def check_answer(self):
        user_input = self.user_input.get().strip().lower()
        if not user_input:
            messagebox.showinfo("提示", "请输入单词")
            return
        
        if user_input == self.target_word_lower:
            result = "正确！"
            color = "#27ae60"
        else:
            result = f"错误！正确答案是：{self.target_word}"
            color = "#e74c3c"
        
        detail = f"\n完整例句：\n{self.sentence['original_eng']}\n{self.sentence['cn']}"
        result_window = tk.Toplevel(self)
        result_window.title("默写结果")
        result_window.geometry("500x200")
        result_window.resizable(False, False)
        
        ttk.Label(
            result_window,
            text=result,
            font=("楷体", 16, "bold"),
            foreground=color
        ).pack(pady=10)
        
        ttk.Label(
            result_window,
            text=detail,
            font=("楷体", 12),
            wraplength=450
        ).pack(pady=10, padx=20)
        
        ttk.Button(
            result_window,
            text="关闭",
            command=lambda: [result_window.destroy(), self.destroy()]
        ).pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = CustomPopup(root)
    root.mainloop()
