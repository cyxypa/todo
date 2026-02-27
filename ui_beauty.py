import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Tuple, Optional
import calendar as _cal
from datetime import date as _date

# -----------------------------
# 深色主题（默认）
# -----------------------------
DARK = {
    "app_bg": "#0B1220",
    "card_bg": "#0F172A",
    "text_fg": "#E5E7EB",
    "muted_fg": "#94A3B8",
    "accent": "#60A5FA",
    "accent_hover": "#3B82F6",
    "border": "#243244",
    "weekend_fg": "#FCA5A5",
    "today_fg": "#93C5FD",
    "badge_bg": "#1E293B",
    "badge_fg": "#E0E7FF",
    "header_bg": "#111C2D",
    "list_bg": "#0B1220",
}

LIGHT = {
    "app_bg": "#F7F8FA",
    "card_bg": "#FFFFFF",
    "text_fg": "#111827",
    "muted_fg": "#6B7280",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "border": "#E5E7EB",
    "weekend_fg": "#DC2626",
    "today_fg": "#1D4ED8",
    "badge_bg": "#EEF2FF",
    "badge_fg": "#3730A3",
    "header_bg": "#F3F4F6",
    "list_bg": "#F9FAFB",
}


@dataclass(frozen=True)
class Theme:
    mode: str
    font_family: str
    app_bg: str
    card_bg: str
    text_fg: str
    muted_fg: str
    accent: str
    accent_hover: str
    border: str
    weekend_fg: str
    today_fg: str
    badge_bg: str
    badge_fg: str
    header_bg: str
    list_bg: str


THEME: Theme = Theme(
    mode="dark",
    font_family="TkDefaultFont",
    **DARK
)


def _pick_font_family() -> str:
    candidates = [
        "Microsoft YaHei UI", "Microsoft YaHei",
        "PingFang SC", "Heiti SC",
        "Noto Sans CJK SC", "Source Han Sans CN",
        "Segoe UI",
        "Arial",
        "TkDefaultFont",
    ]
    try:
        fams = set(tkfont.families())
        for f in candidates:
            if f in fams:
                return f
    except Exception:
        pass
    return "TkDefaultFont"


def setup_theme(root: tk.Tk, mode: str = "dark") -> Theme:
    """
    深色/浅色主题：mode in {"dark","light"}
    在 Tk() 后调用一次即可。
    """
    global THEME
    palette = DARK if mode.lower() == "dark" else LIGHT
    font_family = _pick_font_family()

    THEME = Theme(mode=mode.lower(), font_family=font_family, **palette)

    # 设置默认字体
    try:
        tkfont.nametofont("TkDefaultFont").configure(family=font_family, size=10)
        tkfont.nametofont("TkTextFont").configure(family=font_family, size=10)
        tkfont.nametofont("TkMenuFont").configure(family=font_family, size=10)
    except Exception:
        pass

    root.configure(bg=THEME.app_bg)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Frame / Label
    style.configure("App.TFrame", background=THEME.app_bg)
    style.configure("Card.TFrame", background=THEME.card_bg)

    style.configure("Title.TLabel",
                    background=THEME.card_bg,
                    foreground=THEME.accent,  # 当前月份更显眼：标题用主色
                    font=(THEME.font_family, 20, "bold"))
    style.configure("SubTitle.TLabel",
                    background=THEME.card_bg,
                    foreground=THEME.muted_fg,
                    font=(THEME.font_family, 10))
    style.configure("Hint.TLabel",
                    background=THEME.app_bg,
                    foreground=THEME.muted_fg,
                    font=(THEME.font_family, 10))
    style.configure("FieldLabel.TLabel",
                    background=THEME.card_bg,
                    foreground=THEME.muted_fg,
                    font=(THEME.font_family, 10))

    style.configure("Badge.TLabel",
                    background=THEME.badge_bg,
                    foreground=THEME.badge_fg,
                    padding=(10, 4),
                    font=(THEME.font_family, 10, "bold"))

    # Buttons
    style.configure("Accent.TButton",
                    background=THEME.accent,
                    foreground="white",
                    padding=(14, 8),
                    relief="flat",
                    borderwidth=0,
                    font=(THEME.font_family, 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", THEME.accent_hover), ("pressed", THEME.accent_hover)])

    style.configure("Ghost.TButton",
                    background=THEME.card_bg,
                    foreground=THEME.text_fg,
                    padding=(12, 8),
                    relief="flat",
                    borderwidth=0,
                    font=(THEME.font_family, 10))
    style.map("Ghost.TButton",
              background=[("active", _mix(THEME.card_bg, "#FFFFFF", 0.06)),
                          ("pressed", _mix(THEME.card_bg, "#FFFFFF", 0.12))])

    style.configure("Nav.TButton",
                    background=THEME.card_bg,
                    foreground=THEME.text_fg,
                    padding=(10, 6),
                    relief="flat",
                    borderwidth=0,
                    font=(THEME.font_family, 12, "bold"))
    style.map("Nav.TButton",
              background=[("active", _mix(THEME.card_bg, "#FFFFFF", 0.06)),
                          ("pressed", _mix(THEME.card_bg, "#FFFFFF", 0.12))])

    # Treeview（当天详情列表）
    style.configure("Treeview",
                    background=THEME.card_bg,
                    fieldbackground=THEME.card_bg,
                    foreground=THEME.text_fg,
                    rowheight=30,
                    borderwidth=0,
                    font=(THEME.font_family, 10))
    style.map("Treeview",
              background=[("selected", THEME.accent)],
              foreground=[("selected", "white")])

    style.configure("Treeview.Heading",
                    background=THEME.header_bg,
                    foreground=THEME.text_fg,
                    relief="flat",
                    font=(THEME.font_family, 10, "bold"))

    return THEME


# -----------------------------
# 通用工具：颜色混合 / 居中显示
# -----------------------------
def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    b2 = int(ab + (bb - ab) * t)
    return _rgb_to_hex(r, g, b2)


def center_window(win: tk.Toplevel, width: Optional[int] = None, height: Optional[int] = None,
                  parent: Optional[tk.Widget] = None) -> None:
    """
    把任意 Toplevel 居中显示（相对 parent 居中；没有 parent 则屏幕居中）
    """
    win.update_idletasks()
    w = width or win.winfo_reqwidth()
    h = height or win.winfo_reqheight()

    margin = 16
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    if parent is not None and parent.winfo_exists():
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
    else:
        x = (sw - w) // 2
        y = (sh - h) // 2

    x = max(margin, min(x, sw - w - margin))
    y = max(margin, min(y, sh - h - margin))
    win.geometry(f"{w}x{h}+{x}+{y}")


# -----------------------------
# 主界面布局（卡片化）
# -----------------------------
def build_main_ui(app) -> None:
    """
    app 需要提供：root, prev_month/next_month/reload/open_multiselect_dropdown/clear_highlight
    并提供 selector_summary_var/status_var/data_file
    本函数会创建：title_label/selector_btn/calendar_frame/grid_frame
    """
    root = app.root
    root.title("日程表可视化（日历视图）")
    root.geometry("1040x760")
    root.minsize(920, 640)

    container = ttk.Frame(root, style="App.TFrame")
    container.pack(fill="both", expand=True)

    # 顶部卡片
    header_card = ttk.Frame(container, style="Card.TFrame", padding=(16, 14))
    header_card.pack(fill="x", padx=14, pady=(14, 12))

    left = ttk.Frame(header_card, style="Card.TFrame")
    left.pack(side="left", fill="x", expand=True)

    app.title_label = ttk.Label(left, text="", style="Title.TLabel")
    app.title_label.pack(anchor="w")

    ttk.Label(left, text="双击日期打开详情；悬停查看当天待办。", style="SubTitle.TLabel").pack(anchor="w", pady=(4, 0))

    nav = ttk.Frame(header_card, style="Card.TFrame")
    nav.pack(side="right")

    ttk.Button(nav, text="◀", style="Nav.TButton", command=app.prev_month).pack(side="left", padx=(0, 6))
    ttk.Button(nav, text="▶", style="Nav.TButton", command=app.next_month).pack(side="left", padx=(0, 10))
    ttk.Button(nav, text="重新加载", style="Ghost.TButton", command=app.reload).pack(side="left")

    # 操作卡片
    action_card = ttk.Frame(container, style="Card.TFrame", padding=(16, 12))
    action_card.pack(fill="x", padx=14, pady=(0, 12))

    ttk.Label(action_card, text="检索（多选）", style="FieldLabel.TLabel").pack(side="left")

    app.selector_btn = ttk.Button(
        action_card,
        textvariable=app.selector_summary_var,
        style="Ghost.TButton",
        command=app.open_multiselect_dropdown
    )
    app.selector_btn.pack(side="left", padx=10)

    ttk.Button(action_card, text="清除高亮", style="Ghost.TButton", command=app.clear_highlight).pack(side="left")

    ttk.Label(action_card, textvariable=app.status_var, style="Badge.TLabel").pack(side="right")

    # hint
    hint = f"数据文件：{app.data_file.resolve()}（可直接编辑 JSON）"
    ttk.Label(container, text=hint, style="Hint.TLabel", padding=(14, 0, 14, 10)).pack(fill="x")

    # 日历卡片
    app.calendar_frame = ttk.Frame(container, style="Card.TFrame", padding=12)
    app.calendar_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    # 星期标题行（用 tk.Label 保证背景一致）
    header = tk.Frame(app.calendar_frame, bg=THEME.card_bg)
    header.grid(row=0, column=0, sticky="ew")
    for i in range(7):
        header.grid_columnconfigure(i, weight=1)

    week_names = ["一", "二", "三", "四", "五", "六", "日"]
    for i, w in enumerate(week_names):
        lbl = tk.Label(header,
                       text=w,
                       bg=THEME.header_bg,
                       fg=THEME.text_fg,
                       font=(THEME.font_family, 10, "bold"),
                       padx=8, pady=8)
        lbl.grid(row=0, column=i, sticky="ew", padx=1, pady=(0, 8))

    # 日期网格
    app.grid_frame = ttk.Frame(app.calendar_frame, style="Card.TFrame")
    app.grid_frame.grid(row=1, column=0, sticky="nsew")
    app.calendar_frame.rowconfigure(1, weight=1)
    app.calendar_frame.columnconfigure(0, weight=1)

    for c in range(7):
        app.grid_frame.columnconfigure(c, weight=1)


# -----------------------------
# 控件美化：Listbox / Treeview / Tooltip / 日历文字
# -----------------------------
def style_listbox(lb: tk.Listbox) -> None:
    lb.configure(
        bg=THEME.list_bg,
        fg=THEME.text_fg,
        selectbackground=THEME.accent,
        selectforeground="white",
        highlightthickness=1,
        highlightbackground=THEME.border,
        relief="flat",
    )


def setup_treeview_zebra(tree: ttk.Treeview) -> None:
    tree.tag_configure("even", background=THEME.card_bg)
    tree.tag_configure("odd", background=_mix(THEME.card_bg, "#FFFFFF", 0.06))


def zebra_tag(i: int) -> str:
    return "even" if i % 2 == 0 else "odd"


def day_label_style(col_index: int, is_today: bool) -> Tuple[str, tuple]:
    is_weekend = (col_index >= 5)
    fg = THEME.weekend_fg if is_weekend else THEME.text_fg
    font = (THEME.font_family, 10)
    if is_today:
        fg = THEME.today_fg
        font = (THEME.font_family, 11, "bold")
    return fg, font


def draw_today_badge(parent: tk.Frame, bg: str) -> None:
    # 右上角 “TODAY/今天” 徽标
    badge = tk.Label(parent,
                     text="今天",
                     bg=THEME.accent,
                     fg="white",
                     font=(THEME.font_family, 9, "bold"),
                     padx=6, pady=2)
    badge.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)


def build_tooltip_widgets(win: tk.Toplevel, text: str) -> tk.Label:
    frame = tk.Frame(win, bg=THEME.card_bg, bd=1, relief="solid")
    frame.pack(fill="both", expand=True)
    label = tk.Label(frame,
                     text=text,
                     justify="left",
                     bg=THEME.card_bg,
                     fg=THEME.text_fg,
                     font=(THEME.font_family, 10),
                     padx=10, pady=8)
    label.pack()
    return label

class DatePickerDialog(tk.Toplevel):
    """
    简易日期选择器：点某一天即选择并关闭；支持切换月份；高亮今日/当前选中日。
    返回 self.result: Optional[date]
    """
    def __init__(self, parent: tk.Widget, initial: _date | None = None, title: str = "选择日期"):
        super().__init__(parent)
        self.result: _date | None = None

        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._today = _date.today()
        self._selected = initial or self._today
        self._year = self._selected.year
        self._month = self._selected.month

        wrap = ttk.Frame(self, padding=12, style="Card.TFrame")
        wrap.pack(fill="both", expand=True)

        # 顶部：月份 + 上下月
        top = ttk.Frame(wrap, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 10))

        ttk.Button(top, text="◀", style="Nav.TButton", command=self._prev_month).pack(side="left")
        self._title = ttk.Label(top, text="", style="Title.TLabel")
        self._title.pack(side="left", padx=10)
        ttk.Button(top, text="▶", style="Nav.TButton", command=self._next_month).pack(side="left")

        ttk.Button(top, text="取消", style="Ghost.TButton", command=self._cancel).pack(side="right")

        # 星期标题
        header = tk.Frame(wrap, bg=THEME.card_bg)
        header.pack(fill="x")
        for i in range(7):
            header.grid_columnconfigure(i, weight=1)
        week_names = ["一", "二", "三", "四", "五", "六", "日"]
        for i, w in enumerate(week_names):
            tk.Label(
                header,
                text=w,
                bg=THEME.header_bg,
                fg=THEME.text_fg,
                font=(THEME.font_family, 10, "bold"),
                padx=8, pady=6
            ).grid(row=0, column=i, sticky="ew", padx=1, pady=(0, 6))

        # 日期网格
        self._grid = tk.Frame(wrap, bg=THEME.card_bg)
        self._grid.pack(fill="both", expand=True)

        self.bind("<Escape>", lambda e: self._cancel())
        self._render()
        center_window(self, width=420, height=420, parent=parent)

    def _cancel(self):
        self.result = None
        self.destroy()

    def _prev_month(self):
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._render()

    def _next_month(self):
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._render()

    def _choose(self, d: _date):
        self.result = d
        self.destroy()

    def _render(self):
        self._title.config(text=f"{self._year}年 {self._month}月")

        for w in self._grid.winfo_children():
            w.destroy()

        for c in range(7):
            self._grid.grid_columnconfigure(c, weight=1)

        cal = _cal.Calendar(firstweekday=0)  # 周一开头
        days = list(cal.itermonthdays(self._year, self._month))
        while len(days) < 42:
            days.append(0)

        for r in range(6):
            self._grid.grid_rowconfigure(r, weight=1)
            for c in range(7):
                n = days[r * 7 + c]
                if n == 0:
                    cell = tk.Frame(self._grid, bg=THEME.card_bg, highlightthickness=0, bd=0)
                    cell.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                    continue

                d = _date(self._year, self._month, n)
                is_today = (d == self._today)
                is_sel = (d == self._selected)

                # 背景/边框
                bg = THEME.card_bg
                fg = THEME.weekend_fg if c >= 5 else THEME.text_fg

                # 选中日：用 accent 背景
                if is_sel:
                    bg = THEME.accent
                    fg = "white"

                btn = tk.Button(
                    self._grid,
                    text=str(n),
                    bg=bg,
                    fg=fg,
                    bd=0,
                    relief="flat",
                    activebackground=_mix(bg, "#000000", 0.08) if THEME.mode == "dark" else _mix(bg, "#FFFFFF", 0.08),
                    activeforeground=fg,
                    font=(THEME.font_family, 11, "bold" if (is_today or is_sel) else "normal"),
                    command=lambda dd=d: self._choose(dd),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

                # 今日：加一个描边提示（不影响选中底色）
                if is_today and not is_sel:
                    btn.configure(highlightthickness=2, highlightbackground=THEME.accent, highlightcolor=THEME.accent)
                else:
                    btn.configure(highlightthickness=0)

def pick_date(parent: tk.Widget, initial: _date | None = None, title: str = "选择日期") -> _date | None:
    """弹出日期选择器，返回 date 或 None"""
    dlg = DatePickerDialog(parent, initial=initial, title=title)
    parent.wait_window(dlg)
    return dlg.result