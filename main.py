import json
import calendar
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple


# -----------------------------
# 数据结构
# -----------------------------
@dataclass(frozen=True)
class Event:
    name: str
    start: datetime
    end: datetime
    note: str = ""

    def overlaps_day(self, d: date) -> bool:
        """事件是否覆盖某一天（按日期维度判断，跨天事件会覆盖中间所有日期）"""
        start_day = self.start.date()
        end_day = self.end.date()
        return start_day <= d <= end_day


# -----------------------------
# 本地日程读取/解析
# -----------------------------
DT_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
]


def parse_dt(s: str) -> datetime:
    s = (s or "").strip()
    for fmt in DT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"无法解析日期/时间：{s}（支持：YYYY-MM-DD 或 YYYY-MM-DD HH:MM）")


def ensure_sample_file(path: Path) -> None:
    if path.exists():
        return
    sample = {
        "events": [
            {
                "name": "示例：项目里程碑",
                "start": datetime.now().strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "note": "当天任务示例"
            },
            {
                "name": "示例：跨天出差",
                "start": (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d"),
                "end": (datetime.now().date() + timedelta(days=5)).strftime("%Y-%m-%d"),
                "note": "跨天事件示例：覆盖多天"
            }
        ]
    }
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")


def load_events(path: Path) -> List[Event]:
    ensure_sample_file(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    events: List[Event] = []
    for item in raw.get("events", []):
        name = str(item.get("name", "")).strip() or "未命名事件"
        note = str(item.get("note", "")).strip()

        # 兼容：date(单天) 或 start/end(可跨天)
        if "date" in item and item.get("date"):
            start = parse_dt(str(item["date"]))
            end = start
        else:
            start = parse_dt(str(item.get("start", "")))
            end_str = item.get("end")
            end = parse_dt(str(end_str)) if end_str else start

        # 如果 end 早于 start，自动交换
        if end < start:
            start, end = end, start

        events.append(Event(name=name, start=start, end=end, note=note))

    # 事件按开始时间排序
    events.sort(key=lambda e: (e.start, e.end, e.name))
    return events


def build_day_map(events: List[Event]) -> Dict[date, List[Event]]:
    """把事件映射到每一天：date -> [events...]（跨天事件会加入到每一天）"""
    day_map: Dict[date, List[Event]] = {}
    for e in events:
        d0 = e.start.date()
        d1 = e.end.date()
        cur = d0
        while cur <= d1:
            day_map.setdefault(cur, []).append(e)
            cur += timedelta(days=1)

    # 每天的事件按开始时间排序
    for d in day_map:
        day_map[d].sort(key=lambda e: (e.start, e.end, e.name))
    return day_map


# -----------------------------
# Tooltip 悬浮窗
# -----------------------------
class Tooltip:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.win: Optional[tk.Toplevel] = None
        self.label: Optional[ttk.Label] = None

    def show(self, x: int, y: int, text: str):
        if self.win is None:
            self.win = tk.Toplevel(self.root)
            self.win.wm_overrideredirect(True)
            self.win.attributes("-topmost", True)
            frame = ttk.Frame(self.win, padding=8, style="Tooltip.TFrame")
            frame.pack(fill="both", expand=True)
            self.label = ttk.Label(frame, text=text, justify="left", style="Tooltip.TLabel")
            self.label.pack()

        # 更新文本 & 位置
        if self.label is not None:
            self.label.config(text=text)
        self.win.geometry(f"+{x}+{y}")
        self.win.deiconify()

    def hide(self):
        if self.win is not None:
            self.win.withdraw()


# -----------------------------
# 主界面：日历视图
# -----------------------------
class CalendarApp:
    def __init__(self, root: tk.Tk, data_file: Path):
        self.root = root
        self.data_file = data_file

        self.events = load_events(self.data_file)
        self.day_map = build_day_map(self.events)

        today = date.today()
        self.year = today.year
        self.month = today.month
        self.today = today

        self.tooltip = Tooltip(root)

        self._setup_styles()
        self._build_ui()
        self._render_calendar()

    def _setup_styles(self):
        style = ttk.Style()
        # 尽量使用系统主题
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10))

        style.configure("Day.TLabel", anchor="nw", padding=6, font=("Segoe UI", 10))
        style.configure("Blank.TLabel", anchor="center", padding=6)

        style.configure("EventDay.TLabel", anchor="nw", padding=6, font=("Segoe UI", 10))
        style.map("EventDay.TLabel", background=[("!disabled", "#FFF4CC")])

        style.configure("Today.TLabel", anchor="nw", padding=6, font=("Segoe UI", 10, "bold"))
        style.map("Today.TLabel", background=[("!disabled", "#D6F0FF")])

        style.configure("Tooltip.TFrame", relief="solid", borderwidth=1)
        style.configure("Tooltip.TLabel", font=("Segoe UI", 10))

    def _build_ui(self):
        self.root.title("日程表可视化（日历视图）")
        self.root.geometry("820x560")

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        self.title_label = ttk.Label(top, text="", style="Header.TLabel")
        self.title_label.pack(side="left")

        btns = ttk.Frame(top)
        btns.pack(side="right")

        ttk.Button(btns, text="上个月", command=self.prev_month).pack(side="left", padx=4)
        ttk.Button(btns, text="下个月", command=self.next_month).pack(side="left", padx=4)
        ttk.Button(btns, text="重新加载日程", command=self.reload).pack(side="left", padx=4)

        self.hint_label = ttk.Label(
            self.root,
            text=f"数据文件：{self.data_file.resolve()}（可直接编辑 JSON）",
            style="SubHeader.TLabel",
            padding=(10, 0, 10, 6),
        )
        self.hint_label.pack(fill="x")

        # 星期标题行
        self.calendar_frame = ttk.Frame(self.root, padding=10)
        self.calendar_frame.pack(fill="both", expand=True)

        header = ttk.Frame(self.calendar_frame)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(tuple(range(7)), weight=1)

        week_names = ["一", "二", "三", "四", "五", "六", "日"]
        for i, w in enumerate(week_names):
            lbl = ttk.Label(header, text=w, anchor="center", padding=6)
            lbl.grid(row=0, column=i, sticky="ew")

        # 日期网格容器
        self.grid_frame = ttk.Frame(self.calendar_frame)
        self.grid_frame.grid(row=1, column=0, sticky="nsew")
        self.calendar_frame.rowconfigure(1, weight=1)
        self.calendar_frame.columnconfigure(0, weight=1)

        for c in range(7):
            self.grid_frame.columnconfigure(c, weight=1)

    def reload(self):
        self.events = load_events(self.data_file)
        self.day_map = build_day_map(self.events)
        self._render_calendar()

    def prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._render_calendar()

    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._render_calendar()

    def _clear_grid(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

    def _render_calendar(self):
        self.tooltip.hide()
        self._clear_grid()

        self.title_label.config(text=f"{self.year}年 {self.month}月")

        cal = calendar.Calendar(firstweekday=0)  # 0=周一
        month_days = list(cal.itermonthdays(self.year, self.month))  # 0 表示空格
        # 固定 6 行（最多 42 格）
        while len(month_days) < 42:
            month_days.append(0)

        for r in range(6):
            self.grid_frame.rowconfigure(r, weight=1)
            for c in range(7):
                idx = r * 7 + c
                day = month_days[idx]

                cell = ttk.Frame(self.grid_frame, relief="ridge", borderwidth=1)
                cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                cell.rowconfigure(0, weight=1)
                cell.columnconfigure(0, weight=1)

                if day == 0:
                    ttk.Label(cell, text="", style="Blank.TLabel").grid(row=0, column=0, sticky="nsew")
                    continue

                d = date(self.year, self.month, day)
                events_today = self.day_map.get(d, [])

                # 文本：有事件则加个点
                text = f"{day}"
                if events_today:
                    text += "  •"

                # 样式：今日/有事件/普通
                if d == self.today:
                    style_name = "Today.TLabel"
                elif events_today:
                    style_name = "EventDay.TLabel"
                else:
                    style_name = "Day.TLabel"

                lbl = ttk.Label(cell, text=text, style=style_name)
                lbl.grid(row=0, column=0, sticky="nsew")

                # 只有有日程的日期才显示悬浮窗
                if events_today:
                    lbl.bind("<Enter>", lambda e, dd=d: self._on_enter_day(e, dd))
                    lbl.bind("<Motion>", lambda e, dd=d: self._on_motion_day(e, dd))
                    lbl.bind("<Leave>", lambda e: self.tooltip.hide())

    def _format_tooltip(self, d: date, events: List[Event]) -> str:
        lines = [f"{d.strftime('%Y-%m-%d')} 待办事项："]
        for i, ev in enumerate(events, 1):
            # 显示开始/结束（如果只是日期则不显示具体时间）
            def fmt(dt: datetime) -> str:
                if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                    return dt.strftime("%Y-%m-%d")
                return dt.strftime("%Y-%m-%d %H:%M")

            span = f"{fmt(ev.start)} ~ {fmt(ev.end)}" if ev.end != ev.start else fmt(ev.start)
            note = f"（{ev.note}）" if ev.note else ""
            lines.append(f"{i}. {ev.name}  [{span}]{note}")
        return "\n".join(lines)

    def _on_enter_day(self, event: tk.Event, d: date):
        events_today = self.day_map.get(d, [])
        if not events_today:
            return
        text = self._format_tooltip(d, events_today)

        # 初次显示位置：鼠标右下偏移
        x = self.root.winfo_pointerx() + 14
        y = self.root.winfo_pointery() + 18
        self.tooltip.show(x, y, text)

    def _on_motion_day(self, event: tk.Event, d: date):
        events_today = self.day_map.get(d, [])
        if not events_today:
            self.tooltip.hide()
            return
        text = self._format_tooltip(d, events_today)

        x = self.root.winfo_pointerx() + 14
        y = self.root.winfo_pointery() + 18
        self.tooltip.show(x, y, text)


def main():
    data_file = Path(__file__).with_name("schedule.json")

    root = tk.Tk()
    # Windows 下让缩放更友好（可选）
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    CalendarApp(root, data_file)
    root.mainloop()


if __name__ == "__main__":
    main()