import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import calendar
import random
import threading
import time
import os

# Third-party imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from win10toast import ToastNotifier

# --- PROFESSIONAL DESIGN SYSTEM ---
COLORS = {
    "bg_main": "#0B0E14",
    "bg_card": "#161B22",
    "sidebar": "#010409",
    "accent": "#7928CA",
    "accent_light": "#FF0080",
    "success": "#00FF88",
    "danger": "#F85149",
    "text": "#F5F5F7",
    "text_dim": "#8B949E",
}

class HabitDB:
    def __init__(self):
        self.conn = sqlite3.connect("habitflow_v1.db", check_same_thread=False)
        self.cur = self.conn.cursor()
        self.migrate()

    def migrate(self):
        self.cur.execute('''CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, start_date TEXT, emoji TEXT)''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS logs (
            habit_id INTEGER, date TEXT, UNIQUE(habit_id, date))''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT)''')
        self.conn.commit()

class HabitFlow:
    def __init__(self, root):
        self.root = root
        self.root.title("HabitFlow | V1.0")
        self.root.geometry("1200x850")
        self.root.configure(bg=COLORS["bg_main"])
        
        self.db = HabitDB()
        self.notifier = ToastNotifier()
        self.active_tab = "Dashboard"
        
        self.view_month = datetime.now().month
        self.view_year = datetime.now().year
        
        if not self.get_setting("bg_permission"):
            self.show_welcome_screen()
        else:
            self.setup_layout()
            self.refresh_view()
            self.trigger_startup_notification()

    def get_setting(self, key):
        res = self.db.cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return res[0] if res else None

    # --- ANIMATION ENGINE ---
    def fade_in_widget(self, widget, delay=0.01):
        widget.attributes("-alpha", 0.0)
        def run_fade():
            alpha = 0.0
            while alpha < 1.0:
                alpha += 0.05
                widget.attributes("-alpha", alpha)
                time.sleep(delay)
        threading.Thread(target=run_fade, daemon=True).start()

    def animate_content_entry(self):
        """Creates a smooth slide-up effect for the main content"""
        self.content.place_configure(rely=0.05)
        def slide():
            for i in range(5, 0, -1):
                time.sleep(0.01)
                self.content.place_configure(rely=i/100)
        threading.Thread(target=slide, daemon=True).start()

    def create_sparkle(self, x, y):
        colors = [COLORS["success"], COLORS["accent_light"], "#FFFFFF", COLORS["accent"]]
        for _ in range(8):
            sparkle = tk.Label(self.root, text=random.choice(["✨", "⭐", "💫", "💎"]), 
                              fg=random.choice(colors), bg=COLORS["bg_main"], font=("Arial", 14))
            sx, sy = x + random.randint(-30, 30), y + random.randint(-30, 30)
            sparkle.place(x=sx, y=sy)
            def animate(s=sparkle, start_x=sx, start_y=sy):
                for i in range(30):
                    time.sleep(0.02)
                    if s.winfo_exists():
                        s.place(x=start_x + (random.randint(-2,2)), y=start_y - (i * 4))
                s.destroy()
            threading.Thread(target=animate, daemon=True).start()

    # --- UI LAYOUT ---
    def setup_layout(self):
        self.sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=260)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        tk.Label(self.sidebar, text="HABITFLOW", fg="white", bg=COLORS["sidebar"], font=("Arial Black", 22)).pack(pady=50)
        
        self.menu_btns = {}
        menu = [("📊", "Dashboard"), ("📈", "Analytics"), ("📅", "Calendar"), ("⚙️", "Manage"), ("❤️", "Credits")]
        for icon, name in menu:
            btn = tk.Button(self.sidebar, text=f"  {icon}  {name}", 
                          fg=COLORS["text_dim"] if name != self.active_tab else "white", 
                          bg=COLORS["sidebar"] if name != self.active_tab else COLORS["bg_card"],
                          font=("Segoe UI", 11, "bold" if name == self.active_tab else "normal"), 
                          bd=0, anchor="w", padx=40, pady=20, cursor="hand2",
                          command=lambda n=name: self.switch_tab(n))
            btn.pack(fill=tk.X)
            # Hover effects
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#1A1D23"))
            btn.bind("<Leave>", lambda e, b=btn, n=name: b.config(bg=COLORS["sidebar"] if n != self.active_tab else COLORS["bg_card"]))
            self.menu_btns[name] = btn

        self.content = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.content.place(relx=0.217, rely=0, relwidth=0.783, relheight=1)

    def switch_tab(self, tab):
        self.active_tab = tab
        for name, btn in self.menu_btns.items():
            if name == tab:
                btn.config(fg="white", bg=COLORS["bg_card"], font=("Segoe UI", 11, "bold"))
            else:
                btn.config(fg=COLORS["text_dim"], bg=COLORS["sidebar"], font=("Segoe UI", 11, "normal"))
        self.refresh_view()
        self.animate_content_entry()

    def refresh_view(self):
        for w in self.content.winfo_children(): w.destroy()
        header = tk.Frame(self.content, bg=COLORS["bg_main"], padx=50, pady=40)
        header.pack(fill=tk.X)
        tk.Label(header, text=self.active_tab, fg="white", bg=COLORS["bg_main"], font=("Segoe UI", 32, "bold")).pack(side=tk.LEFT)
        
        if self.active_tab == "Dashboard": self.draw_dashboard()
        elif self.active_tab == "Analytics": self.draw_analytics()
        elif self.active_tab == "Calendar": self.draw_calendar()
        elif self.active_tab == "Manage": self.draw_manager()
        elif self.active_tab == "Credits": self.draw_credits()

    # --- VIEWS ---
    def draw_dashboard(self):
        habits = self.db.cur.execute("SELECT * FROM habits").fetchall()
        if not habits:
            self.draw_empty_state()
            return
        container = tk.Frame(self.content, bg=COLORS["bg_main"], padx=50)
        container.pack(fill=tk.BOTH, expand=True)
        today = datetime.now().strftime("%Y-%m-%d")
        for h in habits:
            done = self.db.cur.execute("SELECT 1 FROM logs WHERE habit_id=? AND date=?", (h[0], today)).fetchone()
            card = tk.Frame(container, bg=COLORS["bg_card"], pady=25, padx=35)
            card.pack(fill=tk.X, pady=12)
            tk.Label(card, text=f"{h[3]}  {h[1]}", fg="white", bg=COLORS["bg_card"], font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
            btn_text = "COMPLETED ✅" if done else "MARK DONE 🎯"
            btn_color = COLORS["success"] if done else COLORS["accent"]
            btn = tk.Button(card, text=btn_text, bg=btn_color, fg="white", font=("Segoe UI", 10, "bold"), 
                          bd=0, padx=25, pady=12, cursor="hand2", command=lambda id=h[0], d=done: self.toggle_habit(id, d))
            btn.pack(side=tk.RIGHT)

    def toggle_habit(self, h_id, done):
        date = datetime.now().strftime("%Y-%m-%d")
        if not done:
            mx, my = self.root.winfo_pointerx() - self.root.winfo_rootx(), self.root.winfo_pointery() - self.root.winfo_rooty()
            self.create_sparkle(mx, my)
            self.db.cur.execute("INSERT INTO logs VALUES (?,?)", (h_id, date))
        else:
            self.db.cur.execute("DELETE FROM logs WHERE habit_id=? AND date=?", (h_id, date))
        self.db.conn.commit()
        self.refresh_view()

    def draw_calendar(self):
        container = tk.Frame(self.content, bg=COLORS["bg_main"], padx=50)
        container.pack(fill=tk.BOTH, expand=True)
        nav = tk.Frame(container, bg=COLORS["bg_main"])
        nav.pack(fill=tk.X, pady=10)
        tk.Button(nav, text="❮", bg=COLORS["bg_card"], fg="white", bd=0, padx=20, pady=10, command=lambda: self.change_month(-1)).pack(side=tk.LEFT)
        month_str = f"{calendar.month_name[self.view_month]} {self.view_year}".upper()
        tk.Label(nav, text=month_str, fg=COLORS["accent_light"], bg=COLORS["bg_main"], font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT, expand=True)
        tk.Button(nav, text="❯", bg=COLORS["bg_card"], fg="white", bd=0, padx=20, pady=10, command=lambda: self.change_month(1)).pack(side=tk.RIGHT)

        grid = tk.Frame(container, bg=COLORS["bg_main"])
        grid.pack(pady=20)
        
        

        for i, d in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]):
            tk.Label(grid, text=d, fg=COLORS["text_dim"], bg=COLORS["bg_main"], font=("Segoe UI", 9, "bold")).grid(row=0, column=i, pady=10)

        cal_data = calendar.monthcalendar(self.view_year, self.view_month)
        logs = [l[0] for l in self.db.cur.execute("SELECT date FROM logs").fetchall()]
        today = datetime.now().strftime("%Y-%m-%d")

        month_hits, total_days = 0, 0
        for r, week in enumerate(cal_data):
            for c, day in enumerate(week):
                if day == 0: continue
                total_days += 1
                ds = f"{self.view_year}-{self.view_month:02d}-{day:02d}"
                is_done = ds in logs
                if is_done: month_hits += 1
                bg = COLORS["success"] if is_done else COLORS["bg_card"]
                fg = "black" if is_done else "white"
                border = COLORS["accent"] if ds == today else COLORS["bg_card"]
                cell = tk.Frame(grid, bg=border, padx=1, pady=1)
                cell.grid(row=r+1, column=c, padx=4, pady=4)
                tk.Label(cell, text=str(day), width=6, height=3, bg=bg, fg=fg, font=("Segoe UI", 10, "bold")).pack()

        footer = tk.Frame(container, bg=COLORS["bg_card"], pady=20)
        footer.pack(fill=tk.X, pady=20)
        consistency = (month_hits / total_days * 100) if total_days > 0 else 0
        for val, lab in [(month_hits, "COMPLETED"), (f"{consistency:.1f}%", "CONSISTENCY"), (total_days, "TOTAL DAYS")]:
            b = tk.Frame(footer, bg=COLORS["bg_card"])
            b.pack(side=tk.LEFT, expand=True)
            tk.Label(b, text=val, fg=COLORS["success"], bg=COLORS["bg_card"], font=("Segoe UI", 20, "bold")).pack()
            tk.Label(b, text=lab, fg=COLORS["text_dim"], bg=COLORS["bg_card"], font=("Segoe UI", 8, "bold")).pack()

    def change_month(self, delta):
        self.view_month += delta
        if self.view_month > 12: self.view_month = 1; self.view_year += 1
        elif self.view_month < 1: self.view_month = 12; self.view_year -= 1
        self.refresh_view()

    def draw_credits(self):
        f = tk.Frame(self.content, bg=COLORS["bg_main"])
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="Developed by Ritesh ❤️", fg=COLORS["accent_light"], bg=COLORS["bg_main"], font=("Segoe UI", 32, "bold")).pack()
        tk.Label(f, text="Instagram: @riteshhuyaar", fg=COLORS["accent"], bg=COLORS["bg_main"], font=("Segoe UI", 18)).pack(pady=10)
        
        # Version Tag
        ver_frame = tk.Frame(f, bg="#1A1D23", padx=20, pady=5)
        ver_frame.pack(pady=20)
        tk.Label(ver_frame, text="VERSION 1.0 (TITANIUM BUILD)", fg=COLORS["text_dim"], bg="#1A1D23", font=("Consolas", 10, "bold")).pack()

    def show_welcome_screen(self):
        self.welcome = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.welcome.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = tk.Frame(self.welcome, bg=COLORS["bg_card"], padx=80, pady=80)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        title = tk.Label(card, text="HABITFLOW", fg=COLORS["accent_light"], bg=COLORS["bg_card"], font=("Segoe UI", 40, "bold"))
        title.pack()

        # Breathing Animation
        def breathe():
            colors = ["#FF0080", "#FF1A8D", "#FF3399", "#FF4DA6", "#FF66B3", "#FF4DA6", "#FF3399", "#FF1A8D"]
            i = 0
            while self.welcome.winfo_exists():
                try: title.config(fg=colors[i % len(colors)]); i += 1; time.sleep(0.15)
                except: break
        threading.Thread(target=breathe, daemon=True).start()

        tk.Label(card, text="Streamline your growth.", fg="white", bg=COLORS["bg_card"], font=("Segoe UI", 14)).pack(pady=20)
        tk.Button(card, text="GET STARTED", bg=COLORS["success"], font=("Segoe UI", 12, "bold"), 
                  padx=50, pady=15, bd=0, command=lambda: self.save_permission("True")).pack(pady=20)

    def trigger_startup_notification(self):
        if self.get_setting("bg_permission") == "True":
            threading.Thread(target=lambda: self.notifier.show_toast("HabitFlow ✨", "V1.0 Initialized. Ready to track.", duration=4), daemon=True).start()

    def save_permission(self, val):
        self.db.cur.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", ("bg_permission", val))
        self.db.conn.commit(); self.welcome.destroy(); self.setup_layout(); self.refresh_view()

    def draw_manager(self):
        f = tk.Frame(self.content, bg=COLORS["bg_main"], padx=50)
        f.pack(fill=tk.X)
        tk.Button(f, text="+ NEW HABIT", bg=COLORS["accent_light"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=30, pady=12, command=self.open_editor).pack(side=tk.LEFT)
        list_f = tk.Frame(self.content, bg=COLORS["bg_main"], padx=50, pady=20)
        list_f.pack(fill=tk.BOTH)
        for h in self.db.cur.execute("SELECT * FROM habits").fetchall():
            row = tk.Frame(list_f, bg=COLORS["bg_card"], pady=15, padx=25)
            row.pack(fill=tk.X, pady=8)
            tk.Label(row, text=f"{h[3]}  {h[1]}", fg="white", bg=COLORS["bg_card"], font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
            tk.Button(row, text="REMOVE", bg="#222", fg=COLORS["danger"], font=("Segoe UI", 8, "bold"), bd=0, padx=15, command=lambda id=h[0]: self.delete_habit(id)).pack(side=tk.RIGHT)

    def open_editor(self):
        win = tk.Toplevel(self.root); win.geometry("450x400"); win.configure(bg=COLORS["bg_card"])
        tk.Label(win, text="HABIT NAME", fg=COLORS["accent_light"], bg=COLORS["bg_card"], font=("Segoe UI", 10, "bold")).pack(pady=(40,5))
        e = tk.Entry(win, font=("Segoe UI", 14), bg="#000", fg="white", bd=0); e.pack(pady=10, padx=50, fill=tk.X)
        tk.Label(win, text="EMOJI", fg=COLORS["accent_light"], bg=COLORS["bg_card"], font=("Segoe UI", 10, "bold")).pack(pady=(20,5))
        emo = tk.Entry(win, font=("Segoe UI", 14), bg="#000", fg="white", bd=0); emo.insert(0, "🔥"); emo.pack(pady=10, padx=50, fill=tk.X)
        tk.Button(win, text="SAVE HABIT", bg=COLORS["success"], font=("Segoe UI", 11, "bold"), padx=40, pady=12, command=lambda: self.save_habit(e.get(), emo.get(), win)).pack(pady=40)

    def save_habit(self, name, emoji, win):
        if name: self.db.cur.execute("INSERT INTO habits (name, start_date, emoji) VALUES (?,?,?)", (name, datetime.now().strftime("%d %b %Y"), emoji)); self.db.conn.commit(); win.destroy(); self.refresh_view()

    def delete_habit(self, h_id):
        if messagebox.askyesno("HabitFlow", "Permanently delete?"): self.db.cur.execute("DELETE FROM habits WHERE id=?"); self.db.cur.execute("DELETE FROM logs WHERE habit_id=?"); self.db.conn.commit(); self.refresh_view()

    def draw_analytics(self):
        container = tk.Frame(self.content, bg=COLORS["bg_main"], padx=50); container.pack(fill=tk.BOTH, expand=True)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), facecolor=COLORS["bg_main"])
        stats = self.db.cur.execute("SELECT date, COUNT(*) FROM logs GROUP BY date ORDER BY date DESC LIMIT 7").fetchall()
        if stats:
            dates, counts = zip(*reversed(stats))
            ax1.plot(dates, counts, color=COLORS["accent_light"], marker='o', linewidth=3)
        ax1.set_facecolor(COLORS["bg_main"]); ax1.set_title("Performance", color="white")
        dist = self.db.cur.execute("SELECT name, (SELECT COUNT(*) FROM logs WHERE habit_id=habits.id) FROM habits").fetchall()
        if dist:
            names, vals = zip(*dist)
            ax2.pie(vals, labels=names, textprops={'color':"w"}, colors=[COLORS["accent"], COLORS["success"]])
        FigureCanvasTkAgg(fig, master=container).get_tk_widget().pack(pady=20, fill=tk.BOTH)

    def draw_empty_state(self):
        tk.Label(self.content, text="No habits found. Let's build your first routine! 🚀", fg=COLORS["text_dim"], bg=COLORS["bg_main"], font=("Segoe UI", 16)).pack(expand=True)

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    root = tk.Tk(); app = HabitFlow(root); root.mainloop()