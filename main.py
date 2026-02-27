import json
import calendar
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import uuid


# -----------------------------
# 数据结构
# -----------------------------
@dataclass
class Event:
    id: str
    name: str
    start: datetime
    end: datetime
    note: str = ""

    def overlaps_day(self, d: date) -> bool:
        return self.start.date() <= d <= self.end.date()


# -----------------------------
# 本地日程读取/解析/保存
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


def dt_to_str(dt: datetime) -> str:
    # 如果是整点 00:00:00，存成日期字符串更干净
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d %H:%M")


def ensure_sample_file(path: Path) -> None:
    if path.exists():
        return
    today = date.today()
    sample = {
        "events": [
            {
                "id": str(uuid.uuid4()),
                "name": "示例：项目里程碑",
                "start": today.strftime("%Y-%m-%d"),
                "end": today.strftime("%Y-%m-%d"),
                "note": "当天任务示例"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "示例：跨天出差",
                "start": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
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
        eid = str(item.get("id") or uuid.uuid4())
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

        if end < start:
            start, end = end, start

        events.append(Event(id=eid, name=name, start=start, end=end, note=note))

    events.sort(key=lambda e: (e.start, e.end, e.name))
    return events


def save_events(path: Path, events: List[Event]) -> None:
    data = {
        "events": [
            {
                "id": e.id,
                "name": e.name,
                "start": dt_to_str(e.start),
                "end": dt_to_str(e.end),
                "note": e.note
            }
            for e in sorted(events, key=lambda x: (x.start, x.end, x.name))
        ]
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_day_map(events: List[Event]) -> Dict[date, List[Event]]:
    day_map: Dict[date, List[Event]] = {}
    for e in events:
        cur = e.start.date()
        endd = e.end.date()
        while cur <= endd:
            day_map.setdefault(cur, []).append(e)
            cur += timedelta(days=1)

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

        if self.label is not None:
            self.label.config(text=text)
        self.win.geometry(f"+{x}+{y}")
        self.win.deiconify()

    def hide(self):
        if self.win is not None:
            self.win.withdraw()


# -----------------------------
# 事件编辑器：新增/编辑
# -----------------------------
class EventEditor(tk.Toplevel):
    """
    modal dialog:
    - mode: "add" or "edit"
    - init_date: 用于新增时默认填充
    - event: 编辑时传入
    """
    def __init__(self, parent: tk.Tk, mode: str, init_date: date, event: Optional[Event] = None):
        super().__init__(parent)
        self.parent = parent
        self.mode = mode
        self.event = event
        self.result: Optional[Dict] = None

        self.title("新增事件" if mode == "add" else "编辑事件")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill="both", expand=True)

        # Fields
        ttk.Label(wrap, text="名称：").grid(row=0, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar(value=(event.name if event else ""))
        ttk.Entry(wrap, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(wrap, text="开始：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(wrap, text="格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM").grid(row=1, column=2, sticky="w", padx=(8, 0))
        self.start_var = tk.StringVar()

        ttk.Entry(wrap, textvariable=self.start_var, width=40).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(wrap, text="结束：").grid(row=2, column=0, sticky="w", pady=4)
        self.end_var = tk.StringVar()
        ttk.Entry(wrap, textvariable=self.end_var, width=40).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(wrap, text="备注：").grid(row=3, column=0, sticky="nw", pady=4)
        self.note_text = tk.Text(wrap, width=40, height=6)
        self.note_text.grid(row=3, column=1, sticky="ew", pady=4)

        # Prefill
        if event:
            self.start_var.set(dt_to_str(event.start))
            self.end_var.set(dt_to_str(event.end))
            self.note_text.insert("1.0", event.note or "")
        else:
            # default: single day
            ds = init_date.strftime("%Y-%m-%d")
            self.start_var.set(ds)
            self.end_var.set(ds)

        # Buttons
        btns = ttk.Frame(wrap)
        btns.grid(row=4, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="取消", command=self._cancel).pack(side="right", padx=6)
        ttk.Button(btns, text="保存", command=self._ok).pack(side="right")

        wrap.columnconfigure(1, weight=1)

        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._ok())

        self.wait_visibility()
        self.focus_force()

    def _cancel(self):
        self.result = None
        self.destroy()

    def _ok(self):
        name = (self.name_var.get() or "").strip()
        if not name:
            messagebox.showerror("错误", "名称不能为空")
            return

        try:
            start = parse_dt(self.start_var.get())
            end = parse_dt(self.end_var.get())
        except Exception as ex:
            messagebox.showerror("错误", str(ex))
            return

        if end < start:
            # 允许用户反着填，自动纠正
            start, end = end, start

        note = self.note_text.get("1.0", "end").rstrip("\n")

        self.result = {
            "name": name,
            "start": start,
            "end": end,
            "note": note
        }
        self.destroy()


# -----------------------------
# 当天详情窗口：列表 + 增删改
# -----------------------------
class DayDetailsWindow(tk.Toplevel):
    def __init__(self, app: "CalendarApp", d: date):
        super().__init__(app.root)
        self.app = app
        self.d = d

        self.title(f"{d.strftime('%Y-%m-%d')} 详细列表")
        self.geometry("760x380")
        self.transient(app.root)

        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill="both", expand=True)

        top = ttk.Frame(wrap)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text=f"{d.strftime('%Y-%m-%d')} 待办事项", font=("Segoe UI", 12, "bold")).pack(side="left")

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="新增", command=self.add_event).pack(side="left", padx=4)
        ttk.Button(btns, text="编辑", command=self.edit_event).pack(side="left", padx=4)
        ttk.Button(btns, text="删除", command=self.delete_event).pack(side="left", padx=4)
        ttk.Button(btns, text="关闭", command=self.destroy).pack(side="left", padx=4)

        # Treeview
        columns = ("name", "start", "end", "note")
        self.tree = ttk.Treeview(wrap, columns=columns, show="headings", height=12)
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("name", text="名称")
        self.tree.heading("start", text="开始")
        self.tree.heading("end", text="结束")
        self.tree.heading("note", text="备注")

        self.tree.column("name", width=180, anchor="w")
        self.tree.column("start", width=140, anchor="w")
        self.tree.column("end", width=140, anchor="w")
        self.tree.column("note", width=260, anchor="w")

        # Scrollbar
        ybar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ybar.set)
        ybar.pack(side="right", fill="y")

        # Double click row to edit
        self.tree.bind("<Double-Button-1>", lambda e: self.edit_event())

        self.refresh()

    def _events_for_day(self) -> List[Event]:
        return self.app.day_map.get(self.d, [])

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        events = self._events_for_day()
        for e in events:
            self.tree.insert(
                "", "end",
                iid=e.id,  # 用事件 id 作为 iid，方便定位编辑/删除
                values=(e.name, dt_to_str(e.start), dt_to_str(e.end), e.note)
            )

    def _selected_event_id(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def add_event(self):
        dlg = EventEditor(self.app.root, mode="add", init_date=self.d)
        if not dlg.result:
            return

        new = Event(
            id=str(uuid.uuid4()),
            name=dlg.result["name"],
            start=dlg.result["start"],
            end=dlg.result["end"],
            note=dlg.result["note"],
        )
        self.app.events.append(new)
        self.app.persist_and_refresh()
        self.refresh()

    def edit_event(self):
        eid = self._selected_event_id()
        if not eid:
            messagebox.showinfo("提示", "请先在列表中选择一个事件（或双击某行进行编辑）")
            return

        ev = self.app.find_event_by_id(eid)
        if not ev:
            messagebox.showerror("错误", "找不到该事件（可能已被删除）")
            self.app.persist_and_refresh()
            self.refresh()
            return

        dlg = EventEditor(self.app.root, mode="edit", init_date=self.d, event=ev)
        if not dlg.result:
            return

        # 原地更新
        ev.name = dlg.result["name"]
        ev.start = dlg.result["start"]
        ev.end = dlg.result["end"]
        ev.note = dlg.result["note"]

        self.app.persist_and_refresh()
        self.refresh()

    def delete_event(self):
        eid = self._selected_event_id()
        if not eid:
            messagebox.showinfo("提示", "请先在列表中选择一个事件")
            return

        ev = self.app.find_event_by_id(eid)
        if not ev:
            messagebox.showerror("错误", "找不到该事件（可能已被删除）")
            self.app.persist_and_refresh()
            self.refresh()
            return

        if not messagebox.askyesno("确认删除", f"确定要删除事件：\n\n{ev.name}\n\n吗？"):
            return

        self.app.events = [e for e in self.app.events if e.id != eid]
        self.app.persist_and_refresh()
        self.refresh()


# -----------------------------
# 主界面：日历视图
# -----------------------------
class CalendarApp:
    def __init__(self, root: tk.Tk, data_file: Path):
        self.root = root
        self.data_file = data_file

        self.events: List[Event] = load_events(self.data_file)
        self.day_map: Dict[date, List[Event]] = build_day_map(self.events)

        today = date.today()
        self.year = today.year
        self.month = today.month
        self.today = today

        self.tooltip = Tooltip(root)
        self.day_windows: Dict[date, DayDetailsWindow] = {}

        self._setup_styles()
        self._build_ui()
        self._render_calendar()

        # 首次运行：如果旧文件没 id，保存一次补齐
        self.persist_and_refresh(save_only=True)

    def _setup_styles(self):
        style = ttk.Style()
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
        self.root.geometry("860x600")

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        self.title_label = ttk.Label(top, text="", style="Header.TLabel")
        self.title_label.pack(side="left")

        btns = ttk.Frame(top)
        btns.pack(side="right")

        ttk.Button(btns, text="上个月", command=self.prev_month).pack(side="left", padx=4)
        ttk.Button(btns, text="下个月", command=self.next_month).pack(side="left", padx=4)
        ttk.Button(btns, text="重新加载日程", command=self.reload).pack(side="left", padx=4)

        hint = "提示：双击任意日期打开详细列表（可新增/编辑/删除）。悬停在有日程的日期会显示 tooltip。"
        self.hint_label = ttk.Label(
            self.root,
            text=f"{hint}\n数据文件：{self.data_file.resolve()}（可直接编辑 JSON）",
            style="SubHeader.TLabel",
            padding=(10, 0, 10, 6),
        )
        self.hint_label.pack(fill="x")

        self.calendar_frame = ttk.Frame(self.root, padding=10)
        self.calendar_frame.pack(fill="both", expand=True)

        header = ttk.Frame(self.calendar_frame)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(tuple(range(7)), weight=1)

        week_names = ["一", "二", "三", "四", "五", "六", "日"]
        for i, w in enumerate(week_names):
            lbl = ttk.Label(header, text=w, anchor="center", padding=6)
            lbl.grid(row=0, column=i, sticky="ew")

        self.grid_frame = ttk.Frame(self.calendar_frame)
        self.grid_frame.grid(row=1, column=0, sticky="nsew")
        self.calendar_frame.rowconfigure(1, weight=1)
        self.calendar_frame.columnconfigure(0, weight=1)

        for c in range(7):
            self.grid_frame.columnconfigure(c, weight=1)

    def reload(self):
        # 从文件重新读取（如果你手动编辑了 schedule.json）
        self.events = load_events(self.data_file)
        self.day_map = build_day_map(self.events)
        self._render_calendar()
        self._refresh_open_day_windows()

    def persist_and_refresh(self, save_only: bool = False):
        # 写回文件 + 重建 day_map + 刷新日历
        # save_only=True 用于首次补齐 id，不打扰 UI
        save_events(self.data_file, self.events)
        if save_only:
            return
        self.day_map = build_day_map(self.events)
        self._render_calendar()
        self._refresh_open_day_windows()

    def _refresh_open_day_windows(self):
        # 如果已经打开了某些“当天详情窗口”，同步刷新它们
        for d, win in list(self.day_windows.items()):
            if not win.winfo_exists():
                self.day_windows.pop(d, None)
                continue
            win.refresh()

    def find_event_by_id(self, eid: str) -> Optional[Event]:
        for e in self.events:
            if e.id == eid:
                return e
        return None

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

    def open_day_details(self, d: date):
        # 同一天只开一个窗口
        win = self.day_windows.get(d)
        if win and win.winfo_exists():
            win.lift()
            win.focus_force()
            return
        win = DayDetailsWindow(self, d)
        self.day_windows[d] = win

    def _clear_grid(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

    def _render_calendar(self):
        self.tooltip.hide()
        self._clear_grid()

        self.title_label.config(text=f"{self.year}年 {self.month}月")

        cal = calendar.Calendar(firstweekday=0)  # 0=周一
        month_days = list(cal.itermonthdays(self.year, self.month))
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

                text = f"{day}"
                if events_today:
                    text += "  •"

                if d == self.today:
                    style_name = "Today.TLabel"
                elif events_today:
                    style_name = "EventDay.TLabel"
                else:
                    style_name = "Day.TLabel"

                lbl = ttk.Label(cell, text=text, style=style_name)
                lbl.grid(row=0, column=0, sticky="nsew")

                # 双击打开当天详情（任何日期都可以双击打开）
                for widget in (cell, lbl):
                    widget.bind("<Double-Button-1>", lambda e, dd=d: self.open_day_details(dd))

                # 有日程的日期才显示 tooltip
                if events_today:
                    for widget in (cell, lbl):
                        widget.bind("<Enter>", lambda e, dd=d: self._on_enter_day(e, dd))
                        widget.bind("<Motion>", lambda e, dd=d: self._on_motion_day(e, dd))
                        widget.bind("<Leave>", lambda e: self.tooltip.hide())

    def _format_tooltip(self, d: date, events: List[Event]) -> str:
        lines = [f"{d.strftime('%Y-%m-%d')} 待办事项："]
        for i, ev in enumerate(events, 1):
            span = f"{dt_to_str(ev.start)} ~ {dt_to_str(ev.end)}" if ev.end != ev.start else dt_to_str(ev.start)
            note = f"（{ev.note}）" if ev.note else ""
            lines.append(f"{i}. {ev.name}  [{span}]{note}")
        return "\n".join(lines)

    def _on_enter_day(self, event: tk.Event, d: date):
        events_today = self.day_map.get(d, [])
        if not events_today:
            return
        text = self._format_tooltip(d, events_today)
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
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    CalendarApp(root, data_file)
    root.mainloop()


if __name__ == "__main__":
    main()