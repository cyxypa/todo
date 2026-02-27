import json
import calendar
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
import uuid
import colorsys

import ui_beauty as ui


# -----------------------------
# 基础配色（业务相关：日历格子背景逻辑）
# -----------------------------
NORMAL_BG = "#FFFFFF"
BLANK_BG = "#F6F6F6"
EVENT_BG = "#FFF2CC"        # 有事件：浅黄
TODAY_BG = "#D6F0FF"        # 今日：浅蓝
BORDER_NORMAL = "#D0D0D0"

MULTI_HIT_BG = "#EFEFEF"    # 多事件命中

HIGHLIGHT_PALETTE = [
    "#DFF7E3",
    "#FFE0E6",
    "#E6E0FF",
    "#FFEACC",
    "#E0F7F7",
    "#FFF2CC",
    "#E7F0FF",
]


@dataclass
class Event:
    id: str
    name: str
    start: datetime
    end: datetime
    note: str = ""

    def overlaps_day(self, d: date) -> bool:
        return self.start.date() <= d <= self.end.date()


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


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def darken(hex_color: str, factor: float = 0.75) -> str:
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return rgb_to_hex(r, g, b)


def pastel_from_index(i: int) -> str:
    hue = (i * 0.13) % 1.0
    sat = 0.35
    val = 0.97
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return rgb_to_hex(int(r * 255), int(g * 255), int(b * 255))


class Tooltip:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.win: Optional[tk.Toplevel] = None
        self.label: Optional[tk.Label] = None

    def show(self, x: int, y: int, text: str):
        if self.win is None:
            self.win = tk.Toplevel(self.root)
            self.win.wm_overrideredirect(True)
            self.win.attributes("-topmost", True)
            self.label = ui.build_tooltip_widgets(self.win, text)

        if self.label is not None:
            self.label.config(text=text)
        self.win.geometry(f"+{x}+{y}")
        self.win.deiconify()

    def hide(self):
        if self.win is not None:
            self.win.withdraw()


class EventEditor(tk.Toplevel):
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

        ttk.Label(wrap, text="名称：").grid(row=0, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar(value=(event.name if event else ""))
        ttk.Entry(wrap, textvariable=self.name_var, width=42).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(wrap, text="开始：").grid(row=1, column=0, sticky="w", pady=4)
        #ttk.Label(wrap, text="格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM").grid(row=1, column=2, sticky="w", padx=(8, 0))
        self.start_var = tk.StringVar()
        start_row = ttk.Frame(wrap)
        start_row.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Entry(start_row, textvariable=self.start_var, width=30).pack(side="left", fill="x", expand=True)

        ttk.Button(
            start_row,
            text="📅 选择日期",
            command=lambda: self._on_pick_start_date(),
        ).pack(side="left", padx=(8, 0))

        ttk.Label(wrap, text="结束：").grid(row=2, column=0, sticky="w", pady=4)
        self.end_var = tk.StringVar()
        end_row = ttk.Frame(wrap)
        end_row.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Entry(end_row, textvariable=self.end_var, width=30).pack(side="left", fill="x", expand=True)

        ttk.Button(
            end_row,
            text="📅 选择日期",
            command=lambda: self._on_pick_end_date(),
        ).pack(side="left", padx=(8, 0))

        ttk.Label(wrap, text="备注：").grid(row=3, column=0, sticky="nw", pady=4)
        self.note_text = tk.Text(wrap, width=42, height=6)
        self.note_text.grid(row=3, column=1, sticky="ew", pady=4)

        if event:
            self.start_var.set(dt_to_str(event.start))
            self.end_var.set(dt_to_str(event.end))
            self.note_text.insert("1.0", event.note or "")
        else:
            ds = init_date.strftime("%Y-%m-%d")
            self.start_var.set(ds)
            self.end_var.set(ds)

        btns = ttk.Frame(wrap)
        btns.grid(row=4, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="取消", command=self._cancel).pack(side="right", padx=6)
        ttk.Button(btns, text="保存", command=self._ok).pack(side="right")

        wrap.columnconfigure(1, weight=1)

        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._ok())

        self.wait_visibility()
        self.focus_force()
        ui.center_window(self, width=720, height=420, parent=parent)

    def _cancel(self):
        self.result = None
        self.destroy()

    def _on_pick_start_date(self):
        # 推断一个初始日期：优先从当前输入解析，否则用 init_date
        init = None
        try:
            init = parse_dt(self.start_var.get()).date()
        except Exception:
            init = None
        chosen = ui.pick_date(self, initial=init, title="选择开始日期")
        if chosen:
            self._set_date_keep_time(self.start_var, chosen)

    def _on_pick_end_date(self):
        init = None
        try:
            init = parse_dt(self.end_var.get()).date()
        except Exception:
            init = None
        chosen = ui.pick_date(self, initial=init, title="选择结束日期")
        if chosen:
            self._set_date_keep_time(self.end_var, chosen)

    def _set_date_keep_time(self, var: tk.StringVar, chosen: date):
        """
        仅替换日期部分，保留用户可能输入的时间部分：
        - '2026-03-05' -> '2026-03-10'
        - '2026-03-05 14:00' -> '2026-03-10 14:00'
        """
        cur = (var.get() or "").strip()
        date_part = chosen.strftime("%Y-%m-%d")
        if " " in cur:
            _, time_part = cur.split(" ", 1)
            var.set(f"{date_part} {time_part.strip()}")
        else:
            var.set(date_part)

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
            start, end = end, start

        note = self.note_text.get("1.0", "end").rstrip("\n")
        self.result = {"name": name, "start": start, "end": end, "note": note}
        self.destroy()


class DayDetailsWindow(tk.Toplevel):
    def __init__(self, app: "CalendarApp", d: date):
        super().__init__(app.root)
        self.app = app
        self.d = d

        self.title(f"{d.strftime('%Y-%m-%d')} 详细列表")
        self.geometry("780x380")
        self.transient(app.root)

        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill="both", expand=True)

        top = ttk.Frame(wrap)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=f"{d.strftime('%Y-%m-%d')} 待办事项", font=(ui.THEME.font_family, 12, "bold")).pack(side="left")

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="新增", command=self.add_event).pack(side="left", padx=4)
        ttk.Button(btns, text="编辑", command=self.edit_event).pack(side="left", padx=4)
        ttk.Button(btns, text="删除", command=self.delete_event).pack(side="left", padx=4)
        ttk.Button(btns, text="关闭", command=self.destroy).pack(side="left", padx=4)

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
        self.tree.column("note", width=300, anchor="w")

        ybar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ybar.set)
        ybar.pack(side="right", fill="y")

        ui.setup_treeview_zebra(self.tree)  # ✅ 斑马纹美化
        self.tree.bind("<Double-Button-1>", lambda e: self.edit_event())
        self.refresh()
        ui.center_window(self, width=920, height=520, parent=app.root)
        ui.setup_treeview_zebra(self.tree)  # 如果你还没加斑马纹
    def _events_for_day(self) -> List[Event]:
        return self.app.day_map.get(self.d, [])

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, e in enumerate(self._events_for_day()):
            self.tree.insert(
                "",
                "end",
                iid=e.id,
                values=(e.name, dt_to_str(e.start), dt_to_str(e.end), e.note),
                tags=(ui.zebra_tag(idx),)
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
            messagebox.showinfo("提示", "请先选择一个事件（或双击某行编辑）")
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

        ev.name = dlg.result["name"]
        ev.start = dlg.result["start"]
        ev.end = dlg.result["end"]
        ev.note = dlg.result["note"]

        self.app.persist_and_refresh()
        self.refresh()

    def delete_event(self):
        eid = self._selected_event_id()
        if not eid:
            messagebox.showinfo("提示", "请先选择一个事件")
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


class MultiSelectDropdown(tk.Toplevel):
    def __init__(self, app: "CalendarApp", anchor_widget: tk.Widget):
        super().__init__(app.root)
        self.app = app

        self.title("选择事件（多选）")
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()  # 模态：防止点到主窗口

        wrap = ttk.Frame(self, padding=12, style="Card.TFrame")
        wrap.pack(fill="both", expand=True)

        top = ttk.Frame(wrap, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="单击条目可选/取消；Enter 应用；Esc 关闭", style="FieldLabel.TLabel").pack(side="left")
        ttk.Button(top, text="关闭", style="Ghost.TButton", command=self.destroy).pack(side="right")

        mid = ttk.Frame(wrap, style="Card.TFrame")
        mid.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(mid, selectmode="multiple", exportselection=False, height=14)
        self.listbox.pack(side="left", fill="both", expand=True)
        ui.style_listbox(self.listbox)

        sb = ttk.Scrollbar(mid, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)

        # 填充选项
        self.items = app.get_event_display_items()  # (display, eid)
        for disp, _ in self.items:
            self.listbox.insert("end", disp)

        # 预选
        selected_ids = app.selected_event_ids.copy()
        for i, (_, eid) in enumerate(self.items):
            if eid in selected_ids:
                self.listbox.selection_set(i)

        # 单击切换选中/取消（无需 Ctrl/Shift）
        self.listbox.bind("<Button-1>", self._on_toggle_click)
        self.listbox.bind("<space>", self._on_toggle_space)

        # 底部按钮
        bottom = ttk.Frame(wrap, style="Card.TFrame")
        bottom.pack(fill="x", pady=(10, 0))

        self.auto_jump = tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom, text="应用后跳转到最早事件月份", variable=self.auto_jump).pack(side="left")

        ttk.Button(bottom, text="全选", style="Ghost.TButton", command=self._select_all).pack(side="right", padx=4)
        ttk.Button(bottom, text="全不选", style="Ghost.TButton", command=self._select_none).pack(side="right", padx=4)
        ttk.Button(bottom, text="应用高亮", style="Accent.TButton", command=self._apply).pack(side="right", padx=4)

        # 快捷键
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._apply())

        # ✅ 居中显示 & 充足高度：彻底解决按钮遮挡
        ui.center_window(self, width=720, height=520, parent=app.root)

    def _select_all(self):
        if self.listbox.size() > 0:
            self.listbox.selection_set(0, "end")

    def _select_none(self):
        self.listbox.selection_clear(0, "end")

    def _apply(self):
        idxs = list(self.listbox.curselection())
        eids = []
        for i in idxs:
            _, eid = self.items[i]
            eids.append(eid)
        self.app.apply_selected_events(set(eids), auto_jump=self.auto_jump.get())
        self.destroy()

    def _on_toggle_click(self, event):
        idx = self.listbox.nearest(event.y)
        if idx < 0 or idx >= self.listbox.size():
            return "break"

        cur = set(self.listbox.curselection())
        if idx in cur:
            self.listbox.selection_clear(idx)
        else:
            self.listbox.selection_set(idx)

        self.listbox.activate(idx)
        self.listbox.see(idx)
        return "break"

    def _on_toggle_space(self, event):
        idx = self.listbox.index("active")
        if idx < 0 or idx >= self.listbox.size():
            return "break"
        cur = set(self.listbox.curselection())
        if idx in cur:
            self.listbox.selection_clear(idx)
        else:
            self.listbox.selection_set(idx)
        return "break"


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

        self.selected_event_ids: Set[str] = set()
        self.highlight_day_to_eids: Dict[date, List[str]] = {}
        self.highlight_color_by_eid: Dict[str, str] = {}

        self.status_var = tk.StringVar(value="")
        self.selector_summary_var = tk.StringVar(value="选择事件（多选）")

        # ✅ UI 美化：布局由 ui_beauty 负责
        ui.build_main_ui(self)

        self._render_calendar()
        self.persist_and_refresh(save_only=True)

    def get_event_display_items(self) -> List[Tuple[str, str]]:
        items: List[Tuple[str, str]] = []
        seen: Set[str] = set()
        for e in sorted(self.events, key=lambda x: (x.start, x.end, x.name)):
            span = f"{dt_to_str(e.start)}~{dt_to_str(e.end)}" if e.end != e.start else dt_to_str(e.start)
            disp = f"{e.name}  |  {span}"
            if disp in seen:
                disp = f"{disp}  ({e.id[:8]})"
            seen.add(disp)
            items.append((disp, e.id))
        return items

    def open_multiselect_dropdown(self):
        MultiSelectDropdown(self, self.selector_btn)

    def apply_selected_events(self, selected_ids: Set[str], auto_jump: bool = True):
        existing_ids = {e.id for e in self.events}
        selected_ids = set(i for i in selected_ids if i in existing_ids)

        old = dict(self.highlight_color_by_eid)
        self.highlight_color_by_eid.clear()

        used_colors = set()
        for eid in selected_ids:
            if eid in old:
                self.highlight_color_by_eid[eid] = old[eid]
                used_colors.add(old[eid])

        next_index = 0
        for eid in selected_ids:
            if eid in self.highlight_color_by_eid:
                continue
            while True:
                if next_index < len(HIGHLIGHT_PALETTE):
                    cand = HIGHLIGHT_PALETTE[next_index]
                else:
                    cand = pastel_from_index(next_index)
                next_index += 1
                if cand not in used_colors:
                    used_colors.add(cand)
                    self.highlight_color_by_eid[eid] = cand
                    break

        self.selected_event_ids = selected_ids
        self._rebuild_highlight_day_map()

        self._update_selector_summary()
        self.status_var.set(f"已选 {len(self.selected_event_ids)} 个事件")

        if auto_jump and self.selected_event_ids:
            evs = [e for e in self.events if e.id in self.selected_event_ids]
            evs.sort(key=lambda e: (e.start, e.end))
            self.year = evs[0].start.year
            self.month = evs[0].start.month

        self._render_calendar()

    def _update_selector_summary(self):
        if not self.selected_event_ids:
            self.selector_summary_var.set("选择事件（多选）")
            return
        names = [e.name for e in self.events if e.id in self.selected_event_ids][:2]
        if len(self.selected_event_ids) <= 2:
            self.selector_summary_var.set("，".join(names))
        else:
            self.selector_summary_var.set(f"{'，'.join(names)} 等（{len(self.selected_event_ids)}）")

    def clear_highlight(self):
        self.selected_event_ids = set()
        self.highlight_day_to_eids = {}
        self.highlight_color_by_eid = {}
        self.status_var.set("")
        self.selector_summary_var.set("选择事件（多选）")
        self._render_calendar()

    def _rebuild_highlight_day_map(self):
        self.highlight_day_to_eids = {}
        selected_events = [e for e in self.events if e.id in self.selected_event_ids]
        selected_events.sort(key=lambda e: (e.start, e.end, e.name))

        for e in selected_events:
            cur = e.start.date()
            endd = e.end.date()
            while cur <= endd:
                lst = self.highlight_day_to_eids.setdefault(cur, [])
                if e.id not in lst:
                    lst.append(e.id)
                cur += timedelta(days=1)

    def reload(self):
        self.events = load_events(self.data_file)
        self.day_map = build_day_map(self.events)
        self.apply_selected_events(self.selected_event_ids, auto_jump=False)
        self._render_calendar()
        self._refresh_open_day_windows()

    def persist_and_refresh(self, save_only: bool = False):
        save_events(self.data_file, self.events)
        if save_only:
            return
        self.day_map = build_day_map(self.events)
        self.apply_selected_events(self.selected_event_ids, auto_jump=False)
        self._render_calendar()
        self._refresh_open_day_windows()

    def _refresh_open_day_windows(self):
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

    def _base_bg(self, d: date, has_events: bool) -> str:
        if d == self.today:
            return TODAY_BG
        if has_events:
            return EVENT_BG
        return NORMAL_BG

    def _draw_highlight_dots(self, parent: tk.Frame, bg: str, eids: List[str]):
        colors = [self.highlight_color_by_eid.get(eid, "#CCCCCC") for eid in eids][:4]
        if not colors:
            return
        w = 10 * len(colors) + 2
        h = 10
        cv = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0, bd=0)
        cv.place(relx=1.0, rely=1.0, anchor="se", x=-6, y=-6)
        x = 5
        for c in colors:
            cv.create_oval(x - 3, 2, x + 3, 8, fill=c, outline=darken(c, 0.7))
            x += 10

    def _render_calendar(self):
        # 1) 清理/标题
        self.tooltip.hide()
        self._clear_grid()

        # 当前月份更显眼：如果正在看的月份就是“本月”，标题追加标识
        is_current_month = (self.year == self.today.year and self.month == self.today.month)
        suffix = "（本月）" if is_current_month else ""
        self.title_label.config(text=f"{self.year}年 {self.month}月 {suffix}".strip())

        # 2) 生成 6x7 日历格（42格）
        cal = calendar.Calendar(firstweekday=0)  # 0=周一
        month_days = list(cal.itermonthdays(self.year, self.month))
        while len(month_days) < 42:
            month_days.append(0)

        for r in range(6):
            self.grid_frame.rowconfigure(r, weight=1)
            for c in range(7):
                idx = r * 7 + c
                day = month_days[idx]

                # 空白格
                if day == 0:
                    cell = tk.Frame(
                        self.grid_frame,
                        bg=BLANK_BG,
                        highlightthickness=1,
                        highlightbackground=BORDER_NORMAL,
                        bd=0
                    )
                    cell.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                    continue

                d = date(self.year, self.month, day)
                events_today = self.day_map.get(d, [])
                has_events = bool(events_today)

                base_bg = self._base_bg(d, has_events)

                # 这一天命中的检索事件
                hit_eids = self.highlight_day_to_eids.get(d, [])

                # 3) 背景/边框（保持你原有的“多选多色高亮”逻辑）
                if len(hit_eids) == 1:
                    bg = self.highlight_color_by_eid.get(hit_eids[0], base_bg)
                    border = darken(bg, 0.7)
                    ht = 2
                elif len(hit_eids) > 1:
                    bg = MULTI_HIT_BG
                    border = "#555555"
                    ht = 2
                else:
                    bg = base_bg
                    border = BORDER_NORMAL
                    ht = 1

                # 4) 今日突出显示：更粗主色边框（覆盖上面的边框策略）
                if d == self.today:
                    border = ui.THEME.accent
                    ht = max(ht, 3)

                cell = tk.Frame(
                    self.grid_frame,
                    bg=bg,
                    highlightthickness=ht,
                    highlightbackground=border,
                    highlightcolor=border,
                    bd=0
                )
                cell.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                cell.grid_propagate(False)

                # 5) 文本（• 表示当天有任何事件）
                text = f"{day}" + ("  •" if has_events else "")

                # 统一日历字体/周末颜色/今日更大更粗
                fg, font = ui.day_label_style(col_index=c, is_today=(d == self.today))

                lbl = tk.Label(
                    cell,
                    text=text,
                    bg=bg,
                    fg=fg,
                    anchor="nw",
                    justify="left",
                    font=font,
                    padx=10,
                    pady=10
                )
                lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

                # 6) 今日徽标（右上角）
                if d == self.today:
                    ui.draw_today_badge(cell, bg)

                # 7) 命中事件的小圆点（保持原逻辑）
                if hit_eids:
                    self._draw_highlight_dots(cell, bg, hit_eids)

                # 8) 交互：双击打开当天详情
                for widget in (cell, lbl):
                    widget.bind("<Double-Button-1>", lambda e, dd=d: self.open_day_details(dd))

                # 9) tooltip：有日程才显示
                if has_events:
                    for widget in (cell, lbl):
                        widget.bind("<Enter>", lambda e, dd=d: self._on_enter_day(dd))
                        widget.bind("<Motion>", lambda e, dd=d: self._on_motion_day(dd))
                        widget.bind("<Leave>", lambda e: self.tooltip.hide())


    def _format_tooltip(self, d: date, events: List[Event]) -> str:
        lines = [f"{d.strftime('%Y-%m-%d')} 待办事项："]
        for i, ev in enumerate(events, 1):
            span = f"{dt_to_str(ev.start)} ~ {dt_to_str(ev.end)}" if ev.end != ev.start else dt_to_str(ev.start)
            note = f"（{ev.note}）" if ev.note else ""
            lines.append(f"{i}. {ev.name}  [{span}]{note}")
        return "\n".join(lines)

    def _on_enter_day(self, d: date):
        events_today = self.day_map.get(d, [])
        if not events_today:
            return
        text = self._format_tooltip(d, events_today)
        x = self.root.winfo_pointerx() + 14
        y = self.root.winfo_pointery() + 18
        self.tooltip.show(x, y, text)

    def _on_motion_day(self, d: date):
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

    ui.setup_theme(root, mode="light")  # ✅ 回退浅色风格

    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    CalendarApp(root, data_file)
    root.mainloop()


if __name__ == "__main__":
    main()