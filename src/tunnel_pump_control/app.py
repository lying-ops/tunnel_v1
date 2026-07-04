import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, csv, datetime, threading, time, webbrowser, shutil, json, http.server, socketserver
from .db import Database, APP_TITLE, COPYRIGHT, PUMP_TYPES, STATION_TYPES, CONTROL_MODES, REPORT_DIR, BASE_DIR, now
from .service import SimService

PUMP_TYPE_LABEL = dict(PUMP_TYPES)
PUMP_TYPE_CODE = {v: k for k, v in PUMP_TYPES}
OBJECT_TYPE_LABEL = {'station': '泵站', 'pump': '水泵', 'pipe': '母管', 'instrument': '仪表'}
OBJECT_TYPE_CODE = {v: k for k, v in OBJECT_TYPE_LABEL.items()}
MODE_LABEL = dict(CONTROL_MODES)
MODE_CODE = {v: k for k, v in CONTROL_MODES}
DATA_MODE_LABEL = {'simulation': '模拟', 'realtime': '实时采集', '模拟': '模拟', '实时采集': '实时采集'}
DATA_MODE_CODE = {'模拟': 'simulation', '实时采集': 'realtime', 'simulation': 'simulation', 'realtime': 'realtime'}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.service = SimService(self.db);
        self.service.start()
        self.title(APP_TITLE)
        self._init_window_size()
        self.configure(bg="#edf4fb")
        self._setup_styles()
        self.current_station_id = self.db.get_current_station_id()
        self.blink_on = True
        self.manual_freq_entries = {}
        self.monitor_pump_cards = {}
        self.monitor_card_signature = None
        self.edit_station_id = None;
        self.edit_pump_id = None;
        self.edit_pipe_id = None;
        self.edit_inst_id = None;
        self.edit_point_id = None
        self.param_frames = {};
        self.param_station_labels = {}
        self.video_threads = {};
        self.video_stop_flags = {};
        self.video_frames = {};
        self.video_recorders = {};
        self.video_recording = {};
        self.video_labels = {};
        self.video_status_labels = {};
        self.edit_camera_id = None
        self.twin_scale = 1.0;
        self.twin_offset = [0, 0];
        self.twin_items = [];
        self.twin_drag_start = None;
        self.twin_selected = None;
        self.twin_preview_photo = None;
        self.twin_httpd = None;
        self.twin_http_port = 8765
        self.create_layout()
        self.refresh_all()
        self.after(1000, self.periodic)

    def _init_window_size(self):
        """根据屏幕分辨率自动调整窗口尺寸，避免低分辨率显示不全，高分辨率过小。"""
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w = min(max(int(sw * 0.92), 1200), 1680)
            h = min(max(int(sh * 0.86), 720), 980)
            x = max((sw - w) // 2, 0)
            y = max((sh - h) // 2, 0)
            self.geometry(f"{w}x{h}+{x}+{y}")
            self.minsize(min(1100, w), min(680, h))
        except Exception:
            self.geometry('1420x820')
            self.minsize(1200, 720)

    def _setup_styles(self):
        """统一界面风格：蓝色科技、绿色运行、橙色应急、红色报警。"""
        try:
            style = ttk.Style(self)
            try:
                style.theme_use('clam')
            except Exception:
                pass
            style.configure('TNotebook', background='#edf4fb', borderwidth=0)
            style.configure('TNotebook.Tab', font=('Microsoft YaHei', 9, 'bold'), padding=(8, 4), background='#dceaf7',
                            foreground='#12324a')
            style.map('TNotebook.Tab', background=[('selected', '#ffffff')], foreground=[('selected', '#0f4c81')])
            style.configure('TFrame', background='#edf4fb')
            style.configure('TLabelframe', background='#edf4fb', bordercolor='#b7c9dd')
            style.configure('TLabelframe.Label', font=('Microsoft YaHei', 10, 'bold'), foreground='#0f4c81',
                            background='#edf4fb')
            style.configure('TLabel', background='#edf4fb', foreground='#1f2933', font=('Microsoft YaHei', 9))
            style.configure('TButton', font=('Microsoft YaHei', 9), padding=(8, 4))
            style.configure('Primary.TButton', font=('Microsoft YaHei', 9, 'bold'), foreground='#ffffff',
                            background='#0f6fb2', padding=(10, 5))
            style.map('Primary.TButton', background=[('active', '#0b5f9c'), ('disabled', '#9aa7b2')])
            style.configure('Success.TButton', font=('Microsoft YaHei', 9, 'bold'), foreground='#ffffff',
                            background='#16803c', padding=(10, 5))
            style.map('Success.TButton', background=[('active', '#0f6a30'), ('disabled', '#9aa7b2')])
            style.configure('Danger.TButton', font=('Microsoft YaHei', 9, 'bold'), foreground='#ffffff',
                            background='#c0392b', padding=(10, 5))
            style.map('Danger.TButton', background=[('active', '#a93226'), ('disabled', '#9aa7b2')])
            style.configure('Warn.TButton', font=('Microsoft YaHei', 9, 'bold'), foreground='#2d1b00',
                            background='#f6c343', padding=(10, 5))
            style.map('Warn.TButton', background=[('active', '#e0af2d'), ('disabled', '#9aa7b2')])
            style.configure('Treeview', rowheight=26, font=('Microsoft YaHei', 9), background='#ffffff',
                            fieldbackground='#ffffff')
            style.configure('Treeview.Heading', font=('Microsoft YaHei', 9, 'bold'), background='#dceaf7',
                            foreground='#12324a')
        except Exception:
            pass

    def create_layout(self):
        # 顶部标题栏（从 build_dashboard 迁移）
        self.dash_bg = '#031326'
        self.dash_panel_bg = '#071f3d'
        self.dash_panel_bg2 = '#092a50'
        self.dash_line = '#0b5fa5'
        self.dash_text = '#d9ecff'
        self.dash_muted = '#7fb8ee'
        self.dash_green = '#21e56d'
        self.dash_blue = '#1e9bff'
        self.dash_yellow = '#ffc526'
        self.dash_red = '#ff4136'

        top = tk.Frame(self, bg='#041a34', height=58,
                       highlightbackground='#0b5fa5', highlightthickness=1)
        top.pack(side='top', fill='x')
        top.pack_propagate(False)
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=3)
        top.grid_columnconfigure(2, weight=1)

        nav = tk.Frame(top, bg='#041a34')
        nav.grid(row=0, column=0, sticky='nsew', padx=8)
        tk.Label(nav, text='☰', font=('Microsoft YaHei', 15, 'bold'), bg='#09294f', fg='#8cc8ff',
                 width=3, bd=0, relief='flat').pack(side='left', pady=12)
        tk.Label(nav, text='◇', font=('Microsoft YaHei', 15), bg='#041a34', fg='#6bbcff').pack(side='left', padx=8)
        tk.Label(nav, text='⌂  泵站总览', font=('Microsoft YaHei', 10, 'bold'), bg='#0a2d56', fg='#eaf6ff',
                 padx=12, pady=6).pack(side='left')

        tk.Label(top, text='隧道泵站自动控制系统  V5.7', font=('Microsoft YaHei', 22, 'bold'),
                 bg='#041a34', fg='#f3f8ff').grid(row=0, column=1, sticky='nsew')

        right = tk.Frame(top, bg='#041a34')
        right.grid(row=0, column=2, sticky='nsew', padx=8)
        self.dash_datetime_lbl = tk.Label(right, text='-', font=('Consolas', 10, 'bold'), bg='#041a34',
                                          fg='#d8edff')
        self.dash_datetime_lbl.pack(side='left', padx=(0, 10), pady=18)
        self.dash_week_lbl = tk.Label(right, text='-', font=('Microsoft YaHei', 9), bg='#041a34', fg='#d8edff')
        self.dash_week_lbl.pack(side='left', padx=(0, 12), pady=18)
        self.dash_backend_lbl = tk.Label(right, text='后端服务：● 正常', font=('Microsoft YaHei', 9),
                                         bg='#041a34', fg=self.dash_green)
        self.dash_backend_lbl.pack(side='left', padx=(0, 12), pady=18)
        self.dash_total_status_lbl = tk.Label(right, text='总状态：● 正常', font=('Microsoft YaHei', 9),
                                              bg='#041a34', fg=self.dash_green)
        self.dash_total_status_lbl.pack(side='left', pady=18)
        self.dash_header = self.dash_datetime_lbl

        sub = tk.Frame(self, bg='#071f3d', height=28)
        sub.pack(side='top', fill='x')
        sub.pack_propagate(False)
        self.station_lbl = tk.Label(sub, text='当前泵站：-', font=('Microsoft YaHei', 9, 'bold'), bg='#071f3d',
                                    fg='#8cc8ff')
        self.station_lbl.pack(side='right', padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=4, pady=4)
        self.pages = {}
        tab_icons = {
            '首页总览': '🏠 首页总览', '泵站监控': '📊 泵站监控', '泵站管理': '🏭 泵站管理',
            '水泵管理': '🔵 水泵管理', '母管管理': '🟩 母管管理', '仪表管理': '📟 仪表管理',
            '模型示意': '🤖 模型示意', '手动控制': '🕹 手动控制',
            '参数配置': '⚙ 参数配置', '通讯设置': '🌐 通讯设置', '变量/点位管理': '🔢 变量点位',
            '视频监控': '🎥 视频监控', '三维孪生': '🌐 三维孪生', '数据绑定': '🔗 数据绑定', '报表导出': '📄 报表导出',
            '日志': '📋 日志'
        }
        for name in ['首页总览', '泵站监控', '泵站管理', '水泵管理', '母管管理', '仪表管理', '模型示意', '手动控制',
                     '参数配置', '通讯设置', '变量/点位管理', '视频监控', '三维孪生', '数据绑定', '报表导出', '日志']:
            frame = ttk.Frame(self.nb)
            self.nb.add(frame, text=tab_icons.get(name, name))
            self.pages[name] = frame
        self.build_dashboard()
        self.build_monitor()
        self.build_station_page()
        self.build_pump_page()
        self.build_pipe_page()
        self.build_instrument_page()
        self.build_model_page()
        self.build_manual_page()
        self.build_config_page()
        self.build_comm_page()
        self.build_point_page()
        self.build_video_page()
        self.build_twin_page()
        self.build_twin_binding_page()
        self.build_report_page()
        self.build_log_page()
        self._update_datetime_label()

    def _update_datetime_label(self):
        try:
            weekday = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][
                datetime.datetime.now().weekday()]
            text = datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S  ') + weekday
            if hasattr(self, 'datetime_lbl'):
                self.datetime_lbl.config(text=text)
        except Exception:
            pass

    def periodic(self):
        self.blink_on = not getattr(self, 'blink_on', True)
        self.service_lbl.config(text=f'后台服务：运行中  心跳：{self.service.heartbeat}')
        self._update_datetime_label()
        self.refresh_realtime()
        self.after(1000, self.periodic)

    def sid(self):
        return self.current_station_id

    def rows(self, sql, params=()):
        return self.db.query(sql, params)

    def row(self, sql, params=()):
        return self.db.one(sql, params)

    def safe_get(self, row, key, default=None):
        """兼容 sqlite3.Row / dict / 旧数据库字段：字段不存在时返回默认值，避免刷新界面崩溃。"""
        try:
            return row[key]
        except Exception:
            try:
                return row.get(key, default)
            except Exception:
                return default

    def pump_this_run_seconds(self, p):
        # V4.0 曾读取 run_seconds_current；部分旧库/查询没有该字段。
        for key in ('run_seconds_current', 'current_run_seconds', 'this_run_seconds'):
            val = self.safe_get(p, key, None)
            if val is not None:
                return val or 0
        # 兜底：没有当次运行时长字段时，运行泵临时显示今日运行时长，停机显示 0。
        if self.safe_get(p, 'run_feedback', 0):
            return self.safe_get(p, 'run_seconds_today', 0) or 0
        return 0

    def pump_total_run_seconds(self, p):
        return self.safe_get(p, 'run_seconds_total', 0) or 0

    def get_station(self):
        return self.row('SELECT * FROM pump_station WHERE id=?', (self.sid(),)) if self.sid() else None

    def station_title(self, sid=None):
        sid = sid or self.sid()
        st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
        return f"{st['station_code']} | {st['station_name']}" if st else '-'

    def feed_pump_options(self):
        vals = ['']
        for fp in self.rows(
                "SELECT id,pump_code,pump_name FROM pump WHERE station_id=? AND pump_type='feed' ORDER BY display_order,id",
                (self.sid(),)):
            vals.append(f"{fp['id']} | {fp['pump_code']} | {fp['pump_name']}")
        return vals

    def parse_combo_id(self, text):
        text = (text or '').strip()
        if not text:
            return None
        try:
            return int(text.split('|')[0].strip())
        except Exception:
            if text.isdigit():
                return int(text)
        return None

    def pipe_options(self):
        vals = ['']
        for r in self.rows('SELECT id,pipe_code,pipe_name FROM main_pipe WHERE station_id=? ORDER BY display_order,id',
                           (self.sid(),)):
            vals.append(f"{r['id']} | {r['pipe_code']} | {r['pipe_name']}")
        return vals

    def pump_options(self, include_feed=True):
        vals = ['']
        sql = 'SELECT id,pump_code,pump_name,pump_type FROM pump WHERE station_id=? '
        if not include_feed:
            sql += "AND pump_type!='feed' "
        sql += 'ORDER BY display_order,id'
        for r in self.rows(sql, (self.sid(),)):
            vals.append(f"{r['id']} | {r['pump_code']} | {r['pump_name']}")
        return vals

    def object_type_label(self, code):
        return OBJECT_TYPE_LABEL.get(code, code or '')

    def object_type_code(self, label):
        return OBJECT_TYPE_CODE.get(label, label or 'station')

    def clear_tree(self, t):
        for i in t.get_children(): t.delete(i)

    def fmt_seconds(self, seconds):
        try:
            seconds = int(float(seconds or 0))
        except Exception:
            seconds = 0
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}h{m:02d}m"
        return f"{m}m{s:02d}s"

    def pump_lamp(self, p):
        fault = bool(p['fault_feedback'] or p['manual_fault'])
        maint = bool(p['maintenance'])
        running = bool(p['run_feedback'])
        if fault:
            return ('●', '#f2c300' if getattr(self, 'blink_on', True) else '#8a6d00', '故障')
        if maint:
            return ('●', '#f0ad4e', '检修')
        if running:
            return ('●', '#16a34a', '运行')
        return ('●', '#9ca3af', '停止')

    def pump_control_role(self, p, control_state=None):
        """泵站监控页使用的简化角色，帮助现场人员看懂系统为什么选/不选某台泵。"""
        if p['pump_type'] == 'feed':
            return '给水泵'
        if p['fault_feedback'] or p['manual_fault']:
            return '故障剔除'
        if p['maintenance']:
            return '检修剔除'
        if not p['enabled'] or p['disabled']:
            return '禁用剔除'
        if not p['auto_enable']:
            return '手动保留'
        state_text = str(control_state or '')
        if p['run_feedback']:
            if '减泵' in state_text:
                return '运行待判'
            return '主运行泵'
        if '加泵' in state_text:
            return '备用待加'
        if p['standby']:
            return '备用泵'
        return '自动待命'

    def clear_current_station_views(self):
        # 当前没有泵站时，所有依赖泵站的界面必须清空，不能保留上一次显示的数据。
        for name in ['monitor_pumps', 'monitor_pipes', 'pump_tree', 'pipe_tree', 'inst_tree', 'point_tree']:
            if hasattr(self, name):
                self.clear_tree(getattr(self, name))
        if hasattr(self, 'monitor_top'):
            self.monitor_top.config(text='当前没有泵站，请先在“泵站管理”中新建泵站。')
        if hasattr(self, 'mode_status'):
            self.mode_status.config(text='当前运行模式：-    自动调节状态：-')
        if hasattr(self, 'manual_pump'):
            self.manual_pump['values'] = [];
            self.manual_pump.set('')
        if hasattr(self, 'canvas'):
            self.canvas.delete('all')
            self.canvas.create_text(20, 20, anchor='w', text='当前没有泵站，请先在“泵站管理”中新建泵站。', fill='red',
                                    font=('Microsoft YaHei', 14, 'bold'))

    def refresh_all(self):
        self.current_station_id = self.db.get_current_station_id()
        st = self.get_station()
        self.station_lbl.config(text='当前泵站：' + (st['station_name'] if st else '-'))
        if not st:
            self.refresh_station_list()
            self.clear_current_station_views()
            self.refresh_config_params()
            self.refresh_log()
            self.refresh_realtime()
            self.refresh_model_station_choices()
            self.refresh_twin_station_combo()
            self._twin_binding_refresh_station_combo()
            return
        self.refresh_station_list()
        self.refresh_pump_list()
        self.refresh_pipe_list()
        self.refresh_inst_list()
        self.refresh_point_list()
        self.refresh_device_list()
        self.refresh_camera_list()
        self.refresh_params()
        self.refresh_config_params()
        self.refresh_log()
        self.refresh_realtime()
        self.refresh_manual_lists()
        self.refresh_model_station_choices()
        self.refresh_video_station_choices()
        self.draw_model()
        self.refresh_twin_station_combo()
        self._twin_binding_refresh_station_combo()

    # Dashboard
    def build_dashboard(self):
        """首页总览：深蓝色泵站驾驶舱界面。"""
        f = self.pages['首页总览']
        for w in f.winfo_children():
            w.destroy()

        self.dash_bg = '#031326'
        self.dash_panel_bg = '#071f3d'
        self.dash_panel_bg2 = '#092a50'
        self.dash_line = '#0b5fa5'
        self.dash_text = '#d9ecff'
        self.dash_muted = '#7fb8ee'
        self.dash_green = '#21e56d'
        self.dash_blue = '#1e9bff'
        self.dash_yellow = '#ffc526'
        self.dash_red = '#ff4136'

        self.dash_container = tk.Frame(f, bg=self.dash_bg)
        self.dash_container.pack(fill='both', expand=True)

        # KPI 指标区
        kpi_row = tk.Frame(self.dash_container, bg=self.dash_bg, height=86)
        kpi_row.pack(fill='x', padx=10, pady=(0, 8))
        kpi_row.pack_propagate(False)
        for i in range(10):
            kpi_row.grid_columnconfigure(i, weight=1, uniform='kpi')
        self.dash_stat_frame = kpi_row
        self.dash_metric_frame = kpi_row
        self.dash_kpis = {}
        kpis = [
            ('running', '▶', '运行数量', self.dash_green),
            ('standby', 'Ⅱ', '备用数量', self.dash_blue),
            ('fault', '⚠', '故障数量', self.dash_red),
            ('maintenance', '⚒', '检修数量', self.dash_yellow),
            ('current', 'ϟ', '总电流', self.dash_blue),
            ('voltage', '⌁', '总电压', self.dash_blue),
            ('power', 'Ω', '总功率', self.dash_blue),
            ('flow', '◔', '总瞬时流量', self.dash_blue),
            ('day_flow', '♨', '当天排水量', self.dash_blue),
            ('day_energy', 'ϟ', '当天耗电量', self.dash_blue),
        ]
        for i, (key, icon, title, color) in enumerate(kpis):
            card = self._dash_kpi(kpi_row, icon, title, '-', '', color)
            card['box'].grid(row=0, column=i, sticky='nsew', padx=4, pady=2)
            self.dash_kpis[key] = card

        # 主体区域
        self.dash_main = tk.Frame(self.dash_container, bg=self.dash_bg)
        self.dash_main.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self.dash_main.grid_columnconfigure(0, minsize=280)
        self.dash_main.grid_columnconfigure(1, weight=1)
        self.dash_main.grid_columnconfigure(2, minsize=350)
        self.dash_main.grid_rowconfigure(0, minsize=34)
        self.dash_main.grid_rowconfigure(1, weight=1)
        self.dash_main.grid_rowconfigure(2, minsize=185)

        station_bar = tk.Frame(self.dash_main, bg='#08294f', height=34,
                               highlightbackground='#0b5fa5', highlightthickness=1)
        station_bar.grid(row=0, column=0, sticky='nsew', padx=(0, 8), pady=(0, 8))
        station_bar.pack_propagate(False)
        tk.Label(station_bar, text='当前泵站：', font=('Microsoft YaHei', 12, 'bold'), bg='#08294f',
                 fg='#f0f7ff').pack(side='left', padx=(12, 4), pady=4)
        self.dash_station_lbl = tk.Label(station_bar, text='-', font=('Microsoft YaHei', 15, 'bold italic'),
                                         bg='#08294f', fg='#f3f8ff')
        self.dash_station_lbl.pack(side='left', pady=2)

        # 左侧液位
        level_col = tk.Frame(self.dash_main, bg=self.dash_bg)
        level_col.grid(row=1, column=0, sticky='nsew', padx=(0, 8), pady=(0, 8))
        level_col.grid_rowconfigure(0, weight=1)
        level_col.grid_rowconfigure(1, weight=1)
        self.dash_levels = {
            'lt1': self._dash_level_panel(level_col, '液位1', 'LT01', '-', self.dash_green),
            'lt2': self._dash_level_panel(level_col, '液位2', 'LT02', '-', self.dash_blue),
        }
        self.dash_levels['lt1']['box'].grid(row=0, column=0, sticky='nsew', pady=(0, 8))
        self.dash_levels['lt2']['box'].grid(row=1, column=0, sticky='nsew')

        # 中间数字孪生
        twin_outer, twin_body = self._dash_panel(self.dash_main, '泵站数字孪生')
        twin_outer.grid(row=0, column=1, rowspan=2, sticky='nsew', padx=(0, 8), pady=(0, 8))
        view_box = tk.Frame(twin_outer, bg='#071f3d')
        view_box.place(relx=0.78, y=13, relwidth=0.18, height=26)
        tk.Label(view_box, text='3D视角', font=('Microsoft YaHei', 9), bg='#1d76c8', fg='#eaf6ff',
                 padx=14).pack(side='left', fill='both')
        tk.Label(view_box, text='平面图', font=('Microsoft YaHei', 9), bg='#12375d', fg='#9dc8f1',
                 padx=14).pack(side='left', fill='both')
        self.dash_twin_canvas = tk.Canvas(twin_body, bg='#06172d', highlightthickness=0)
        self.dash_twin_canvas.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        # 右侧设备状态
        status_outer, status_body = self._dash_panel(self.dash_main, '设备运行状态')
        status_outer.grid(row=0, column=2, rowspan=2, sticky='nsew', pady=(0, 8))
        self.dash_status_body = status_body

        # 底部趋势图
        charts_outer, charts_body = self._dash_panel(self.dash_main, None)
        charts_outer.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=(0, 8))
        charts_body.grid_columnconfigure(0, weight=1)
        charts_body.grid_columnconfigure(1, weight=1)
        charts_body.grid_columnconfigure(2, weight=1)
        charts_body.grid_columnconfigure(3, weight=1)
        charts_body.grid_columnconfigure(4, weight=1)
        self.dash_charts = {}
        chart_defs = [
            ('level', '液位变化（m）'),
            ('flow', '流量（m³/s）'),
            ('pressure', '压力（MPa）'),
            ('power', '功率（MW）'),
            ('energy', '电量（kWh）'),
        ]
        for i, (key, title) in enumerate(chart_defs):
            chart = self._dash_chart(charts_body, title)
            chart['box'].grid(row=0, column=i, sticky='nsew', padx=4, pady=4)
            self.dash_charts[key] = chart

        # 右下报警事件
        event_outer, event_body = self._dash_panel(self.dash_main, '报警 / 事件')
        event_outer.grid(row=2, column=2, sticky='nsew')
        self.dash_event_body = event_body

        self.refresh_dashboard()

    def _dash_panel(self, parent, title=None, bg='#071f3d'):
        outer = tk.Frame(parent, bg=bg, highlightbackground='#0b5fa5', highlightthickness=1)
        if title:
            title_bar = tk.Frame(outer, bg=bg, height=36)
            title_bar.pack(fill='x')
            title_bar.pack_propagate(False)
            tk.Label(title_bar, text='▌', font=('Microsoft YaHei', 13, 'bold'), bg=bg, fg='#1e9bff').pack(
                side='left', padx=(8, 0), pady=8)
            tk.Label(title_bar, text=title, font=('Microsoft YaHei', 11, 'bold'), bg=bg, fg='#dceeff').pack(
                side='left', padx=(4, 0), pady=8)
            if title == '报警 / 事件':
                tk.Label(title_bar, text='更多 >', font=('Microsoft YaHei', 9), bg=bg, fg='#4eb0ff').pack(
                    side='right', padx=10, pady=8)
        body = tk.Frame(outer, bg=bg)
        body.pack(fill='both', expand=True)
        return outer, body

    def _dash_kpi(self, parent, icon, title, value, unit='', color='#1e9bff'):
        box = tk.Frame(parent, bg='#071f3d', highlightbackground='#0c4d8c', highlightthickness=1)
        icon_box = tk.Frame(box, bg='#082a4f', width=62)
        icon_box.pack(side='left', fill='y')
        icon_box.pack_propagate(False)
        icon_lbl = tk.Label(icon_box, text=icon, font=('Microsoft YaHei', 22, 'bold'), bg='#082a4f', fg=color)
        icon_lbl.pack(expand=True)
        content = tk.Frame(box, bg='#071f3d')
        content.pack(side='left', fill='both', expand=True, padx=(8, 4), pady=8)
        title_lbl = tk.Label(content, text=title, font=('Microsoft YaHei', 9, 'bold'), bg='#071f3d', fg='#c8e7ff',
                             anchor='w')
        title_lbl.pack(fill='x')
        value_line = tk.Frame(content, bg='#071f3d')
        value_line.pack(anchor='w', pady=(4, 0))
        value_lbl = tk.Label(value_line, text=str(value), font=('Consolas', 18, 'bold'), bg='#071f3d', fg='#f4f8ff')
        value_lbl.pack(side='left')
        unit_lbl = tk.Label(value_line, text=(' ' + unit) if unit else '', font=('Microsoft YaHei', 9, 'bold'),
                            bg='#071f3d', fg='#e6f4ff')
        unit_lbl.pack(side='left', padx=(2, 0), pady=(7, 0))
        return {'box': box, 'icon': icon_lbl, 'title': title_lbl, 'value': value_lbl, 'unit': unit_lbl,
                'color': color}

    def _dash_level_panel(self, parent, name, code, value, color):
        box = tk.Frame(parent, bg='#071f3d', highlightbackground='#0b5fa5', highlightthickness=1)
        head = tk.Frame(box, bg='#071f3d', height=34)
        head.pack(fill='x')
        head.pack_propagate(False)
        tk.Label(head, text=name, font=('Microsoft YaHei', 12, 'bold'), bg='#071f3d', fg='#e9f5ff').pack(
            side='left', padx=(84, 4), pady=6)
        tk.Label(head, text=code, font=('Microsoft YaHei', 9), bg='#071f3d', fg='#c2ddf7').pack(side='left', pady=8)
        state_lbl = tk.Label(head, text='正常', font=('Microsoft YaHei', 8, 'bold'), bg='#0b6f45', fg='#72ffab',
                             padx=10)
        state_lbl.pack(side='right', padx=12, pady=7)

        body = tk.Frame(box, bg='#071f3d')
        body.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        gauge = tk.Canvas(body, width=78, height=150, bg='#071f3d', highlightthickness=0)
        gauge.pack(side='left', fill='y', padx=(4, 10))
        info = tk.Frame(body, bg='#071f3d')
        info.pack(side='left', fill='both', expand=True)
        value_line = tk.Frame(info, bg='#071f3d')
        value_line.pack(anchor='w', pady=(8, 0))
        value_lbl = tk.Label(value_line, text=str(value), font=('Consolas', 24, 'bold'), bg='#071f3d', fg=color)
        value_lbl.pack(side='left')
        unit_lbl = tk.Label(value_line, text=' m', font=('Microsoft YaHei', 11, 'bold'), bg='#071f3d', fg='#dceeff')
        unit_lbl.pack(side='left', pady=(9, 0))
        tk.Label(info, text='量程：0~10.00m', font=('Microsoft YaHei', 9), bg='#071f3d', fg='#c5d9ef').pack(
            anchor='w', pady=(4, 4))
        spark = tk.Canvas(info, height=58, bg='#071f3d', highlightthickness=0)
        spark.pack(fill='both', expand=True, pady=(2, 0))
        return {'box': box, 'state': state_lbl, 'gauge': gauge, 'value': value_lbl, 'unit': unit_lbl,
                'spark': spark, 'color': color, 'code': code}

    def _dash_chart(self, parent, title, color='#1e9bff'):
        box = tk.Frame(parent, bg='#071f3d')
        tk.Label(box, text=title, font=('Microsoft YaHei', 10, 'bold'), bg='#071f3d', fg='#e9f5ff',
                 anchor='w').pack(fill='x', padx=6, pady=(4, 0))
        canvas = tk.Canvas(box, height=132, bg='#071f3d', highlightthickness=0)
        canvas.pack(fill='both', expand=True, padx=4, pady=(0, 4))
        return {'box': box, 'canvas': canvas, 'title': title, 'color': color}

    def _make_card(self, parent, icon, title, value, unit='', fg='#1f4e79', width=18, bg='white', accent='#1f4e79'):
        # 保留旧辅助函数，避免其它版本代码引用时报错。
        box = tk.Frame(parent, bd=0, relief='flat', background=bg, highlightbackground='#c8d3df',
                       highlightthickness=1,
                       padx=0, pady=0)
        tk.Frame(box, bg=accent, width=5).pack(side='left', fill='y')
        content = tk.Frame(box, background=bg, padx=8, pady=7)
        content.pack(side='left', fill='both', expand=True)
        top = tk.Frame(content, background=bg)
        top.pack(fill='x')
        tk.Label(top, text=icon, font=('Segoe UI Symbol', 22), bg=bg, fg=fg, width=3).pack(side='left')
        tk.Label(top, text=title, font=('Microsoft YaHei', 9, 'bold'), bg=bg, fg='#2d3748', anchor='w').pack(
            side='left', fill='x', expand=True)
        tk.Label(content, text=f'{value} {unit}'.strip(), font=('Microsoft YaHei', 15, 'bold'), bg=bg, fg=fg,
                 width=width, anchor='w').pack(anchor='w', pady=(2, 0))
        return box

    def _pump_state_icon(self, running, fault, maintenance, standby=False):
        if fault:
            return '⚠', self.dash_red if hasattr(self, 'dash_red') else '#d00000', '故障'
        if maintenance:
            return '⚒', self.dash_yellow if hasattr(self, 'dash_yellow') else '#d49b00', '检修'
        if running:
            return '▶', self.dash_green if hasattr(self, 'dash_green') else '#008000', '运行'
        return 'Ⅱ', self.dash_blue if hasattr(self, 'dash_blue') else '#1f77b4', '备用' if standby else '停止'

    def _mini_text(self, parent, text, fg='#333333'):
        tk.Label(parent, text=text, font=('Microsoft YaHei', 9), bg='white', fg=fg, anchor='w').pack(anchor='w',
                                                                                                     fill='x',
                                                                                                     pady=1)

    def _dashboard_level_values(self):
        """Return two level sensor values for the current station.
        Values come from actual Modbus point last_value when available;
        fallback to station current_level for display continuity.
        """
        vals = []
        try:
            sid = self.sid()
            rows = self.rows("""SELECT point_code, point_name, last_value
                                FROM modbus_point
                                WHERE station_id = ?
                                  AND enabled = 1
                                  AND (point_code LIKE '%LT%' OR point_name LIKE '%液位%')
                                ORDER BY id LIMIT 2""", (sid,))
            for r in rows:
                v = r['last_value']
                try:
                    vals.append(float(v))
                except Exception:
                    vals.append(None)
            if len(vals) < 2:
                st = self.row('SELECT current_level FROM pump_station WHERE id=?', (sid,))
                fallback = float(st['current_level'] or 0) if st else 0.0
                while len(vals) < 2:
                    vals.append(fallback if len(vals) == 0 else None)
        except Exception:
            vals = [None, None]
        return vals[:2]

    def _dash_float(self, value, default=0.0):
        try:
            if value is None or value == '':
                return default
            return float(value)
        except Exception:
            return default

    def _dash_update_kpi(self, key, value, unit='', color=None):
        item = getattr(self, 'dash_kpis', {}).get(key)
        if not item:
            return
        item['value'].config(text=str(value))
        item['unit'].config(text=(' ' + unit) if unit else '')
        if color:
            item['icon'].config(fg=color)
            item['value'].config(fg='#f4f8ff')

    def _dash_pump_state(self, p, standby=True):
        if not p:
            return 'Ⅱ', self.dash_blue, '备用'
        fault = bool(self.safe_get(p, 'fault_feedback', 0) or self.safe_get(p, 'manual_fault', 0))
        maint = bool(self.safe_get(p, 'maintenance', 0))
        running = bool(self.safe_get(p, 'run_feedback', 0))
        return self._pump_state_icon(running, fault, maint, standby=standby)

    def _dash_pump_code(self, p, prefix, index):
        try:
            code = self.safe_get(p, 'pump_code', None)
            return code or f'{prefix}{index}'
        except Exception:
            return f'{prefix}{index}'

    def _draw_level_gauge(self, panel, value, color):
        c = panel['gauge']
        c.delete('all')
        c.update_idletasks()
        w = max(int(c.winfo_width() or 78), 78)
        h = max(int(c.winfo_height() or 150), 150)
        x0, x1 = 18, w - 18
        y0, y1 = 10, h - 10
        c.create_rectangle(x0, y0 + 12, x1, y1 - 12, outline='#365c82', width=2, fill='#09233f')
        c.create_oval(x0, y0, x1, y0 + 24, outline='#577898', width=2, fill='#0b2b4d')
        c.create_oval(x0, y1 - 24, x1, y1, outline='#577898', width=2, fill='#071f3d')
        for i in range(1, 9):
            y = y0 + 16 + (y1 - y0 - 32) * i / 10
            c.create_line(x0 + 4, y, x0 + 14, y, fill='#7295b8')
        try:
            ratio = min(max(float(value or 0) / 10.0, 0.0), 1.0)
        except Exception:
            ratio = 0.0
        fy = y1 - 13 - (y1 - y0 - 30) * ratio
        c.create_rectangle(x0 + 4, fy, x1 - 4, y1 - 13, outline='', fill=color)
        c.create_oval(x0 + 4, fy - 9, x1 - 4, fy + 9, outline='', fill=color)
        c.create_line((x0 + x1) / 2, fy + 2, (x0 + x1) / 2, y0 + 12, fill='#b8fff5', width=2)

    def _draw_sparkline(self, canvas, base_value, color, second_value=None, second_color='#1e9bff'):
        canvas.delete('all')
        canvas.update_idletasks()
        w = max(int(canvas.winfo_width() or 180), 120)
        h = max(int(canvas.winfo_height() or 58), 48)
        left, right, top, bottom = 24, 6, 8, 16
        canvas.create_line(left, h - bottom, w - right, h - bottom, fill='#1d4569')
        canvas.create_line(left, top, left, h - bottom, fill='#1d4569')
        for k in range(3):
            y = top + k * (h - top - bottom) / 2
            canvas.create_line(left, y, w - right, y, fill='#12385a')

        def make_points(seed, scale):
            pts = []
            n = 28
            for i in range(n):
                x = left + (w - left - right) * i / (n - 1)
                v = 0.45 + ((i * 7 + seed) % 17) / 50.0 + ((i % 5) - 2) / 70.0
                y = h - bottom - min(max(v * scale, 0.05), 0.95) * (h - top - bottom)
                pts.extend([x, y])
            return pts

        canvas.create_line(*make_points(int((base_value or 0) * 10) % 17, 0.95), fill=color, width=2, smooth=True)
        if second_value is not None:
            canvas.create_line(*make_points(int((second_value or 0) * 11) % 19, 0.75), fill=second_color, width=2,
                               smooth=True)
        canvas.create_text(left, h - 4, text='09:24', fill='#9abde0', font=('Consolas', 7), anchor='sw')
        canvas.create_text(w // 2, h - 4, text='09:54', fill='#9abde0', font=('Consolas', 7), anchor='s')
        canvas.create_text(w - right, h - 4, text='10:24', fill='#9abde0', font=('Consolas', 7), anchor='se')

    def _draw_dash_chart(self, chart, series_list, ymax=None, labels=None):
        canvas = chart['canvas']
        canvas.delete('all')
        canvas.update_idletasks()
        w = max(int(canvas.winfo_width() or 210), 160)
        h = max(int(canvas.winfo_height() or 126), 100)
        left, right, top, bottom = 34, 8, 12, 22
        plot_w = w - left - right
        plot_h = h - top - bottom
        colors = ['#21e56d', '#1e9bff', '#9bd97b', '#ffc526']
        if ymax is None:
            ymax = 1.0
            for s in series_list:
                if s:
                    ymax = max(ymax, max(s))
            ymax = ymax * 1.2 if ymax > 0 else 1.0
        canvas.create_rectangle(0, 0, w, h, fill='#071f3d', outline='')
        for i in range(4):
            y = top + plot_h * i / 3
            canvas.create_line(left, y, w - right, y, fill='#12385a')
            val = ymax * (3 - i) / 3
            canvas.create_text(2, y, text=f'{val:.0f}' if ymax >= 10 else f'{val:.1f}', fill='#b8d5ef',
                               font=('Consolas', 8), anchor='w')
        canvas.create_line(left, top, left, top + plot_h, fill='#1d4569')
        canvas.create_line(left, top + plot_h, w - right, top + plot_h, fill='#1d4569')
        for idx, series in enumerate(series_list):
            if not series:
                continue
            pts = []
            n = len(series)
            for i, val in enumerate(series):
                x = left + plot_w * i / max(n - 1, 1)
                y = top + plot_h - min(max(val / ymax, 0), 1) * plot_h
                pts.extend([x, y])
            canvas.create_line(*pts, fill=colors[idx % len(colors)], width=2, smooth=True)
            if pts:
                canvas.create_oval(pts[-2] - 2, pts[-1] - 2, pts[-2] + 2, pts[-1] + 2,
                                   fill=colors[idx % len(colors)], outline='')
        now_dt = datetime.datetime.now()
        times = [(now_dt - datetime.timedelta(hours=6)).strftime('%H:%M'),
                 (now_dt - datetime.timedelta(hours=3)).strftime('%H:%M'),
                 now_dt.strftime('%H:%M')]
        canvas.create_text(left, h - 4, text=times[0], fill='#9abde0', font=('Consolas', 8), anchor='sw')
        canvas.create_text(left + plot_w / 2, h - 4, text=times[1], fill='#9abde0', font=('Consolas', 8),
                           anchor='s')
        canvas.create_text(w - right, h - 4, text=times[2], fill='#9abde0', font=('Consolas', 8), anchor='se')
        if labels:
            lx = max(left + 70, w - 92)
            for i, text in enumerate(labels[:2]):
                canvas.create_rectangle(lx, 2 + i * 13, lx + 8, 10 + i * 13, fill=colors[i % len(colors)],
                                        outline='')
                canvas.create_text(lx + 12, 7 + i * 13, text=text, fill='#c9e6ff', font=('Microsoft YaHei', 8),
                                   anchor='w')

    def _dash_series(self, base, count=32, spread=0.18, trend=0.0):
        base = max(float(base or 0), 0.01)
        arr = []
        sec = int(time.time()) // 5
        for i in range(count):
            wave = (((i * 7 + sec) % 19) - 9) / 9.0
            small = (((i * 5 + sec) % 11) - 5) / 18.0
            val = base * (1 + wave * spread + small * spread * 0.6) + base * trend * i / max(count - 1, 1)
            arr.append(max(val, 0.0))
        return arr

    def _draw_dashboard_twin(self, pumps, feed_pumps, pipes, lv1, lv2):
        c = self.dash_twin_canvas
        c.delete('all')
        c.update_idletasks()
        w = max(int(c.winfo_width() or 760), 650)
        h = max(int(c.winfo_height() or 360), 300)
        c.create_rectangle(0, 0, w, h, fill='#06172d', outline='')
        for i in range(10):
            y = i * h / 10
            c.create_line(0, y, w, y + 40, fill='#08294a')
        # 地面、集水池和控制柜
        c.create_polygon(0, h * 0.36, w * 0.24, h * 0.24, w * 0.28, h * 0.82, 0, h * 0.92,
                         fill='#08233f', outline='#0a5eaa')
        c.create_polygon(20, h * 0.45, w * 0.22, h * 0.34, w * 0.24, h * 0.69, 20, h * 0.78,
                         fill='#0b4d79', outline='#168ce4')
        c.create_text(w * 0.12, h * 0.39, text='集水池', fill='#c9e6ff', font=('Microsoft YaHei', 10, 'bold'))
        c.create_rectangle(w * 0.38, 12, w * 0.68, 62, fill='#1b2f43', outline='#586e7d')
        for i in range(9):
            x = w * 0.39 + i * (w * 0.27 / 9)
            c.create_rectangle(x, 18, x + w * 0.022, 58, fill='#31455a', outline='#7791aa')
            c.create_rectangle(x + 5, 28, x + w * 0.022 - 5, 37, fill='#76c7ff', outline='')
        c.create_text(w * 0.53, 72, text='母管（A1~P8）', fill='#e6f4ff', font=('Microsoft YaHei', 10, 'bold'))
        # 管道
        upper_y = h * 0.35
        lower_y = h * 0.67
        left_x = w * 0.22
        right_x = w * 0.90
        c.create_line(left_x, upper_y, right_x, upper_y, fill='#0c69b4', width=22, capstyle='round')
        c.create_line(left_x, upper_y, right_x, upper_y, fill='#23a8ff', width=8, capstyle='round')
        c.create_line(left_x * 0.82, lower_y, right_x, lower_y, fill='#0d7e4a', width=20, capstyle='round')
        c.create_line(left_x * 0.82, lower_y, right_x, lower_y, fill='#25e073', width=7, capstyle='round')
        c.create_line(right_x, upper_y, w - 35, upper_y + 34, fill='#0c69b4', width=22, capstyle='round')
        c.create_line(right_x, upper_y, w - 35, upper_y + 34, fill='#23a8ff', width=8, capstyle='round')
        c.create_line(right_x, lower_y, w - 35, lower_y, fill='#0d7e4a', width=20, capstyle='round')
        c.create_line(right_x, lower_y, w - 35, lower_y, fill='#25e073', width=7, capstyle='round')
        c.create_text(w - 58, upper_y + 28, text='出水方向', fill='#bfe8ff', font=('Microsoft YaHei', 9, 'bold'))
        c.create_polygon(w - 36, upper_y + 34, w - 58, upper_y + 20, w - 58, upper_y + 48, fill='#58bcff')
        c.create_polygon(w - 36, lower_y, w - 58, lower_y - 14, w - 58, lower_y + 14, fill='#5cff9c')
        # 传感器牌
        flow_a = self._dash_float(self.safe_get(pipes[0], 'estimated_running_flow', 13.62) if pipes else 13.62)
        press_a = self._dash_float(self.safe_get(pipes[0], 'pressure', 0.63) if pipes else 0.63)
        flow_b = self._dash_float(
            self.safe_get(pipes[1], 'estimated_running_flow', flow_a * 0.9) if len(pipes) > 1 else flow_a * 0.9)
        press_b = self._dash_float(self.safe_get(pipes[1], 'pressure', 0.58) if len(pipes) > 1 else 0.58)

        def tag(x, y, title, value, color):
            c.create_rectangle(x, y, x + 76, y + 42, fill='#08253f', outline=color, width=1)
            c.create_text(x + 6, y + 12, text=title, fill='#cfefff', font=('Consolas', 9, 'bold'), anchor='w')
            c.create_text(x + 6, y + 30, text=value, fill=color, font=('Consolas', 10, 'bold'), anchor='w')

        tag(w * 0.66, upper_y - 72, 'FT-A', f'{flow_a:.2f}m³/s', '#25e0ff')
        tag(w * 0.76, upper_y - 60, 'PT-A', f'{press_a:.2f}MPa', '#5cff9c')
        tag(w * 0.77, lower_y - 66, 'FT-B', f'{flow_b:.2f}m³/s', '#ffc526')
        tag(w * 0.88, lower_y - 60, 'PT-B', f'{press_b:.2f}MPa', '#5cff9c')
        tag(w * 0.24, upper_y - 78, 'LT01', f'{(lv1 or 0):.2f}m', '#58ff9d')
        tag(w * 0.13, lower_y - 88, 'LT02', f'{(lv2 or 0):.2f}m', '#4bb7ff')
        # 水泵
        pump_area_left = w * 0.25
        pump_area_right = w * 0.79
        gap = (pump_area_right - pump_area_left) / 7

        def draw_pump(x, y, code, icon, color, upper=True):
            c.create_line(x, y - 45 if upper else y - 36, x, upper_y if upper else lower_y,
                          fill='#8bc6e8' if upper else '#85f0a9', width=5)
            c.create_oval(x - 20, y - 18, x + 20, y + 18, fill='#1b354d', outline='#7da5c5', width=2)
            c.create_rectangle(x - 10, y - 26, x + 10, y - 14, fill='#2f4b65', outline='#8aaac6')
            c.create_oval(x - 25, y + 12, x + 25, y + 28, outline=color, width=4)
            c.create_text(x, y + 45, text=code, fill='#eaf6ff', font=('Consolas', 10, 'bold'))
            c.create_text(x, y + 24, text=icon, fill=color, font=('Microsoft YaHei', 13, 'bold'))

        for i in range(8):
            p = pumps[i] if i < len(pumps) else None
            icon, color, text = self._dash_pump_state(p, standby=True)
            code = self._dash_pump_code(p, 'P', i + 1)
            draw_pump(pump_area_left + i * gap, h * 0.50, code, icon, color, upper=True)
        c.create_text(w * 0.51, h * 0.58, text='母管（B路）', fill='#e6f4ff', font=('Microsoft YaHei', 10, 'bold'))
        for i in range(8):
            p = feed_pumps[i] if i < len(feed_pumps) else None
            icon, color, text = self._dash_pump_state(p, standby=True)
            code = self._dash_pump_code(p, 'JP', i + 1)
            draw_pump(pump_area_left - 45 + i * gap, h * 0.79, code, icon, color, upper=False)
        # 光效
        for x in range(int(left_x), int(right_x), 42):
            c.create_oval(x - 3, upper_y - 3, x + 3, upper_y + 3, fill='#7be6ff', outline='')
        for x in range(int(left_x * 0.82), int(right_x), 42):
            c.create_oval(x - 3, lower_y - 3, x + 3, lower_y + 3, fill='#7cff9f', outline='')

    def _build_status_cards(self, pumps, feed_pumps):
        for w in self.dash_status_body.winfo_children():
            w.destroy()

        def section(title, row):
            tk.Label(self.dash_status_body, text='▌' + title, font=('Microsoft YaHei', 10, 'bold'), bg='#071f3d',
                     fg='#dceeff', anchor='w').grid(row=row, column=0, columnspan=4, sticky='ew', padx=10,
                                                    pady=(6, 4))

        def card(p, prefix, idx, row, col):
            icon, color, text = self._dash_pump_state(p, standby=True)
            code = self._dash_pump_code(p, prefix, idx)
            bg = '#092e34' if text == '运行' else '#08284c' if text == '备用' else '#332d09' if text == '检修' else '#350b18'
            box = tk.Frame(self.dash_status_body, bg=bg, highlightbackground=color, highlightthickness=1)
            box.grid(row=row, column=col, sticky='nsew', padx=5, pady=4)
            top = tk.Frame(box, bg=bg)
            top.pack(fill='x', padx=8, pady=(7, 1))
            tk.Label(top, text=icon, font=('Microsoft YaHei', 12, 'bold'), bg=bg, fg=color).pack(side='left')
            tk.Label(top, text=code, font=('Consolas', 11, 'bold'), bg=bg, fg='#eaf6ff').pack(side='left',
                                                                                              padx=(5, 0))
            tk.Label(box, text=text, font=('Microsoft YaHei', 10, 'bold'), bg=bg, fg=color).pack(pady=(0, 8))

        for col in range(4):
            self.dash_status_body.grid_columnconfigure(col, weight=1, uniform='status')
        section('主泵（P1~P8）', 0)
        for i in range(8):
            card(pumps[i] if i < len(pumps) else None, 'P', i + 1, 1 + i // 4, i % 4)
        tk.Frame(self.dash_status_body, bg='#12385a', height=1).grid(row=3, column=0, columnspan=4, sticky='ew',
                                                                     padx=10, pady=4)
        section('补水泵（JP1~JP8）', 4)
        for i in range(8):
            card(feed_pumps[i] if i < len(feed_pumps) else None, 'JP', i + 1, 5 + i // 4, i % 4)
        legend = tk.Frame(self.dash_status_body, bg='#071f3d')
        legend.grid(row=7, column=0, columnspan=4, sticky='ew', padx=10, pady=(8, 4))
        for text, color in [('运行', self.dash_green), ('备用', self.dash_blue), ('检修', self.dash_yellow),
                            ('故障', self.dash_red), ('停止', '#95a3b3')]:
            tk.Label(legend, text='●', font=('Microsoft YaHei', 10, 'bold'), bg='#071f3d', fg=color).pack(
                side='left', padx=(0, 3))
            tk.Label(legend, text=text, font=('Microsoft YaHei', 8), bg='#071f3d', fg='#dceeff').pack(side='left',
                                                                                                      padx=(0, 12))

    def _build_event_list(self, summary, pumps, pipes):
        for w in self.dash_event_body.winfo_children():
            w.destroy()
        events = []
        t = datetime.datetime.now().strftime('%H:%M:%S')
        if summary.get('fault', 0):
            events.append(('✚', 'P3 故障停机', '主泵存在故障保护动作', t, self.dash_red))
        if summary.get('maintenance', 0):
            events.append(('ℹ', 'P6 检修模式', '主泵处于检修状态', t, self.dash_blue))
        if summary.get('comm_offline', 0):
            events.append(
                ('⚠', '通讯异常', f"{summary.get('comm_offline', 0)} 台设备通讯异常", t, self.dash_yellow))
        else:
            events.append(('●', '通讯在线', '所有设备通讯正常', t, self.dash_green))
        if pipes:
            flow = self._dash_float(self.safe_get(pipes[-1], 'estimated_running_flow', 0))
            if flow > 0:
                events.append(('⚠', '母管B流量偏低', f'FT-B 流量 {flow:.2f} m³/s，低于设定值', t, self.dash_yellow))
        events.insert(0, ('●', '正常', '系统运行正常', t, self.dash_green))
        # 追加最近操作日志，最多补足 5 条。
        try:
            rows = self.rows("""SELECT operation_time, operation_type, object_name, result, remark
                                FROM operation_log
                                ORDER BY id DESC LIMIT 3""")
            for r in rows:
                ot = str(self.safe_get(r, 'operation_time', '') or '')[-8:] or t
                title = str(self.safe_get(r, 'operation_type', '操作事件') or '操作事件')
                desc = str(self.safe_get(r, 'object_name', '') or self.safe_get(r, 'remark', '') or '现场操作记录')
                events.append(('ℹ', title, desc, ot, self.dash_blue))
        except Exception:
            pass
        for icon, title, desc, tm, color in events[:5]:
            row = tk.Frame(self.dash_event_body, bg='#071f3d')
            row.pack(fill='x', padx=10, pady=4)
            tk.Label(row, text=icon, font=('Microsoft YaHei', 11, 'bold'), bg='#071f3d', fg=color, width=3).pack(
                side='left')
            txt = tk.Frame(row, bg='#071f3d')
            txt.pack(side='left', fill='x', expand=True)
            tk.Label(txt, text=title, font=('Microsoft YaHei', 9, 'bold'), bg='#071f3d', fg=color, anchor='w').pack(
                fill='x')
            tk.Label(txt, text=desc, font=('Microsoft YaHei', 8), bg='#071f3d', fg='#c3d9ef', anchor='w').pack(
                fill='x')
            tk.Label(row, text=tm, font=('Consolas', 9), bg='#071f3d', fg='#c3d9ef').pack(side='right')

    def refresh_dashboard(self):
        if not hasattr(self, 'dash_container'):
            return
        try:
            s = self.db.dashboard_summary()
        except Exception:
            s = {'station_count': 0, 'pump_count': 0, 'running': 0, 'standby': 0, 'fault': 0, 'maintenance': 0,
                 'total_current': 0, 'total_voltage': 0, 'total_power': 0, 'total_flow': 0, 'day_flow': 0,
                 'day_energy': 0, 'comm_online': 0, 'comm_offline': 0, 'comm_total': 0}
        dt = datetime.datetime.now()
        week_map = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        self.dash_datetime_lbl.config(text=dt.strftime('%Y-%m-%d   %H:%M:%S'))
        self.dash_week_lbl.config(text=week_map[dt.weekday()])
        heartbeat = getattr(getattr(self, 'service', None), 'heartbeat', 0)
        self.dash_backend_lbl.config(text=f'后端服务：● 正常', fg=self.dash_green)
        ok = (s.get('fault', 0) == 0 and s.get('comm_offline', 0) == 0)
        self.dash_total_status_lbl.config(text='总状态：● 正常' if ok else '总状态：● 异常',
                                          fg=self.dash_green if ok else self.dash_red)

        st = self.get_station()
        if st:
            self.dash_station_lbl.config(text=f"{st['station_code']}  {st['station_name']}")
        else:
            self.dash_station_lbl.config(text='暂无泵站')

        self._dash_update_kpi('running', s.get('running', 0), '台', self.dash_green)
        self._dash_update_kpi('standby', s.get('standby', 0), '台', self.dash_blue)
        self._dash_update_kpi('fault', s.get('fault', 0), '台', self.dash_red)
        self._dash_update_kpi('maintenance', s.get('maintenance', 0), '台', self.dash_yellow)
        self._dash_update_kpi('current', f"{self._dash_float(s.get('total_current')):.1f}", 'A', self.dash_blue)
        self._dash_update_kpi('voltage', f"{self._dash_float(s.get('total_voltage')) / 1000:.2f}", 'kV',
                              self.dash_blue)
        self._dash_update_kpi('power', f"{self._dash_float(s.get('total_power')) / 1000:.2f}", 'MW', self.dash_blue)
        self._dash_update_kpi('flow', f"{self._dash_float(s.get('total_flow')):.2f}", 'm³/s', self.dash_blue)
        self._dash_update_kpi('day_flow', f"{self._dash_float(s.get('day_flow')):,.0f}", 'm³', self.dash_blue)
        self._dash_update_kpi('day_energy', f"{self._dash_float(s.get('day_energy')):,.0f}", 'kWh', self.dash_blue)

        lv1, lv2 = self._dashboard_level_values()
        for key, value, color in [('lt1', lv1, self.dash_green), ('lt2', lv2, self.dash_blue)]:
            panel = self.dash_levels[key]
            if value is None:
                panel['value'].config(text='-')
                v = 0.0
            else:
                v = self._dash_float(value)
                panel['value'].config(text=f'{v:.2f}')
            self._draw_level_gauge(panel, v, color)
            self._draw_sparkline(panel['spark'], v, color)

        sid = self.sid()
        pumps = []
        feed_pumps = []
        pipes = []
        if sid:
            try:
                pumps = list(self.rows(
                    "SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id",
                    (sid,)))
                feed_pumps = list(self.rows(
                    "SELECT * FROM pump WHERE station_id=? AND pump_type='feed' ORDER BY display_order,id", (sid,)))
                pipes = list(
                    self.rows("SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id", (sid,)))
            except Exception:
                pumps, feed_pumps, pipes = [], [], []
        self._draw_dashboard_twin(pumps, feed_pumps, pipes, lv1 or 0, lv2 or 0)
        self._build_status_cards(pumps, feed_pumps)

        total_flow = self._dash_float(s.get('total_flow'))
        total_power = self._dash_float(s.get('total_power')) / 1000.0
        day_energy = self._dash_float(s.get('day_energy'))
        press1 = self._dash_float(self.safe_get(pipes[0], 'pressure', 0.6) if pipes else 0.6)
        press2 = self._dash_float(self.safe_get(pipes[1], 'pressure', 0.5) if len(pipes) > 1 else press1 * 0.9)
        self._draw_dash_chart(self.dash_charts['level'],
                              [self._dash_series(lv1 or 0.1, spread=0.10),
                               self._dash_series(lv2 or 0.1, spread=0.12)],
                              ymax=6, labels=['LT01', 'LT02'])
        self._draw_dash_chart(self.dash_charts['flow'],
                              [self._dash_series(total_flow or 1, spread=0.16),
                               self._dash_series((total_flow or 1) * 0.48, spread=0.18)],
                              ymax=max(total_flow * 1.5, 30), labels=['FT-A', 'FT-B'])
        self._draw_dash_chart(self.dash_charts['pressure'],
                              [self._dash_series(press1, spread=0.12), self._dash_series(press2, spread=0.12)],
                              ymax=max(press1, press2, 1.5), labels=['PT-A', 'PT-B'])
        self._draw_dash_chart(self.dash_charts['power'],
                              [self._dash_series(total_power or 0.1, spread=0.18, trend=0.15)],
                              ymax=max(total_power * 1.6, 15), labels=['总功率'])
        energy_line = [max(day_energy, 1) * (i + 1) / 32 for i in range(32)]
        self._draw_dash_chart(self.dash_charts['energy'], [energy_line], ymax=max(day_energy * 1.2, 60000),
                              labels=['累计电量'])
        self._build_event_list(s, pumps, pipes)

    def _dashboard_open_station(self, sid):
        self.db.set_current_station(sid)
        self.current_station_id = sid
        self.refresh_all()
        self.nb.select(self.pages['泵站监控'])

    # Monitor
    def build_monitor(self):
        f = self.pages['泵站监控']
        self.monitor_top = ttk.Label(f, text='', font=('Microsoft YaHei', 12, 'bold'))
        self.monitor_top.pack(anchor='w', padx=8, pady=6)
        status_bar = ttk.Frame(f);
        status_bar.pack(fill='x', padx=8, pady=(0, 4))
        self.monitor_mode_lbl = ttk.Label(status_bar, text='运行状态：-', font=('Microsoft YaHei', 11, 'bold'),
                                          foreground='blue')
        self.monitor_mode_lbl.pack(side='left', padx=(0, 20))
        self.monitor_count_lbl = ttk.Label(status_bar, text='水泵：-', font=('Microsoft YaHei', 10, 'bold'))
        self.monitor_count_lbl.pack(side='left')

        self.monitor_nb = ttk.Notebook(f)
        self.monitor_nb.pack(fill='both', expand=True, padx=8, pady=6)
        overview = ttk.Frame(self.monitor_nb)
        pump_page = ttk.Frame(self.monitor_nb)
        pipe_page = ttk.Frame(self.monitor_nb)
        self.monitor_nb.add(overview, text='运行总览')
        self.monitor_nb.add(pump_page, text='水泵监测')
        self.monitor_nb.add(pipe_page, text='母管监测')

        diag = ttk.Frame(overview)
        diag.pack(fill='x', padx=8, pady=(6, 4))
        status_box = ttk.LabelFrame(diag, text='控制状态 / 事件状态')
        status_box.pack(side='left', fill='both', expand=True, padx=(0, 6))
        self.ctrl_state_lbl = ttk.Label(status_box, text='控制状态：-', font=('Microsoft YaHei', 11, 'bold'),
                                        foreground='#1f4e79')
        self.ctrl_state_lbl.grid(row=0, column=0, sticky='w', padx=8, pady=(6, 2))
        self.ctrl_event_lbl = ttk.Label(status_box, text='当前事件：-', font=('Microsoft YaHei', 10, 'bold'))
        self.ctrl_event_lbl.grid(row=0, column=1, sticky='w', padx=8, pady=(6, 2))
        self.ctrl_action_lbl = ttk.Label(status_box, text='当前动作：-', font=('Microsoft YaHei', 10))
        self.ctrl_action_lbl.grid(row=1, column=0, sticky='w', padx=8, pady=2)
        self.ctrl_next_lbl = ttk.Label(status_box, text='下一步：-', font=('Microsoft YaHei', 10))
        self.ctrl_next_lbl.grid(row=1, column=1, sticky='w', padx=8, pady=2)
        self.ctrl_reason_lbl = ttk.Label(status_box, text='判断说明：-', font=('Microsoft YaHei', 9), wraplength=620,
                                         justify='left', foreground='#334155')
        self.ctrl_reason_lbl.grid(row=2, column=0, columnspan=2, sticky='w', padx=8, pady=(2, 6))
        status_box.grid_columnconfigure(0, weight=1);
        status_box.grid_columnconfigure(1, weight=1)

        event_box = ttk.LabelFrame(diag, text='最近控制事件')
        event_box.pack(side='right', fill='both', padx=(6, 0))
        evcols = ('时间', '事件', '动作', '设备')
        self.control_event_tree = ttk.Treeview(event_box, columns=evcols, show='headings', height=5)
        widths = {'时间': 90, '事件': 110, '动作': 110, '设备': 80}
        for c in evcols:
            self.control_event_tree.heading(c, text=c);
            self.control_event_tree.column(c, width=widths.get(c, 100), anchor='center')
        self.control_event_tree.pack(fill='both', expand=True, padx=4, pady=4)

        card_wrap = ttk.LabelFrame(overview, text='主排水泵运行状态总览（紧凑卡片，可滚动查看全部主泵）')
        card_wrap.pack(fill='both', expand=True, padx=8, pady=(4, 6))
        self.monitor_card_canvas = tk.Canvas(card_wrap, height=520, highlightthickness=0, bg='#eef3f8')
        self.monitor_card_vbar = ttk.Scrollbar(card_wrap, orient='vertical', command=self.monitor_card_canvas.yview)
        self.monitor_card_hbar = ttk.Scrollbar(card_wrap, orient='horizontal', command=self.monitor_card_canvas.xview)
        self.monitor_card_frame = tk.Frame(self.monitor_card_canvas, bg='#f4f7fb')
        self.monitor_card_window = self.monitor_card_canvas.create_window((0, 0), window=self.monitor_card_frame,
                                                                          anchor='nw')
        self.monitor_card_canvas.configure(xscrollcommand=self.monitor_card_hbar.set,
                                           yscrollcommand=self.monitor_card_vbar.set)
        self.monitor_card_frame.bind('<Configure>', lambda e: self.monitor_card_canvas.configure(
            scrollregion=self.monitor_card_canvas.bbox('all')))
        self.monitor_card_canvas.pack(side='left', fill='both', expand=True, padx=(4, 0), pady=(4, 0))
        self.monitor_card_vbar.pack(side='right', fill='y', pady=(4, 0))
        self.monitor_card_hbar.pack(fill='x', padx=4, pady=(0, 4))

        def _on_card_mousewheel(event):
            try:
                delta = -1 if event.delta > 0 else 1
                self.monitor_card_canvas.yview_scroll(delta, 'units')
            except Exception:
                pass

        self.monitor_card_canvas.bind('<MouseWheel>', _on_card_mousewheel)
        self.monitor_card_frame.bind('<MouseWheel>', _on_card_mousewheel)

        ttk.Label(pump_page, text='水泵监测明细（包含主泵和给水泵，可用于核对实时参数）', foreground='#1f3b5f',
                  font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', padx=8, pady=(8, 2))
        cols = ('编号', '名称', '类型', '状态', '当前角色', '运行', '故障', '检修', '备用', '设定Hz', '运行Hz', '电流A',
                '电压V', '当次运行', '累计运行')
        pump_box = ttk.Frame(pump_page);
        pump_box.pack(fill='both', expand=True, padx=8, pady=4)
        self.monitor_pumps = ttk.Treeview(pump_box, columns=cols, show='headings', height=22)
        for c in cols:
            self.monitor_pumps.heading(c, text=c);
            self.monitor_pumps.column(c, width=110 if c == '当前角色' else (95 if c != '名称' else 180),
                                      anchor='center')
        pump_y = ttk.Scrollbar(pump_box, orient='vertical', command=self.monitor_pumps.yview)
        pump_x = ttk.Scrollbar(pump_page, orient='horizontal', command=self.monitor_pumps.xview)
        self.monitor_pumps.configure(yscrollcommand=pump_y.set, xscrollcommand=pump_x.set)
        self.monitor_pumps.pack(side='left', fill='both', expand=True);
        pump_y.pack(side='right', fill='y')
        pump_x.pack(fill='x', padx=8)

        ttk.Label(pipe_page, text='母管监测明细（流量、压力、流速、管径校核和接入主泵）', foreground='#1f3b5f',
                  font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', padx=8, pady=(8, 2))
        pcols = ('编号', '名称', 'DN', '理论流量', '估算流量', '流速', '校核', '接入水泵')
        pipe_box = ttk.Frame(pipe_page);
        pipe_box.pack(fill='both', expand=True, padx=8, pady=4)
        self.monitor_pipes = ttk.Treeview(pipe_box, columns=pcols, show='headings', height=22)
        for c in pcols:
            self.monitor_pipes.heading(c, text=c);
            self.monitor_pipes.column(c, width=130 if c != '接入水泵' else 320, anchor='center')
        pipe_y = ttk.Scrollbar(pipe_box, orient='vertical', command=self.monitor_pipes.yview)
        pipe_x = ttk.Scrollbar(pipe_page, orient='horizontal', command=self.monitor_pipes.xview)
        self.monitor_pipes.configure(yscrollcommand=pipe_y.set, xscrollcommand=pipe_x.set)
        self.monitor_pipes.pack(side='left', fill='both', expand=True);
        pipe_y.pack(side='right', fill='y')
        pipe_x.pack(fill='x', padx=8)

    def rebuild_monitor_pump_cards(self, pumps):
        if not hasattr(self, 'monitor_card_frame'):
            return
        for w in self.monitor_card_frame.winfo_children():
            w.destroy()
        self.monitor_pump_cards = {}
        try:
            canvas_w = max(int(self.monitor_card_canvas.winfo_width() or 1200), 900)
        except Exception:
            canvas_w = 1200
        card_w = 260
        cols = max(2, min(6, canvas_w // card_w))
        for idx, p in enumerate(pumps):
            r, c = divmod(idx, cols)
            frame = tk.Frame(self.monitor_card_frame, bg='white', highlightbackground='#cbd5e1', highlightthickness=1,
                             padx=6, pady=5)
            frame.grid(row=r, column=c, padx=5, pady=5, sticky='nsew')
            lamp = tk.Label(frame, text='●', font=('Microsoft YaHei', 18, 'bold'), bg='white', fg='#9ca3af', width=2)
            lamp.grid(row=0, column=0, rowspan=2, padx=(0, 4), sticky='n')
            title_text = f"{p['pump_code']}  {p['pump_name']}"
            if len(title_text) > 18:
                title_text = title_text[:18] + '…'
            title = tk.Label(frame, text=title_text, font=('Microsoft YaHei', 10, 'bold'), bg='white', fg='#111827')
            title.grid(row=0, column=1, columnspan=3, sticky='w')
            state = tk.Label(frame, text='停止', font=('Microsoft YaHei', 9, 'bold'), bg='white', fg='#374151')
            state.grid(row=1, column=1, columnspan=3, sticky='w')
            data = {}
            labels = [('current', '电流'), ('set_freq', '设定'), ('run_freq', '运行'), ('this_run', '本次'),
                      ('total_run', '累计')]
            for i, (key, label) in enumerate(labels):
                rr = 2 + i // 2;
                cc = (i % 2) * 2
                tk.Label(frame, text=label + '：', font=('Microsoft YaHei', 8), bg='white', fg='#64748b').grid(row=rr,
                                                                                                              column=cc,
                                                                                                              sticky='e',
                                                                                                              padx=(0,
                                                                                                                    2),
                                                                                                              pady=1)
                v = tk.Label(frame, text='-', font=('Consolas', 9, 'bold'), bg='white', fg='#0f172a', width=8,
                             anchor='w')
                v.grid(row=rr, column=cc + 1, sticky='w', pady=1)
                data[key] = v
            self.monitor_pump_cards[p['id']] = {'frame': frame, 'lamp': lamp, 'state': state, 'data': data,
                                                'title': title}
        for cc in range(cols):
            self.monitor_card_frame.grid_columnconfigure(cc, weight=1, minsize=card_w)

    def update_monitor_pump_cards(self, pumps):
        sig = tuple((p['id'], p['pump_code'], p['pump_name']) for p in pumps)
        if sig != getattr(self, 'monitor_card_signature', None):
            self.monitor_card_signature = sig
            self.rebuild_monitor_pump_cards(pumps)
        for p in pumps:
            card = self.monitor_pump_cards.get(p['id'])
            if not card:
                continue
            symbol, color, text = self.pump_lamp(p)
            card['lamp'].config(text=symbol, fg=color)
            card['state'].config(text=text, fg=color if text != '停止' else '#6b7280')
            card['data']['current'].config(text=f"{float(p['current'] or 0):.1f} A")
            card['data']['set_freq'].config(text=f"{float(p['set_frequency'] or 0):.1f} Hz")
            card['data']['run_freq'].config(text=f"{float(p['frequency'] or 0):.1f} Hz")
            card['data']['this_run'].config(text=self.fmt_seconds(self.pump_this_run_seconds(p)))
            card['data']['total_run'].config(text=self.fmt_seconds(self.pump_total_run_seconds(p)))

    def refresh_monitor(self):
        st = self.get_station();
        if not st:
            self.clear_tree(self.monitor_pumps);
            self.clear_tree(self.monitor_pipes)
            self.monitor_top.config(text='当前没有泵站，请先在“泵站管理”中新建泵站。')
            if hasattr(self, 'monitor_mode_lbl'): self.monitor_mode_lbl.config(text='运行状态：-')
            if hasattr(self, 'monitor_count_lbl'): self.monitor_count_lbl.config(text='水泵：-')
            if hasattr(self, 'ctrl_state_lbl'):
                self.ctrl_state_lbl.config(text='控制状态：-')
                self.ctrl_event_lbl.config(text='当前事件：-')
                self.ctrl_action_lbl.config(text='当前动作：-')
                self.ctrl_next_lbl.config(text='下一步：-')
                self.ctrl_reason_lbl.config(text='判断说明：-')
                if hasattr(self, 'control_event_tree'): self.clear_tree(self.control_event_tree)
            if hasattr(self, 'monitor_card_frame'):
                for w in self.monitor_card_frame.winfo_children(): w.destroy()
                self.monitor_pump_cards = {};
                self.monitor_card_signature = None
            return
        mode_text = MODE_LABEL.get(st['control_mode'], st['control_mode'])
        pumps = self.rows('SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id', (self.sid(),))
        main_pumps = [p for p in pumps if p['pump_type'] != 'feed']
        pump_total = len(pumps)
        main_total = len(main_pumps)
        running_total = sum(1 for p in main_pumps if p['run_feedback'])
        current_level = float(st['current_level'] or 0)
        current_rate = float(st['level_rise_rate'] or 0)
        self.monitor_top.config(
            text=f"当前监控泵站：{st['station_code']} {st['station_name']} | 液位 {current_level:.2f} m | 液位速率 {current_rate:+.3f} m/min")
        self.monitor_mode_lbl.config(
            text=f"运行状态：{mode_text}    数据源：{DATA_MODE_LABEL.get(st['data_source_mode'], st['data_source_mode'] if 'data_source_mode' in st.keys() else '模拟')}    自动调节状态：{st['emergency_level']}")
        self.monitor_count_lbl.config(text=f"水泵总数：{pump_total}，主排水泵：{main_total}，运行中：{running_total}")

        ctrl_state = self.row('SELECT * FROM station_control_state WHERE station_id=?', (self.sid(),))
        if hasattr(self, 'ctrl_state_lbl'):
            if ctrl_state:
                cs = ctrl_state['control_state'] or '-'
                es = ctrl_state['event_state'] or '-'
                act = ctrl_state['current_action'] or '-'
                nxt = ctrl_state['next_action'] or '-'
                reason = ctrl_state['reason_text'] or '-'
                # 如果刚从手动切到自动，后台下一轮自动控制尚未写入状态，界面先按泵站实时模式显示，避免仍显示“手动”。
                try:
                    if (ctrl_state['control_mode'] or '') != (st['control_mode'] or ''):
                        if st['control_mode'] == 'auto':
                            cs = '自动模式';
                            es = '自动平衡待命';
                            act = '等待自动控制刷新';
                            nxt = '后台控制循环即将接管';
                            reason = '已切换为自动模式，等待自动平衡控制投入'
                        else:
                            cs = '手动模式';
                            es = '手动待命';
                            act = '无自动动作';
                            nxt = '等待人工操作或切换自动';
                            reason = '手动模式，自动控制未投入'
                except Exception:
                    pass
                update_time = str(ctrl_state['updated_at'] or '')[11:19] if ctrl_state['updated_at'] else '-'
                self.ctrl_state_lbl.config(
                    text=f"控制状态：{cs}  |  液位 {current_level:.2f}m  |  速率 {current_rate:+.3f}m/min")
                self.ctrl_event_lbl.config(text=f"当前事件：{es}")
                self.ctrl_action_lbl.config(text=f"当前动作：{act}    更新时间：{update_time}")
                self.ctrl_next_lbl.config(text=f"下一步：{nxt}")
                self.ctrl_reason_lbl.config(text=f"判断说明：{reason}")
            else:
                self.ctrl_state_lbl.config(text='控制状态：暂无自动控制状态')
                self.ctrl_event_lbl.config(text='当前事件：-')
                self.ctrl_action_lbl.config(text='当前动作：-')
                self.ctrl_next_lbl.config(text='下一步：-')
                self.ctrl_reason_lbl.config(text='判断说明：等待后台控制循环刷新')
            if hasattr(self, 'control_event_tree'):
                existing = set(self.control_event_tree.get_children(''))
                wanted = []
                for ev in self.rows('SELECT * FROM station_control_event WHERE station_id=? ORDER BY id DESC LIMIT 8',
                                    (self.sid(),)):
                    iid = 'ev_' + str(ev['id']);
                    wanted.append(iid)
                    t = str(ev['event_time'] or '')[11:19] if ev['event_time'] else ''
                    vals = (t, ev['event_type'] or '', ev['action_type'] or '', ev['target_device'] or '')
                    if iid in existing:
                        if tuple(map(str, self.control_event_tree.item(iid, 'values'))) != tuple(map(str, vals)):
                            self.control_event_tree.item(iid, values=vals)
                    else:
                        self.control_event_tree.insert('', 'end', iid=iid, values=vals)
                for iid in existing - set(wanted):
                    self.control_event_tree.delete(iid)
        self.update_monitor_pump_cards(main_pumps)
        self.monitor_pumps.tag_configure('running', foreground='green')
        self.monitor_pumps.tag_configure('stopped', foreground='gray')
        self.monitor_pumps.tag_configure('fault', foreground='red')
        self.monitor_pumps.tag_configure('maintenance', foreground='#b8860b')
        self.monitor_pumps.tag_configure('standby', foreground='blue')
        existing = set(self.monitor_pumps.get_children(''))
        wanted = []
        for p in pumps:
            state = self.pump_state_icon_text(p)
            tag = self.pump_state_tag(p)
            run_text = '是' if p['run_feedback'] else '否'
            iid = str(p['id'])
            wanted.append(iid)
            role = self.pump_control_role(p, ctrl_state['control_state'] if ctrl_state else '')
            values = (p['pump_code'], p['pump_name'], PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type']), state, role,
                      run_text, '是' if p['fault_feedback'] or p['manual_fault'] else '否',
                      '是' if p['maintenance'] else '否', '是' if p['standby'] else '否',
                      f"{float(p['set_frequency'] or 0):.1f}", f"{float(p['frequency'] or 0):.1f}",
                      f"{float(p['current'] or 0):.1f}", f"{float(p['voltage'] or 0):.0f}",
                      self.fmt_seconds(self.pump_this_run_seconds(p)), self.fmt_seconds(self.pump_total_run_seconds(p)))
            if iid in existing:
                if tuple(map(str, self.monitor_pumps.item(iid, 'values'))) != tuple(map(str, values)):
                    self.monitor_pumps.item(iid, values=values, tags=(tag,))
            else:
                self.monitor_pumps.insert('', 'end', iid=iid, values=values, tags=(tag,))
        for iid in existing - set(wanted):
            self.monitor_pumps.delete(iid)

        existing = set(self.monitor_pipes.get_children(''))
        wanted = []
        for pipe in self.rows('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (self.sid(),)):
            rels = self.rows("""SELECT p.pump_code
                                FROM pump p
                                         JOIN pump_pipe_relation r ON r.pump_id = p.id
                                WHERE r.pipe_id = ?
                                  AND r.enabled = 1
                                  AND p.pump_type!='feed'
                                ORDER BY p.display_order, p.id""", (pipe['id'],))
            pump_codes = ','.join([r['pump_code'] for r in rels]) or '-'
            iid = 'pipe_' + str(pipe['id'])
            wanted.append(iid)
            values = (pipe['pipe_code'], pipe['pipe_name'], pipe['standard_dn'], f"{pipe['theoretical_flow']:.1f}",
                      f"{pipe['estimated_running_flow']:.1f}", f"{pipe['estimated_velocity']:.2f}",
                      pipe['diameter_check_status'], pump_codes)
            if iid in existing:
                if tuple(map(str, self.monitor_pipes.item(iid, 'values'))) != tuple(map(str, values)):
                    self.monitor_pipes.item(iid, values=values)
            else:
                self.monitor_pipes.insert('', 'end', iid=iid, values=values)
        for iid in existing - set(wanted):
            self.monitor_pipes.delete(iid)

    # Station page
    def build_station_page(self):
        f = self.pages['泵站管理'];
        left = ttk.Frame(f);
        left.pack(side='left', fill='both', expand=True, padx=8, pady=8);
        right = ttk.LabelFrame(f, text='新增 / 编辑泵站');
        right.pack(side='right', fill='y', padx=8, pady=8)
        cols = ('ID', '编号', '名称', '类型', '启用', '数据源', '模式', '水泵数', '母管数')
        self.station_tree = ttk.Treeview(left, columns=cols, show='headings', height=20)
        for c in cols: self.station_tree.heading(c, text=c); self.station_tree.column(c, width=90, anchor='center')
        self.station_tree.pack(fill='both', expand=True)
        self.station_tree.bind('<<TreeviewSelect>>', self.on_station_select)
        ttk.Button(left, text='切换到选中泵站', command=self.switch_station).pack(side='left', padx=5, pady=5);
        ttk.Button(left, text='刷新', command=self.refresh_station_list).pack(side='left')
        self.st_vars = {}
        fields = [('station_code', '泵站编号'), ('station_name', '泵站名称'), ('station_type', '泵站类型'),
                  ('enabled', '是否启用'), ('data_source_mode', '系统数据'), ('pump_count', '主排水泵数量'),
                  ('pipe_count', '母管数量'), ('default_pump_type', '默认水泵类型'),
                  ('default_rated_flow', '默认流量m³/h'), ('default_rated_head', '默认扬程m'),
                  ('default_rated_power', '默认功率kW'), ('default_rated_current', '默认电流A'),
                  ('level_sensor_count', '液位计数量'), ('min_running_count', '最小运行台数'),
                  ('max_running_count', '最大运行台数'), ('emergency_max_running_count', '应急最大台数'),
                  ('remark', '备注')]
        self.station_edit_label = ttk.Label(right, text='当前：新增泵站', foreground='blue');
        self.station_edit_label.grid(row=0, column=0, columnspan=2, sticky='w', padx=6, pady=4)
        ttk.Label(right, text='提示：此处一次性生成主泵、给水泵、母管和仪表；模式请到“手动控制”切换。',
                  foreground='blue').grid(row=1, column=0, columnspan=2, sticky='w', padx=6, pady=3)
        for i, (key, label) in enumerate(fields, 2):
            ttk.Label(right, text=label).grid(row=i, column=0, sticky='e', padx=4, pady=3)
            if key == 'station_type':
                w = ttk.Combobox(right, values=STATION_TYPES, width=24)
            elif key == 'default_pump_type':
                w = ttk.Combobox(right, values=['潜污泵', '多级离心泵', '给水泵'], width=24, state='normal')
            elif key == 'data_source_mode':
                w = ttk.Combobox(right, values=['模拟', '实时采集'], width=24, state='readonly')
            elif key == 'control_mode':
                w = ttk.Combobox(right, values=[x[0] for x in CONTROL_MODES], width=24)
            else:
                w = ttk.Entry(right, width=27)
            w.grid(row=i, column=1, padx=4, pady=3);
            self.st_vars[key] = w
        btn = ttk.Frame(right);
        btn.grid(row=len(fields) + 3, column=0, columnspan=2, pady=8)
        ttk.Button(btn, text='新增泵站', command=self.add_station).pack(side='left', padx=4);
        ttk.Button(btn, text='保存修改', command=self.save_station).pack(side='left', padx=4);
        ttk.Button(btn, text='删除泵站', command=self.delete_station).pack(side='left', padx=4);
        ttk.Button(btn, text='清空表单', command=self.clear_station_form).pack(side='left', padx=4)

    def refresh_station_list(self):
        self.clear_tree(self.station_tree)
        cur = self.sid()
        for r in self.rows('SELECT * FROM pump_station ORDER BY id'):
            name = r['station_name'] + (' ★当前' if r['id'] == cur else '')
            self.station_tree.insert('', 'end', iid=str(r['id']),
                                     values=(r['id'], r['station_code'], name, r['station_type'],
                                             '是' if r['enabled'] else '否', DATA_MODE_LABEL.get(r['data_source_mode'],
                                                                                                 r[
                                                                                                     'data_source_mode'] if 'data_source_mode' in r.keys() else '模拟'),
                                             MODE_LABEL.get(r['control_mode'], r['control_mode']), r['pump_count'],
                                             r['pipe_count']))
        try:
            if cur:
                self.station_tree.selection_set(str(cur));
                self.station_tree.see(str(cur))
        except Exception:
            pass
        if not self.edit_station_id: self.clear_station_form()

    def clear_station_form(self):
        self.edit_station_id = None;
        self.station_edit_label.config(text='当前：新增泵站')
        vals = {'station_code': self.db.next_station_code(), 'station_name': '新建泵站', 'station_type': '隧道排水',
                'enabled': '1', 'data_source_mode': '模拟', 'pump_count': '4', 'pipe_count': '1',
                'default_pump_type': '潜污泵', 'default_rated_flow': '300', 'default_rated_head': '60',
                'default_rated_power': '55', 'default_rated_current': '100', 'level_sensor_count': '2',
                'min_running_count': '1', 'max_running_count': '3', 'emergency_max_running_count': '3', 'remark': ''}
        for k, w in self.st_vars.items(): w.delete(0, 'end'); w.insert(0, vals.get(k, ''))

    def on_station_select(self, e=None):
        sel = self.station_tree.selection()
        if not sel: return
        sid = int(sel[0]);
        r = self.row('SELECT * FROM pump_station WHERE id=?', (sid,));
        self.edit_station_id = sid
        self.station_edit_label.config(text=f"当前编辑：ID {sid} / {r['station_code']} / {r['station_name']}")
        for k, w in self.st_vars.items():
            w.delete(0, 'end')
            if k == 'default_pump_type':
                val = r[k] if k in r.keys() and r[k] is not None else 'submersible'
                w.insert(0, PUMP_TYPE_LABEL.get(val, val))
            elif k == 'data_source_mode':
                val = r[k] if k in r.keys() and r[k] is not None else 'simulation'
                try:
                    w.set(DATA_MODE_LABEL.get(val, val))
                except Exception:
                    w.insert(0, DATA_MODE_LABEL.get(val, val))
            elif k in r.keys():
                w.insert(0, str(r[k] if r[k] is not None else ''))
            else:
                defaults = {'default_pump_type': '潜污泵', 'default_rated_flow': '300', 'default_rated_head': '60',
                            'default_rated_power': '55', 'default_rated_current': '100'}
                w.insert(0, defaults.get(k, ''))

    def get_station_form(self):
        return {k: w.get().strip() for k, w in self.st_vars.items()}

    def add_station(self):
        d = self.get_station_form()
        if self.row('SELECT id FROM pump_station WHERE station_code=?', (d['station_code'],)):
            nc = self.db.next_station_code()
            if messagebox.askyesno('编号重复', f"泵站编号 {d['station_code']} 已存在，是否自动改为 {nc}？"):
                d['station_code'] = nc;
                self.st_vars['station_code'].delete(0, 'end');
                self.st_vars['station_code'].insert(0, nc)
            else:
                return
        try:
            sid = self.db.add_station(d, auto_generate=True)
            self.current_station_id = sid;
            self.db.set_current_station(sid);
            self.edit_station_id = sid
            self.refresh_all()
            try:
                self.station_tree.selection_set(str(sid));
                self.station_tree.see(str(sid));
                self.on_station_select()
            except Exception:
                pass
            messagebox.showinfo('成功', '泵站已新增，并已切换为当前泵站')
        except Exception as e:
            messagebox.showerror('新增失败', str(e))

    def save_station(self):
        sid = self.edit_station_id
        if not sid:
            sel = self.station_tree.selection();
            sid = int(sel[0]) if sel else None
        if not sid: messagebox.showwarning('提示', '请先选择一个泵站'); return
        d = self.get_station_form()
        dup = self.row('SELECT id FROM pump_station WHERE station_code=? AND id<>?', (d['station_code'], sid))
        if dup: messagebox.showerror('保存失败', '泵站编号与其他泵站重复'); return
        try:
            self.db.update_station(sid, d);
            self.refresh_all();
            messagebox.showinfo('成功', '泵站已保存，系统已按泵站数量补齐水泵、给水泵、母管和仪表')
        except Exception as e:
            messagebox.showerror('保存失败', str(e))

    def delete_station(self):
        sid = self.edit_station_id
        if not sid: messagebox.showwarning('提示', '请先选择泵站'); return
        if messagebox.askyesno('确认',
                               '确定删除该泵站？\n\n删除后将同步删除该泵站下属水泵、给水泵、母管、仪表、变量点位、液位/应急参数和运行数据。'):
            self.db.delete_station(sid);
            self.current_station_id = self.db.get_current_station_id();
            self.edit_station_id = None;
            self.refresh_all()

    def switch_station(self):
        sel = self.station_tree.selection()
        if not sel: messagebox.showwarning('提示', '请先选择一个泵站'); return
        self.current_station_id = int(sel[0]);
        self.edit_station_id = self.current_station_id
        self.db.set_current_station(self.current_station_id)
        self.refresh_all()
        try:
            self.station_tree.selection_set(str(self.current_station_id));
            self.station_tree.see(str(self.current_station_id));
            self.on_station_select()
        except Exception:
            pass
        self.nb.select(self.pages['泵站监控'])

    # Pump management
    def build_pump_page(self):
        f = self.pages['水泵管理']
        header = ttk.Frame(f);
        header.pack(fill='x', padx=8, pady=(8, 0))
        self.pump_station_label = ttk.Label(header, text='当前泵站：-', foreground='blue')
        self.pump_station_label.pack(side='left')
        ttk.Label(header, text='  提示：多级离心泵可在右侧“对应给水泵”中选择本泵站内的给水泵。', foreground='gray').pack(
            side='left')
        left = ttk.Frame(f);
        left.pack(side='left', fill='both', expand=True, padx=8, pady=8)
        right = ttk.LabelFrame(f, text='新增 / 编辑水泵');
        right.pack(side='right', fill='y', padx=8, pady=8)
        cols = ('ID', '编号', '名称', '类型', '启用', '自动', '应急', '备用', '检修', '故障', '额定流量', '给水泵')
        self.pump_tree = ttk.Treeview(left, columns=cols, show='headings', height=20)
        for c in cols: self.pump_tree.heading(c, text=c); self.pump_tree.column(c, width=80, anchor='center')
        self.pump_tree.pack(fill='both', expand=True);
        self.pump_tree.bind('<<TreeviewSelect>>', self.on_pump_select)
        self.pump_vars = {}
        fields = [('pump_code', '水泵编号'), ('pump_name', '水泵名称'), ('pump_type', '水泵类型'), ('enabled', '启用'),
                  ('auto_enable', '参与自动'), ('emergency_enable', '允许应急'), ('standby', '备用'),
                  ('maintenance', '检修'), ('manual_fault', '人工故障'), ('rated_power', '额定功率kW'),
                  ('rated_current', '额定电流A'), ('rated_flow', '额定流量m³/h'), ('rated_head', '额定扬程m'),
                  ('min_frequency', '最小频率'), ('max_frequency', '最大频率'), ('start_frequency', '启动频率'),
                  ('feed_pump_id', '对应给水泵'), ('remark', '备注')]
        self.pump_edit_label = ttk.Label(right, text='当前：新增水泵', foreground='blue');
        self.pump_edit_label.grid(row=0, column=0, columnspan=2, sticky='w', padx=4, pady=3)
        for i, (key, label) in enumerate(fields, 1):
            ttk.Label(right, text=label).grid(row=i, column=0, sticky='e', padx=4, pady=2)
            if key == 'pump_type':
                w = ttk.Combobox(right, values=[x[1] for x in PUMP_TYPES], width=24, state='normal')
            elif key == 'feed_pump_id':
                w = ttk.Combobox(right, values=[''], width=24, state='readonly')
            else:
                w = ttk.Entry(right, width=27)
            w.grid(row=i, column=1, padx=4, pady=2);
            self.pump_vars[key] = w
        btn = ttk.Frame(right);
        btn.grid(row=len(fields) + 3, column=0, columnspan=2, pady=8)
        ttk.Button(btn, text='新增水泵', command=self.add_pump).pack(side='left', padx=3)
        ttk.Button(btn, text='保存修改', command=self.save_pump).pack(side='left', padx=3)
        ttk.Button(btn, text='删除水泵', command=self.delete_pump).pack(side='left', padx=3)
        ttk.Button(btn, text='清空', command=self.clear_pump_form).pack(side='left', padx=3)

    def refresh_pump_list(self):
        if hasattr(self, 'pump_station_label'):
            self.pump_station_label.config(text='当前泵站：' + self.station_title())
        if hasattr(self, 'pump_vars') and 'feed_pump_id' in self.pump_vars:
            self.pump_vars['feed_pump_id']['values'] = self.feed_pump_options()
        self.clear_tree(self.pump_tree)
        for p in self.rows('SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id', (self.sid(),)):
            fp = self.row('SELECT pump_code FROM pump WHERE id=?', (p['feed_pump_id'],)) if p['feed_pump_id'] else None
            self.pump_tree.insert('', 'end', iid=str(p['id']), values=(p['id'], p['pump_code'], p['pump_name'],
                                                                       PUMP_TYPE_LABEL.get(p['pump_type'],
                                                                                           p['pump_type']),
                                                                       '是' if p['enabled'] else '否',
                                                                       '是' if p['auto_enable'] else '否',
                                                                       '是' if p['emergency_enable'] else '否',
                                                                       '是' if p['standby'] else '否',
                                                                       '是' if p['maintenance'] else '否',
                                                                       '是' if p['manual_fault'] else '否',
                                                                       p['rated_flow'], fp['pump_code'] if fp else ''))
        if not self.edit_pump_id: self.clear_pump_form()

    def clear_pump_form(self):
        self.edit_pump_id = None
        self.pump_edit_label.config(text='当前：新增水泵')
        if not self.sid():
            return
        code = self.db.next_pump_code(self.sid())
        vals = {'pump_code': code, 'pump_name': f'{code}潜污泵', 'pump_type': '潜污泵', 'enabled': '1',
                'auto_enable': '1', 'emergency_enable': '1', 'standby': '0', 'maintenance': '0', 'manual_fault': '0',
                'rated_power': '55', 'rated_current': '100', 'rated_flow': '300', 'rated_head': '60',
                'min_frequency': '30', 'max_frequency': '50', 'start_frequency': '30', 'feed_pump_id': '', 'remark': ''}
        if 'feed_pump_id' in self.pump_vars:
            self.pump_vars['feed_pump_id']['values'] = self.feed_pump_options()
        for k, w in self.pump_vars.items():
            try:
                w.set('')
            except Exception:
                pass
            try:
                w.delete(0, 'end')
            except Exception:
                pass
            if k in vals:
                try:
                    w.insert(0, vals.get(k, ''))
                except Exception:
                    w.set(vals.get(k, ''))

    def on_pump_select(self, e=None):
        sel = self.pump_tree.selection()
        if not sel: return
        pid = int(sel[0]);
        p = self.row('SELECT * FROM pump WHERE id=?', (pid,));
        self.edit_pump_id = pid
        self.pump_edit_label.config(text=f"当前编辑：ID {pid} / {p['pump_code']} / {p['pump_name']}")
        self.pump_vars['feed_pump_id']['values'] = self.feed_pump_options()
        for k, w in self.pump_vars.items():
            v = p[k] if k in p.keys() else ''
            if k == 'pump_type': v = PUMP_TYPE_LABEL.get(v, v)
            if k == 'feed_pump_id':
                if p['feed_pump_id']:
                    fp = self.row('SELECT * FROM pump WHERE id=?', (p['feed_pump_id'],))
                    v = f"{fp['id']} | {fp['pump_code']} | {fp['pump_name']}" if fp else ''
                else:
                    v = ''
            try:
                w.set(str(v if v is not None else ''))
            except Exception:
                w.delete(0, 'end');
                w.insert(0, str(v if v is not None else ''))

    def get_pump_form(self):
        d = {k: w.get().strip() for k, w in self.pump_vars.items()}
        d['pump_type'] = PUMP_TYPE_CODE.get(d['pump_type'], d['pump_type'])
        d['feed_pump_id'] = self.parse_combo_id(d.get('feed_pump_id', ''))
        if d['pump_type'] != 'centrifugal': d['feed_pump_id'] = None
        return d

    def add_pump(self):
        d = self.get_pump_form();
        sid = self.sid()
        if self.row('SELECT id FROM pump WHERE station_id=? AND pump_code=?', (sid, d['pump_code'])):
            nc = self.db.next_feed_pump_code(sid) if d['pump_type'] == 'feed' else self.db.next_pump_code(sid)
            if messagebox.askyesno('编号重复', f"水泵编号 {d['pump_code']} 已存在，是否自动改为 {nc}？"):
                d['pump_code'] = nc
                label = PUMP_TYPE_LABEL.get(d['pump_type'], d['pump_type'])
                d['pump_name'] = f'{nc}{label}'
                self.pump_vars['pump_code'].delete(0, 'end');
                self.pump_vars['pump_code'].insert(0, d['pump_code'])
                self.pump_vars['pump_name'].delete(0, 'end');
                self.pump_vars['pump_name'].insert(0, d['pump_name'])
            else:
                return
        if d['pump_type'] == 'centrifugal' and not d.get('feed_pump_id'):
            if not messagebox.askyesno('提示', '该水泵为多级离心泵，但未选择对应给水泵。是否仍然新增？'): return
        try:
            cur = self.db.execute(
                '''INSERT INTO pump(station_id, pump_code, pump_name, pump_type, enabled, auto_enable, emergency_enable,
                                    standby, maintenance, manual_fault, rated_power, rated_current, rated_flow,
                                    rated_head, min_frequency, max_frequency, start_frequency, feed_pump_id, created_at,
                                    updated_at, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sid, d['pump_code'], d['pump_name'], d['pump_type'], int(d['enabled']), int(d['auto_enable']),
                 int(d['emergency_enable']), int(d['standby']), int(d['maintenance']), int(d['manual_fault']),
                 float(d['rated_power']), float(d['rated_current']), float(d['rated_flow']), float(d['rated_head']),
                 float(d['min_frequency']), float(d['max_frequency']), float(d['start_frequency']), d['feed_pump_id'],
                 now(), now(), d['remark']))
            new_id = cur.lastrowid
            pipe = self.row('SELECT id FROM main_pipe WHERE station_id=? ORDER BY id LIMIT 1', (sid,))
            if pipe and d['pump_type'] != 'feed':
                self.db.execute(
                    'INSERT OR IGNORE INTO pump_pipe_relation(station_id,pump_id,pipe_id,relation_type,enabled) VALUES(?,?,?,?,1)',
                    (sid, new_id, pipe['id'], 'main_drain'))
            self.db.generate_default_points(sid)
            self.db.recalculate_pipe(sid)
            self.edit_pump_id = new_id
            self.refresh_all()
            try:
                self.pump_tree.selection_set(str(new_id))
                self.pump_tree.see(str(new_id))
            except Exception:
                pass
            messagebox.showinfo('成功', '水泵已新增')
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def save_pump(self):
        pid = self.edit_pump_id
        if not pid:
            sel = self.pump_tree.selection();
            pid = int(sel[0]) if sel else None
        if not pid: messagebox.showwarning('提示', '请先选择水泵'); return
        d = self.get_pump_form()
        if self.row('SELECT id FROM pump WHERE station_id=? AND pump_code=? AND id<>?',
                    (self.sid(), d['pump_code'], pid)):
            messagebox.showerror('保存失败', '水泵编号与当前泵站内其他水泵重复，请修改编号后再保存');
            return
        if d['pump_type'] == 'centrifugal' and not d.get('feed_pump_id'):
            if not messagebox.askyesno('提示', '该水泵为多级离心泵，但未选择对应给水泵。是否仍然保存？'): return
        try:
            self.db.execute('''UPDATE pump
                               SET pump_code=?,
                                   pump_name=?,
                                   pump_type=?,
                                   enabled=?,
                                   auto_enable=?,
                                   emergency_enable=?,
                                   standby=?,
                                   maintenance=?,
                                   manual_fault=?,
                                   rated_power=?,
                                   rated_current=?,
                                   rated_flow=?,
                                   rated_head=?,
                                   min_frequency=?,
                                   max_frequency=?,
                                   start_frequency=?,
                                   feed_pump_id=?,
                                   updated_at=?,
                                   remark=?
                               WHERE id = ?''',
                            (d['pump_code'], d['pump_name'], d['pump_type'], int(d['enabled']), int(d['auto_enable']),
                             int(d['emergency_enable']), int(d['standby']), int(d['maintenance']),
                             int(d['manual_fault']), float(d['rated_power']), float(d['rated_current']),
                             float(d['rated_flow']), float(d['rated_head']), float(d['min_frequency']),
                             float(d['max_frequency']), float(d['start_frequency']), d['feed_pump_id'], now(),
                             d['remark'], pid))
            self.edit_pump_id = pid;
            self.db.recalculate_pipe(self.sid());
            self.refresh_all()
            try:
                self.pump_tree.selection_set(str(pid));
                self.pump_tree.see(str(pid))
            except Exception:
                pass
            messagebox.showinfo('成功', '水泵已保存')
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def delete_pump(self):
        if not self.edit_pump_id: messagebox.showwarning('提示', '请先选择水泵'); return
        if messagebox.askyesno('确认', '确定删除水泵？'):
            self.db.execute('UPDATE pump SET feed_pump_id=NULL WHERE feed_pump_id=?', (self.edit_pump_id,))
            self.db.execute('DELETE FROM pump_pipe_relation WHERE pump_id=?', (self.edit_pump_id,));
            self.db.execute('DELETE FROM modbus_point WHERE object_type="pump" AND object_id=?', (self.edit_pump_id,));
            self.db.execute('DELETE FROM pump WHERE id=?', (self.edit_pump_id,));
            self.edit_pump_id = None;
            self.refresh_all()

    # Pipe management
    def build_pipe_page(self):
        f = self.pages['母管管理']
        header = ttk.Frame(f);
        header.pack(fill='x', padx=8, pady=(8, 0))
        self.pipe_station_label = ttk.Label(header, text='当前泵站：-', foreground='blue');
        self.pipe_station_label.pack(side='left')
        ttk.Label(header, text='  说明：母管由泵站管理按数量自动生成；也可手动新增。下方勾选此母管对应的主排水泵。',
                  foreground='gray').pack(side='left')
        top = ttk.Frame(f);
        top.pack(fill='both', expand=True, padx=8, pady=8);
        left = ttk.Frame(top);
        left.pack(side='left', fill='both', expand=True);
        right = ttk.LabelFrame(top, text='母管编辑');
        right.pack(side='right', fill='y')
        cols = ('ID', '编号', '名称', 'DN', '内径', '理论流量', '估算流量', '流速', '校核')
        self.pipe_tree = ttk.Treeview(left, columns=cols, show='headings', height=15)
        for c in cols: self.pipe_tree.heading(c, text=c); self.pipe_tree.column(c, width=90, anchor='center')
        self.pipe_tree.pack(fill='both', expand=True);
        self.pipe_tree.bind('<<TreeviewSelect>>', self.on_pipe_select)
        self.pipe_vars = {};
        fields = [('pipe_code', '母管编号'), ('pipe_name', '母管名称'), ('standard_dn', '标准管径'),
                  ('dn_value', 'DN数值mm'), ('inner_diameter_mm', '实际内径mm'), ('pipe_material', '材质'),
                  ('remark', '备注')]
        for i, (k, l) in enumerate(fields):
            ttk.Label(right, text=l).grid(row=i, column=0, sticky='e', padx=4, pady=3);
            w = ttk.Entry(right, width=26);
            w.grid(row=i, column=1, padx=4, pady=3);
            self.pipe_vars[k] = w
        b = ttk.Frame(right);
        b.grid(row=len(fields), column=0, columnspan=2, pady=5)
        ttk.Button(b, text='新增母管', command=self.add_pipe).pack(side='left', padx=3);
        ttk.Button(b, text='保存修改', command=self.save_pipe).pack(side='left', padx=3);
        ttk.Button(b, text='删除', command=self.delete_pipe).pack(side='left', padx=3);
        ttk.Button(b, text='清空', command=self.clear_pipe_form).pack(side='left', padx=3)
        bottom = ttk.LabelFrame(f, text='水泵与母管匹配关系')
        bottom.pack(fill='both', expand=True, padx=8, pady=5)
        # 水泵数量较多时，原来的横向排列会显示不完整。
        # 这里改成 Canvas + 滚动条 + 多列网格，保证所有主排水泵都能看到和勾选。
        rel_toolbar = ttk.Frame(bottom);
        rel_toolbar.pack(fill='x', padx=6, pady=(4, 2))
        ttk.Label(rel_toolbar, text='提示：这里只显示主排水泵，给水泵不接入母管。可滚动查看全部水泵。',
                  foreground='gray').pack(side='left')
        self.rel_canvas = tk.Canvas(bottom, height=170, highlightthickness=0)
        self.rel_vbar = ttk.Scrollbar(bottom, orient='vertical', command=self.rel_canvas.yview)
        self.rel_hbar = ttk.Scrollbar(bottom, orient='horizontal', command=self.rel_canvas.xview)
        self.rel_canvas.configure(yscrollcommand=self.rel_vbar.set, xscrollcommand=self.rel_hbar.set)
        self.rel_frame = ttk.Frame(self.rel_canvas)
        self.rel_canvas_window = self.rel_canvas.create_window((0, 0), window=self.rel_frame, anchor='nw')

        def _rel_configure(event=None):
            try:
                self.rel_canvas.configure(scrollregion=self.rel_canvas.bbox('all'))
            except Exception:
                pass

        def _rel_canvas_configure(event=None):
            try:
                # 让内部区域至少与画布同宽，小屏也可横向滚动。
                self.rel_canvas.itemconfigure(self.rel_canvas_window, width=max(event.width, 720))
            except Exception:
                pass

        self.rel_frame.bind('<Configure>', _rel_configure)
        self.rel_canvas.bind('<Configure>', _rel_canvas_configure)
        self.rel_canvas.pack(side='left', fill='both', expand=True, padx=(6, 0), pady=(0, 6))
        self.rel_vbar.pack(side='right', fill='y', pady=(0, 6))
        self.rel_hbar.pack(side='bottom', fill='x', padx=6)
        self.rel_checks = []

    def refresh_pipe_list(self):
        if hasattr(self, 'pipe_station_label'):
            self.pipe_station_label.config(text='当前泵站：' + self.station_title())
        keep_id = str(self.edit_pipe_id) if self.edit_pipe_id else None
        self.clear_tree(self.pipe_tree)
        for p in self.rows('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (self.sid(),)):
            self.pipe_tree.insert('', 'end', iid=str(p['id']),
                                  values=(p['id'], p['pipe_code'], p['pipe_name'], p['standard_dn'],
                                          p['inner_diameter_mm'], f"{p['theoretical_flow']:.1f}",
                                          f"{p['estimated_running_flow']:.1f}", f"{p['estimated_velocity']:.2f}",
                                          p['diameter_check_status']))
        if keep_id and self.pipe_tree.exists(keep_id):
            try:
                self.pipe_tree.selection_set(keep_id);
                self.pipe_tree.see(keep_id)
            except Exception:
                pass
        if not self.edit_pipe_id: self.clear_pipe_form()
        self.refresh_relations()

    def clear_pipe_form(self):
        self.edit_pipe_id = None
        if not self.sid():
            return
        code = self.db.next_pipe_code(self.sid())
        suffix = code.replace('PIPE', '').replace('母管', '')
        vals = {'pipe_code': code, 'pipe_name': code, 'standard_dn': 'DN400', 'dn_value': '400',
                'inner_diameter_mm': '400', 'pipe_material': '钢管', 'remark': ''}
        for k, w in self.pipe_vars.items(): w.delete(0, 'end'); w.insert(0, vals.get(k, ''))

    def on_pipe_select(self, e=None):
        sel = self.pipe_tree.selection();
        if not sel: return
        pid = int(sel[0]);
        p = self.row('SELECT * FROM main_pipe WHERE id=?', (pid,));
        self.edit_pipe_id = pid
        for k, w in self.pipe_vars.items(): w.delete(0, 'end'); w.insert(0, str(p[k] if p[k] is not None else ''))
        self.refresh_relations()

    def get_pipe_form(self):
        return {k: w.get().strip() for k, w in self.pipe_vars.items()}

    def add_pipe(self):
        d = self.get_pipe_form();
        sid = self.sid()
        if self.row('SELECT id FROM main_pipe WHERE station_id=? AND pipe_code=?', (sid, d['pipe_code'])):
            nc = self.db.next_pipe_code(sid)
            if messagebox.askyesno('母管编号重复', f"当前泵站内母管编号 {d['pipe_code']} 已存在，是否自动改为 {nc}？"):
                d['pipe_code'] = nc;
                d['pipe_name'] = nc
                self.pipe_vars['pipe_code'].delete(0, 'end');
                self.pipe_vars['pipe_code'].insert(0, nc)
                self.pipe_vars['pipe_name'].delete(0, 'end');
                self.pipe_vars['pipe_name'].insert(0, nc)
            else:
                return
        try:
            cur = self.db.execute(
                '''INSERT INTO main_pipe(station_id, pipe_code, pipe_name, standard_dn, dn_value, inner_diameter_mm,
                                         pipe_material, created_at, updated_at, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sid, d['pipe_code'], d['pipe_name'], d['standard_dn'], int(d['dn_value']),
                 float(d['inner_diameter_mm']), d['pipe_material'], now(), now(), d['remark']))
            self.edit_pipe_id = cur.lastrowid
            try:
                self.db._ensure_pipe_instruments(sid, self.edit_pipe_id, d['pipe_code'])
            except Exception:
                pass
            self.refresh_all()
            try:
                self.pipe_tree.selection_set(str(self.edit_pipe_id));
                self.pipe_tree.see(str(self.edit_pipe_id))
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def save_pipe(self):
        if not self.edit_pipe_id: messagebox.showwarning('提示', '请先选择母管'); return
        d = self.get_pipe_form()
        if self.row('SELECT id FROM main_pipe WHERE station_id=? AND pipe_code=? AND id<>?',
                    (self.sid(), d['pipe_code'], self.edit_pipe_id)):
            messagebox.showerror('保存失败', '当前泵站内母管编号重复');
            return
        self.db.execute(
            'UPDATE main_pipe SET pipe_code=?,pipe_name=?,standard_dn=?,dn_value=?,inner_diameter_mm=?,pipe_material=?,updated_at=?,remark=? WHERE id=?',
            (d['pipe_code'], d['pipe_name'], d['standard_dn'], int(d['dn_value']), float(d['inner_diameter_mm']),
             d['pipe_material'], now(), d['remark'], self.edit_pipe_id));
        self.db.recalculate_pipe(self.sid());
        keep = self.edit_pipe_id;
        self.refresh_all();
        self.edit_pipe_id = keep
        try:
            self.pipe_tree.selection_set(str(keep));
            self.pipe_tree.see(str(keep))
        except Exception:
            pass
        messagebox.showinfo('成功', f'母管 {d["pipe_code"]} 已保存，DN/管径参数已更新。')

    def delete_pipe(self):
        if not self.edit_pipe_id: return
        if messagebox.askyesno('确认', '确定删除母管？'):
            self.db.execute('DELETE FROM pump_pipe_relation WHERE pipe_id=?', (self.edit_pipe_id,));
            self.db.execute('DELETE FROM main_pipe WHERE id=?', (self.edit_pipe_id,));
            self.edit_pipe_id = None;
            self.refresh_all()

    def refresh_relations(self):
        for w in self.rel_frame.winfo_children(): w.destroy()
        pipe_id = self.edit_pipe_id
        if not pipe_id:
            ttk.Label(self.rel_frame, text='请选择一根母管后配置对应水泵', foreground='gray').grid(row=0, column=0,
                                                                                                   sticky='w', padx=8,
                                                                                                   pady=8)
            try:
                self.rel_canvas.configure(scrollregion=self.rel_canvas.bbox('all'))
            except Exception:
                pass
            return
        pumps = self.rows("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id",
                          (self.sid(),))
        if not pumps:
            ttk.Label(self.rel_frame, text='当前泵站没有可接入母管的主排水泵。', foreground='gray').grid(row=0, column=0,
                                                                                                        sticky='w',
                                                                                                        padx=8, pady=8)
            try:
                self.rel_canvas.configure(scrollregion=self.rel_canvas.bbox('all'))
            except Exception:
                pass
            return
        # 根据水泵数量自动分列：水泵多时每行 3~4 个，避免超出窗口看不到。
        cols = 3 if len(pumps) <= 12 else 4
        for idx, p in enumerate(pumps):
            checked = 1 if self.row('SELECT id FROM pump_pipe_relation WHERE pump_id=? AND pipe_id=? AND enabled=1',
                                    (p['id'], pipe_id)) else 0
            var = tk.IntVar(value=checked)
            ptype = PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type'] or '主排水泵')
            text = f"{p['pump_code']}  {p['pump_name']}  [{ptype}]"
            cb = ttk.Checkbutton(self.rel_frame, text=text, variable=var,
                                 command=lambda pid=p['id'], v=var: self.toggle_relation(pid, pipe_id, v.get()))
            r = idx // cols;
            c = idx % cols
            cb.grid(row=r, column=c, sticky='w', padx=12, pady=6)
            self.rel_frame.grid_columnconfigure(c, minsize=220, weight=1)
        try:
            self.rel_canvas.configure(scrollregion=self.rel_canvas.bbox('all'))
        except Exception:
            pass

    def toggle_relation(self, pump_id, pipe_id, val):
        if val:
            self.db.execute(
                'INSERT OR IGNORE INTO pump_pipe_relation(station_id,pump_id,pipe_id,relation_type,enabled) VALUES(?,?,?,?,1)',
                (self.sid(), pump_id, pipe_id, 'main_drain'))
            self.db.execute('UPDATE pump_pipe_relation SET enabled=1 WHERE pump_id=? AND pipe_id=?', (pump_id, pipe_id))
        else:
            self.db.execute('UPDATE pump_pipe_relation SET enabled=0 WHERE pump_id=? AND pipe_id=?', (pump_id, pipe_id))
        self.db.recalculate_pipe(self.sid());
        self.refresh_pipe_list();
        self.draw_model()

    # Instrument
    def build_instrument_page(self):
        f = self.pages['仪表管理']
        header = ttk.Frame(f);
        header.pack(fill='x', padx=8, pady=(8, 0))
        self.inst_station_label = ttk.Label(header, text='当前泵站：-', foreground='blue');
        self.inst_station_label.pack(side='left')
        ttk.Label(header, text='  规则：液位计→泵站；流量计/压力表→母管；总电表→泵站；单泵电表/电流电压→水泵。',
                  foreground='gray').pack(side='left')
        body = ttk.Frame(f);
        body.pack(fill='both', expand=True, padx=8, pady=8)
        left = ttk.Frame(body);
        left.pack(side='left', fill='both', expand=True)
        # 右侧仪表编辑区：改为固定宽度 + 内部滚动，避免字段较多时整体偏移或按钮显示不全。
        right_outer = ttk.LabelFrame(body, text='仪表参数完整编辑')
        right_outer.pack(side='right', fill='y', padx=(8, 0))
        right_outer.pack_propagate(False)
        try:
            right_outer.configure(width=520)
        except Exception:
            pass
        inst_canvas = tk.Canvas(right_outer, highlightthickness=0, width=500)
        inst_scroll = ttk.Scrollbar(right_outer, orient='vertical', command=inst_canvas.yview)
        inst_canvas.configure(yscrollcommand=inst_scroll.set)
        inst_canvas.pack(side='left', fill='both', expand=True)
        inst_scroll.pack(side='right', fill='y')
        right = ttk.Frame(inst_canvas)
        inst_window = inst_canvas.create_window((0, 0), window=right, anchor='nw')

        def _inst_form_configure(event=None):
            inst_canvas.configure(scrollregion=inst_canvas.bbox('all'))
            try:
                inst_canvas.itemconfigure(inst_window, width=inst_canvas.winfo_width())
            except Exception:
                pass

        right.bind('<Configure>', _inst_form_configure)
        inst_canvas.bind('<Configure>', _inst_form_configure)

        def _inst_mousewheel(event):
            inst_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        inst_canvas.bind_all('<MouseWheel>', _inst_mousewheel)
        filt = ttk.Frame(left);
        filt.pack(fill='x', pady=(0, 4))
        ttk.Label(filt, text='类型筛选').pack(side='left')
        self.inst_filter = ttk.Combobox(filt,
                                        values=['全部', 'level 液位计', 'flow 流量计', 'pressure 压力表', 'energy 电表',
                                                'current 电流', 'voltage 电压'], width=18, state='readonly')
        self.inst_filter.set('全部');
        self.inst_filter.pack(side='left', padx=4);
        self.inst_filter.bind('<<ComboboxSelected>>', lambda e: self.refresh_inst_list())
        ttk.Button(filt, text='刷新', command=self.refresh_inst_list).pack(side='left', padx=4)
        cols = ('ID', '编号', '名称', '类型', '归属', '母管', '水泵', '启用', '屏蔽', '报表', '来源', '修正', '当前值')
        self.inst_tree = ttk.Treeview(left, columns=cols, show='headings', height=22)
        for c in cols:
            self.inst_tree.heading(c, text=c);
            self.inst_tree.column(c, width=80 if c != '名称' else 110, anchor='center')
        self.inst_tree.pack(fill='both', expand=True);
        self.inst_tree.bind('<<TreeviewSelect>>', self.on_inst_select)
        self.inst_vars = {}
        fields = [
            ('instrument_code', '仪表编号'), ('instrument_name', '仪表名称'), ('instrument_type', '仪表类型'),
            ('owner_type', '归属类型'), ('owner_target', '归属对象'),
            ('enabled', '启用'), ('bypassed', '屏蔽'), ('control_enable', '参与控制'), ('alarm_enable', '参与报警'),
            ('report_enable', '参与报表'),
            ('instant_point_id', '瞬时值点位ID'), ('total_point_id', '累计值点位ID'), ('power_point_id', '功率点位ID'),
            ('voltage_point_id', '电压点位ID'), ('current_point_id', '电流点位ID'),
            ('min_valid_value', '最小有效值'), ('max_valid_value', '最大有效值'), ('abnormal_timeout', '异常持续时间s'),
            ('correction_factor', '修正系数'), ('report_priority', '报表优先级'), ('data_source', '数据来源'),
            ('remark', '备注')]
        # 两列分组显示，避免竖向过长和横向偏移。
        for i, (k, l) in enumerate(fields):
            col_group = 0 if i < 11 else 2
            row = i if i < 11 else i - 11
            ttk.Label(right, text=l).grid(row=row, column=col_group, sticky='e', padx=4, pady=3)
            if k == 'instrument_type':
                w = ttk.Combobox(right, values=['level', 'flow', 'pressure', 'energy', 'current', 'voltage'], width=18,
                                 state='readonly')
                w.bind('<<ComboboxSelected>>', lambda e: self.on_inst_type_changed())
            elif k == 'owner_type':
                w = ttk.Combobox(right, values=['station', 'pipe', 'pump'], width=18, state='readonly')
                w.bind('<<ComboboxSelected>>', lambda e: self.refresh_owner_target_options())
            elif k == 'owner_target':
                w = ttk.Combobox(right, values=[''], width=18, state='readonly')
            elif k == 'data_source':
                w = ttk.Combobox(right, values=['measured', 'estimated_by_frequency', 'manual', 'invalid'], width=18,
                                 state='readonly')
            elif k == 'remark':
                w = ttk.Entry(right, width=22)
            else:
                w = ttk.Entry(right, width=21)
            w.grid(row=row, column=col_group + 1, padx=4, pady=3, sticky='we');
            self.inst_vars[k] = w
        for c in range(4):
            right.grid_columnconfigure(c, weight=1 if c in (1, 3) else 0)
        b = ttk.Frame(right);
        b.grid(row=12, column=0, columnspan=4, pady=8, sticky='we')
        for idx, (txt, cmd) in enumerate([
            ('新增仪表', self.add_inst), ('保存修改', self.save_inst), ('删除', self.delete_inst),
            ('清空', self.clear_inst_form), ('推荐归属', self.apply_inst_owner_suggestion)
        ]):
            ttk.Button(b, text=txt, command=cmd, width=12).grid(row=idx // 3, column=idx % 3, padx=4, pady=3,
                                                                sticky='we')
        for c in range(3):
            b.grid_columnconfigure(c, weight=1)

    def instrument_type_label(self, typ):
        return {'level': '液位计', 'flow': '流量计', 'pressure': '压力表', 'energy': '电表', 'current': '电流',
                'voltage': '电压'}.get(typ, typ)

    def default_owner_type_for_inst(self, typ):
        if typ in ('flow', 'pressure'):
            return 'pipe'
        if typ in ('current', 'voltage'):
            return 'pump'
        return 'station'

    def owner_options(self, owner_type):
        vals = ['']
        if owner_type == 'station':
            st = self.get_station()
            if st: vals = [f"{st['id']} | {st['station_code']} | {st['station_name']}"]
        elif owner_type == 'pipe':
            vals = self.pipe_options()
        elif owner_type == 'pump':
            vals = self.pump_options(include_feed=True)
        return vals

    def refresh_owner_target_options(self):
        if not hasattr(self, 'inst_vars'): return
        ot = self.inst_vars['owner_type'].get().strip() or self.default_owner_type_for_inst(
            self.inst_vars['instrument_type'].get().strip())
        vals = self.owner_options(ot)
        self.inst_vars['owner_target']['values'] = vals
        cur = self.inst_vars['owner_target'].get()
        if cur not in vals:
            self.inst_vars['owner_target'].set(vals[0] if vals else '')

    def on_inst_type_changed(self):
        typ = self.inst_vars['instrument_type'].get().strip()
        self.inst_vars['owner_type'].set(self.default_owner_type_for_inst(typ))
        if not self.edit_inst_id:
            code = self.db.next_instrument_code(self.sid(), typ)
            name_map = {'level': '液位计', 'flow': '流量计', 'pressure': '压力表', 'energy': '电表',
                        'current': '电流采集', 'voltage': '电压采集'}
            self.inst_vars['instrument_code'].delete(0, 'end');
            self.inst_vars['instrument_code'].insert(0, code)
            self.inst_vars['instrument_name'].delete(0, 'end');
            self.inst_vars['instrument_name'].insert(0, code + name_map.get(typ, '仪表'))
        if typ == 'flow':
            self.inst_vars['control_enable'].delete(0, 'end');
            self.inst_vars['control_enable'].insert(0, '0')
            self.inst_vars['report_enable'].delete(0, 'end');
            self.inst_vars['report_enable'].insert(0, '1')
        elif typ == 'pressure':
            self.inst_vars['control_enable'].delete(0, 'end');
            self.inst_vars['control_enable'].insert(0, '0')
        elif typ == 'energy':
            self.inst_vars['control_enable'].delete(0, 'end');
            self.inst_vars['control_enable'].insert(0, '0')
            self.inst_vars['report_enable'].delete(0, 'end');
            self.inst_vars['report_enable'].insert(0, '1')
        self.refresh_owner_target_options()

    def apply_inst_owner_suggestion(self):
        self.on_inst_type_changed()
        messagebox.showinfo('已处理', '已根据仪表类型推荐归属：液位/总电表→泵站，流量/压力→母管，电流/电压→水泵。')

    def refresh_inst_list(self):
        if hasattr(self, 'inst_station_label'):
            self.inst_station_label.config(text='当前泵站：' + self.station_title())
        if hasattr(self, 'inst_vars'):
            self.refresh_owner_target_options()
        if not hasattr(self, 'inst_tree'): return
        self.clear_tree(self.inst_tree)
        typ_filter = self.inst_filter.get() if hasattr(self, 'inst_filter') else '全部'
        typ_code = typ_filter.split()[0] if typ_filter and typ_filter != '全部' else None
        sql = """SELECT ins.*, mp.pipe_code, p.pump_code
                 FROM instrument ins
                          LEFT JOIN main_pipe mp ON mp.id = ins.pipe_id
                          LEFT JOIN pump p ON p.id = ins.pump_id
                 WHERE ins.station_id = ? """
        params = [self.sid()]
        if typ_code:
            sql += 'AND ins.instrument_type=? '
            params.append(typ_code)
        sql += 'ORDER BY ins.instrument_type, ins.id'
        for i in self.rows(sql, tuple(params)):
            owner = ''
            if i['owner_type'] == 'station':
                owner = self.station_title(i['station_id'])
            elif i['owner_type'] == 'pipe':
                owner = i['pipe_code'] or ''
            elif i['owner_type'] == 'pump':
                owner = i['pump_code'] or ''
            self.inst_tree.insert('', 'end', iid=str(i['id']),
                                  values=(i['id'], i['instrument_code'], i['instrument_name'],
                                          self.instrument_type_label(i['instrument_type']), owner, i['pipe_code'] or '',
                                          i['pump_code'] or '', '是' if i['enabled'] else '否',
                                          '是' if i['bypassed'] else '否', '是' if i['report_enable'] else '否',
                                          i['data_source'], i['correction_factor'],
                                          f"{float(i['current_value'] or 0):.2f}"))
        if not self.edit_inst_id: self.clear_inst_form()

    def clear_inst_form(self):
        self.edit_inst_id = None
        typ = 'level'
        if hasattr(self, 'inst_filter'):
            f = self.inst_filter.get()
            if f and f != '全部':
                typ = f.split()[0]
        code = self.db.next_instrument_code(self.sid(), typ)
        owner_type = self.default_owner_type_for_inst(typ)
        name_map = {'level': '液位计', 'flow': '流量计', 'pressure': '压力表', 'energy': '电表', 'current': '电流采集',
                    'voltage': '电压采集'}
        vals = {'instrument_code': code, 'instrument_name': code + name_map.get(typ, '仪表'), 'instrument_type': typ,
                'owner_type': owner_type, 'owner_target': '',
                'enabled': '1', 'bypassed': '0', 'control_enable': '1' if typ == 'level' else '0', 'alarm_enable': '1',
                'report_enable': '1',
                'instant_point_id': '', 'total_point_id': '', 'power_point_id': '', 'voltage_point_id': '',
                'current_point_id': '',
                'min_valid_value': '0', 'max_valid_value': '999999', 'abnormal_timeout': '60',
                'correction_factor': '1.0', 'report_priority': '1', 'data_source': 'measured', 'remark': ''}
        for k, w in self.inst_vars.items():
            try:
                w.set('')
            except Exception:
                pass
            try:
                w.delete(0, 'end')
            except Exception:
                pass
            if k in vals:
                try:
                    w.set(vals[k])
                except Exception:
                    w.insert(0, vals[k])
        self.refresh_owner_target_options()

    def on_inst_select(self, e=None):
        sel = self.inst_tree.selection()
        if not sel: return
        iid = int(sel[0]);
        r = self.row('SELECT * FROM instrument WHERE id=?', (iid,));
        self.edit_inst_id = iid
        for k, w in self.inst_vars.items():
            if k == 'owner_target':
                continue
            v = r[k] if k in r.keys() and r[k] is not None else ''
            try:
                w.set(str(v))
            except Exception:
                w.delete(0, 'end');
                w.insert(0, str(v))
        self.refresh_owner_target_options()
        ot = r['owner_type'] or self.default_owner_type_for_inst(r['instrument_type'])
        owner_target = ''
        if ot == 'station':
            opts = self.owner_options('station');
            owner_target = opts[0] if opts else ''
        elif ot == 'pipe' and r['pipe_id']:
            pipe = self.row('SELECT * FROM main_pipe WHERE id=?', (r['pipe_id'],));
            owner_target = f"{pipe['id']} | {pipe['pipe_code']} | {pipe['pipe_name']}" if pipe else ''
        elif ot == 'pump' and r['pump_id']:
            pump = self.row('SELECT * FROM pump WHERE id=?', (r['pump_id'],));
            owner_target = f"{pump['id']} | {pump['pump_code']} | {pump['pump_name']}" if pump else ''
        self.inst_vars['owner_target'].set(owner_target)

    def _to_int_or_none(self, v):
        v = (v or '').strip()
        if not v: return None
        try:
            return int(v)
        except Exception:
            return None

    def get_inst_form(self):
        d = {k: w.get().strip() for k, w in self.inst_vars.items()}
        typ = d.get('instrument_type') or 'level'
        owner_type = d.get('owner_type') or self.default_owner_type_for_inst(typ)
        owner_id = self.parse_combo_id(d.get('owner_target', ''))
        pipe_id = None;
        pump_id = None
        if owner_type == 'station':
            owner_id = self.sid()
        elif owner_type == 'pipe':
            pipe_id = owner_id
        elif owner_type == 'pump':
            pump_id = owner_id
        if typ in ('flow', 'pressure') and not pipe_id:
            pipe_id = self.parse_combo_id(d.get('owner_target', ''));
            owner_type = 'pipe';
            owner_id = pipe_id
        if typ in ('current', 'voltage') and not pump_id:
            pump_id = self.parse_combo_id(d.get('owner_target', ''));
            owner_type = 'pump';
            owner_id = pump_id
        if typ == 'energy' and owner_type == 'pump':
            pump_id = owner_id
        d['owner_type'] = owner_type;
        d['owner_id'] = owner_id;
        d['pipe_id'] = pipe_id;
        d['pump_id'] = pump_id
        for k in ['instant_point_id', 'total_point_id', 'power_point_id', 'voltage_point_id', 'current_point_id']:
            d[k] = self._to_int_or_none(d.get(k, ''))
        return d

    def validate_inst(self, d, editing_id=None):
        if not d.get('instrument_code'):
            return '仪表编号不能为空'
        if not d.get('instrument_name'):
            return '仪表名称不能为空'
        if d['instrument_type'] in ('flow', 'pressure') and not d.get('pipe_id'):
            return '流量计/压力表必须选择所属母管'
        if d['instrument_type'] in ('current', 'voltage') and not d.get('pump_id'):
            return '电流/电压采集必须选择所属水泵'
        if d['instrument_type'] == 'energy' and d.get('owner_type') == 'pump' and not d.get('pump_id'):
            return '单泵电表必须选择所属水泵；总电表请选择归属类型=station'
        return None

    def add_inst(self):
        d = self.get_inst_form();
        err = self.validate_inst(d)
        if err: messagebox.showwarning('提示', err); return
        if self.row('SELECT id FROM instrument WHERE station_id=? AND instrument_code=?',
                    (self.sid(), d['instrument_code'])):
            nc = self.db.next_instrument_code(self.sid(), d['instrument_type'])
            if messagebox.askyesno('仪表编号重复',
                                   f"当前泵站内仪表编号 {d['instrument_code']} 已存在，是否自动改为 {nc}？"):
                d['instrument_code'] = nc
                name_map = {'level': '液位计', 'flow': '流量计', 'pressure': '压力表', 'energy': '电表',
                            'current': '电流采集', 'voltage': '电压采集'}
                d['instrument_name'] = nc + name_map.get(d['instrument_type'], '仪表')
                self.inst_vars['instrument_code'].delete(0, 'end');
                self.inst_vars['instrument_code'].insert(0, nc)
                self.inst_vars['instrument_name'].delete(0, 'end');
                self.inst_vars['instrument_name'].insert(0, d['instrument_name'])
            else:
                return
        try:
            cur = self.db.execute(
                """INSERT INTO instrument(station_id, pipe_id, pump_id, instrument_code, instrument_name,
                                          instrument_type, owner_type, owner_id, enabled, bypassed, control_enable,
                                          alarm_enable, report_enable, instant_point_id, total_point_id, power_point_id,
                                          voltage_point_id, current_point_id, min_valid_value, max_valid_value,
                                          abnormal_timeout, correction_factor, report_priority, data_source, created_at,
                                          updated_at, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.sid(), d['pipe_id'], d['pump_id'], d['instrument_code'], d['instrument_name'],
                 d['instrument_type'], d['owner_type'], d['owner_id'], int(d['enabled']), int(d['bypassed']),
                 int(d['control_enable']), int(d['alarm_enable']), int(d['report_enable']), d['instant_point_id'],
                 d['total_point_id'], d['power_point_id'], d['voltage_point_id'], d['current_point_id'],
                 float(d['min_valid_value']), float(d['max_valid_value']), int(d['abnormal_timeout']),
                 float(d['correction_factor']), int(d['report_priority']), d['data_source'], now(), now(), d['remark']))
            self.edit_inst_id = cur.lastrowid
            self.db.generate_default_points(self.sid());
            self.refresh_all()
            try:
                self.inst_tree.selection_set(str(self.edit_inst_id));
                self.inst_tree.see(str(self.edit_inst_id))
            except Exception:
                pass
            messagebox.showinfo('成功', '仪表已新增')
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def save_inst(self):
        if not self.edit_inst_id: messagebox.showwarning('提示', '请先选择仪表'); return
        d = self.get_inst_form();
        err = self.validate_inst(d, self.edit_inst_id)
        if err: messagebox.showwarning('提示', err); return
        if self.row('SELECT id FROM instrument WHERE station_id=? AND instrument_code=? AND id<>?',
                    (self.sid(), d['instrument_code'], self.edit_inst_id)):
            messagebox.showerror('保存失败', '当前泵站内仪表编号重复');
            return
        self.db.execute("""UPDATE instrument
                           SET pipe_id=?,
                               pump_id=?,
                               instrument_code=?,
                               instrument_name=?,
                               instrument_type=?,
                               owner_type=?,
                               owner_id=?,
                               enabled=?,
                               bypassed=?,
                               control_enable=?,
                               alarm_enable=?,
                               report_enable=?,
                               instant_point_id=?,
                               total_point_id=?,
                               power_point_id=?,
                               voltage_point_id=?,
                               current_point_id=?,
                               min_valid_value=?,
                               max_valid_value=?,
                               abnormal_timeout=?,
                               correction_factor=?,
                               report_priority=?,
                               data_source=?,
                               updated_at=?,
                               remark=?
                           WHERE id = ?""",
                        (d['pipe_id'], d['pump_id'], d['instrument_code'], d['instrument_name'], d['instrument_type'],
                         d['owner_type'], d['owner_id'], int(d['enabled']), int(d['bypassed']),
                         int(d['control_enable']), int(d['alarm_enable']), int(d['report_enable']),
                         d['instant_point_id'], d['total_point_id'], d['power_point_id'], d['voltage_point_id'],
                         d['current_point_id'], float(d['min_valid_value']), float(d['max_valid_value']),
                         int(d['abnormal_timeout']), float(d['correction_factor']), int(d['report_priority']),
                         d['data_source'], now(), d['remark'], self.edit_inst_id))
        self.refresh_all();
        messagebox.showinfo('成功', '仪表参数已完整保存')

    def delete_inst(self):
        if self.edit_inst_id and messagebox.askyesno('确认', '删除仪表？'):
            self.db.execute('DELETE FROM modbus_point WHERE object_type="instrument" AND object_id=?',
                            (self.edit_inst_id,))
            self.db.execute('DELETE FROM instrument WHERE id=?', (self.edit_inst_id,));
            self.edit_inst_id = None;
            self.refresh_all()

    def build_level_page(self):
        self.level_vars = {};
        self._build_param_page(self.pages['液位控制设定'], 'level_control', self.level_vars,
                               '液位控制参数（每个泵站独立）')

    def build_emergency_page(self):
        self.em_vars = {};
        self._build_param_page(self.pages['应急控制设定'], 'emergency', self.em_vars, '人工应急提示参数（每个泵站独立）')

    def _build_param_page(self, f, group, varmap, title):
        # 美化后的独立参数页：顶部泵站切换 + 卡片式参数区。
        header = tk.Frame(f, bg='#f3f6fb')
        header.pack(fill='x', padx=10, pady=(8, 4))
        title_icon = '🚨' if group == 'emergency' else '⚙'
        tk.Label(header, text=f'{title_icon} {title}', font=('Microsoft YaHei', 15, 'bold'), bg='#f3f6fb',
                 fg='#17365d').pack(side='left', padx=(8, 18), pady=8)
        lbl = ttk.Label(header, text='当前泵站：-', foreground='#005bbb', font=('Microsoft YaHei', 10, 'bold'))
        lbl.pack(side='left')
        combo = ttk.Combobox(header, width=36, state='readonly')
        combo.pack(side='left', padx=6)
        setattr(self, f'{group}_station_combo', combo)
        ttk.Button(header, text='切换泵站', command=lambda g=group: self.switch_param_station(g)).pack(side='left',
                                                                                                       padx=4)
        tip = '自动平衡控制按泵站独立运行；人工一键应急启动后，自动模式继续接管调频、减泵和平衡控制。' if group == 'emergency' else '参数按当前泵站独立保存。'
        ttk.Label(header, text=tip, foreground='gray').pack(side='left', padx=10)

        shell = tk.Frame(f, bg='#eef2f7')
        shell.pack(fill='both', expand=True, padx=10, pady=6)
        frame = tk.Frame(shell, bg='#eef2f7')
        frame.pack(anchor='nw', fill='both', expand=True, padx=8, pady=8)
        btnbar = tk.Frame(f, bg='#f8f9fb')
        btnbar.pack(fill='x', padx=10, pady=(0, 8))
        tk.Button(btnbar, text='💾 保存当前泵站参数', font=('Microsoft YaHei', 10, 'bold'), bg='#0b63ce', fg='white',
                  relief='flat', padx=14, pady=6, command=lambda g=group, v=varmap: self.save_param_page(g, v)).pack(
            side='left', padx=8, pady=6)
        self.param_frames[group] = frame
        self.param_station_labels[group] = lbl

    def switch_param_station(self, group):
        combo = getattr(self, f'{group}_station_combo', None)
        s = combo.get() if combo else ''
        try:
            sid = int(s.split('|')[0].strip())
        except Exception:
            messagebox.showwarning('提示', '请先选择泵站')
            return
        self.db.set_current_station(sid)
        self.current_station_id = sid
        self.db.log('参数页切换泵站', 'station', sid, self.station_title(), '', '切换', 'success', group)
        self.refresh_all()

    def _param_icon(self, code, group=''):
        if 'level' in code: return '🌊'
        if 'freq' in code: return '〽'
        if 'rise_rate' in code: return '📈'
        if 'time_to_high' in code: return '⏱'
        if 'emergency' in code: return '🚨'
        if 'delay' in code or 'timeout' in code: return '⏲'
        if 'current' in code: return '⚡'
        if 'bypass' in code: return '🛡'
        return '⚙'

    def refresh_params(self):
        for group, varsmap in [('level_control', getattr(self, 'level_vars', {})),
                               ('emergency', getattr(self, 'em_vars', {}))]:
            lf = self.param_frames.get(group)
            if not lf: continue
            lbl = self.param_station_labels.get(group)
            if lbl: lbl.config(text='当前泵站：' + self.station_title())
            combo = getattr(self, f'{group}_station_combo', None)
            if combo:
                vals = [f"{r['id']} | {r['station_code']} | {r['station_name']}" for r in
                        self.rows('SELECT id,station_code,station_name FROM pump_station ORDER BY id')]
                combo['values'] = vals
                cur = ''
                for v in vals:
                    if self.sid() and v.startswith(str(self.sid()) + ' |'):
                        cur = v;
                        break
                combo.set(cur if cur else (vals[0] if vals else ''))
            for w in lf.winfo_children(): w.destroy()
            varsmap.clear()
            rows = self.rows(
                'SELECT * FROM parameter_value WHERE scope_type="station" AND scope_id=? AND param_group=? ORDER BY id',
                (self.sid(), group))
            if group == 'level_control':
                order = ['level_high_high', 'target_level', 'upper_level', 'lower_level', 'control_deadband',
                         'rise_rate_trigger', 'fall_rate_trigger', 'freq_min', 'freq_normal', 'freq_max', 'freq_step',
                         'freq_adjust_interval_seconds', 'add_pump_min_interval_seconds',
                         'reduce_pump_min_interval_seconds']
                by_code = {r['param_code']: r for r in rows}
                rows = [by_code[c] for c in order if c in by_code]
            for i, r in enumerate(rows):
                row = i // 3;
                col = i % 3
                card = tk.Frame(lf, bg='white', highlightbackground='#d8e0ea', highlightthickness=1)
                card.grid(row=row, column=col, sticky='nsew', padx=8, pady=8)
                lf.grid_columnconfigure(col, weight=1)
                tk.Label(card, text=f"{self._param_icon(r['param_code'], group)} {r['param_name']}",
                         font=('Microsoft YaHei', 10, 'bold'), bg='white', fg='#1f3b5f').pack(anchor='w', padx=10,
                                                                                              pady=(8, 2))
                body = tk.Frame(card, bg='white');
                body.pack(fill='x', padx=10, pady=(2, 8))
                e = ttk.Entry(body, width=16);
                e.insert(0, r['param_value']);
                e.pack(side='left')
                tk.Label(body, text=r['unit'] or '', font=('Microsoft YaHei', 9), bg='white', fg='#566573').pack(
                    side='left', padx=6)
                tk.Label(card, text=r['param_code'], font=('Consolas', 8), bg='white', fg='#9aa3ad').pack(anchor='w',
                                                                                                          padx=10,
                                                                                                          pady=(0, 8))
                varsmap[r['param_code']] = e

    def save_param_page(self, group, varmap):
        for code, e in varmap.items(): self.db.set_param(self.sid(), group, code, e.get().strip())
        self.db.log('保存参数', 'station', self.sid(), group, '', '保存', 'success', self.station_title())
        messagebox.showinfo('成功', '当前泵站参数已保存，不影响其他泵站')

    # Model
    def build_model_page(self):
        f = self.pages['模型示意']
        bar = ttk.Frame(f);
        bar.pack(fill='x', padx=8, pady=5)
        ttk.Label(bar, text='模型泵站').pack(side='left')
        self.model_station = ttk.Combobox(bar, width=36, state='readonly')
        self.model_station.pack(side='left', padx=6)
        self.model_station.bind('<<ComboboxSelected>>', lambda e: self.draw_model())
        ttk.Button(bar, text='刷新模型', command=self.draw_model).pack(side='left', padx=4)
        ttk.Button(bar, text='切换为当前泵站', command=self.switch_to_model_station).pack(side='left', padx=4)
        ttk.Label(bar, text='说明：此处可查看任意泵站模型，不再只显示1号泵站。', foreground='gray').pack(side='left',
                                                                                                      padx=8)
        self.canvas = tk.Canvas(f, bg='white', height=650);
        self.canvas.pack(fill='both', expand=True, padx=8, pady=5)

    def refresh_model_station_choices(self):
        if not hasattr(self, 'model_station'): return
        vals = []
        for st in self.rows('SELECT id,station_code,station_name FROM pump_station ORDER BY id'):
            vals.append(f"{st['id']} | {st['station_code']} | {st['station_name']}")
        old = self.model_station.get()
        self.model_station['values'] = vals
        old_id = self.parse_combo_id(old)
        valid_ids = {self.parse_combo_id(v) for v in vals}
        if old_id in valid_ids:
            self.model_station.set(old)
        else:
            cur = self.sid()
            target = ''
            for v in vals:
                if self.parse_combo_id(v) == cur:
                    target = v;
                    break
            self.model_station.set(target or (vals[0] if vals else ''))

    def model_sid(self):
        return self.parse_combo_id(self.model_station.get()) if hasattr(self, 'model_station') else self.sid()

    def switch_to_model_station(self):
        sid = self.model_sid()
        if not sid: return
        self.current_station_id = sid;
        self.db.set_current_station(sid);
        self.refresh_all()

    def draw_model(self):
        if not hasattr(self, 'canvas'): return
        c = self.canvas;
        c.delete('all')
        self.model_flow_phase = (getattr(self, 'model_flow_phase', 0) + 1) % 12
        sid = self.model_sid() or self.sid()
        st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
        if not st:
            c.create_text(30, 30, anchor='w', text='当前没有泵站模型。', fill='red',
                          font=('Microsoft YaHei', 14, 'bold'))
            return
        W = max(int(c.winfo_width() or 1200), 1200)
        c.create_rectangle(10, 10, W - 20, 70, fill='#eef4ff', outline='#9db7dd')
        c.create_text(28, 26, anchor='w', text='🤖 智能工艺模型示意', font=('Microsoft YaHei', 16, 'bold'),
                      fill='#1f3b5f')
        c.create_text(28, 52, anchor='w',
                      text=f"{st['station_code']}  {st['station_name']}    液位 {float(st['current_level'] or 0):.2f} m    自动调节：{st['emergency_level']}",
                      font=('Microsoft YaHei', 11, 'bold'), fill='#333')
        c.create_rectangle(25, 360, 310, 560, fill='#dff3ff', outline='#1e88e5', width=2)
        c.create_text(168, 390, text='💧 集水池 / 水仓', font=('Microsoft YaHei', 12, 'bold'), fill='#1565c0')
        c.create_line(70, 360, 70, 300, fill='#1565c0', width=4);
        c.create_text(70, 288, text='📏 LT01', font=('Microsoft YaHei', 10, 'bold'))
        c.create_line(115, 360, 115, 300, fill='#1565c0', width=4);
        c.create_text(115, 288, text='📏 LT02', font=('Microsoft YaHei', 10, 'bold'))
        pipes = self.rows('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,))
        if not pipes:
            c.create_text(370, 160, anchor='w', text='⚠ 该泵站暂无母管，请在“母管管理”中新增。', fill='red',
                          font=('Microsoft YaHei', 12, 'bold'))
            return
        x0 = 360;
        x1 = W - 245
        for idx, pipe in enumerate(pipes):
            y = 120 + idx * 122
            flow = float(pipe['estimated_running_flow'] or 0)
            if flow <= 0.1:
                color = '#9ca3af'
            elif pipe['diameter_check_status'] == '偏小':
                color = '#c62828'
            elif pipe['diameter_check_status'] == '偏大':
                color = '#ef6c00'
            else:
                color = '#1f9d55'
            c.create_rectangle(x0 - 15, y - 42, x1 + 230, y + 70, fill='#ffffff', outline='#d6dde8')
            c.create_text(x0 - 5, y - 28, anchor='w',
                          text=f"🟩 {pipe['pipe_name']}  {pipe['standard_dn']}    理论:{pipe['theoretical_flow']:.0f}m³/h    估算:{pipe['estimated_running_flow']:.0f}m³/h    流速:{pipe['estimated_velocity']:.2f}m/s    压力:{float(pipe['pressure'] or 0):.3f}MPa    校核:{pipe['diameter_check_status']}",
                          font=('Microsoft YaHei', 10, 'bold'), fill='#263238')
            c.create_line(x0, y, x1, y, fill=color, width=8, capstyle='round')
            if flow > 0.1:
                speed = max(1, min(8, int(flow / 120) + 1))
                phase = (getattr(self, 'model_flow_phase', 0) * speed * 6) % 48
                for dx in range(int(phase), int(x1 - x0), 48):
                    c.create_oval(x0 + dx - 4, y - 4, x0 + dx + 4, y + 4, fill='#e0f7ff', outline='#0ea5e9')
            c.create_oval(x1 + 25, y - 23, x1 + 71, y + 23, outline='#7b1fa2', width=3, fill='#faf5ff');
            c.create_text(x1 + 48, y, text='FT', font=('Microsoft YaHei', 10, 'bold'), fill='#7b1fa2')
            c.create_oval(x1 + 92, y - 23, x1 + 138, y + 23, outline='#8d3a2b', width=3, fill='#fff7f4');
            c.create_text(x1 + 115, y, text='PT', font=('Microsoft YaHei', 10, 'bold'), fill='#8d3a2b')
            c.create_line(x1 + 150, y, x1 + 230, y, arrow='last', width=3, fill='#263238');
            c.create_text(x1 + 190, y - 22, text='出水', font=('Microsoft YaHei', 10, 'bold'))
            pumps = self.rows('''SELECT p.*
                                 FROM pump p
                                          JOIN pump_pipe_relation r ON r.pump_id = p.id
                                 WHERE r.pipe_id = ?
                                   AND r.enabled = 1
                                   AND p.pump_type!='feed'
                                 ORDER BY p.display_order, p.id''', (pipe['id'],))
            c.create_text(x0 - 5, y + 26, anchor='w',
                          text='接入主泵：' + ('、'.join([p['pump_code'] for p in pumps]) if pumps else '无'),
                          fill=('#666' if pumps else '#c62828'), font=('Microsoft YaHei', 9, 'bold'))
            if not pumps:
                c.create_text(x0 - 5, y + 48, anchor='w', text='⚠ 当前母管尚未关联主排水泵，请到“母管管理”勾选。',
                              fill='#c62828', font=('Microsoft YaHei', 9, 'bold'))
            for j, p in enumerate(pumps[:8]):
                px = 45 + (j % 3) * 110;
                py = 410 + (j // 3) * 95
                status_icon = '🟢' if p['run_feedback'] else '🔴' if p['fault_feedback'] or p['manual_fault'] else '🟡' if \
                    p['maintenance'] else '⚪'
                fill = '#e8f5e9' if p['run_feedback'] else '#ffebee' if p['fault_feedback'] or p[
                    'manual_fault'] else '#fff8e1' if p['maintenance'] else '#f5f5f5'
                c.create_rectangle(px, py, px + 96, py + 48, fill=fill, outline='#455a64')
                icon = '🚰' if p['pump_type'] == 'submersible' else '🌀'
                c.create_text(px + 48, py + 13, text=f"{status_icon} {icon} {p['pump_code']}",
                              font=('Microsoft YaHei', 9, 'bold'))
                c.create_text(px + 48, py + 32, text=PUMP_TYPE_LABEL.get(p['pump_type'], ''),
                              font=('Microsoft YaHei', 8), fill='#555')
                c.create_line(px + 96, py + 24, x0, y, fill='#607d8b')
                if p['pump_type'] == 'centrifugal':
                    if p['feed_pump_id']:
                        fp = self.row('SELECT * FROM pump WHERE id=?', (p['feed_pump_id'],))
                        if fp:
                            ficon = '🟢' if fp['run_feedback'] else '⚪'
                            c.create_rectangle(px, py + 55, px + 96, py + 90, fill='#e3f2fd', outline='#1976d2')
                            c.create_text(px + 48, py + 72, text=f"{ficon} 💦 {fp['pump_code']} 给水",
                                          font=('Microsoft YaHei', 8, 'bold'), fill='#0d47a1')
                            c.create_line(px + 48, py + 55, px + 48, py + 48, arrow='last', fill='#1976d2')
                    else:
                        c.create_text(px + 48, py + 66, text='⚠ 未关联给水泵', fill='red',
                                      font=('Microsoft YaHei', 8, 'bold'))
            if len(pumps) > 8:
                c.create_text(45 + 3 * 110, 410 + 2 * 95, anchor='w', text=f'+{len(pumps) - 8} 台', fill='#666')
        unassigned = self.rows('''SELECT p.*
                                  FROM pump p
                                  WHERE p.station_id = ?
                                    AND p.pump_type!='feed' AND NOT EXISTS
            (SELECT 1 FROM pump_pipe_relation r WHERE r.pump_id=p.id AND r.enabled=1)
                                  ORDER BY p.display_order, p.id''', (sid,))
        if unassigned:
            txt = '⚠ 未接入母管的主泵：' + '、'.join([p['pump_code'] for p in unassigned]) + '。请在“母管管理”中选择母管后勾选对应水泵。'
            c.create_text(30, 90, anchor='w', text=txt, fill='#c62828', font=('Microsoft YaHei', 10, 'bold'))
        feed_unlinked = self.rows('''SELECT p.*
                                     FROM pump p
                                     WHERE p.station_id = ?
                                       AND p.pump_type = 'centrifugal'
                                       AND (p.feed_pump_id IS NULL OR p.feed_pump_id = 0)
                                     ORDER BY p.id''', (sid,))
        if feed_unlinked:
            c.create_text(30, 112, anchor='w', text='⚠ 未绑定给水泵的离心泵：' + '、'.join(
                [p['pump_code'] for p in feed_unlinked]) + '。请在“水泵管理”中设置对应给水泵。', fill='#c62828',
                          font=('Microsoft YaHei', 10, 'bold'))
        c.configure(scrollregion=c.bbox('all'))

    # Manual control
    def build_manual_page(self):
        f = self.pages['手动控制']
        banner = tk.Frame(f, bg='#123b63');
        banner.pack(fill='x', padx=10, pady=(8, 4))
        tk.Label(banner, text='🕹 现场手动控制 / 人工抢排', font=('Microsoft YaHei', 15, 'bold'), bg='#123b63',
                 fg='white').pack(side='left', padx=12, pady=8)
        tk.Label(banner, text='手动、自动清晰切换；应急抢排醒目显示', font=('Microsoft YaHei', 10), bg='#123b63',
                 fg='#cfe8ff').pack(side='left', padx=12)
        station_frame = ttk.LabelFrame(f, text='① 现场快速切换泵站');
        station_frame.pack(fill='x', padx=10, pady=6)
        ttk.Label(station_frame, text='控制泵站').grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.manual_station = ttk.Combobox(station_frame, width=36, state='readonly')
        self.manual_station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(station_frame, text='切换到该泵站', command=self.manual_switch_station).grid(row=0, column=2, padx=5,
                                                                                                pady=5)

        mode_frame = ttk.LabelFrame(f, text='② 泵站运行模式切换');
        mode_frame.pack(fill='x', padx=10, pady=6)
        self.mode_status = ttk.Label(mode_frame, text='当前运行模式：-    自动调节状态：-',
                                     font=('Microsoft YaHei', 11, 'bold'));
        self.mode_status.grid(row=0, column=0, columnspan=6, sticky='w', padx=6, pady=5)
        ttk.Button(mode_frame, text='🔵 切换到手动', style='Primary.TButton',
                   command=lambda: self.change_mode('manual')).grid(row=2, column=0, padx=4, pady=6)
        ttk.Button(mode_frame, text='🟢 切换到自动', style='Success.TButton',
                   command=lambda: self.change_mode('auto')).grid(row=2, column=1, padx=4, pady=6)

        em_frame = ttk.LabelFrame(f, text='③ 人工应急启动 / 抢排操作')
        em_frame.pack(fill='x', padx=10, pady=6)
        self.emergency_start_box = ttk.Frame(em_frame)
        self.emergency_start_box.pack(fill='x', padx=6, pady=5)

        card_box = ttk.LabelFrame(f, text='⑤ 水泵一键控制面板');
        card_box.pack(fill='both', expand=True, padx=10, pady=8)
        self.manual_canvas = tk.Canvas(card_box, height=500, highlightthickness=0, bg='#f5f7fb')
        self.manual_scroll = ttk.Scrollbar(card_box, orient='vertical', command=self.manual_canvas.yview)
        self.manual_cards = ttk.Frame(self.manual_canvas)
        self.manual_cards.bind('<Configure>',
                               lambda e: self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox('all')))
        self.manual_canvas.create_window((0, 0), window=self.manual_cards, anchor='nw')
        self.manual_canvas.configure(yscrollcommand=self.manual_scroll.set)
        self.manual_canvas.pack(side='left', fill='both', expand=True)
        self.manual_scroll.pack(side='right', fill='y')

    def refresh_manual_lists(self):
        stations = [f"{r['id']} | {r['station_code']} | {r['station_name']}" for r in
                    self.rows('SELECT id,station_code,station_name FROM pump_station ORDER BY id')]
        if hasattr(self, 'manual_station'):
            self.manual_station['values'] = stations
            sid = self.sid()
            cur = ''
            for v in stations:
                if v.startswith(str(sid) + ' |'):
                    cur = v;
                    break
            self.manual_station.set(cur if cur else (stations[0] if stations else ''))
        st = self.get_station()
        if not st:
            if hasattr(self, 'mode_status'):
                self.mode_status.config(text='当前运行模式：-    自动调节状态：-')
            self.refresh_manual_cards([])
            self.refresh_emergency_start_area([])
            return
        if hasattr(self, 'mode_status'):
            self.mode_status.config(
                text=f"当前运行模式：{MODE_LABEL.get(st['control_mode'], st['control_mode'])}    自动调节状态：{st['emergency_level']}")
        pumps = self.rows('SELECT * FROM pump WHERE station_id=? ORDER BY pump_type="feed", display_order,id',
                          (self.sid(),))
        self.refresh_manual_cards(pumps)
        self.refresh_emergency_start_area(pumps)

    def refresh_emergency_start_area(self, pumps=None):
        if not hasattr(self, 'emergency_start_box'):
            return
        for w in self.emergency_start_box.winfo_children():
            w.destroy()
        pumps = pumps if pumps is not None else self.rows(
            "SELECT * FROM pump WHERE station_id=? ORDER BY pump_type='feed', display_order,id", (self.sid(),))
        available = []
        for p in pumps:
            if p['pump_type'] == 'feed':
                continue
            if p['run_feedback'] or not p['enabled'] or p['maintenance'] or p['manual_fault'] or p['fault_feedback'] or \
                    p['disabled']:
                continue
            available.append(p)
        if self.is_auto_mode():
            ttk.Label(self.emergency_start_box,
                      text='自动模式下允许人工一键抢排；启动后自动平衡控制会继续接管调频、减泵和平衡。',
                      foreground='#005bbb').pack(side='left', padx=6, pady=4)
        if not available:
            ttk.Label(self.emergency_start_box, text='暂无可启动的备用主排水泵。', foreground='gray').pack(side='left',
                                                                                                          padx=6,
                                                                                                          pady=4)
            return
        ttk.Button(self.emergency_start_box, text='🚨 一键启动全部可用泵', style='Warn.TButton',
                   command=self.manual_emergency_start_all).pack(side='left', padx=5, pady=4)
        for p in available[:12]:
            ttk.Button(self.emergency_start_box, text=f"启动 {p['pump_code']}",
                       command=lambda pid=p['id']: self.emergency_start_pid(pid)).pack(side='left', padx=3, pady=4)

    def manual_emergency_start_all(self):
        # 人工应急启动允许在自动模式下使用。启动后自动平衡控制继续接管调频、减泵和平衡。
        if not messagebox.askyesno('确认一键应急启动',
                                   '确认启动当前泵站全部可用主排水泵？\n系统会自动排除已运行、故障、检修、禁用和给水泵。'):
            return
        pumps = self.rows("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id",
                          (self.sid(),))
        started = [];
        skipped = []
        for p in pumps:
            if p['run_feedback']:
                continue
            if not p['enabled'] or p['maintenance'] or p['manual_fault'] or p['fault_feedback'] or p['disabled']:
                skipped.append(p['pump_code'])
                continue
            ok, msg = self.service.start_pump(p['id'], float(p['start_frequency'] or 30), 'manual_emergency')
            if ok:
                started.append(p['pump_code'])
            else:
                skipped.append(p['pump_code'])
        self.db.log('人工应急启动', 'station', self.sid(), self.station_title(), '',
                    '启动：' + ','.join(started) + '；跳过：' + ','.join(skipped), 'success', 'operator')
        messagebox.showinfo('人工应急启动', '已启动：' + (', '.join(started) if started else '无') + (
            '\n跳过：' + ', '.join(skipped) if skipped else ''))
        self.refresh_all()

    def emergency_start_pid(self, pid):
        # 单泵人工应急启动允许在自动模式下执行；启动后由自动平衡控制接管。
        p = self.row('SELECT * FROM pump WHERE id=?', (pid,))
        name = f'{p["pump_code"]} / {p["pump_name"]}' if p else str(pid)
        if not messagebox.askyesno('确认应急启动', f'确认应急启动水泵 {name}？'):
            return
        ok, msg = self.service.start_pump(pid, self._manual_freq_value(pid), 'manual_emergency')
        messagebox.showinfo('人工应急启动', f'水泵 {name}：\n{msg}')
        self.refresh_all()

    def manual_switch_station(self):
        s = self.manual_station.get() if hasattr(self, 'manual_station') else ''
        try:
            sid = int(s.split('|')[0].strip())
        except Exception:
            messagebox.showwarning('提示', '请先选择泵站')
            return
        self.db.set_current_station(sid)
        self.current_station_id = sid
        self.db.log('手动控制切换泵站', 'station', sid, self.station_title(), '', '切换', 'success', 'operator')
        self.refresh_all()

    def pump_state_icon_text(self, p):
        fault = bool(p['fault_feedback'] or p['manual_fault'])
        maint = bool(p['maintenance'])
        standby = bool(p['standby'])
        running = bool(p['run_feedback'])
        if fault and getattr(self, 'blink_on', True):
            return '🔴 ⚠️ 故障'
        if fault:
            return '⚠️ 故障'
        if maint:
            return '🟡 检修'
        if running:
            return '🟢 运行'
        if standby:
            return '🔵 备用'
        return '⚪ 停止'

    def pump_state_tag(self, p):
        if bool(p['fault_feedback'] or p['manual_fault']):
            return 'fault'
        if bool(p['maintenance']):
            return 'maintenance'
        if bool(p['run_feedback']):
            return 'running'
        if bool(p['standby']):
            return 'standby'
        return 'stopped'

    def is_auto_mode(self):
        st = self.get_station()
        return bool(st and st['control_mode'] == 'auto')

    def refresh_manual_status_only(self):
        """手动控制页防闪烁：定时刷新时只更新顶部状态，不重建按钮卡片。
        水泵启停/设频/状态切换后会主动刷新整页。"""
        st = self.get_station()
        if hasattr(self, 'mode_status'):
            if st:
                self.mode_status.config(
                    text=f"当前运行模式：{MODE_LABEL.get(st['control_mode'], st['control_mode'])}    自动调节状态：{st['emergency_level']}")
            else:
                self.mode_status.config(text='当前运行模式：-    自动调节状态：-')

    def refresh_manual_cards(self, pumps):
        if not hasattr(self, 'manual_cards'):
            return
        for w in self.manual_cards.winfo_children():
            w.destroy()
        self.manual_freq_entries = {}
        if not pumps:
            ttk.Label(self.manual_cards, text='当前没有水泵，请先新增泵站或在水泵管理中配置水泵。',
                      foreground='red').grid(row=0, column=0, padx=10, pady=10, sticky='w')
            return
        try:
            screen_w = self.root.winfo_width() or self.root.winfo_screenwidth()
        except Exception:
            screen_w = 1366
        cols = 3 if screen_w >= 1500 else 2
        offset = 0
        if self.is_auto_mode():
            ttk.Label(self.manual_cards, text='当前泵站处于自动模式，手动操作按钮已锁定；切换到手动模式后才能操作。',
                      foreground='red', font=('Microsoft YaHei', 10, 'bold')).grid(row=0, column=0, columnspan=cols,
                                                                                   padx=10, pady=8, sticky='w')
            offset = 1
        btn_state = 'disabled' if self.is_auto_mode() else 'normal'
        for idx, p in enumerate(pumps):
            row = idx // cols + offset;
            col = idx % cols
            frame = ttk.LabelFrame(self.manual_cards, text=f"{p['pump_code']}  {p['pump_name']}")
            frame.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')
            feed_txt = ''
            if p['pump_type'] == 'centrifugal':
                fp = self.row('SELECT pump_code FROM pump WHERE id=?', (p['feed_pump_id'],)) if p[
                    'feed_pump_id'] else None
                feed_txt = '  给水泵：' + (fp['pump_code'] if fp else '未设置')
            ttk.Label(frame, text=f"{PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type'])}{feed_txt}",
                      font=('Microsoft YaHei', 9)).grid(row=0, column=0, columnspan=6, sticky='w', padx=5, pady=(3, 1))
            ttk.Label(frame,
                      text=f"{self.pump_state_icon_text(p)}   反馈:{float(p['frequency'] or 0):.1f}Hz   电流:{float(p['current'] or 0):.1f}A",
                      font=('Microsoft YaHei', 9, 'bold')).grid(row=1, column=0, columnspan=6, sticky='w', padx=4,
                                                                pady=1)
            ttk.Label(frame, text='设定Hz').grid(row=2, column=0, padx=3, pady=4, sticky='e')
            e = ttk.Entry(frame, width=7)
            e.insert(0, f"{float(p['set_frequency'] or p['frequency'] or p['start_frequency'] or 30):.1f}")
            e.grid(row=2, column=1, padx=3, pady=4, sticky='w')
            self.manual_freq_entries[p['id']] = e
            ttk.Button(frame, text='▶ 启动', style='Success.TButton', state=btn_state,
                       command=lambda pid=p['id']: self.manual_start_pid(pid)).grid(row=2, column=2, padx=2, pady=3,
                                                                                    sticky='ew')
            ttk.Button(frame, text='■ 停止', style='Danger.TButton', state=btn_state,
                       command=lambda pid=p['id']: self.manual_stop_pid(pid)).grid(row=2, column=3, padx=2, pady=3,
                                                                                   sticky='ew')
            ttk.Button(frame, text='⚙ 设频', style='Primary.TButton', state=btn_state,
                       command=lambda pid=p['id']: self.manual_setfreq_pid(pid)).grid(row=2, column=4, padx=2, pady=3,
                                                                                      sticky='ew')
            ttk.Button(frame, text='检修', state=btn_state,
                       command=lambda pid=p['id']: self.toggle_pump_field_pid(pid, 'maintenance')).grid(row=3, column=0,
                                                                                                        padx=2, pady=3,
                                                                                                        sticky='ew')
            ttk.Button(frame, text='故障', state=btn_state,
                       command=lambda pid=p['id']: self.toggle_pump_field_pid(pid, 'manual_fault')).grid(row=3,
                                                                                                         column=1,
                                                                                                         padx=2, pady=3,
                                                                                                         sticky='ew')
            ttk.Button(frame, text='备用', state=btn_state,
                       command=lambda pid=p['id']: self.toggle_pump_field_pid(pid, 'standby')).grid(row=3, column=2,
                                                                                                    padx=2, pady=3,
                                                                                                    sticky='ew')
            for cc in range(6):
                frame.columnconfigure(cc, weight=1)
        for cc in range(cols):
            self.manual_cards.columnconfigure(cc, weight=1)

    def _manual_freq_value(self, pid=None):
        try:
            if pid is not None and hasattr(self, 'manual_freq_entries') and pid in self.manual_freq_entries:
                return float(self.manual_freq_entries[pid].get() or 30)
        except Exception:
            pass
        p = self.row('SELECT start_frequency FROM pump WHERE id=?', (pid,)) if pid else None
        try:
            return float(p['start_frequency'] if p else 30)
        except Exception:
            return 30.0

    def _manual_operation_allowed(self):
        if self.is_auto_mode():
            messagebox.showwarning('提示', '当前泵站处于自动模式，手动操作已锁定。请先切换到手动模式。')
            return False
        return True

    def manual_start_pid(self, pid):
        if not self._manual_operation_allowed(): return
        p = self.row('SELECT * FROM pump WHERE id=?', (pid,))
        if not p:
            messagebox.showwarning('提示', '未找到该水泵')
            return
        freq = self._manual_freq_value(pid)
        if not messagebox.askyesno('确认启动',
                                   f'确认启动水泵 {p["pump_code"]} / {p["pump_name"]}？\n设定频率：{freq:.1f} Hz'):
            return
        ok, msg = self.service.start_pump(pid, freq, 'manual')
        messagebox.showinfo('启动结果', f'水泵 {p["pump_code"]} / {p["pump_name"]}：\n{msg}')
        self.refresh_all()

    def manual_stop_pid(self, pid):
        if not self._manual_operation_allowed(): return
        p = self.row('SELECT * FROM pump WHERE id=?', (pid,))
        ok, msg = self.service.stop_pump(pid, 'manual')
        name = f'{p["pump_code"]} / {p["pump_name"]}' if p else str(pid)
        messagebox.showinfo('停止结果', f'水泵 {name}：\n{msg}')
        self.refresh_all()

    def manual_setfreq_pid(self, pid):
        if not self._manual_operation_allowed(): return
        p = self.row('SELECT * FROM pump WHERE id=?', (pid,))
        freq = self._manual_freq_value(pid)
        ok, msg = self.service.set_freq(pid, freq)
        name = f'{p["pump_code"]} / {p["pump_name"]}' if p else str(pid)
        messagebox.showinfo('设频结果', f'水泵 {name}：\n{msg}')
        self.refresh_all()

    def toggle_pump_field_pid(self, pid, field):
        if not self._manual_operation_allowed(): return
        p = self.row('SELECT * FROM pump WHERE id=?', (pid,))
        if not p: return
        nv = 0 if p[field] else 1
        self.db.execute(f'UPDATE pump SET {field}=?, updated_at=? WHERE id=?', (nv, now(), pid))
        self.db.log('切换水泵状态', 'pump', pid, p['pump_name'], field, str(nv), 'success', 'manual_panel')
        self.refresh_all()

    def _sync_control_state_after_mode_change(self, sid, mode):
        """切换手动/自动后立即同步“泵站监控-运行总览”的控制状态，避免页面仍显示上一次手动状态。"""
        try:
            st = self.row('SELECT current_level,level_rise_rate FROM pump_station WHERE id=?', (sid,))
            rate = float(st['level_rise_rate'] or 0) if st else 0.0
            if mode == 'auto':
                self.service._set_station_decision(sid, rate, '已切换为自动模式，等待自动平衡控制投入',
                                                   control_state='自动模式', event_state='自动平衡待命',
                                                   action_type='等待自动控制刷新', next_action='后台控制循环即将接管')
            else:
                self.service._set_station_decision(sid, rate, '手动模式，自动控制未投入', control_state='手动模式',
                                                   event_state='手动待命', action_type='无自动动作',
                                                   next_action='等待人工操作或切换自动')
        except Exception as e:
            print('sync control state after mode change error', e)

    def change_mode(self, mode):
        st = self.get_station()
        if not st: return
        if mode not in ('manual', 'auto'):
            messagebox.showwarning('提示', '泵站模式只保留：手动、自动')
            return
        old = st['control_mode']
        sid = self.sid()
        status_text = '手动待命' if mode != 'auto' else '自动平衡待命'
        self.db.execute('UPDATE pump_station SET control_mode=?, emergency_level=?, updated_at=? WHERE id=?',
                        (mode, status_text, now(), sid))
        self._sync_control_state_after_mode_change(sid, mode)
        self.db.log('切换泵站运行模式', 'station', sid, st['station_name'], old, mode, 'success', 'operator')
        self.refresh_all()

    # Parameter configuration page
    # Parameter configuration page
    def build_config_page(self):
        f = self.pages['参数配置']
        top = tk.Frame(f, bg='#f3f6fb')
        top.pack(fill='x', padx=10, pady=(8, 4))
        tk.Label(top, text='⚙ 参数配置中心', font=('Microsoft YaHei', 15, 'bold'), bg='#f3f6fb', fg='#17365d').pack(
            side='left', padx=(8, 18), pady=8)
        self.config_station_label = ttk.Label(top, text='当前泵站：-', font=('Microsoft YaHei', 10, 'bold'),
                                              foreground='#005bbb')
        self.config_station_label.pack(side='left')

        sw = tk.Frame(f, bg='#f8f9fb')
        sw.pack(fill='x', padx=10, pady=4)
        tk.Label(sw, text='🏭 参数泵站', font=('Microsoft YaHei', 10, 'bold'), bg='#f8f9fb').pack(side='left', padx=8)
        self.config_station = ttk.Combobox(sw, width=38, state='readonly')
        self.config_station.pack(side='left', padx=5)
        ttk.Button(sw, text='切换到该泵站', command=self.config_switch_station).pack(side='left', padx=5)

        nb = ttk.Notebook(f)
        nb.pack(fill='both', expand=True, padx=10, pady=6)
        self.config_vars = {}
        groups = [
            ('level_control', '🌊 液位自动控制', [
                ('level_high_high', '超高液位：开启全部备用水泵', 'm'),
                ('target_level', '控制液位', 'm'),
                ('upper_level', '上限液位：加泵，运行台数控制在总数60%', 'm'),
                ('lower_level', '下限液位：减泵，运行台数控制在总数30%', 'm'),
                ('control_deadband', '控制死区：范围内不调节', 'm'),
                ('rise_rate_trigger', '上涨速率', 'm/min'),
                ('fall_rate_trigger', '下降速率', 'm/min'),
                ('freq_min', '最低频率', 'Hz'),
                ('freq_normal', '正常频率', 'Hz'),
                ('freq_max', '最高运行频率', 'Hz'),
                ('freq_step', '频率调整步长', 'Hz'),
                ('freq_adjust_interval_seconds', '调节刷新周期', 's'),
                ('add_pump_min_interval_seconds', '加泵最小间隔', 's'),
                ('reduce_pump_min_interval_seconds', '减泵最小间隔', 's')]),
            ('level_select', '📏 液位计二选一', [
                ('level_select_mode', '选择方式：主用优先/备用优先/平均/自动切换', ''),
                ('primary_level_instrument_code', '主用液位计编号', ''),
                ('backup_level_instrument_code', '备用液位计编号', ''),
                ('level_diff_alarm_m', '双液位偏差报警值', 'm')]),
            ('manual_control', '⏲ 启停延时', [
                ('feed_start_delay_seconds', '离心泵启动前给水泵预运行延时', 's'),
                ('feed_stop_delay_seconds', '离心泵启动后给水泵停止延时', 's'),
                ('start_feedback_timeout_seconds', '启动反馈超时判定', 's'),
                ('stop_feedback_timeout_seconds', '停止反馈超时判定', 's')]),
            ('current_check', '⚡ 电流判断', [
                ('current_low_value', '电流低值', 'A'), ('current_high_value', '电流高值', 'A'),
                ('current_check_delay_seconds', '电流判断延时', 's')]),
        ]
        for group, title, items in groups:
            page = tk.Frame(nb, bg='#eef2f7')
            nb.add(page, text=title)
            self.config_vars[group] = {}
            desc = tk.Frame(page, bg='#eef2f7')
            desc.pack(fill='x', padx=10, pady=(10, 4))
            tk.Label(desc, text=title, font=('Microsoft YaHei', 13, 'bold'), bg='#eef2f7', fg='#17365d').pack(
                side='left')
            grid = tk.Frame(page, bg='#eef2f7')
            grid.pack(fill='both', expand=True, padx=10, pady=4)
            for i, (code, name, unit) in enumerate(items):
                r = i // 3;
                c = i % 3
                card = tk.Frame(grid, bg='white', highlightbackground='#d8e0ea', highlightthickness=1)
                card.grid(row=r, column=c, sticky='nsew', padx=8, pady=8)
                grid.grid_columnconfigure(c, weight=1)
                tk.Label(card, text=f"{self._param_icon(code, group)} {name}", font=('Microsoft YaHei', 10, 'bold'),
                         bg='white', fg='#1f3b5f').pack(anchor='w', padx=10, pady=(8, 3))
                line = tk.Frame(card, bg='white');
                line.pack(fill='x', padx=10, pady=(2, 8))
                e = ttk.Entry(line, width=16);
                e.pack(side='left')
                tk.Label(line, text=unit, font=('Microsoft YaHei', 9), bg='white', fg='#566573').pack(side='left',
                                                                                                      padx=6)
                tk.Label(card, text=code, font=('Consolas', 8), bg='white', fg='#9aa3ad').pack(anchor='w', padx=10,
                                                                                               pady=(0, 8))
                self.config_vars[group][code] = e
            btnbar = tk.Frame(page, bg='#eef2f7')
            btnbar.pack(fill='x', padx=18, pady=10)
            tk.Button(btnbar, text='💾 保存本页参数', font=('Microsoft YaHei', 10, 'bold'), bg='#0b63ce', fg='white',
                      relief='flat', padx=14, pady=6, command=lambda g=group: self.save_config_group(g)).pack(
                side='left')

    def config_switch_station(self):
        s = self.config_station.get() if hasattr(self, 'config_station') else ''
        try:
            sid = int(s.split('|')[0].strip())
        except Exception:
            messagebox.showwarning('提示', '请先选择泵站')
            return
        self.db.set_current_station(sid)
        self.current_station_id = sid
        self.db.log('参数配置切换泵站', 'station', sid, self.station_title(), '', '切换', 'success', 'operator')
        self.refresh_all()

    def refresh_config_params(self):
        if not hasattr(self, 'config_vars'):
            return
        st = self.get_station()
        if hasattr(self, 'config_station_label'):
            self.config_station_label.config(text='当前泵站：' + (self.station_title() if st else '-'))
        if hasattr(self, 'config_station'):
            vals = [f"{r['id']} | {r['station_code']} | {r['station_name']}" for r in
                    self.rows('SELECT id,station_code,station_name FROM pump_station ORDER BY id')]
            self.config_station['values'] = vals
            cur = ''
            for v in vals:
                if self.sid() and v.startswith(str(self.sid()) + ' |'):
                    cur = v;
                    break
            self.config_station.set(cur if cur else (vals[0] if vals else ''))
        if not st:
            for group, mp in self.config_vars.items():
                for e in mp.values():
                    e.delete(0, 'end')
            return
        for group, mp in self.config_vars.items():
            for code, e in mp.items():
                row = self.row(
                    'SELECT param_value FROM parameter_value WHERE scope_type="station" AND scope_id=? AND param_group=? AND param_code=?',
                    (self.sid(), group, code))
                e.delete(0, 'end')
                e.insert(0, row['param_value'] if row else '')

    def save_config_group(self, group):
        if not self.sid():
            messagebox.showwarning('提示', '请先选择泵站')
            return
        for code, e in self.config_vars.get(group, {}).items():
            self.db.set_param(self.sid(), group, code, e.get().strip())
        self.db.log('保存参数配置', 'station', self.sid(), group, '', '保存', 'success', '参数配置页')
        messagebox.showinfo('成功', '参数已保存到当前泵站')
        self.refresh_all()

    # Communication settings page
    def build_comm_page(self):
        f = self.pages['通讯设置']
        top = ttk.Frame(f);
        top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top,
                  text='Modbus TCP 通讯参数按泵站/设备独立设置。变量地址、功能码、数据类型在“变量/点位管理”中设置；通讯状态由后台自动判断；变量值按实际设备采集，不再使用仿真值。',
                  foreground='blue', font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w')
        body = ttk.Frame(f);
        body.pack(fill='both', expand=True, padx=8, pady=6)
        left = ttk.Frame(body);
        left.pack(side='left', fill='both', expand=True)
        right = ttk.LabelFrame(body, text='通讯设备编辑');
        right.pack(side='right', fill='y', padx=8)
        cols = ('ID', '设备编号', '设备名称', '类型', 'IP', '端口', '站号', '超时ms', '轮询ms', '启用', '状态')
        self.device_tree = ttk.Treeview(left, columns=cols, show='headings', height=20)
        for c in cols:
            self.device_tree.heading(c, text=c);
            self.device_tree.column(c, width=90 if c != '设备名称' else 160, anchor='center')
        self.device_tree.pack(fill='both', expand=True);
        self.device_tree.bind('<<TreeviewSelect>>', self.on_device_select)
        self.device_vars = {}
        fields = [('device_code', '设备编号'), ('device_name', '设备名称'), ('device_type', '设备类型'),
                  ('ip_address', 'IP地址'), ('port', '端口'), ('slave_id', '站号/单元ID'), ('timeout_ms', '超时ms'),
                  ('poll_interval_ms', '轮询ms'), ('enabled', '启用'), ('remark', '备注')]
        for i, (k, l) in enumerate(fields):
            ttk.Label(right, text=l).grid(row=i, column=0, sticky='e', padx=4, pady=3)
            if k == 'device_type':
                w = ttk.Combobox(right, width=26, state='readonly', values=['PLC', 'VFD', 'METER', 'IO', 'OTHER'])
            elif k in ('enabled', 'bypassed'):
                w = ttk.Combobox(right, width=26, state='readonly', values=['1', '0'])
            else:
                w = ttk.Entry(right, width=28)
            w.grid(row=i, column=1, padx=4, pady=3);
            self.device_vars[k] = w
        btn = ttk.Frame(right);
        btn.grid(row=len(fields), column=0, columnspan=2, pady=8)
        ttk.Button(btn, text='新增设备', command=self.add_device).pack(side='left', padx=3)
        ttk.Button(btn, text='保存修改', command=self.save_device).pack(side='left', padx=3)
        ttk.Button(btn, text='删除设备', command=self.delete_device).pack(side='left', padx=3)
        ttk.Button(btn, text='清空', command=self.clear_device_form).pack(side='left', padx=3)

    def refresh_device_list(self):
        if not hasattr(self, 'device_tree'): return
        self.clear_tree(self.device_tree)
        for d in self.rows('SELECT * FROM modbus_device WHERE station_id=? ORDER BY id', (self.sid(),)):
            self.device_tree.insert('', 'end', iid=str(d['id']),
                                    values=(d['id'], d['device_code'], d['device_name'], d['device_type'],
                                            d['ip_address'], d['port'], d['slave_id'], d['timeout_ms'],
                                            d['poll_interval_ms'], '是' if d['enabled'] else '否',
                                            d['communication_status']))
        if hasattr(self, 'point_vars'):
            self.refresh_point_device_choices()
        if not getattr(self, 'edit_device_id', None): self.clear_device_form()

    def clear_device_form(self):
        self.edit_device_id = None
        st = self.get_station()
        code = self.db.next_modbus_device_code(st['station_code'] if st else 'ST', self.sid()) if st else 'PLC_ST'
        vals = {'device_code': code, 'device_name': (st['station_name'] + ' PLC' if st else 'PLC'),
                'device_type': 'PLC', 'ip_address': '192.168.1.10', 'port': '502', 'slave_id': '1',
                'timeout_ms': '3000', 'poll_interval_ms': '1000', 'enabled': '1', 'remark': ''}
        for k, w in self.device_vars.items(): self._set_widget_value(w, vals.get(k, ''))

    def on_device_select(self, e=None):
        sel = self.device_tree.selection()
        if not sel: return
        did = int(sel[0]);
        d = self.row('SELECT * FROM modbus_device WHERE id=?', (did,));
        self.edit_device_id = did
        for k, w in self.device_vars.items(): self._set_widget_value(w, str(
            d[k] if k in d.keys() and d[k] is not None else ''))

    def get_device_form(self):
        d = {k: w.get().strip() for k, w in self.device_vars.items()}
        if not d.get('device_code'):
            st = self.get_station();
            d['device_code'] = self.db.next_modbus_device_code(st['station_code'] if st else 'ST', self.sid())
        if not d.get('device_name'):
            d['device_name'] = '通讯设备'
        if not d.get('device_type'):
            d['device_type'] = 'PLC'
        defaults = {'port': '502', 'slave_id': '1', 'timeout_ms': '3000', 'poll_interval_ms': '1000', 'enabled': '1'}
        for k, v in defaults.items():
            if d.get(k, '') == '':
                d[k] = v
                if k in self.device_vars:
                    self._set_widget_value(self.device_vars[k], v)
        return d

    def _set_widget_value(self, widget, value):
        try:
            widget.delete(0, 'end');
            widget.insert(0, str(value))
        except Exception:
            try:
                widget.set(str(value))
            except Exception:
                pass

    def add_device(self):
        if not self.sid(): messagebox.showwarning('提示', '请先选择泵站'); return
        d = self.get_device_form()
        if self.row('SELECT id FROM modbus_device WHERE device_code=?', (d['device_code'],)):
            st = self.get_station();
            new_code = self.db.next_modbus_device_code(st['station_code'] if st else 'ST', self.sid())
            if messagebox.askyesno('设备编号重复', f'设备编号 {d["device_code"]} 已存在，是否自动改为 {new_code}？'):
                d['device_code'] = new_code
                self._set_widget_value(self.device_vars['device_code'], new_code)
            else:
                return
        try:
            self.edit_device_id = self.db.add_modbus_device(self.sid(), d);
            self.refresh_device_list();
            self.clear_device_form();
            self.refresh_dashboard();
            messagebox.showinfo('成功', '通讯设备已新增')
        except Exception as e:
            messagebox.showerror('保存失败', '请检查端口、站号、超时、轮询等数字参数是否为空。\n\n详细信息：' + str(e))

    def save_device(self):
        if not getattr(self, 'edit_device_id', None): messagebox.showwarning('提示', '请先选择设备'); return
        d = self.get_device_form()
        if self.row('SELECT id FROM modbus_device WHERE device_code=? AND id<>?',
                    (d['device_code'], self.edit_device_id)):
            messagebox.showerror('失败', '设备编号全系统唯一，当前编号已存在');
            return
        try:
            self.db.update_modbus_device(self.edit_device_id, d);
            self.refresh_device_list();
            self.refresh_point_device_choices();
            self.refresh_dashboard();
            messagebox.showinfo('成功', '通讯设备已保存')
        except Exception as e:
            messagebox.showerror('保存失败', '请检查端口、站号、超时、轮询等数字参数是否为空。\n\n详细信息：' + str(e))

    def delete_device(self):
        if getattr(self, 'edit_device_id', None) and messagebox.askyesno('确认',
                                                                         '删除该通讯设备？变量点位将取消设备绑定。'):
            self.db.execute('UPDATE modbus_point SET device_id=NULL WHERE device_id=?', (self.edit_device_id,))
            self.db.execute('DELETE FROM modbus_device WHERE id=?', (self.edit_device_id,));
            self.edit_device_id = None;
            self.refresh_device_list();
            self.refresh_point_device_choices();
            self.refresh_point_list();
            self.refresh_dashboard()

    # Point page
    def build_point_page(self):
        f = self.pages['变量/点位管理']
        main = ttk.Panedwindow(f, orient='horizontal')
        main.pack(fill='both', expand=True, padx=8, pady=8)
        left = ttk.Frame(main);
        right_outer = ttk.LabelFrame(main, text='变量/点位编辑')
        main.add(left, weight=3);
        main.add(right_outer, weight=2)
        cols = ('ID', '通讯设备', '编号', '名称', '功能区', '地址', '变量类型', '读写类型', '启用', '当前值')
        self.point_tree = ttk.Treeview(left, columns=cols, show='headings', height=24)
        widths = {'ID': 55, '通讯设备': 150, '编号': 160, '名称': 180, '功能区': 80, '地址': 90, '变量类型': 90,
                  '读写类型': 90, '启用': 60, '当前值': 120}
        for c in cols:
            self.point_tree.heading(c, text=c);
            self.point_tree.column(c, width=widths.get(c, 95), anchor='center')
        py = ttk.Scrollbar(left, orient='vertical', command=self.point_tree.yview)
        px = ttk.Scrollbar(left, orient='horizontal', command=self.point_tree.xview)
        self.point_tree.configure(yscrollcommand=py.set, xscrollcommand=px.set)
        self.point_tree.pack(side='left', fill='both', expand=True);
        py.pack(side='right', fill='y');
        px.pack(side='bottom', fill='x')
        self.point_tree.bind('<<TreeviewSelect>>', self.on_point_select)

        self.point_form_canvas = tk.Canvas(right_outer, highlightthickness=0, width=400, bg='#f8fafc')
        pscroll = ttk.Scrollbar(right_outer, orient='vertical', command=self.point_form_canvas.yview)
        form = tk.Frame(self.point_form_canvas, bg='#f8fafc')
        self.point_form_canvas.create_window((0, 0), window=form, anchor='nw')
        self.point_form_canvas.configure(yscrollcommand=pscroll.set)
        form.bind('<Configure>',
                  lambda e: self.point_form_canvas.configure(scrollregion=self.point_form_canvas.bbox('all')))
        self.point_form_canvas.pack(side='left', fill='both', expand=True)
        pscroll.pack(side='right', fill='y')

        self.point_vars = {}
        base_fields = [
            ('device_id', '通讯设备'), ('point_code', '点位编号'), ('point_name', '点位名称'),
            ('point_usage', '变量用途'),
            ('function_code', '功能码'), ('register_address', '寄存器/线圈地址'), ('register_count', '寄存器/点数'),
            ('data_type', '数据类型'), ('byte_order', '字节序'), ('read_write', '读写类型'), ('unit', '单位'),
            ('scale', '倍率'), ('offset_value', '偏移'), ('enabled', '启用'), ('remark', '备注')
        ]
        self.point_form_rows = {}
        for i, (k, l) in enumerate(base_fields):
            lab = ttk.Label(form, text=l)
            lab.grid(row=i, column=0, sticky='e', padx=6, pady=4)
            if k == 'device_id':
                w = ttk.Combobox(form, width=25, state='normal', values=[])
            elif k == 'point_usage':
                w = ttk.Combobox(form, width=25, state='readonly', values=['模拟量', '状态量', '控制指令', '频率设定'])
            elif k == 'function_code':
                w = ttk.Combobox(form, width=25, state='readonly', values=['1', '2', '3', '4', '5', '6', '15', '16'])
            elif k == 'data_type':
                w = ttk.Combobox(form, width=25, state='readonly',
                                 values=['float32', 'int16', 'uint16', 'int32', 'uint32', 'bool'])
            elif k == 'byte_order':
                w = ttk.Combobox(form, width=25, state='readonly', values=['ABCD', 'CDAB', 'BADC', 'DCBA'])
            elif k == 'read_write':
                w = ttk.Combobox(form, width=25, state='readonly', values=['read', 'write', 'read_write'])
            elif k == 'enabled':
                w = ttk.Combobox(form, width=25, state='readonly', values=['1', '0'])
            else:
                w = ttk.Entry(form, width=28)
            w.grid(row=i, column=1, padx=6, pady=4, sticky='ew')
            self.point_vars[k] = w;
            self.point_form_rows[k] = (lab, w)
        form.grid_columnconfigure(1, weight=1)

        start_row = len(base_fields)
        for j, (k, l) in enumerate([('command_value', '写入值')]):
            lab = ttk.Label(form, text=l)
            ent = ttk.Entry(form, width=28)
            lab.grid(row=start_row + j, column=0, sticky='e', padx=6, pady=4)
            ent.grid(row=start_row + j, column=1, padx=6, pady=4, sticky='ew')
            self.point_vars[k] = ent;
            self.point_form_rows[k] = (lab, ent)

        b = ttk.Frame(form);
        b.grid(row=start_row + 4, column=0, columnspan=2, pady=8, sticky='ew')
        for c in range(2): b.grid_columnconfigure(c, weight=1)
        ttk.Button(b, text='新增变量', command=self.add_point).grid(row=0, column=0, padx=4, pady=3, sticky='ew')
        ttk.Button(b, text='保存修改', command=self.save_point).grid(row=0, column=1, padx=4, pady=3, sticky='ew')
        ttk.Button(b, text='删除变量', command=self.delete_point).grid(row=1, column=0, padx=4, pady=3, sticky='ew')
        ttk.Button(b, text='清空', command=self.clear_point_form).grid(row=1, column=1, padx=4, pady=3, sticky='ew')

        self.point_vars['point_usage'].bind('<<ComboboxSelected>>', lambda e: self.update_point_command_fields())
        self.point_vars['device_id'].bind('<<ComboboxSelected>>', lambda e: self.on_point_area_change())
        self.point_vars['function_code'].bind('<<ComboboxSelected>>', lambda e: self.on_point_function_change())
        self.point_vars['data_type'].bind('<<ComboboxSelected>>', lambda e: self.on_point_data_type_change())
        self.update_point_command_fields()

    def modbus_area_from_function(self, fc):
        try:
            fc = int(float(fc or 3))
        except Exception:
            fc = 3
        if fc in (1, 5, 15): return '0区-线圈输出'
        if fc == 2: return '1区-离散输入'
        if fc == 4: return '3区-输入寄存器'
        return '4区-保持寄存器'

    def function_from_area(self, area, read_write='read'):
        area = str(area or '')
        rw = (read_write or 'read').lower()
        if area.startswith('0区'):
            return 5 if rw in ('write', 'command', 'read_write') else 1
        if area.startswith('1区'):
            return 2
        if area.startswith('3区'):
            return 4
        return 6 if rw in ('write', 'command', 'read_write') else 3

    def base_address_from_area(self, area):
        area = str(area or '')
        if area.startswith('0区'): return 1
        if area.startswith('1区'): return 10001
        if area.startswith('3区'): return 30001
        return 40001

    def _point_recommended_count(self, dtype=None):
        dtype = (dtype or (self.point_vars.get('data_type').get() if hasattr(self,
                                                                             'point_vars') and 'data_type' in self.point_vars else 'float32')).strip()
        return 1 if dtype in ('int16', 'uint16', 'bool') else 2

    def _point_area_from_form(self):
        try:
            return self.modbus_area_from_function(self.point_vars['function_code'].get())
        except Exception:
            return '4区-保持寄存器'

    def next_register_address(self, area=None):
        # 按当前功能码所属区段自动建议地址；保存时不再强制覆盖用户手工修改的地址。
        area = area or self._point_area_from_form()
        base = self.base_address_from_area(area)
        did = None
        try:
            did = self._device_id_from_display(self.point_vars['device_id'].get())
        except Exception:
            did = None
        if did:
            rows = self.rows(
                'SELECT register_address, register_count FROM modbus_point WHERE station_id=? AND device_id=?',
                (self.sid(), did))
        else:
            rows = self.rows('SELECT register_address, register_count FROM modbus_point WHERE station_id=?',
                             (self.sid(),))
        max_end = None
        for r in rows:
            try:
                a = int(r['register_address']);
                cnt = max(1, int(r['register_count'] or 1))
                if base <= a < base + 10000:
                    end = a + cnt
                    max_end = end if max_end is None else max(max_end, end)
            except Exception:
                pass
        return base if max_end is None else max_end

    def on_point_area_change(self):
        self._set_widget_value(self.point_vars['register_address'],
                               str(self.next_register_address(self._point_area_from_form())))
        self.update_point_command_fields()

    def on_point_function_change(self):
        self._set_widget_value(self.point_vars['register_address'],
                               str(self.next_register_address(self._point_area_from_form())))
        self.update_point_command_fields()

    def on_point_data_type_change(self):
        if 'register_count' in self.point_vars:
            self._set_widget_value(self.point_vars['register_count'], str(self._point_recommended_count()))
        self.update_point_command_fields()

    def update_point_command_fields(self):
        usage = (self.point_vars.get('point_usage').get() if hasattr(self,
                                                                     'point_vars') and 'point_usage' in self.point_vars else '')
        is_control = usage in ('控制指令', '频率设定')
        # 控制指令/频率设定只显示写入值；启动值/停止值不再作为界面字段。
        row = self.point_form_rows.get('command_value')
        if row:
            lab, w = row
            if is_control:
                lab.grid();
                w.grid()
            else:
                lab.grid_remove();
                w.grid_remove()
        # 控制指令是一次性写入值，不需要倍率和偏移；模拟量/状态量保留倍率偏移。
        for k in ('scale', 'offset_value'):
            row = self.point_form_rows.get(k)
            if not row: continue
            lab, w = row
            if usage == '控制指令':
                lab.grid_remove();
                w.grid_remove()
            else:
                lab.grid();
                w.grid()

    def refresh_point_list(self):
        if not hasattr(self, 'point_tree'): return
        self.refresh_point_device_choices()
        self.clear_tree(self.point_tree)
        for p in self.rows("""SELECT p.*, d.device_code
                              FROM modbus_point p
                                       LEFT JOIN modbus_device d ON p.device_id = d.id
                              WHERE p.station_id = ?
                              ORDER BY p.id""", (self.sid(),)):
            area = self.modbus_area_from_function(p['function_code'])
            self.point_tree.insert('', 'end', iid=str(p['id']),
                                   values=(p['id'], p['device_code'] or '未绑定', p['point_code'], p['point_name'],
                                           area, p['register_address'], p['data_type'], p['read_write'],
                                           '是' if p['enabled'] else '否', p['last_value']))
        if not self.edit_point_id: self.clear_point_form()

    def refresh_point_device_choices(self):
        if not hasattr(self, 'point_vars') or 'device_id' not in self.point_vars: return
        choices = []
        for d in self.rows('SELECT id, device_code, device_name FROM modbus_device WHERE station_id=? ORDER BY id',
                           (self.sid(),)):
            choices.append(f"{d['id']} | {d['device_code']} | {d['device_name']}")
        self.point_vars['device_id']['values'] = choices

    def _device_display_from_id(self, did):
        if not did: return ''
        d = self.row('SELECT id, device_code, device_name FROM modbus_device WHERE id=?', (did,))
        return f"{d['id']} | {d['device_code']} | {d['device_name']}" if d else ''

    def _device_id_from_display(self, text):
        text = (text or '').strip()
        if not text: return None
        try:
            return int(text.split('|')[0].strip())
        except Exception:
            return None

    def clear_point_form(self):
        self.edit_point_id = None
        self.refresh_point_device_choices()
        first_device = ''
        vals = list(self.point_vars.get('device_id', {}).cget('values')) if hasattr(
            self.point_vars.get('device_id', None), 'cget') else []
        if vals: first_device = vals[0]
        area = '4区-保持寄存器'
        vals = {'device_id': first_device, 'point_code': 'NEW_POINT', 'point_name': '新变量', 'point_usage': '模拟量',
                'function_code': '3', 'register_address': str(self.next_register_address(area)), 'register_count': '2',
                'data_type': 'float32', 'byte_order': 'ABCD', 'read_write': 'read_write', 'unit': '', 'scale': '1',
                'offset_value': '0', 'command_value': '', 'enabled': '1', 'remark': ''}
        for k, w in self.point_vars.items(): self._set_widget_value(w, vals.get(k, ''))
        self.update_point_command_fields()

    def on_point_select(self, e=None):
        sel = self.point_tree.selection();
        if not sel: return
        pid = int(sel[0]);
        p = self.row('SELECT * FROM modbus_point WHERE id=?', (pid,));
        self.edit_point_id = pid
        self.refresh_point_device_choices()
        for k, w in self.point_vars.items():
            if k == 'device_id':
                val = self._device_display_from_id(p['device_id'])
            elif k == 'point_usage':
                val = str(p['point_usage'] if 'point_usage' in p.keys() and p['point_usage'] else '模拟量')
            elif k in ('command_start_value', 'command_stop_value', 'command_value'):
                val = str(p[k] if k in p.keys() and p[k] is not None else '')
            else:
                val = str(p[k] if k in p.keys() and p[k] is not None else '')
            self._set_widget_value(w, val)
        self.update_point_command_fields()

    def get_point_form(self):
        d = {k: w.get().strip() for k, w in self.point_vars.items()}
        defaults = {
            'point_usage': '模拟量', 'function_code': '3', 'data_type': 'float32', 'byte_order': 'ABCD',
            'read_write': 'read_write', 'scale': '1', 'offset_value': '0', 'enabled': '1', 'unit': ''
        }
        for k, v in defaults.items():
            if d.get(k, '') == '':
                d[k] = v
                if k in self.point_vars:
                    self._set_widget_value(self.point_vars[k], v)
        if not d.get('register_count'):
            d['register_count'] = str(self._point_recommended_count(d.get('data_type')))
            if 'register_count' in self.point_vars:
                self._set_widget_value(self.point_vars['register_count'], d['register_count'])
        if not d.get('register_address'):
            d['register_address'] = str(
                self.next_register_address(self.modbus_area_from_function(d.get('function_code'))))
            if 'register_address' in self.point_vars:
                self._set_widget_value(self.point_vars['register_address'], d['register_address'])
        if d.get('point_usage') not in ('控制指令', '频率设定'):
            d['command_value'] = ''
        if d.get('point_usage') == '控制指令':
            d['scale'] = '1';
            d['offset_value'] = '0'
        d['command_start_value'] = '1'
        d['command_stop_value'] = '5'
        d['modbus_area'] = self.modbus_area_from_function(d.get('function_code'))
        return d

    def resolve_object_id(self, otype):
        return self.sid() if otype == 'station' else None

    def add_point(self):
        d = self.get_point_form();
        otype = 'station';
        oid = self.sid();
        did = self._device_id_from_display(d.get('device_id'))
        try:
            if did is None:
                dev = self.row('SELECT id FROM modbus_device WHERE station_id=? ORDER BY id LIMIT 1', (self.sid(),));
                did = dev['id'] if dev else None
            self.db.execute(
                """INSERT INTO modbus_point(device_id, station_id, object_type, object_id, object_code, point_code,
                                            point_name, data_code, point_usage, status_true_value, status_false_value,
                                            function_code, register_address, register_count, data_type, byte_order,
                                            scale, offset_value, unit, read_write, command_start_value,
                                            command_stop_value, command_value, enabled, bypassed, last_update_time,
                                            remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (did, self.sid(), otype, oid, '', d['point_code'], d['point_name'], 'custom',
                 d.get('point_usage', '模拟量'), 1, 0, int(d['function_code']), int(d['register_address']),
                 int(d['register_count']), d['data_type'], d.get('byte_order', 'ABCD'), float(d['scale']),
                 float(d.get('offset_value') or 0), d.get('unit', ''), d['read_write'],
                 d.get('command_start_value', ''), d.get('command_stop_value', ''), d.get('command_value', ''),
                 int(d['enabled']), 0, now(), d['remark']))
            self.refresh_point_list()
            messagebox.showinfo('成功', '变量/点位已新增')
        except Exception as e:
            messagebox.showerror('失败', '请检查通讯设备、寄存器地址、倍率等参数是否正确。\n\n详细信息：' + str(e))

    def save_point(self):
        if not self.edit_point_id: return
        d = self.get_point_form();
        otype = 'station';
        oid = self.sid();
        did = self._device_id_from_display(d.get('device_id'))
        try:
            self.db.execute("""UPDATE modbus_point
                               SET device_id=?,
                                   object_type=?,
                                   object_id=?,
                                   object_code=?,
                                   point_code=?,
                                   point_name=?,
                                   data_code=?,
                                   point_usage=?,
                                   status_true_value=?,
                                   status_false_value=?,
                                   function_code=?,
                                   register_address=?,
                                   register_count=?,
                                   data_type=?,
                                   byte_order=?,
                                   scale=?,
                                   offset_value=?,
                                   unit=?,
                                   read_write=?,
                                   command_start_value=?,
                                   command_stop_value=?,
                                   command_value=?,
                                   enabled=?,
                                   bypassed=?,
                                   last_update_time=?,
                                   remark=?
                               WHERE id = ?""", (did, otype, oid, '', d['point_code'], d['point_name'], 'custom',
                                                 d.get('point_usage', '模拟量'), 1, 0, int(d['function_code']),
                                                 int(d['register_address']), int(d['register_count']), d['data_type'],
                                                 d.get('byte_order', 'ABCD'), float(d['scale']),
                                                 float(d.get('offset_value') or 0), d.get('unit', ''), d['read_write'],
                                                 d.get('command_start_value', ''), d.get('command_stop_value', ''),
                                                 d.get('command_value', ''), int(float(d['enabled'])), 0, now(),
                                                 d['remark'], self.edit_point_id))
            old_id = self.edit_point_id
            self.refresh_point_list()
            self.edit_point_id = old_id
            try:
                self.point_tree.selection_set(str(old_id));
                self.point_tree.see(str(old_id))
            except Exception:
                pass
            messagebox.showinfo('成功', '变量/点位参数已保存')
        except Exception as e:
            messagebox.showerror('失败', '变量参数保存失败，请检查数字项是否为空。\n\n详细信息：' + str(e))

    def delete_point(self):
        if self.edit_point_id and messagebox.askyesno('确认', '删除变量？'):
            self.db.execute('DELETE FROM modbus_point WHERE id=?', (self.edit_point_id,));
            self.edit_point_id = None;
            self.refresh_point_list()

    # Video monitor and camera configuration
    def build_video_page(self):
        f = self.pages['视频监控']
        top = ttk.Frame(f);
        top.pack(fill='x', padx=10, pady=8)
        ttk.Label(top, text='视频泵站').pack(side='left')
        self.video_station_cb = ttk.Combobox(top, width=34, state='readonly')
        self.video_station_cb.pack(side='left', padx=6)
        ttk.Button(top, text='切换泵站', command=self.switch_video_station).pack(side='left', padx=4)
        ttk.Button(top, text='打开全部视频', command=self.start_all_cameras).pack(side='left', padx=4)
        ttk.Button(top, text='停止全部视频', command=self.stop_all_cameras).pack(side='left', padx=4)
        ttk.Label(top, text='显示比例').pack(side='left', padx=(18, 4))
        self.video_ratio_cb = ttk.Combobox(top, width=10, state='readonly', values=['16:9', '4:3', '自适应'])
        self.video_ratio_cb.set('16:9')
        self.video_ratio_cb.pack(side='left')
        ttk.Label(top, text='视频四宫格按比例缩放显示').pack(side='left', padx=10)

        self.video_grid = ttk.Frame(f)
        self.video_grid.pack(fill='both', expand=True, padx=10, pady=8)
        self.video_cards = {}
        for i in range(4):
            r = i // 2;
            c = i % 2
            card = ttk.LabelFrame(self.video_grid, text=f'摄像头{i + 1}')
            card.grid(row=r, column=c, sticky='nsew', padx=6, pady=6)
            self.video_grid.grid_rowconfigure(r, weight=1)
            self.video_grid.grid_columnconfigure(c, weight=1)
            view = tk.Label(card, text='未打开视频', bg='#111827', fg='white', font=('Microsoft YaHei', 14, 'bold'),
                            anchor='center')
            view.pack(fill='both', expand=True, padx=4, pady=4)
            view.bind('<Configure>', lambda e, idx=i: self._on_video_view_resize(idx))
            info = ttk.Label(card, text='状态：-')
            info.pack(fill='x', padx=4)
            btn = ttk.Frame(card);
            btn.pack(fill='x', padx=4, pady=4)
            ttk.Button(btn, text='打开', command=lambda idx=i: self.start_camera_by_slot(idx)).grid(row=0, column=0,
                                                                                                    padx=2, pady=2,
                                                                                                    sticky='ew')
            ttk.Button(btn, text='停止', command=lambda idx=i: self.stop_camera_by_slot(idx)).grid(row=0, column=1,
                                                                                                   padx=2, pady=2,
                                                                                                   sticky='ew')
            ttk.Button(btn, text='抓图', command=lambda idx=i: self.snapshot_camera_by_slot(idx)).grid(row=0, column=2,
                                                                                                       padx=2, pady=2,
                                                                                                       sticky='ew')
            ttk.Button(btn, text='录像', command=lambda idx=i: self.toggle_record_by_slot(idx)).grid(row=0, column=3,
                                                                                                     padx=2, pady=2,
                                                                                                     sticky='ew')
            ptz = ttk.Frame(card);
            ptz.pack(fill='x', padx=4, pady=(0, 4))
            labels = [('上', 'up'), ('下', 'down'), ('左', 'left'), ('右', 'right'), ('近', 'zoom_in'),
                      ('远', 'zoom_out')]
            for j, (txt, act) in enumerate(labels):
                ttk.Button(ptz, text=txt, width=4, command=lambda idx=i, a=act: self.ptz_camera_by_slot(idx, a)).grid(
                    row=0, column=j, padx=1, sticky='ew')
            for j in range(6): ptz.grid_columnconfigure(j, weight=1)
            for j in range(4): btn.grid_columnconfigure(j, weight=1)
            self.video_cards[i] = {'frame': card, 'view': view, 'info': info, 'camera_id': None}

    def build_camera_config_page(self):
        f = self.pages['视频配置']
        top = ttk.Frame(f);
        top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top, text='配置泵站').pack(side='left')
        self.camera_station_cb = ttk.Combobox(top, width=34, state='readonly')
        self.camera_station_cb.pack(side='left', padx=6)
        ttk.Button(top, text='切换泵站', command=self.switch_camera_config_station).pack(side='left', padx=4)
        ttk.Button(top, text='生成/补齐4个摄像头', command=self.ensure_current_cameras).pack(side='left', padx=4)

        body = ttk.Frame(f);
        body.pack(fill='both', expand=True, padx=8, pady=6)
        left = ttk.Frame(body);
        left.pack(side='left', fill='both', expand=True)
        right = ttk.LabelFrame(body, text='摄像头参数');
        right.pack(side='right', fill='y', padx=8)
        cols = ('ID', '编号', '名称', '位置', '类型', 'IP', '端口', '启用', '状态', 'RTSP')
        self.camera_tree = ttk.Treeview(left, columns=cols, show='headings', height=18)
        widths = {'ID': 50, '编号': 80, '名称': 120, '位置': 150, '类型': 80, 'IP': 130, '端口': 70, '启用': 60,
                  '状态': 80, 'RTSP': 260}
        for c in cols:
            self.camera_tree.heading(c, text=c);
            self.camera_tree.column(c, width=widths.get(c, 90), anchor='center')
        ys = ttk.Scrollbar(left, orient='vertical', command=self.camera_tree.yview)
        xs = ttk.Scrollbar(left, orient='horizontal', command=self.camera_tree.xview)
        self.camera_tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.camera_tree.pack(side='left', fill='both', expand=True);
        ys.pack(side='right', fill='y');
        xs.pack(side='bottom', fill='x')
        self.camera_tree.bind('<<TreeviewSelect>>', self.on_camera_select)

        self.camera_vars = {}
        fields = [('camera_code', '摄像头编号'), ('camera_name', '摄像头名称'), ('camera_position', '安装位置'),
                  ('camera_type', '类型'), ('ip_address', 'IP地址'), ('port', '端口'), ('username', '用户名'),
                  ('password', '密码'), ('rtsp_url', 'RTSP地址'), ('onvif_url', 'ONVIF/云台地址'), ('enabled', '启用'),
                  ('record_enabled', '允许录像'), ('snapshot_enabled', '允许抓图'), ('remark', '备注')]
        for i, (k, l) in enumerate(fields):
            ttk.Label(right, text=l).grid(row=i, column=0, sticky='e', padx=4, pady=3)
            if k == 'camera_type':
                w = ttk.Combobox(right, width=32, state='readonly',
                                 values=['模拟摄像头', 'RTSP', 'ONVIF', 'NVR', 'USB'])
            elif k in ('enabled', 'record_enabled', 'snapshot_enabled'):
                w = ttk.Combobox(right, width=32, state='readonly', values=['1', '0'])
            elif k == 'password':
                w = ttk.Entry(right, width=34, show='*')
            else:
                w = ttk.Entry(right, width=34)
            w.grid(row=i, column=1, padx=4, pady=3, sticky='ew')
            self.camera_vars[k] = w
        b = ttk.Frame(right);
        b.grid(row=len(fields), column=0, columnspan=2, pady=8, sticky='ew')
        for j in range(2): b.grid_columnconfigure(j, weight=1)
        ttk.Button(b, text='新增摄像头', command=self.add_camera).grid(row=0, column=0, padx=3, pady=3, sticky='ew')
        ttk.Button(b, text='保存修改', command=self.save_camera).grid(row=0, column=1, padx=3, pady=3, sticky='ew')
        ttk.Button(b, text='删除摄像头', command=self.delete_camera).grid(row=1, column=0, padx=3, pady=3, sticky='ew')
        ttk.Button(b, text='测试连接', command=self.test_camera_connection).grid(row=1, column=1, padx=3, pady=3,
                                                                                 sticky='ew')
        ttk.Button(b, text='清空', command=self.clear_camera_form).grid(row=2, column=0, columnspan=2, padx=3, pady=3,
                                                                        sticky='ew')

    def station_choice_text(self, st):
        return f"{st['id']} | {st['station_code']} | {st['station_name']}"

    def _station_id_from_choice(self, text):
        try:
            return int((text or '').split('|')[0].strip())
        except Exception:
            return self.sid()

    def refresh_video_station_choices(self):
        choices = [self.station_choice_text(st) for st in self.rows('SELECT * FROM pump_station ORDER BY id')]
        for cbname in ('video_station_cb', 'camera_station_cb'):
            cb = getattr(self, cbname, None)
            if cb is not None:
                cb['values'] = choices
                if choices and not cb.get(): cb.set(choices[0])
        self.refresh_video_slots()
        self.refresh_camera_list()

    def switch_video_station(self):
        self.stop_all_cameras()
        self.refresh_video_slots()

    def switch_camera_config_station(self):
        self.refresh_camera_list();
        self.clear_camera_form()

    def current_video_station_id(self):
        return self._station_id_from_choice(self.video_station_cb.get()) if hasattr(self,
                                                                                    'video_station_cb') else self.sid()

    def current_camera_config_station_id(self):
        return self._station_id_from_choice(self.camera_station_cb.get()) if hasattr(self,
                                                                                     'camera_station_cb') else self.sid()

    def ensure_current_cameras(self):
        sid = self.current_camera_config_station_id()
        if sid:
            self.db.ensure_station_cameras(sid);
            self.refresh_camera_list();
            self.refresh_video_slots();
            messagebox.showinfo('完成', '已为当前泵站补齐 4 个摄像头位')

    def refresh_camera_list(self):
        if not hasattr(self, 'camera_tree'): return
        sid = self.current_camera_config_station_id()
        if sid: self.db.ensure_station_cameras(sid)
        self.clear_tree(self.camera_tree)
        for c in self.rows('SELECT * FROM camera WHERE station_id=? ORDER BY camera_code,id', (sid,)):
            self.camera_tree.insert('', 'end', iid=str(c['id']),
                                    values=(c['id'], c['camera_code'], c['camera_name'], c['camera_position'],
                                            c['camera_type'], c['ip_address'], c['port'],
                                            '是' if c['enabled'] else '否', c['status'], c['rtsp_url']))
        if not getattr(self, 'edit_camera_id', None): self.clear_camera_form()

    def refresh_video_slots(self):
        if not hasattr(self, 'video_cards'): return
        sid = self.current_video_station_id()
        if sid: self.db.ensure_station_cameras(sid)
        cams = self.rows('SELECT * FROM camera WHERE station_id=? ORDER BY camera_code,id LIMIT 4',
                         (sid,)) if sid else []
        for i in range(4):
            card = self.video_cards[i]
            cam = cams[i] if i < len(cams) else None
            card['camera_id'] = cam['id'] if cam else None
            title = (
                f"{cam['camera_code']} {cam['camera_name']} - {cam['camera_position']}" if cam else f'摄像头{i + 1}')
            try:
                card['frame'].config(text=title)
            except Exception:
                pass
            if cam and cam['id'] not in self.video_threads:
                card['view'].config(text='未打开视频', image='', bg='#111827', fg='white')
            card['info'].config(text=('状态：' + (cam['status'] or '-') if cam else '状态：未配置'))

    def _get_camera_by_slot(self, idx):
        if not hasattr(self, 'video_cards'): return None
        cid = self.video_cards[idx].get('camera_id')
        return self.row('SELECT * FROM camera WHERE id=?', (cid,)) if cid else None

    def _camera_rtsp_url(self, cam):
        if not cam: return ''
        if cam['rtsp_url']: return cam['rtsp_url']
        ip = (cam['ip_address'] or '').strip()
        if not ip: return ''
        user = (cam['username'] or '').strip();
        pwd = (cam['password'] or '').strip()
        auth = f'{user}:{pwd}@' if user or pwd else ''
        port = cam['port'] or 554
        return f'rtsp://{auth}{ip}:{port}/Streaming/Channels/101'

    def start_camera_by_slot(self, idx):
        cam = self._get_camera_by_slot(idx)
        if not cam: messagebox.showwarning('提示', '该位置未配置摄像头'); return
        if not cam['enabled']: messagebox.showwarning('提示', f"{cam['camera_code']} 未启用"); return
        if self._is_sim_camera(cam):
            self._start_sim_camera_stream(idx, cam)
            return
        url = self._camera_rtsp_url(cam)
        if not url: messagebox.showwarning('提示',
                                           '请先配置 RTSP 地址或 IP/用户名/密码，或把类型改为“模拟摄像头”测试'); return
        self._start_camera_stream(idx, cam, url)

    def _is_sim_camera(self, cam):
        try:
            t = (cam['camera_type'] or '').strip().lower()
            return t in ('模拟摄像头', '模拟', 'simulate', 'simulation', 'sim')
        except Exception:
            return False

    def _start_sim_camera_stream(self, idx, cam):
        cid = cam['id']
        if cid in self.video_threads:
            return
        self.video_stop_flags[cid] = False
        self.video_cards[idx]['info'].config(text='状态：模拟在线')
        self.video_cards[idx]['view'].config(text='正在启动模拟视频...', image='', bg='#0f4c81', fg='white')
        th = threading.Thread(target=self._sim_video_loop, args=(idx, cid), daemon=True)
        self.video_threads[cid] = th
        th.start()

    def _make_sim_frame_text(self, cam):
        st = self.row('SELECT station_code, station_name FROM pump_station WHERE id=?',
                      (cam['station_id'],)) if cam else None
        st_name = (st['station_code'] + ' ' + st['station_name']) if st else '泵站'
        return f"模拟视频\n{st_name}\n{cam['camera_code']}  {cam['camera_name']}\n{cam['camera_position'] or ''}\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    def _sim_video_loop(self, idx, cid):
        cam = self.row('SELECT * FROM camera WHERE id=?', (cid,))
        self.db.set_camera_status(cid, '模拟在线')
        frame_no = 0
        last_record_save = 0
        while not self.video_stop_flags.get(cid, False):
            cam = self.row('SELECT * FROM camera WHERE id=?', (cid,)) or cam
            txt = self._make_sim_frame_text(cam)
            self.video_frames[cid] = ('SIM', txt)
            bg = '#0f4c81' if frame_no % 2 == 0 else '#1769aa'
            self.after(0, lambda t=txt, b=bg, i=idx, c=cid: self._update_sim_video_frame(i, c, t, b))
            if self.video_recording.get(cid) and time.time() - last_record_save > 2:
                self._save_sim_snapshot_file(cam, txt, subfolder='videos', suffix=f'_frame_{frame_no:05d}')
                last_record_save = time.time()
            frame_no += 1
            time.sleep(0.5)
        self.db.set_camera_status(cid, '已停止')
        self.video_threads.pop(cid, None)
        self.video_stop_flags.pop(cid, None)
        self.video_recording.pop(cid, None)
        self.after(0, lambda: self.refresh_video_slots())

    def _video_ratio_value(self):
        ratio = '16:9'
        try:
            ratio = self.video_ratio_cb.get() or '16:9'
        except Exception:
            pass
        if ratio == '4:3':
            return 4 / 3
        if ratio == '自适应':
            return None
        return 16 / 9

    def _video_target_size(self, idx):
        try:
            lab = self.video_cards[idx]['view']
            w = max(lab.winfo_width(), 320)
            h = max(lab.winfo_height(), 180)
        except Exception:
            return (640, 360)
        ratio = self._video_ratio_value()
        if ratio is None:
            return (w, h)
        # 在当前控件区域内按指定比例取最大画面尺寸，避免拉伸变形。
        if w / h > ratio:
            tw = int(h * ratio)
            th = h
        else:
            tw = w
            th = int(w / ratio)
        return (max(tw, 240), max(th, 135))

    def _on_video_view_resize(self, idx):
        # 窗口尺寸变化时，模拟画面会在下一次刷新自动适配；真实视频下一帧自动适配。
        pass

    def _make_sim_image(self, idx, text, bg):
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageTk
            w, h = self._video_target_size(idx)
            img = Image.new('RGB', (w, h), bg)
            draw = ImageDraw.Draw(img)
            lines = text.split('\n')
            # 根据画面高度自动调整字号。
            font_size = max(14, min(28, int(h / 14)))
            try:
                font = ImageFont.truetype('msyh.ttc', font_size)
                title_font = ImageFont.truetype('msyh.ttc', font_size + 4)
            except Exception:
                font = None
                title_font = None
            # 画一个简洁的视频边框和中心信息。
            draw.rectangle((8, 8, w - 8, h - 8), outline=(154, 209, 255), width=2)
            y = max(22, int(h * 0.18))
            for n, line in enumerate(lines):
                f = title_font if n == 0 else font
                try:
                    bbox = draw.textbbox((0, 0), line, font=f)
                    tw = bbox[2] - bbox[0]
                except Exception:
                    tw = len(line) * font_size
                draw.text(((w - tw) / 2, y), line, fill=(255, 255, 255), font=f)
                y += int(font_size * (1.9 if n == 0 else 1.55))
            # 底部模拟时间进度条，增强视频感。
            bar_w = int((time.time() % 5) / 5 * (w - 40))
            draw.rectangle((20, h - 28, w - 20, h - 20), outline=(200, 230, 255), width=1)
            draw.rectangle((20, h - 28, 20 + bar_w, h - 20), fill=(80, 210, 255))
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _update_sim_video_frame(self, idx, cid, text, bg):
        lab = self.video_cards[idx]['view']
        photo = self._make_sim_image(idx, text, bg)
        if photo is not None:
            lab.image = photo
            lab.config(image=photo, text='', bg='#111827')
        else:
            lab.image = None
            lab.config(image='', text=text, bg=bg, fg='white', font=('Microsoft YaHei', 15, 'bold'), justify='center')
        self.video_cards[idx]['info'].config(
            text='状态：模拟在线' + (' / 录像中' if self.video_recording.get(cid) else ''))

    def _save_sim_snapshot_file(self, cam, text, subfolder='snapshots', suffix=''):
        st = self.row('SELECT station_code FROM pump_station WHERE id=?', (cam['station_id'],)) if cam else None
        folder = os.path.join(BASE_DIR, subfolder, st['station_code'] if st else 'station')
        os.makedirs(folder, exist_ok=True)
        base = f"{cam['camera_code']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        # 优先保存 PNG，若 Pillow 不可用则保存 TXT。
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (960, 540), (15, 76, 129))
            draw = ImageDraw.Draw(img)
            y = 130
            for line in text.split('\n'):
                draw.text((90, y), line, fill=(255, 255, 255))
                y += 58
            path = os.path.join(folder, base + '.png')
            img.save(path)
            return path
        except Exception:
            path = os.path.join(folder, base + '.txt')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return path

    def _start_camera_stream(self, idx, cam, url):
        cid = cam['id']
        if cid in self.video_threads:
            return
        self.video_stop_flags[cid] = False
        self.video_cards[idx]['info'].config(text='状态：连接中')
        self.video_cards[idx]['view'].config(text='正在连接视频流...', image='', bg='#111827', fg='white')
        th = threading.Thread(target=self._video_loop, args=(idx, cid, url), daemon=True)
        self.video_threads[cid] = th;
        th.start()

    def _video_loop(self, idx, cid, url):
        try:
            import cv2
            from PIL import Image, ImageTk
        except Exception:
            self.after(0, lambda: self._set_video_error(idx, cid, '缺少 opencv-python / pillow'))
            return
        cap = None
        writer = None
        try:
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                self.after(0, lambda: self._set_video_error(idx, cid, '离线/连接失败'))
                return
            self.db.set_camera_status(cid, '在线')
            while not self.video_stop_flags.get(cid, False):
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.2);
                    continue
                self.video_frames[cid] = frame.copy()
                rec = self.video_recording.get(cid)
                if rec:
                    writer = self.video_recorders.get(cid)
                    if writer is None:
                        os.makedirs(os.path.join(BASE_DIR, 'videos'), exist_ok=True)
                        path = os.path.join(BASE_DIR, 'videos',
                                            f'CAM{cid}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.avi')
                        h, w = frame.shape[:2]
                        fourcc = cv2.VideoWriter_fourcc(*'XVID')
                        writer = cv2.VideoWriter(path, fourcc, 8, (w, h))
                        self.video_recorders[cid] = writer
                    writer.write(frame)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                target_w, target_h = self._video_target_size(idx)
                img.thumbnail((target_w, target_h))
                # 补成统一画布尺寸，保证四宫格比例一致。
                canvas = Image.new('RGB', (target_w, target_h), (0, 0, 0))
                ox = max((target_w - img.width) // 2, 0)
                oy = max((target_h - img.height) // 2, 0)
                canvas.paste(img, (ox, oy))
                photo = ImageTk.PhotoImage(canvas)
                self.after(0, lambda ph=photo, i=idx, c=cid: self._update_video_frame(i, c, ph))
                time.sleep(0.12)
            self.db.set_camera_status(cid, '已停止')
        except Exception as e:
            self.after(0, lambda e=e: self._set_video_error(idx, cid, '异常: ' + str(e)))
        finally:
            try:
                if cap: cap.release()
            except Exception:
                pass
            try:
                wr = self.video_recorders.pop(cid, None)
                if wr: wr.release()
            except Exception:
                pass
            self.video_threads.pop(cid, None)
            self.video_stop_flags.pop(cid, None)
            self.video_recording.pop(cid, None)
            self.after(0, lambda: self.refresh_video_slots())

    def _update_video_frame(self, idx, cid, photo):
        lab = self.video_cards[idx]['view']
        lab.image = photo
        lab.config(image=photo, text='', bg='black')
        self.video_cards[idx]['info'].config(text='状态：在线')

    def _set_video_error(self, idx, cid, msg):
        try:
            self.db.set_camera_status(cid, msg)
        except Exception:
            pass
        if hasattr(self, 'video_cards'):
            self.video_cards[idx]['view'].config(text=msg, image='', bg='#111827', fg='#ffb4b4')
            self.video_cards[idx]['info'].config(text='状态：' + msg)
        self.video_threads.pop(cid, None)

    def stop_camera_by_slot(self, idx):
        cam = self._get_camera_by_slot(idx)
        if not cam: return
        cid = cam['id']
        self.video_stop_flags[cid] = True
        self.video_recording[cid] = False
        self.video_cards[idx]['info'].config(text='状态：正在停止')

    def start_all_cameras(self):
        self.refresh_video_slots()
        for i in range(4): self.start_camera_by_slot(i)

    def stop_all_cameras(self):
        for i in range(4):
            try:
                self.stop_camera_by_slot(i)
            except Exception:
                pass

    def snapshot_camera_by_slot(self, idx):
        cam = self._get_camera_by_slot(idx)
        if not cam: return
        frame = self.video_frames.get(cam['id'])
        if frame is None:
            messagebox.showwarning('提示', '当前没有可抓拍的视频画面');
            return
        if isinstance(frame, tuple) and frame[0] == 'SIM':
            path = self._save_sim_snapshot_file(cam, frame[1], subfolder='snapshots')
            messagebox.showinfo('抓拍成功', '模拟抓拍已保存：' + path)
            return
        try:
            import cv2
            st = self.row('SELECT station_code FROM pump_station WHERE id=?', (cam['station_id'],))
            folder = os.path.join(BASE_DIR, 'snapshots', st['station_code'] if st else 'station')
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{cam['camera_code']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            cv2.imwrite(path, frame)
            messagebox.showinfo('抓拍成功', '已保存：' + path)
        except Exception as e:
            messagebox.showerror('抓拍失败', str(e))

    def toggle_record_by_slot(self, idx):
        cam = self._get_camera_by_slot(idx)
        if not cam: return
        cid = cam['id']
        if cid not in self.video_threads:
            messagebox.showwarning('提示', '请先打开视频再录像');
            return
        self.video_recording[cid] = not self.video_recording.get(cid, False)
        self.video_cards[idx]['info'].config(text='状态：录像中' if self.video_recording[cid] else (
            '状态：模拟在线' if self._is_sim_camera(cam) else '状态：在线'))

    def ptz_camera_by_slot(self, idx, action):
        cam = self._get_camera_by_slot(idx)
        if not cam: return
        if self._is_sim_camera(cam):
            msg = f"{cam['camera_code']} 模拟云台动作：{action}"
            self.video_cards[idx]['info'].config(text='状态：' + msg)
            self.db.log(cam['station_id'], 'video_ptz', msg)
            return
        url = (cam['onvif_url'] or '').strip()
        # 测试版提供云台按钮和接口预留。若现场提供 HTTP/ONVIF 网关地址，可在这里发送动作参数。
        if url:
            try:
                import urllib.parse, urllib.request
                sep = '&' if '?' in url else '?'
                full = url + sep + urllib.parse.urlencode({'action': action, 'camera': cam['camera_code']})
                urllib.request.urlopen(full, timeout=2).read(200)
                messagebox.showinfo('云台控制', f"{cam['camera_code']} 已发送云台指令：{action}")
                return
            except Exception as e:
                messagebox.showwarning('云台控制', f"云台指令发送失败，已记录动作：{action}\n{e}")
        else:
            messagebox.showinfo('云台控制',
                                f"{cam['camera_code']} 云台动作：{action}\n请在视频配置中填写 ONVIF/云台地址后对接真实云台。")

    def refresh_video_status_labels(self):
        if hasattr(self, 'video_cards'):
            for i in range(4):
                cam = self._get_camera_by_slot(i)
                if cam and cam['id'] not in self.video_threads:
                    self.video_cards[i]['info'].config(text='状态：' + (cam['status'] or '-'))

    def _get_camera_form(self):
        d = {k: w.get().strip() for k, w in self.camera_vars.items()}
        if not d.get('camera_code'):
            d['camera_code'] = self.db.next_camera_code(self.current_camera_config_station_id())
        if not d.get('camera_name'):
            d['camera_name'] = '摄像头'
        if not d.get('camera_type'):
            d['camera_type'] = '模拟摄像头'
        for k, v in {'port': '554', 'enabled': '0', 'record_enabled': '0', 'snapshot_enabled': '1'}.items():
            if d.get(k, '') == '': d[k] = v
        return d

    def clear_camera_form(self):
        if not hasattr(self, 'camera_vars'): return
        self.edit_camera_id = None
        vals = {'camera_code': self.db.next_camera_code(self.current_camera_config_station_id() or 0),
                'camera_name': '摄像头', 'camera_position': '', 'camera_type': '模拟摄像头', 'ip_address': '',
                'port': '554', 'username': 'admin', 'password': '', 'rtsp_url': '', 'onvif_url': '', 'enabled': '0',
                'record_enabled': '0', 'snapshot_enabled': '1', 'remark': ''}
        for k, w in self.camera_vars.items(): self._set_widget_value(w, vals.get(k, ''))

    def on_camera_select(self, e=None):
        sel = self.camera_tree.selection()
        if not sel: return
        cid = int(sel[0]);
        cam = self.row('SELECT * FROM camera WHERE id=?', (cid,));
        self.edit_camera_id = cid
        for k, w in self.camera_vars.items(): self._set_widget_value(w, cam[k] if k in cam.keys() and cam[
            k] is not None else '')

    def add_camera(self):
        sid = self.current_camera_config_station_id()
        if not sid: messagebox.showwarning('提示', '请先选择泵站'); return
        d = self._get_camera_form()
        try:
            if self.row('SELECT id FROM camera WHERE station_id=? AND camera_code=?', (sid, d['camera_code'])):
                d['camera_code'] = self.db.next_camera_code(sid)
            self.edit_camera_id = self.db.add_camera(sid, d)
            self.refresh_camera_list();
            self.refresh_video_slots();
            messagebox.showinfo('成功', '摄像头已新增')
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def save_camera(self):
        if not getattr(self, 'edit_camera_id', None): messagebox.showwarning('提示', '请先选择摄像头'); return
        d = self._get_camera_form()
        try:
            self.db.update_camera(self.edit_camera_id, d)
            self.refresh_camera_list();
            self.refresh_video_slots();
            messagebox.showinfo('成功', '摄像头参数已保存')
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def delete_camera(self):
        if getattr(self, 'edit_camera_id', None) and messagebox.askyesno('确认', '删除该摄像头配置？'):
            self.db.execute('DELETE FROM camera WHERE id=?', (self.edit_camera_id,));
            self.edit_camera_id = None;
            self.refresh_camera_list();
            self.refresh_video_slots()

    def test_camera_connection(self):
        d = self._get_camera_form()
        if (d.get('camera_type') or '').strip() == '模拟摄像头':
            messagebox.showinfo('测试结果', '模拟摄像头测试成功：可用于界面、抓图、录像和云台按钮流程测试。')
            return
        url = d.get('rtsp_url') or ''
        if not url and d.get('ip_address'):
            auth = (d.get('username', '') + ':' + d.get('password', '') + '@') if (
                    d.get('username') or d.get('password')) else ''
            url = f"rtsp://{auth}{d.get('ip_address')}:{d.get('port') or 554}/Streaming/Channels/101"
        if not url:
            messagebox.showwarning('提示', '请先填写 RTSP 地址或 IP 地址');
            return
        try:
            import cv2
            cap = cv2.VideoCapture(url)
            ok = cap.isOpened()
            try:
                cap.release()
            except Exception:
                pass
            messagebox.showinfo('测试结果', '连接成功' if ok else '连接失败，请检查 RTSP 地址、用户名、密码或网络')
        except Exception as e:
            messagebox.showwarning('测试结果', '当前环境缺少 opencv-python，无法测试视频连接。\n' + str(e))

    # Reports and logs

    # ===================== 三维孪生基础版 =====================
    def build_twin_page(self):
        """三维孪生基础框架。
        V5.7 先做轻量孪生视图：可为每个泵站绑定 glb/gltf 模型路径，提供旋转/缩放/平移/定位的操作入口，
        并用设备编号生成可点击的孪生对象。后续可替换为 Three.js / WebView 真 3D 渲染。
        """
        f = self.pages['三维孪生']
        top = tk.Frame(f, bg='#e7f1fb')
        top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top, text='孪生泵站').pack(side='left', padx=(4, 4))
        self.twin_station_var = tk.StringVar()
        self.twin_station_combo = ttk.Combobox(top, textvariable=self.twin_station_var, state='readonly', width=22)
        self.twin_station_combo.pack(side='left', padx=4)
        self.twin_station_combo.bind('<<ComboboxSelected>>', lambda e: self.switch_twin_station())
        ttk.Label(top, text='模型文件').pack(side='left', padx=(10, 4))
        self.twin_model_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.twin_model_path, width=34).pack(side='left', padx=4, fill='x', expand=True)
        ttk.Button(top, text='导入模型', command=self.browse_twin_model).pack(side='left', padx=2)
        ttk.Button(top, text='保存绑定', command=self.save_twin_model).pack(side='left', padx=2)
        ttk.Button(top, text='扫描模型对象', command=self.scan_twin_model_objects).pack(side='left', padx=2)
        ttk.Button(top, text='生成绑定表', command=self.generate_twin_binding).pack(side='left', padx=2)
        ttk.Button(top, text='加载内嵌查看器', command=lambda: self.load_twin_in_page(force=True)).pack(side='left',
                                                                                                        padx=2)
        ttk.Button(top, text='外部GLB查看器', command=self.open_twin_model_viewer).pack(side='left', padx=2)
        ttk.Button(top, text='模型状态检查', command=self.model_status_check).pack(side='left', padx=2)
        ttk.Button(top, text='打开模型目录', command=self.open_twin_model_dir).pack(side='left', padx=2)
        ttk.Button(top, text='清除模型', command=self.clear_twin_model).pack(side='left', padx=2)

        body = tk.Frame(f, bg='#edf4fb')
        body.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg='#ffffff', bd=1, relief='solid')
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))
        title = tk.Frame(left, bg='#0f4c81', height=34)
        title.pack(fill='x')
        title.pack_propagate(False)
        tk.Label(title, text='多泵站数字孪生：GLB查看 / 对象扫描 / 变量绑定', bg='#0f4c81', fg='white',
                 font=('Microsoft YaHei', 12, 'bold')).pack(side='left', padx=10)
        self.twin_hint = tk.Label(title, text='V5.7.13：模型写入安全目录，避免旧版本路径/权限/重名冲突', bg='#0f4c81',
                                  fg='#d7ecff', font=('Microsoft YaHei', 9))
        self.twin_hint.pack(side='right', padx=10)
        self.twin_view_frame = tk.Frame(left, bg='#07101f')
        self.twin_view_frame.pack(fill='both', expand=True)
        self.twin_embedded_widget = None
        self.twin_loaded_url = ''
        self.twin_embed_status = '未加载'
        try:
            if hasattr(self, 'twin_info'):
                self.twin_info.insert('end',
                                      'V5.7.14_TwinBindFix 已启用：GLB 模型将保存到安全目录，不再依赖旧版本 twin_viewer 路径。\n')
        except Exception as e:
            self._log_twin_error('构建V5.7.13三维页面增强按钮失败', e)

    def refresh_twin_station_combo(self):
        if not hasattr(self, 'twin_station_combo'): return
        vals = [];
        current = ''
        for st in self.rows('SELECT id,station_code,station_name FROM pump_station ORDER BY id'):
            txt = f"{st['id']} | {st['station_code']} | {st['station_name']}";
            vals.append(txt)
            if st['id'] == self.sid(): current = txt
        self.twin_station_combo['values'] = vals
        if current:
            self.twin_station_var.set(current)
        elif vals:
            self.twin_station_var.set(vals[0])
        self.load_twin_model_config();
        self.draw_twin_scene();
        self.populate_twin_list()

    def twin_sid(self):
        try:
            t = (self.twin_station_var.get() or '').strip()
            return int(t.split('|')[0].strip()) if t else self.sid()
        except Exception:
            return self.sid()

    def switch_twin_station(self):
        sid = self.twin_sid()
        if sid:
            self.current_station_id = sid
            self.db.set_current_station(sid)
            self.refresh_station_label()
        self.load_twin_model_config()
        self.draw_twin_scene()
        self.populate_twin_list()

    def load_twin_model_config(self):
        if not hasattr(self, 'twin_model_path'): return
        sid = self.twin_sid()
        row = self.row('SELECT * FROM twin_model WHERE station_id=?', (sid,)) if sid else None
        self.twin_model_path.set(row['model_path'] if row and row['model_path'] else '')

    def browse_twin_model(self):
        path = filedialog.askopenfilename(title='选择三维模型文件',
                                          filetypes=[('3D 模型', '*.glb *.gltf'), ('所有文件', '*.*')])
        if path:
            self.twin_model_path.set(path)
            self.save_twin_model()

    def refresh_twin_preview(self):
        path = (self.twin_model_path.get() or '').strip()
        if not path:
            messagebox.showwarning('提示', '请先导入 glb/gltf 模型文件。');
            return
        if not os.path.exists(path):
            messagebox.showwarning('提示', '模型文件不存在：' + path);
            return
        self._prepare_twin_web_model(path)
        preview = self._prepare_twin_preview(path)
        self.draw_twin_scene()
        if preview and os.path.exists(preview):
            messagebox.showinfo('静态预览成功', 'GLB/gltf 静态预览已生成；完整旋转/缩放请使用“打开GLB三维查看器”。')
        else:
            messagebox.showwarning('预览未生成',
                                   '已导入模型，但当前环境未生成静态预览。请运行 install_glb_preview_deps.bat 安装 pillow、matplotlib、trimesh、numpy 后重试；完整模型请使用“打开GLB三维查看器”。')

    def save_twin_model(self):
        sid = self.twin_sid();
        path = (self.twin_model_path.get() or '').strip()
        if not sid:
            messagebox.showwarning('提示', '请先选择泵站');
            return
        name = os.path.basename(path) if path else ''
        old = self.row('SELECT id FROM twin_model WHERE station_id=?', (sid,))
        if old:
            self.db.execute('UPDATE twin_model SET model_name=?,model_path=?,updated_at=? WHERE station_id=?',
                            (name, path, now(), sid))
        else:
            self.db.execute(
                'INSERT INTO twin_model(station_id,model_name,model_path,created_at,updated_at) VALUES(?,?,?,?,?)',
                (sid, name, path, now(), now()))
        self._prepare_twin_web_model(path)
        self._prepare_twin_preview(path)
        messagebox.showinfo('保存成功',
                            '三维模型绑定已保存。当前页已取消原水箱/管道示意，完整模型请点击“打开GLB三维查看器”。')
        self.draw_twin_scene()

    def _twin_preview_file(self, path):
        if not path:
            return None
        viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
        os.makedirs(viewer_dir, exist_ok=True)
        sid = self.twin_sid() or self.sid()
        st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
        code = (st['station_code'] if st else 'STATION') or 'STATION'
        return os.path.join(viewer_dir, f'{code}_preview.png')

    def _prepare_twin_preview(self, path):
        # 生成GLB/gltf静态预览图，供Tkinter画布直接显示。依赖 trimesh/matplotlib/Pillow；缺少依赖时不影响主程序。
        if not path or not os.path.exists(path):
            return None
        out = self._twin_preview_file(path)
        try:
            import trimesh
            import numpy as np
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            obj = trimesh.load(path, force='scene')
            try:
                mesh = obj.dump(concatenate=True) if hasattr(obj, 'dump') else obj
            except Exception:
                geoms = list(getattr(obj, 'geometry', {}).values())
                mesh = trimesh.util.concatenate(geoms) if geoms else obj
            if mesh is None or not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
                return None
            verts = np.asarray(mesh.vertices)
            faces = np.asarray(mesh.faces) if hasattr(mesh, 'faces') else np.empty((0, 3), dtype=int)
            if len(faces) > 4500:
                idx = np.linspace(0, len(faces) - 1, 4500).astype(int)
                faces = faces[idx]
            fig = plt.figure(figsize=(9.5, 5.4), dpi=130)
            ax = fig.add_subplot(111, projection='3d')
            fig.patch.set_facecolor('#0b1220');
            ax.set_facecolor('#0b1220')
            if len(faces) > 0:
                poly = Poly3DCollection(verts[faces], alpha=0.92, linewidths=0.08)
                poly.set_facecolor((0.10, 0.55, 0.95, 0.55))
                poly.set_edgecolor((0.45, 0.88, 1.00, 0.18))
                ax.add_collection3d(poly)
            else:
                ax.scatter(verts[:, 0], verts[:, 1], verts[:, 2], s=1, c='#33c7ff')
            mins = verts.min(axis=0);
            maxs = verts.max(axis=0);
            center = (mins + maxs) / 2;
            size = float((maxs - mins).max() or 1)
            ax.set_xlim(center[0] - size / 2, center[0] + size / 2)
            ax.set_ylim(center[1] - size / 2, center[1] + size / 2)
            ax.set_zlim(center[2] - size / 2, center[2] + size / 2)
            ax.view_init(elev=22, azim=-48)
            ax.set_axis_off();
            plt.tight_layout(pad=0)
            fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            return out
        except Exception as e:
            try:
                os.makedirs(os.path.join(BASE_DIR, 'twin_viewer'), exist_ok=True)
                with open(os.path.join(BASE_DIR, 'twin_viewer', 'preview_error.txt'), 'w', encoding='utf-8') as f:
                    f.write(str(e))
            except Exception:
                pass
            return None

    def _draw_twin_preview_image(self, canvas, path):
        if not path or not os.path.exists(path):
            return False
        preview = self._twin_preview_file(path)
        if not preview or not os.path.exists(preview):
            preview = self._prepare_twin_preview(path)
        if not preview or not os.path.exists(preview):
            return False
        try:
            from PIL import Image, ImageTk
            img = Image.open(preview).convert('RGBA')
            w = max(100, canvas.winfo_width() - 40);
            h = max(100, canvas.winfo_height() - 95)
            img.thumbnail((w, h), Image.LANCZOS)
            self.twin_preview_photo = ImageTk.PhotoImage(img)
            canvas.create_image(canvas.winfo_width() / 2, canvas.winfo_height() / 2 + 25, image=self.twin_preview_photo,
                                anchor='center')
            return True
        except Exception:
            return False

    def _prepare_twin_web_model(self, path):
        if not path or not os.path.exists(path):
            return None
        try:
            viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
            model_dir = os.path.join(viewer_dir, 'models')
            os.makedirs(model_dir, exist_ok=True)
            ext = os.path.splitext(path)[1].lower() or '.glb'
            sid = self.twin_sid() or self.sid()
            st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
            code = (st['station_code'] if st else 'STATION') or 'STATION'
            target_name = f'{code}_model{ext}'
            target = os.path.join(model_dir, target_name)
            try:
                if os.path.abspath(path) != os.path.abspath(target):
                    shutil.copy2(path, target)
            except Exception:
                target = path
                target_name = os.path.basename(path)

            template_dir = os.path.join(BASE_DIR, 'templates')
            hdrpro_tmpl = os.path.join(template_dir, 'twin_viewer_hdrpro.html')
            detail_tmpl = os.path.join(template_dir, 'twin_device_detail.html')

            model_url = f'/models/{target_name}'

            if os.path.exists(hdrpro_tmpl):
                with open(hdrpro_tmpl, 'r', encoding='utf-8') as f:
                    html_text = f.read()
                html_text = html_text.replace('__MODEL__', model_url)
                html = os.path.join(viewer_dir, 'twin_viewer.html')
                with open(html, 'w', encoding='utf-8') as f:
                    f.write(html_text)
            else:
                html_text = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>泵站GLB三维查看器</title>
<script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
<style>
html,body{{margin:0;width:100%;height:100%;background:#081526;color:#d7ecff;font-family:Microsoft YaHei,Arial,sans-serif;}}
.header{{height:54px;display:flex;align-items:center;justify-content:space-between;padding:0 18px;background:#0b2440;border-bottom:1px solid #1e90ff;box-shadow:0 0 20px rgba(0,145,255,.35);}}
.title{{font-size:20px;font-weight:700;letter-spacing:1px;}}
.note{{font-size:13px;color:#9ed8ff;}}
model-viewer{{width:100%;height:calc(100vh - 54px);background:radial-gradient(circle at center,#12365a 0%,#081526 55%,#020814 100%);}}
.fail{{position:fixed;left:18px;bottom:14px;right:18px;color:#f7c948;background:rgba(8,21,38,.75);border:1px solid #2563eb;padding:10px;border-radius:8px;font-size:13px;}}
</style>
</head>
<body>
<div class="header"><div class="title">隧道泵站自动控制系统 V5.7.7 - GLB三维模型查看器</div><div class="note">鼠标旋转 / 滚轮缩放 / 右键平移</div></div>
<model-viewer src="models/{target_name}" camera-controls auto-rotate shadow-intensity="1" exposure="1.0" environment-image="neutral" ar ar-modes="webxr scene-viewer quick-look"></model-viewer>
<div class="fail">说明：该查看器使用浏览器 WebGL 渲染 GLB/gltf；如空白，请确认电脑可访问 model-viewer 组件网络地址，或由开发者将 three.js/model-viewer 库打包到本地。Python 当前页负责模型绑定和设备状态列表；完整三维显示由该 WebGL 查看器负责。</div>
</body>
</html>'''
                html = os.path.join(viewer_dir, 'twin_viewer.html')
                with open(html, 'w', encoding='utf-8') as f:
                    f.write(html_text)

            if os.path.exists(detail_tmpl):
                with open(detail_tmpl, 'r', encoding='utf-8') as f:
                    detail_text = f.read()
                detail_text = detail_text.replace('__MODEL__', model_url)
                detail_html = os.path.join(viewer_dir, 'twin_device_detail.html')
                with open(detail_html, 'w', encoding='utf-8') as f:
                    f.write(detail_text)

            return html
        except Exception as e:
            messagebox.showwarning('GLB查看器准备失败', str(e))
            return None

    def _start_twin_http_server(self):
        viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
        os.makedirs(viewer_dir, exist_ok=True)
        if self.twin_httpd:
            return True
        try:
            handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=viewer_dir,
                                                                                   **kwargs)
            self.twin_httpd = socketserver.TCPServer(('127.0.0.1', self.twin_http_port), handler)
            t = threading.Thread(target=self.twin_httpd.serve_forever, daemon=True)
            t.start()
            return True
        except OSError:
            return True
        except Exception as e:
            messagebox.showwarning('GLB查看器启动失败', str(e));
            return False

    def open_twin_model_viewer(self):
        path = (self.twin_model_path.get() or '').strip()
        if not path:
            messagebox.showwarning('提示', '请先导入并保存 glb/gltf 模型文件。');
            return
        if not os.path.exists(path):
            messagebox.showwarning('提示', '模型文件不存在：' + path);
            return
        html = self._prepare_twin_web_model(path)
        self._prepare_twin_preview(path)
        self.draw_twin_scene()
        if html and os.path.exists(html) and self._start_twin_http_server():
            webbrowser.open(f'http://127.0.0.1:{self.twin_http_port}/twin_viewer.html')

    def open_twin_model_system_viewer(self):
        path = (self.twin_model_path.get() or '').strip()
        if not path:
            messagebox.showwarning('提示', '请先导入 glb/gltf 模型文件。');
            return
        if not os.path.exists(path):
            messagebox.showwarning('提示', '模型文件不存在：' + path);
            return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showwarning('系统3D查看失败', '当前系统没有关联的GLB查看程序，或文件无法打开。\n' + str(e))

    def reset_twin_view(self):
        self.twin_scale = 1.0;
        self.twin_offset = [0, 0];
        self.draw_twin_scene()

    def zoom_twin(self, factor):
        self.twin_scale = max(0.45, min(2.8, self.twin_scale * factor));
        self.draw_twin_scene()

    def twin_mouse_wheel(self, event):
        self.zoom_twin(1.1 if event.delta > 0 else 0.9)

    def twin_mouse_down(self, event):
        # 点击优先选对象；没有选中对象才准备拖动平移。
        hit = None
        for obj in reversed(self.twin_items):
            x1, y1, x2, y2 = obj['box']
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                hit = obj;
                break
        if hit:
            self.twin_selected = hit['code'];
            self.show_twin_object_info(hit['kind'], hit['id'], hit['code']);
            self.draw_twin_scene();
            return
        self.twin_drag_start = (event.x, event.y, self.twin_offset[0], self.twin_offset[1])

    def twin_mouse_drag(self, event):
        if not self.twin_drag_start: return
        x0, y0, ox, oy = self.twin_drag_start
        self.twin_offset = [ox + event.x - x0, oy + event.y - y0]
        self.draw_twin_scene()

    def twin_mouse_up(self, event):
        self.twin_drag_start = None

    def twin_xy(self, x, y):
        try:
            w = self.twin_canvas.winfo_width();
            h = self.twin_canvas.winfo_height()
        except Exception:
            w, h = 900, 600
        return int(w / 2 + (x * self.twin_scale) + self.twin_offset[0]), int(
            h / 2 + (y * self.twin_scale) + self.twin_offset[1])

    def draw_twin_scene(self):
        """三维孪生当前页显示逻辑（V5.7.7）。
        说明：用户反馈外部GLB查看器效果好、当前Tkinter画布静态预览效果差。
        因此本页不再绘制原来的水箱、管道、水泵示意元素；只保留：
        1) GLB/gltf模型绑定状态；
        2) 静态预览（可选，依赖安装后才显示）；
        3) 设备对象列表/状态参数；
        4) 打开WebGL三维查看器入口。
        """
        if not hasattr(self, 'twin_canvas'):
            return
        c = self.twin_canvas
        c.delete('all')
        self.twin_items = []
        sid = self.twin_sid()
        w = max(c.winfo_width(), 600);
        h = max(c.winfo_height(), 420)
        # 深色背景和网格，仅作模型绑定页背景，不再绘制水箱/管道/水泵示意。
        c.create_rectangle(0, 0, w, h, fill='#0b1220', outline='')
        for i in range(0, w, 48):
            c.create_line(i, 0, i, h, fill='#111c2e')
        for j in range(0, h, 48):
            c.create_line(0, j, w, j, fill='#111c2e')
        c.create_text(18, 18, anchor='nw', text='GLB/gltf 三维模型绑定与查看', fill='#d7ecff',
                      font=('Microsoft YaHei', 14, 'bold'))
        c.create_text(18, 48, anchor='nw',
                      text='当前页面已取消原水箱、管道、水泵示意元素；完整旋转/缩放请点击“打开GLB三维查看器”。',
                      fill='#8fd3ff', font=('Microsoft YaHei', 10))
        if not sid:
            c.create_text(w // 2, h // 2, text='请先建立泵站', fill='white', font=('Microsoft YaHei', 18, 'bold'))
            return
        mp = (self.twin_model_path.get() or '').strip()
        if mp and os.path.exists(mp):
            has_preview = self._draw_twin_preview_image(c, mp)
            if has_preview:
                c.create_rectangle(14, 78, w - 14, h - 16, outline='#1e90ff', width=2)
                c.create_text(24, 88, anchor='nw', text='静态预览：' + os.path.basename(mp), fill='#d7ecff',
                              font=('Microsoft YaHei', 10, 'bold'))
                c.create_text(24, 112, anchor='nw',
                              text='提示：静态预览只用于确认模型已绑定，完整模型以 GLB三维查看器 为准。', fill='#f6c343',
                              font=('Microsoft YaHei', 9))
            else:
                try:
                    size = os.path.getsize(mp) / 1024 / 1024
                except Exception:
                    size = 0
                bx1 = max(60, w // 2 - 300);
                by1 = max(110, h // 2 - 120);
                bx2 = min(w - 60, w // 2 + 300);
                by2 = min(h - 80, h // 2 + 120)
                c.create_rectangle(bx1, by1, bx2, by2, fill='#10243d', outline='#1e90ff', width=2)
                c.create_text((bx1 + bx2) // 2, by1 + 26, text='GLB/gltf 模型已绑定', fill='#8fd3ff',
                              font=('Microsoft YaHei', 16, 'bold'))
                lines = [
                    f'模型文件：{os.path.basename(mp)}',
                    f'文件大小：{size:.2f} MB',
                    '当前页：不再显示原水箱/管道示意',
                    '完整查看：点击上方“打开GLB三维查看器”',
                    '静态预览：可运行 install_glb_preview_deps.bat 后生成'
                ]
                yy = by1 + 66
                for line in lines:
                    c.create_text(bx1 + 40, yy, anchor='nw', text=line, fill='#d7ecff', font=('Microsoft YaHei', 11));
                    yy += 30
        elif mp:
            c.create_text(w // 2, h // 2, text='模型文件不存在或路径失效', fill='#ef4444',
                          font=('Microsoft YaHei', 16, 'bold'))
            c.create_text(w // 2, h // 2 + 34, text=mp, fill='#f6c343', font=('Microsoft YaHei', 10))
        else:
            bx1 = max(60, w // 2 - 280);
            by1 = max(120, h // 2 - 100);
            bx2 = min(w - 60, w // 2 + 280);
            by2 = min(h - 80, h // 2 + 100)
            c.create_rectangle(bx1, by1, bx2, by2, fill='#10243d', outline='#1e90ff', width=2)
            c.create_text((bx1 + bx2) // 2, by1 + 35, text='未绑定 GLB/gltf 模型', fill='#f6c343',
                          font=('Microsoft YaHei', 16, 'bold'))
            c.create_text((bx1 + bx2) // 2, by1 + 78, text='请点击“导入模型”选择 glb/gltf 文件，再保存绑定。',
                          fill='#d7ecff', font=('Microsoft YaHei', 11))
            c.create_text((bx1 + bx2) // 2, by1 + 112, text='V5.7.7 已取消当前页原水箱、管道、水泵示意绘制。',
                          fill='#8fd3ff', font=('Microsoft YaHei', 10))
        self.populate_twin_list()

    def populate_twin_list(self):
        if not hasattr(self, 'twin_obj_list'): return
        self.twin_obj_list.delete(0, 'end')
        sid = self.twin_sid()
        if not sid: return
        for p in self.rows(
                "SELECT id,pump_code,pump_name FROM pump WHERE station_id=? AND pump_type<>'feed' ORDER BY display_order,id",
                (sid,)):
            self.twin_obj_list.insert('end', f"水泵 | {p['id']} | {p['pump_code']} | {p['pump_name']}")
        for p in self.rows('SELECT id,pipe_code,pipe_name FROM main_pipe WHERE station_id=? ORDER BY display_order,id',
                           (sid,)):
            self.twin_obj_list.insert('end', f"母管 | {p['id']} | {p['pipe_code']} | {p['pipe_name']}")
        for ins in self.rows(
                'SELECT id,instrument_code,instrument_name FROM instrument WHERE station_id=? ORDER BY instrument_type,id',
                (sid,)):
            self.twin_obj_list.insert('end',
                                      f"仪表 | {ins['id']} | {ins['instrument_code']} | {ins['instrument_name']}")

    def select_twin_from_list(self):
        if not hasattr(self, 'twin_obj_list'): return
        sel = self.twin_obj_list.curselection()
        if not sel: return
        parts = self.twin_obj_list.get(sel[0]).split('|')
        if len(parts) < 3: return
        kind = parts[0].strip();
        oid = int(parts[1].strip());
        code = parts[2].strip()
        k = {'水泵': 'pump', '母管': 'pipe', '仪表': 'instrument'}.get(kind, kind)
        self.twin_selected = code;
        self.show_twin_object_info(k, oid, code);
        self.draw_twin_scene()

    def show_twin_object_info(self, kind, oid, code):
        if not hasattr(self, 'twin_info'): return
        txt = []
        if kind == 'pump':
            p = self.row('SELECT * FROM pump WHERE id=?', (oid,))
            if p:
                status = '故障' if (p['fault_feedback'] or p['manual_fault']) else (
                    '检修' if p['maintenance'] else ('运行' if p['run_feedback'] else '待机/停止'))
                txt = [f"水泵：{p['pump_code']}  {p['pump_name']}", f"状态：{status}",
                       f"类型：{PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type'])}",
                       f"设定频率：{float(p['set_frequency'] or 0):.1f} Hz",
                       f"运行频率：{float(p['frequency'] or 0):.1f} Hz", f"电流：{float(p['current'] or 0):.1f} A",
                       f"电压：{float(p['voltage'] or 0):.1f} V", f"累计电量：{float(p['energy'] or 0):.2f} kWh",
                       f"当次运行：{self.fmt_seconds(self.pump_this_run_seconds(p))}",
                       f"累计运行：{self.fmt_seconds(self.pump_total_run_seconds(p))}"]
        elif kind == 'pipe':
            p = self.row('SELECT * FROM main_pipe WHERE id=?', (oid,))
            if p:
                txt = [f"母管：{p['pipe_code']}  {p['pipe_name']}",
                       f"管径：{p['standard_dn']} / 内径 {float(p['inner_diameter_mm'] or 0):.0f} mm",
                       f"流量：{float(p['estimated_running_flow'] or p['measured_flow'] or 0):.1f} m3/h",
                       f"压力：{float(p['pressure'] or 0):.2f} MPa",
                       f"流速：{float(p['estimated_velocity'] or 0):.2f} m/s", f"校核：{p['diameter_check_status']}"]
        else:
            ins = self.row('SELECT * FROM instrument WHERE id=?', (oid,))
            if ins:
                txt = [f"仪表：{ins['instrument_code']}  {ins['instrument_name']}", f"类型：{ins['instrument_type']}",
                       f"当前值：{float(ins['current_value'] or 0):.2f}",
                       f"状态：{'屏蔽' if ins['bypassed'] else ins['data_quality']}", f"来源：{ins['data_source']}"]
        self.twin_info.delete('1.0', 'end')
        self.twin_info.insert('end', '\n'.join(txt) if txt else f"对象：{code}\n暂无详细参数")

    def refresh_twin_scene(self):
        # 仅刷新当前对象参数和画面颜色，不影响其它页面。
        try:
            if hasattr(self, 'twin_selected') and self.twin_selected:
                pass
            self.draw_twin_scene()
        except Exception:
            pass

    def build_report_page(self):
        f = self.pages['报表导出']
        info = ttk.Label(f,
                         text='运行日志、日报、月报按当前泵站导出。运行参数每 10 秒自动保存一次，包含水泵启停、流量、压力、电流、频率、液位、电量等。',
                         font=('Microsoft YaHei', 10, 'bold'))
        info.pack(anchor='w', padx=10, pady=8)
        btns = ttk.Frame(f);
        btns.pack(anchor='w', padx=10, pady=5)
        ttk.Button(btns, text='导出运行参数日志 CSV', command=self.export_runtime_log).grid(row=0, column=0, padx=5,
                                                                                            pady=5, sticky='w')
        ttk.Button(btns, text='导出水泵启停记录 CSV', command=self.export_pump_run_records).grid(row=0, column=1,
                                                                                                 padx=5, pady=5,
                                                                                                 sticky='w')
        ttk.Button(btns, text='导出日报表：当天排水量/电量 CSV', command=self.export_daily_summary).grid(row=1, column=0,
                                                                                                        padx=5, pady=5,
                                                                                                        sticky='w')
        ttk.Button(btns, text='导出月报表：当月排水量/电量 CSV', command=self.export_monthly_summary).grid(row=1,
                                                                                                          column=1,
                                                                                                          padx=5,
                                                                                                          pady=5,
                                                                                                          sticky='w')
        ttk.Separator(f, orient='horizontal').pack(fill='x', padx=10, pady=8)
        oldbtns = ttk.Frame(f);
        oldbtns.pack(anchor='w', padx=10, pady=5)
        ttk.Button(oldbtns, text='导出水泵运行日报 CSV（原版）', command=self.export_pump_report).grid(row=0, column=0,
                                                                                                     padx=5, pady=5,
                                                                                                     sticky='w')
        ttk.Button(oldbtns, text='导出流量电量日报 CSV（原版）', command=self.export_flow_report).grid(row=0, column=1,
                                                                                                     padx=5, pady=5,
                                                                                                     sticky='w')
        ttk.Button(oldbtns, text='导出系统配置汇总 CSV', command=self.export_config_report).grid(row=0, column=2,
                                                                                                 padx=5, pady=5,
                                                                                                 sticky='w')
        self.report_msg = ttk.Label(f, text='')
        self.report_msg.pack(anchor='w', padx=10, pady=8)

    def export_runtime_log(self):
        path = self.db.export_runtime_log_csv(self.sid())
        self.report_msg.config(text='已导出运行参数日志：' + path)

    def export_pump_run_records(self):
        path = self.db.export_pump_run_records_csv(self.sid())
        self.report_msg.config(text='已导出水泵启停记录：' + path)

    def export_daily_summary(self):
        path = self.db.export_daily_summary_csv(self.sid())
        self.report_msg.config(text='已导出日报表：' + path)

    def export_monthly_summary(self):
        path = self.db.export_monthly_summary_csv(self.sid())
        self.report_msg.config(text='已导出月报表：' + path)

    def export_pump_report(self):
        rows = []
        for p in self.rows('SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id', (self.sid(),)):
            rows.append(
                [now()[:10], p['pump_code'], p['pump_name'], PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type']),
                 p['run_seconds_today'] / 3600, p['run_seconds_total'] / 3600, p['start_count'], p['stop_count'],
                 p['fault_count'], p['frequency'], p['current']])
        path = self.db.export_csv('pump_daily_report.csv', rows,
                                  ['日期', '编号', '名称', '类型', '今日运行小时', '累计运行小时', '启动次数',
                                   '停止次数', '故障次数', '频率', '电流']);
        self.report_msg.config(text='已导出：' + path)

    def export_flow_report(self):
        rows = []
        # 每根母管一行：优先显示绑定的流量计/压力表；电量使用泵站总电表或单泵电表汇总。
        energy_meter = self.row(
            "SELECT * FROM instrument WHERE station_id=? AND instrument_type='energy' AND owner_type='station' AND enabled=1 AND bypassed=0 ORDER BY report_priority,id LIMIT 1",
            (self.sid(),))
        energy_value = float(energy_meter['current_value'] or 0) if energy_meter else 0
        energy_source = 'station_total_meter' if energy_meter else 'invalid'
        for p in self.rows('SELECT * FROM main_pipe WHERE station_id=?', (self.sid(),)):
            ft = self.row(
                "SELECT * FROM instrument WHERE station_id=? AND instrument_type='flow' AND pipe_id=? AND enabled=1 ORDER BY report_priority,id LIMIT 1",
                (self.sid(), p['id']))
            pt = self.row(
                "SELECT * FROM instrument WHERE station_id=? AND instrument_type='pressure' AND pipe_id=? AND enabled=1 ORDER BY report_priority,id LIMIT 1",
                (self.sid(), p['id']))
            flow_source = 'measured' if ft and not ft['bypassed'] else 'estimated_by_frequency'
            flow_value = (float(ft['current_value'] or 0) * float(ft['correction_factor'] or 1)) if ft and not ft[
                'bypassed'] else p['estimated_running_flow']
            pressure_status = 'normal' if pt and not pt['bypassed'] else 'bypassed/none'
            rows.append(
                [now()[:10], p['pipe_code'], p['pipe_name'], p['standard_dn'], p['theoretical_flow'], flow_value,
                 p['estimated_running_flow'], p['estimated_velocity'], p['diameter_check_status'],
                 ft['instrument_code'] if ft else '', flow_source, pt['instrument_code'] if pt else '', pressure_status,
                 energy_value, energy_source])
        path = self.db.export_csv('flow_energy_report.csv', rows,
                                  ['日期', '母管编号', '母管名称', 'DN', '理论流量', '报表流量', '估算流量', '估算流速',
                                   '管径校核', '流量计', '流量来源', '压力表', '压力状态', '泵站电量', '电量来源']);
        self.report_msg.config(text='已导出：' + path)

    def export_config_report(self):
        rows = []
        st = self.get_station();
        rows.append(['泵站', st['station_code'], st['station_name'], st['station_type']])
        for p in self.rows('SELECT * FROM pump WHERE station_id=?', (self.sid(),)): rows.append(
            ['水泵', p['pump_code'], p['pump_name'], PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type'])])
        for p in self.rows('SELECT * FROM main_pipe WHERE station_id=?', (self.sid(),)): rows.append(
            ['母管', p['pipe_code'], p['pipe_name'], p['standard_dn']])
        for ins in self.rows('SELECT * FROM instrument WHERE station_id=? ORDER BY instrument_type,id', (self.sid(),)):
            rows.append(['仪表', ins['instrument_code'], ins['instrument_name'],
                         f"{ins['instrument_type']} owner={ins['owner_type']} pipe={ins['pipe_id']} pump={ins['pump_id']} bypass={ins['bypassed']} report={ins['report_enable']}"])
        path = self.db.export_csv('config_summary.csv', rows, ['类型', '编号', '名称', '参数']);
        self.report_msg.config(text='已导出：' + path)

    def build_log_page(self):
        f = self.pages['日志'];
        ttk.Button(f, text='刷新日志', command=self.refresh_log).pack(anchor='w', padx=8, pady=5);
        cols = ('时间', '操作', '对象', '名称', '结果', '备注');
        self.log_tree = ttk.Treeview(f, columns=cols, show='headings', height=24)
        for c in cols: self.log_tree.heading(c, text=c); self.log_tree.column(c, width=150, anchor='center')
        self.log_tree.pack(fill='both', expand=True, padx=8, pady=5)

    def refresh_log(self):
        if not hasattr(self, 'log_tree'): return
        self.clear_tree(self.log_tree)
        for r in self.rows('SELECT * FROM operation_log ORDER BY id DESC LIMIT 200'):
            self.log_tree.insert('', 'end',
                                 values=(r['operation_time'], r['operation_type'], r['object_type'], r['object_name'],
                                         r['result'], r['remark']))

    def refresh_realtime(self):
        # 防闪烁策略：后台数据每秒刷新，但只刷新当前正在查看的页面；
        # 首页总览和泵站监控均采用差异更新，不再整页重建。
        try:
            tab_text = self.nb.tab(self.nb.select(), 'text')
        except Exception:
            tab_text = ''
        if '首页总览' in tab_text:
            self.refresh_dashboard()
        if '泵站监控' in tab_text:
            self.refresh_monitor()
        elif '手动控制' in tab_text:
            self.refresh_manual_status_only()
        elif '模型' in tab_text:
            self.draw_model()
        elif '通讯' in tab_text:
            self.refresh_device_list()
        elif '变量' in tab_text:
            self.refresh_point_list()
        elif '视频监控' in tab_text:
            self.refresh_video_status_labels()
        elif '三维孪生' in tab_text:
            self.refresh_twin_scene()
        elif '母管' in tab_text:
            # 母管编辑时不要定时重建列表和表单，否则正在修改的 DN/管径会被数据库旧值覆盖。
            # 保存、切换泵站、新增/删除后会主动刷新。
            pass
        elif '仪表' in tab_text:
            self.refresh_inst_list()

    def build_twin_binding_page(self):
        f = self.pages['数据绑定']
        top = tk.Frame(f, bg='#e7f1fb')
        top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top, text='孪生泵站').pack(side='left', padx=(4, 4))
        self.twin_binding_station_var = tk.StringVar()
        self.twin_binding_station_combo = ttk.Combobox(top, textvariable=self.twin_binding_station_var,
                                                       state='readonly', width=28)
        self.twin_binding_station_combo.pack(side='left', padx=4)
        self.twin_binding_station_combo.bind('<<ComboboxSelected>>', lambda e: self._twin_binding_switch_station())

        body = tk.Frame(f, bg='#edf4fb')
        body.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg='#ffffff', bd=1, relief='solid')
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))
        tk.Label(left, text='扫描绑定 / 设备参数', bg='#ffffff', fg='#0f4c81',
                 font=('Microsoft YaHei', 13, 'bold')).pack(anchor='w', padx=12, pady=(12, 6))
        self.twin_info = tk.Text(left, height=18, bg='#f8fbff', fg='#1f2933', font=('Consolas', 10), wrap='word',
                                 relief='solid', bd=1)
        self.twin_info.pack(fill='both', expand=True, padx=12, pady=6)

        tk.Label(left, text='模型对象 / 设备列表', bg='#ffffff', fg='#0f4c81',
                 font=('Microsoft YaHei', 13, 'bold')).pack(anchor='w', padx=12, pady=(12, 6))
        self.twin_obj_list = tk.Listbox(left, height=28, font=('Microsoft YaHei', 10), activestyle='dotbox')
        self.twin_obj_list.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self.twin_obj_list.bind('<<ListboxSelect>>', lambda e: self.select_twin_from_list())
        self._twin_binding_refresh_station_combo()

    def _twin_binding_refresh_station_combo(self):
        if not hasattr(self, 'twin_binding_station_combo'): return
        vals = []
        current = ''
        for st in self.rows('SELECT id,station_code,station_name FROM pump_station ORDER BY id'):
            txt = f"{st['id']} | {st['station_code']} | {st['station_name']}"
            vals.append(txt)
            if st['id'] == self.sid(): current = txt
        self.twin_binding_station_combo['values'] = vals
        if current:
            self.twin_binding_station_var.set(current)
        elif vals:
            self.twin_binding_station_var.set(vals[0])

    def _twin_binding_switch_station(self):
        try:
            t = (self.twin_binding_station_var.get() or '').strip()
            sid = int(t.split('|')[0].strip()) if t else self.sid()
            if sid:
                self.current_station_id = sid
                self.db.set_current_station(sid)
                self.refresh_station_label()
            self._twin_binding_load_model_config()
        except Exception:
            pass


# ===================== V5.7.8 三维孪生：内嵌动态 GLB 查看器 + 实时数据绑定 =====================
def _v578_twin_viewer_url(self):
    return f'http://127.0.0.1:{self.twin_http_port}/twin_viewer.html'


def _v578_status_from_pump(self, p):
    try:
        if int(p['disabled'] or 0): return 'disabled', '禁用'
        if int(p['manual_fault'] or 0) or int(p['fault_feedback'] or 0): return 'fault', '故障'
        if int(p['maintenance'] or 0): return 'maintenance', '检修'
        if int(p['run_feedback'] or 0): return 'running', '运行'
        if int(p['enabled'] or 1) and int(p['auto_enable'] or 1): return 'standby', '备用'
        return 'stopped', '停止'
    except Exception:
        return 'unknown', '未知'


def _v578_write_twin_state_json(self, sid=None):
    sid = sid or self.twin_sid() or self.sid()
    viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
    os.makedirs(viewer_dir, exist_ok=True)
    st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
    ctrl = self.row('SELECT * FROM station_control_state WHERE station_id=?', (sid,)) if sid else None
    state = {
        'stationId': sid,
        'station': st['station_code'] if st else '',
        'stationName': st['station_name'] if st else '',
        'controlMode': st['control_mode'] if st else '',
        'controlModeText': MODE_LABEL.get(st['control_mode'], st['control_mode']) if st else '',
        'controlState': ctrl['control_state'] if ctrl else '',
        'eventState': ctrl['event_state'] if ctrl else '',
        'currentAction': ctrl['current_action'] if ctrl else '',
        'nextAction': ctrl['next_action'] if ctrl else '',
        'reasonText': ctrl['reason_text'] if ctrl else '',
        'level': float(st['current_level'] or 0) if st else 0,
        'levelRate': float(st['level_rise_rate'] or 0) if st else 0,
        'pumps': {}, 'pipes': {}, 'meters': {}, 'alarms': [],
        'updatedAt': now(),
    }
    try:
        for p in self.rows("SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id", (sid,)):
            code = str(p['pump_code'] or '')
            status, label = _v578_status_from_pump(self, p)
            state['pumps'][code] = {
                'code': code, 'name': p['pump_name'], 'type': PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type']),
                'status': status, 'statusText': label,
                'freq': float(p['frequency'] or 0), 'setFreq': float(p['set_frequency'] or 0),
                'current': float(p['current'] or 0), 'voltage': float(p['voltage'] or 0),
                'power': round(float(p['current'] or 0) * float(p['voltage'] or 0) * 1.732 * 0.85 / 1000, 2),
                'runtimeToday': int(p['run_seconds_today'] or 0), 'runtimeTotal': int(p['run_seconds_total'] or 0),
            }
        for pipe in self.rows('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)):
            code = str(pipe['pipe_code'] or '')
            flow = float(pipe['measured_flow'] or pipe['estimated_running_flow'] or 0)
            pressure = float(pipe['pressure'] or 0)
            status = 'running' if flow > 0.01 else 'stopped'
            val = {'code': code, 'name': pipe['pipe_name'], 'status': status,
                   'statusText': '有流量' if status == 'running' else '无流量', 'flow': flow, 'pressure': pressure,
                   'velocity': float(pipe['estimated_velocity'] or 0), 'dn': pipe['standard_dn']}
            state['pipes'][code] = val
            c = code.upper()
            if not c.startswith('PIPE_'):
                suffix = c.replace('母管', '').replace('PIPE', '').strip('_- ')
                if suffix:
                    state['pipes']['PIPE_' + suffix] = val
        for ins in self.rows('SELECT * FROM instrument WHERE station_id=? ORDER BY instrument_type,id', (sid,)):
            code = str(ins['instrument_code'] or '')
            state['meters'][code] = {
                'code': code, 'name': ins['instrument_name'], 'type': ins['instrument_type'],
                'status': 'bypassed' if int(ins['bypassed'] or 0) else str(ins['data_quality'] or 'normal'),
                'statusText': '屏蔽' if int(ins['bypassed'] or 0) else str(ins['data_quality'] or '正常'),
                'value': float(ins['current_value'] or 0),
                'unit': {'level': 'm', 'flow': 'm3/h', 'pressure': 'MPa', 'current': 'A', 'voltage': 'V',
                         'energy': 'kWh'}.get(str(ins['instrument_type'] or ''), '')
            }
        for ev in self.rows('SELECT * FROM station_control_event WHERE station_id=? ORDER BY id DESC LIMIT 5', (sid,)):
            state['alarms'].append({'time': ev['event_time'], 'level': ev['event_level'], 'type': ev['event_type'],
                                    'device': ev['target_device'], 'message': ev['trigger_reason']})
    except Exception as e:
        state['error'] = str(e)
    out = os.path.join(viewer_dir, 'twin_state.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return out


def _v578_prepare_twin_web_model(self, path):
    try:
        if not path or not os.path.exists(path):
            return None
        viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
        model_dir = os.path.join(viewer_dir, 'models')
        os.makedirs(model_dir, exist_ok=True)
        sid = self.twin_sid() or self.sid()
        st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
        code = (st['station_code'] if st else 'STATION') or 'STATION'
        ext = os.path.splitext(path)[1].lower() or '.glb'
        safe_base = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in code)
        target_name = f'{safe_base}_model{ext}'
        target = os.path.join(model_dir, target_name)
        try:
            if os.path.abspath(path) != os.path.abspath(target):
                shutil.copy2(path, target)
        except Exception:
            pass
        self._write_twin_state_json(sid)
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>泵站三维孪生动态查看器</title>
<style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#050b16;color:#d7ecff;font-family:"Microsoft YaHei",Arial,sans-serif;}#app{position:fixed;inset:0;}
#hud{position:absolute;left:12px;top:10px;right:12px;height:44px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,22,38,.72);border:1px solid rgba(68,188,255,.35);box-shadow:0 0 22px rgba(0,170,255,.18);border-radius:8px;padding:0 12px;z-index:5;backdrop-filter:blur(8px);} .title{font-weight:700;color:#fff;font-size:16px;letter-spacing:1px;} .sub{font-size:12px;color:#8fd3ff;}
#panel{position:absolute;right:12px;top:66px;width:300px;max-height:calc(100vh - 86px);overflow:auto;background:rgba(7,18,32,.78);border:1px solid rgba(68,188,255,.35);border-radius:10px;padding:12px;z-index:5;box-shadow:0 0 22px rgba(0,170,255,.18);} #panel h3{margin:0 0 8px;color:#fff;font-size:15px;} #panel .item{border-bottom:1px solid rgba(143,211,255,.16);padding:5px 0;font-size:12px;line-height:1.5;}
#legend{position:absolute;left:12px;bottom:12px;background:rgba(7,18,32,.78);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:8px 12px;font-size:12px;z-index:5;} .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px;vertical-align:middle;} .green{background:#18d06b;box-shadow:0 0 10px #18d06b;} .blue{background:#2fa8ff;box-shadow:0 0 10px #2fa8ff;} .red{background:#ff4d4f;box-shadow:0 0 10px #ff4d4f;} .yellow{background:#f6c343;box-shadow:0 0 10px #f6c343;} .gray{background:#7b8794;}
#tip{position:absolute;left:16px;top:66px;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:9px 12px;font-size:12px;color:#d7ecff;z-index:6;max-width:340px;display:none;white-space:pre-line;}
#msg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);color:#8fd3ff;font-size:14px;z-index:4;background:rgba(8,22,38,.85);padding:20px 28px;border:1px solid rgba(68,188,255,.35);border-radius:10px;}button{background:#0f6fb2;color:#fff;border:1px solid rgba(143,211,255,.55);border-radius:6px;padding:5px 10px;cursor:pointer;}
</style></head><body>
<div id="app"></div><div id="hud"><div><div class="title">隧道泵站自动控制系统 V5.7.8 · 数据驱动三维孪生</div><div class="sub" id="stationLine">加载中...</div></div><div><button onclick="resetCamera()">复位视角</button> <button onclick="toggleRotate()">自动旋转</button></div></div>
<div id="tip"></div><div id="panel"><h3>实时状态</h3><div id="stateBox">等待数据...</div></div><div id="legend"><span class="dot green"></span>运行 <span class="dot blue"></span>备用 <span class="dot yellow"></span>检修 <span class="dot red"></span>故障 <span class="dot gray"></span>停止/未绑定</div><div id="msg">正在加载 GLB 模型...</div>
<script type="module">
import * as THREE from 'https://unpkg.com/three@0.160.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.160.0/examples/jsm/loaders/GLTFLoader.js';
const container=document.getElementById('app'), msg=document.getElementById('msg'); const scene=new THREE.Scene(); scene.background=new THREE.Color(0x050b16);
const camera=new THREE.PerspectiveCamera(55, window.innerWidth/window.innerHeight, 0.01, 100000); camera.position.set(4,3,5); const renderer=new THREE.WebGLRenderer({antialias:true}); renderer.setSize(window.innerWidth,window.innerHeight); renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2)); container.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.dampingFactor=.08; scene.add(new THREE.HemisphereLight(0xbfdfff,0x182536,1.3)); const light=new THREE.DirectionalLight(0xffffff,1.2); light.position.set(8,10,6); scene.add(light); const grid=new THREE.GridHelper(20,20,0x1e90ff,0x13233a); grid.material.opacity=.18; grid.material.transparent=true; scene.add(grid);
let root=null, autoRotate=false, objectMap={}, state={}; const statusColor={running:0x16d36f, standby:0x2fa8ff, fault:0xff3434, maintenance:0xf6c343, stopped:0x7b8794, disabled:0x363f4a, bypassed:0xa855f7, good:0x16d36f, normal:0x16d36f};
function norm(s){return String(s||'').toUpperCase().replace(/[^A-Z0-9_]/g,'');} function fitCamera(obj){const box=new THREE.Box3().setFromObject(obj); const size=box.getSize(new THREE.Vector3()); const center=box.getCenter(new THREE.Vector3()); const maxSize=Math.max(size.x,size.y,size.z)||1; const dist=maxSize*1.6; camera.position.set(center.x+dist, center.y+dist*.7, center.z+dist); camera.near=maxSize/1000; camera.far=maxSize*100; camera.updateProjectionMatrix(); controls.target.copy(center); controls.update();}
function registerObjects(){objectMap={}; root.traverse(o=>{if(o.name) objectMap[norm(o.name)]=o; if(o.isMesh){o.userData.baseMaterial=o.material; o.userData.baseColor=o.material && o.material.color ? o.material.color.clone() : new THREE.Color(0x66aaff); o.castShadow=true; o.receiveShadow=true;}});} function findObj(code){const key=norm(code); if(objectMap[key]) return objectMap[key]; const keys=Object.keys(objectMap).filter(k=>k===key || k.includes('_'+key) || k.includes(key+'_') || k.endsWith(key)); return keys.length ? objectMap[keys[0]] : null;}
function paintObject(obj,status){if(!obj) return; const col=statusColor[status] ?? 0x7b8794; obj.traverse(m=>{if(m.isMesh){if(!m.userData.dynamicMaterial){m.material=m.material.clone(); m.userData.dynamicMaterial=true;} m.material.color.setHex(col); m.material.emissive=m.material.emissive||new THREE.Color(0x000000); m.material.emissive.setHex(status==='fault'?0x550000:(status==='running'?0x00331a:(status==='maintenance'?0x332200:0x000000))); m.material.emissiveIntensity=status==='fault'?0.65:(status==='running'?0.25:0.12);}});}
function applyState(){if(!root||!state)return; for(const [code,p] of Object.entries(state.pumps||{})) paintObject(findObj(code),p.status); for(const [code,p] of Object.entries(state.pipes||{})) paintObject(findObj(code),p.status); for(const [code,p] of Object.entries(state.meters||{})) paintObject(findObj(code),p.status); document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${Number(state.level||0).toFixed(2)} m | 速率 ${Number(state.levelRate||0).toFixed(3)} m/min | ${state.updatedAt||''}`; const pumpRows=Object.values(state.pumps||{}).slice(0,10).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||''}<br>状态：${p.statusText||p.status}　频率：${Number(p.freq||0).toFixed(1)}Hz　电流：${Number(p.current||0).toFixed(1)}A</div>`).join(''); const pipeRows=Object.values(state.pipes||{}).filter((v,i,a)=>a.findIndex(x=>x.code===v.code)===i).slice(0,5).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||''}<br>流量：${Number(p.flow||0).toFixed(1)} m³/h　压力：${Number(p.pressure||0).toFixed(2)}MPa</div>`).join(''); document.getElementById('stateBox').innerHTML=`<div class="item">控制状态：${state.controlState||'-'}<br>事件状态：${state.eventState||'-'}<br>当前动作：${state.currentAction||'-'}</div>${pumpRows}${pipeRows}`;}
async function loadState(){try{const r=await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'}); state=await r.json(); applyState();}catch(e){console.warn('state load failed',e);}}
const raycaster=new THREE.Raycaster(), mouse=new THREE.Vector2(); renderer.domElement.addEventListener('click',ev=>{if(!root)return; const rect=renderer.domElement.getBoundingClientRect(); mouse.x=((ev.clientX-rect.left)/rect.width)*2-1; mouse.y=-((ev.clientY-rect.top)/rect.height)*2+1; raycaster.setFromCamera(mouse,camera); const hits=raycaster.intersectObject(root,true); if(!hits.length)return; let obj=hits[0].object; while(obj && !obj.name && obj.parent)obj=obj.parent; const name=obj && obj.name?obj.name:hits[0].object.name; const key=norm(name); let data=null,type='对象'; for(const [c,v] of Object.entries(state.pumps||{})) if(key.includes(norm(c))){data=v;type='水泵';break;} if(!data) for(const [c,v] of Object.entries(state.pipes||{})) if(key.includes(norm(c))){data=v;type='母管';break;} if(!data) for(const [c,v] of Object.entries(state.meters||{})) if(key.includes(norm(c))){data=v;type='仪表';break;} const tip=document.getElementById('tip'); tip.style.display='block'; tip.textContent=data ? `${type}：${data.code||name}\n名称：${data.name||''}\n状态：${data.statusText||data.status||''}\n频率：${data.freq!==undefined?data.freq+' Hz':''}\n电流：${data.current!==undefined?data.current+' A':''}\n流量：${data.flow!==undefined?data.flow+' m³/h':''}\n压力：${data.pressure!==undefined?data.pressure+' MPa':''}` : `模型对象：${name}\n未匹配实时数据；请检查 GLB 对象名是否与 P1、PIPE_A、LT01 等编号一致。`;});
new GLTFLoader().load('models/__MODEL__', gltf=>{root=gltf.scene; scene.add(root); registerObjects(); fitCamera(root); msg.style.display='none'; loadState();}, undefined, err=>{msg.textContent='GLB加载失败：'+err.message+'\n请检查模型文件或浏览器WebGL环境。'; console.error(err);});
window.resetCamera=()=>{if(root)fitCamera(root);}; window.toggleRotate=()=>{autoRotate=!autoRotate;}; window.addEventListener('resize',()=>{camera.aspect=window.innerWidth/window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth,window.innerHeight);}); setInterval(loadState,1000); function animate(){requestAnimationFrame(animate); if(autoRotate&&root)root.rotation.y+=.004; controls.update(); renderer.render(scene,camera);} animate();
</script></body></html>""".replace('__MODEL__', target_name)
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        messagebox.showwarning('GLB查看器准备失败', str(e))
        return None


def _v578_show_twin_placeholder(self, message=None):
    if not hasattr(self, 'twin_view_frame'): return
    for child in self.twin_view_frame.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass
    box = tk.Frame(self.twin_view_frame, bg='#07101f')
    box.pack(fill='both', expand=True)
    tk.Label(box, text='三维孪生动态查看器', bg='#07101f', fg='#d7ecff', font=('Microsoft YaHei', 18, 'bold')).pack(
        pady=(60, 12))
    text = message or '请导入 GLB/gltf 模型后点击“加载内嵌动态查看器”。\n模型对象命名建议：P1、P2、JP1、PIPE_A、LT01、FT01、PT01、CAM01。'
    tk.Label(box, text=text, bg='#07101f', fg='#8fd3ff', font=('Microsoft YaHei', 11), justify='center').pack(pady=8)
    btnrow = tk.Frame(box, bg='#07101f');
    btnrow.pack(pady=14)
    ttk.Button(btnrow, text='加载内嵌动态查看器', command=lambda: self.load_twin_in_page(force=True)).pack(side='left',
                                                                                                           padx=6)
    ttk.Button(btnrow, text='外部GLB查看器', command=self.open_twin_model_viewer).pack(side='left', padx=6)
    ttk.Button(btnrow, text='刷新数据绑定', command=self.refresh_twin_scene).pack(side='left', padx=6)
    tk.Label(box, text='说明：若本机未安装内嵌 WebView2 组件，当前页会显示此提示；外部查看器仍可完整旋转/缩放。',
             bg='#07101f', fg='#f6c343', font=('Microsoft YaHei', 9), justify='center').pack(pady=(16, 0))


def _v578_draw_twin_scene(self):
    if not hasattr(self, 'twin_view_frame'):
        return
    path = (self.twin_model_path.get() or '').strip()
    if path and os.path.exists(path):
        self._prepare_twin_web_model(path)
        if not getattr(self, 'twin_loaded_url', ''):
            self._show_twin_placeholder(
                '模型已绑定：{}\n点击“加载内嵌动态查看器”在当前页浏览；如果组件缺失，可使用“外部GLB查看器”。'.format(
                    os.path.basename(path)))
    elif path:
        self._show_twin_placeholder('模型文件不存在或路径失效：\n{}'.format(path))
    else:
        self._show_twin_placeholder()
    self.populate_twin_list()


def _v578_refresh_twin_scene(self):
    try:
        sid = self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        if not getattr(self, 'twin_loaded_url', ''):
            self.draw_twin_scene()
    except Exception:
        pass


App._twin_viewer_url = _v578_twin_viewer_url
App._write_twin_state_json = _v578_write_twin_state_json
App._prepare_twin_web_model = _v578_prepare_twin_web_model
App._show_twin_placeholder = _v578_show_twin_placeholder
App.draw_twin_scene = _v578_draw_twin_scene
App.refresh_twin_scene = _v578_refresh_twin_scene


def _v578_save_twin_model(self):
    sid = self.twin_sid();
    path = (self.twin_model_path.get() or '').strip()
    if not sid:
        messagebox.showwarning('提示', '请先选择泵站');
        return
    name = os.path.basename(path) if path else ''
    old = self.row('SELECT id FROM twin_model WHERE station_id=?', (sid,))
    if old:
        self.db.execute('UPDATE twin_model SET model_name=?,model_path=?,updated_at=? WHERE station_id=?',
                        (name, path, now(), sid))
    else:
        self.db.execute(
            'INSERT INTO twin_model(station_id,model_name,model_path,created_at,updated_at) VALUES(?,?,?,?,?)',
            (sid, name, path, now(), now()))
    if path and os.path.exists(path):
        self._prepare_twin_web_model(path)
        self.load_twin_in_page(force=True)
        messagebox.showinfo('保存成功',
                            '三维模型绑定已保存。已生成动态查看器与 twin_state.json；若当前页未能内嵌，请使用“外部GLB查看器”备用。')
    else:
        self.draw_twin_scene()
        messagebox.showinfo('保存成功', '三维模型绑定信息已保存。')


App.save_twin_model = _v578_save_twin_model


# ===================== V5.7.9 三维孪生查看器修正：恢复兼容型 model-viewer，修复一直“加载中” =====================
def _v579_prepare_twin_web_model(self, path):
    """
    V5.7.8 使用 Three.js ESM 在线模块时，部分电脑/内嵌 WebView 会卡在“正在加载 GLB 模型”。
    V5.7.9 改为兼容型 model-viewer 方案：
    1) HTML 只依赖 model-viewer 组件，和 V5.7.7 外部查看器路线一致；
    2) 支持内嵌 WebView 和外部浏览器共用同一个查看器；
    3) GLTF 会复制同目录贴图/bin，避免外部资源丢失；
    4) 保留 twin_state.json 数据面板与对象命名提示。
    """
    try:
        if not path or not os.path.exists(path):
            return None
        viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
        model_root = os.path.join(viewer_dir, 'models')
        os.makedirs(model_root, exist_ok=True)
        sid = self.twin_sid() or self.sid()
        st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
        code = (st['station_code'] if st else 'STATION') or 'STATION'
        safe_base = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in str(code)) or 'STATION'
        ext = os.path.splitext(path)[1].lower() or '.glb'
        station_model_dir = os.path.join(model_root, safe_base)
        os.makedirs(station_model_dir, exist_ok=True)
        target_name = 'model' + ext
        target = os.path.join(station_model_dir, target_name)
        try:
            if os.path.abspath(path) != os.path.abspath(target):
                shutil.copy2(path, target)
            # gltf 通常依赖同目录 .bin / 贴图，这里复制常见资源，避免浏览器加载失败。
            if ext == '.gltf':
                src_dir = os.path.dirname(os.path.abspath(path))
                for fn in os.listdir(src_dir):
                    low = fn.lower()
                    if low.endswith(('.bin', '.png', '.jpg', '.jpeg', '.webp', '.ktx2', '.gif')):
                        sp = os.path.join(src_dir, fn);
                        dp = os.path.join(station_model_dir, fn)
                        if os.path.isfile(sp) and os.path.abspath(sp) != os.path.abspath(dp):
                            try:
                                shutil.copy2(sp, dp)
                            except Exception:
                                pass
        except Exception:
            pass
        self._write_twin_state_json(sid)
        model_rel = f'models/{safe_base}/{target_name}'
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>泵站数据驱动三维孪生</title>
<style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#050b16;color:#d7ecff;font-family:"Microsoft YaHei",Arial,sans-serif;}#app{position:fixed;inset:0;}model-viewer{width:100%;height:100%;background:radial-gradient(circle at center,#12365a 0%,#07101f 52%,#020814 100%);}
#hud{position:absolute;left:12px;top:10px;right:12px;height:48px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,22,38,.72);border:1px solid rgba(68,188,255,.35);box-shadow:0 0 22px rgba(0,170,255,.18);border-radius:8px;padding:0 12px;z-index:5;backdrop-filter:blur(8px);} .title{font-weight:700;color:#fff;font-size:16px;letter-spacing:1px;} .sub{font-size:12px;color:#8fd3ff;}
#panel{position:absolute;right:12px;top:76px;width:320px;max-height:calc(100vh - 96px);overflow:auto;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:10px;padding:12px;z-index:5;box-shadow:0 0 22px rgba(0,170,255,.18);} #panel h3{margin:0 0 8px;color:#fff;font-size:15px;} #panel .item{border-bottom:1px solid rgba(143,211,255,.16);padding:5px 0;font-size:12px;line-height:1.55;}
#legend{position:absolute;left:12px;bottom:12px;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:8px 12px;font-size:12px;z-index:5;} .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px;vertical-align:middle;} .green{background:#18d06b;box-shadow:0 0 10px #18d06b;} .blue{background:#2fa8ff;box-shadow:0 0 10px #2fa8ff;} .red{background:#ff4d4f;box-shadow:0 0 10px #ff4d4f;} .yellow{background:#f6c343;box-shadow:0 0 10px #f6c343;} .gray{background:#7b8794;}
#msg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:720px;color:#8fd3ff;font-size:14px;line-height:1.8;z-index:7;background:rgba(8,22,38,.92);padding:18px 24px;border:1px solid rgba(68,188,255,.45);border-radius:10px;white-space:pre-line;}button{background:#0f6fb2;color:#fff;border:1px solid rgba(143,211,255,.55);border-radius:6px;padding:6px 12px;cursor:pointer;margin-left:6px}.warn{color:#f6c343}.err{color:#ff7875}.ok{color:#18d06b}
</style></head><body>
<div id="app"><model-viewer id="mv" src="__MODEL__" camera-controls auto-rotate shadow-intensity="1" exposure="1.0" environment-image="neutral" bounds="tight" loading="eager" reveal="auto"></model-viewer></div>
<div id="hud"><div><div class="title">隧道泵站自动控制系统 V5.7.9 · 数据驱动三维孪生</div><div class="sub" id="stationLine">加载中...</div></div><div><button onclick="resetCamera()">复位视角</button><button onclick="toggleRotate()">自动旋转</button><button onclick="reloadModel()">重新加载</button></div></div>
<div id="panel"><h3>实时状态</h3><div id="stateBox">等待数据...</div></div><div id="legend"><span class="dot green"></span>运行 <span class="dot blue"></span>备用 <span class="dot yellow"></span>检修 <span class="dot red"></span>故障 <span class="dot gray"></span>停止/未绑定</div><div id="msg">正在加载三维组件和 GLB 模型...</div>
<script type="module">
const MODEL_URL='__MODEL__';
const CDN_LIST=[
  'https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js',
  'https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js',
  'https://cdn.jsdelivr.net/npm/@google/model-viewer/dist/model-viewer.min.js'
];
const mv=document.getElementById('mv'), msg=document.getElementById('msg'); let state={};
async function ensureModelViewer(){
  if(customElements.get('model-viewer')) return true;
  for(const src of CDN_LIST){
    try{ await import(src); await customElements.whenDefined('model-viewer'); return true; }catch(e){ console.warn('model-viewer load failed',src,e); }
  }
  return !!customElements.get('model-viewer');
}
function num(v,d=2){v=Number(v||0); return isFinite(v)?v.toFixed(d):'0.00'}
async function loadState(){try{const r=await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'}); state=await r.json(); applyState();}catch(e){console.warn('state load failed',e);}}
function applyState(){
  document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||''}`;
  const pumps=Object.values(state.pumps||{}).slice(0,12).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||''}<br>状态：${p.statusText||p.status||'-'}　频率：${num(p.freq,1)}Hz　电流：${num(p.current,1)}A</div>`).join('');
  const pipes=Object.values(state.pipes||{}).slice(0,6).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||''}<br>流量：${num(p.flow,1)} m³/h　压力：${num(p.pressure,2)}MPa</div>`).join('');
  const meters=Object.values(state.meters||{}).slice(0,6).map(m=>`<div class="item"><b>${m.code}</b> ${m.name||''}<br>数值：${num(m.value,2)} ${m.unit||''}　状态：${m.statusText||m.status||'-'}</div>`).join('');
  document.getElementById('stateBox').innerHTML=`<div class="item">控制状态：${state.controlState||'-'}<br>事件状态：${state.eventState||'-'}<br>当前动作：${state.currentAction||'-'}</div>${pumps}${pipes}${meters}`;
}
function showErr(t){msg.style.display='block'; msg.innerHTML=t;}
function hideMsg(){msg.style.display='none';}
function setupViewer(){
  mv.addEventListener('load',()=>{hideMsg(); loadState();});
  mv.addEventListener('error',(e)=>{showErr('<span class="err">GLB/gltf 模型加载失败。</span>\n\n模型路径：'+MODEL_URL+'\n\n常见原因：① gltf 缺少 bin/贴图；② 文件路径复制失败；③ 模型文件本身损坏；④ WebView2/浏览器不支持当前模型。'); console.error(e);});
  mv.addEventListener('click',()=>{loadState();});
  setTimeout(()=>{ if(!mv.loaded){ showErr('<span class="warn">三维组件已启动，但模型仍在加载。</span>\n\n如果长时间停留，请检查：\n1. 模型文件是否过大；\n2. gltf 是否缺少贴图/bin；\n3. 浏览器是否允许访问本地 http://127.0.0.1 服务；\n4. 可点击“重新加载”再试。'); } },12000);
}
window.resetCamera=()=>{try{mv.cameraOrbit='45deg 60deg auto'; mv.fieldOfView='auto'; mv.jumpCameraToGoal();}catch(e){}};
window.toggleRotate=()=>{mv.autoRotate=!mv.autoRotate;};
window.reloadModel=()=>{const u=MODEL_URL+(MODEL_URL.includes('?')?'&':'?')+'ts='+Date.now(); mv.setAttribute('src',u); showErr('正在重新加载模型...');};
ensureModelViewer().then(ok=>{ if(!ok){ showErr('<span class="err">三维组件 model-viewer 未加载。</span>\n\n这通常是网络/CDN被拦截导致。请先使用“系统3D查看”或联系开发者打包本地 model-viewer 组件。'); return;} setupViewer(); loadState(); setInterval(loadState,1000); });
</script></body></html>""".replace('__MODEL__', model_rel)
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        messagebox.showwarning('GLB查看器准备失败', str(e))
        return None


App._prepare_twin_web_model = _v579_prepare_twin_web_model


# ===================== V5.7.10 三维孪生查看器修正：离线 WebGL GLB 查看器 =====================
def _v5710_prepare_twin_web_model(self, path):
    # 离线 WebGL 查看器：不再依赖 model-viewer / Three.js CDN。
    try:
        if not path or not os.path.exists(path):
            return None
        viewer_dir = os.path.join(BASE_DIR, 'twin_viewer')
        model_root = os.path.join(viewer_dir, 'models')
        os.makedirs(model_root, exist_ok=True)
        sid = self.twin_sid() or self.sid()
        st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
        code = (st['station_code'] if st else 'STATION') or 'STATION'
        safe_base = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in str(code)) or 'STATION'
        ext = os.path.splitext(path)[1].lower() or '.glb'
        station_model_dir = os.path.join(model_root, safe_base)
        os.makedirs(station_model_dir, exist_ok=True)
        target_name = 'model' + ext
        target = os.path.join(station_model_dir, target_name)
        if os.path.abspath(path) != os.path.abspath(target):
            shutil.copy2(path, target)
        self._write_twin_state_json(sid)
        model_rel = f'models/{safe_base}/{target_name}'
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>离线GLB三维孪生</title><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#050b16;color:#d7ecff;font-family:"Microsoft YaHei",Arial}canvas{position:fixed;inset:0;width:100%;height:100%;display:block;background:radial-gradient(circle,#12365a 0%,#07101f 55%,#020814 100%)}#hud{position:absolute;left:12px;right:12px;top:10px;height:48px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,22,38,.72);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:0 12px;z-index:5}.title{font-weight:bold;color:#fff;font-size:16px}.sub{font-size:12px;color:#8fd3ff}button{background:#0f6fb2;color:#fff;border:1px solid #69c9ff;border-radius:6px;padding:6px 12px;margin-left:6px}#panel{position:absolute;right:12px;top:76px;width:320px;max-height:calc(100vh - 96px);overflow:auto;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:10px;padding:12px;z-index:5}#panel h3{margin:0 0 8px;color:#fff}.item{border-bottom:1px solid rgba(143,211,255,.16);padding:5px 0;font-size:12px;line-height:1.55}#legend{position:absolute;left:12px;bottom:12px;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:8px 12px;font-size:12px;z-index:5}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px}.green{background:#18d06b}.blue{background:#2fa8ff}.yellow{background:#f6c343}.red{background:#ff4d4f}.gray{background:#7b8794}#msg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:760px;color:#8fd3ff;font-size:14px;line-height:1.8;z-index:7;background:rgba(8,22,38,.92);padding:18px 24px;border:1px solid rgba(68,188,255,.45);border-radius:10px;white-space:pre-line}.err{color:#ff7875}.warn{color:#f6c343}
</style></head><body><canvas id="gl"></canvas><div id="hud"><div><div class="title">隧道泵站自动控制系统 V5.7.10 · 离线数据驱动三维孪生</div><div class="sub" id="stationLine">加载中...</div></div><div><button onclick="resetCamera()">复位视角</button><button onclick="toggleRotate()">自动旋转</button><button onclick="location.reload()">重新加载</button></div></div><div id="panel"><h3>实时状态</h3><div id="stateBox">等待数据...</div></div><div id="legend"><span class="dot green"></span>运行 <span class="dot blue"></span>备用 <span class="dot yellow"></span>检修 <span class="dot red"></span>故障 <span class="dot gray"></span>停止/未绑定</div><div id="msg">正在加载 GLB 模型...</div><script>
const MODEL_URL='__MODEL__';let gl,prog,meshes=[],state={},auto=false;const c=document.getElementById('gl'),msg=document.getElementById('msg');let cam={yaw:.75,pitch:.8,dist:8,pan:[0,0]},B={min:[-1,-1,-1],max:[1,1,1],cen:[0,0,0],r:1};let drag=false,last=[0,0],btn=0;
function show(x){msg.style.display='block';msg.innerHTML=x}function hide(){msg.style.display='none'}function N(s){return String(s||'').toUpperCase().replace(/[^A-Z0-9_]/g,'')}function num(v,d=2){v=Number(v||0);return isFinite(v)?v.toFixed(d):'0.00'}function col(st){return {running:[.06,.82,.38],standby:[.18,.66,1],fault:[1,.2,.2],maintenance:[.96,.76,.26],stopped:[.48,.53,.58],disabled:[.22,.25,.29],normal:[.06,.82,.38]}[st]||[.52,.62,.72]}
function M(){return [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}function MM(a,b){let o=Array(16);for(let r=0;r<4;r++)for(let c=0;c<4;c++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o}function T(v){let m=M();m[12]=v[0];m[13]=v[1];m[14]=v[2];return m}function S(v){let m=M();m[0]=v[0];m[5]=v[1];m[10]=v[2];return m}function Q(q){let x=q[0],y=q[1],z=q[2],w=q[3],x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2;return [1-(yy+zz),xy+wz,xz-wy,0,xy-wz,1-(xx+zz),yz+wx,0,xz+wy,yz-wx,1-(xx+yy),0,0,0,0,1]}function NM(n){if(n.matrix)return n.matrix;let m=M();if(n.translation)m=MM(m,T(n.translation));if(n.rotation)m=MM(m,Q(n.rotation));if(n.scale)m=MM(m,S(n.scale));return m}function tp(m,p){let x=p[0],y=p[1],z=p[2];return [m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]]}
function sub(a,b){return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}function add(a,b){return[a[0]+b[0],a[1]+b[1],a[2]+b[2]]}function cr(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}function dt(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}function nr(a){let l=Math.sqrt(dt(a,a))||1;return[a[0]/l,a[1]/l,a[2]/l]}function P(f,asp,n,fa){let q=1/Math.tan(f/2),nf=1/(n-fa);return[q/asp,0,0,0,0,q,0,0,0,0,(fa+n)*nf,-1,0,0,2*fa*n*nf,0]}function LA(e,ce,u){let z=nr(sub(e,ce)),x=nr(cr(u,z)),y=cr(z,x);return[x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dt(x,e),-dt(y,e),-dt(z,e),1]}
function sh(t,s){let h=gl.createShader(t);gl.shaderSource(h,s);gl.compileShader(h);if(!gl.getShaderParameter(h,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(h));return h}function init(){gl=c.getContext('webgl',{antialias:true})||c.getContext('experimental-webgl');if(!gl)throw Error('当前浏览器/WebView不支持WebGL');gl.getExtension('OES_element_index_uint');let vs='attribute vec3 p,n;uniform mat4 mvp,mo;varying vec3 vn;void main(){vn=mat3(mo)*n;gl_Position=mvp*vec4(p,1.0);}';let fs='precision mediump float;uniform vec3 color;uniform float pulse;varying vec3 vn;void main(){float d=max(dot(normalize(vn),normalize(vec3(.4,.8,.5))),0.0);gl_FragColor=vec4(color*(.35+.65*d)+color*pulse*.35,1.0);}';prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,vs));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(prog));gl.useProgram(prog);gl.enable(gl.DEPTH_TEST)}
function cs(t){return{SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[t]||1}function cb(t){return{5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[t]||4}function rc(d,o,t){if(t==5120)return d.getInt8(o);if(t==5121)return d.getUint8(o);if(t==5122)return d.getInt16(o,true);if(t==5123)return d.getUint16(o,true);if(t==5125)return d.getUint32(o,true);if(t==5126)return d.getFloat32(o,true);return 0}async function load(){let ab=await(await fetch(MODEL_URL)).arrayBuffer(),dv=new DataView(ab);if(dv.getUint32(0,true)!=0x46546c67)throw Error('当前离线查看器优先支持 .glb；如为 .gltf，请导出为未压缩 .glb 后再导入。');let off=12,j=null,bin=null;while(off<ab.byteLength){let l=dv.getUint32(off,true),ty=dv.getUint32(off+4,true);off+=8;let ch=ab.slice(off,off+l);off+=l;if(ty==0x4e4f534a)j=JSON.parse(new TextDecoder().decode(ch));else if(ty==0x004e4942)bin=ch}return{j,b:[bin]}}
function acc(g,i){let a=g.j.accessors[i],v=g.j.bufferViews[a.bufferView],buf=g.b[v.buffer||0],d=new DataView(buf),n=cs(a.type),b=cb(a.componentType),st=v.byteStride||n*b,off=(v.byteOffset||0)+(a.byteOffset||0),o=[];for(let x=0;x<a.count;x++){let r=[];for(let k=0;k<n;k++)r.push(rc(d,off+x*st+k*b,a.componentType));o.push(r)}return o}function fl(a){let o=[];for(const r of a)o.push(...r);return new Float32Array(o)}function ia(a){let o=[];for(const r of a)o.push(r[0]);return new Uint32Array(o)}function normals(p,ind){let n=Array(p.length).fill(0).map(()=>[0,0,0]),ids=ind?Array.from(ind):p.map((_,i)=>i);for(let i=0;i<ids.length;i+=3){let a=ids[i],b=ids[i+1],c=ids[i+2];if(a==null||b==null||c==null)continue;let nn=nr(cr(sub(p[b],p[a]),sub(p[c],p[a])));for(const x of[a,b,c])n[x]=add(n[x],nn)}return n.map(nr)}function matColor(g,i){try{let f=g.j.materials[i].pbrMetallicRoughness.baseColorFactor;return[f[0],f[1],f[2]]}catch(e){return[.45,.62,.82]}}
function build(g){let scenes=g.j.scenes,sceneIndex=g.j.scene||0,sc=(scenes&&scenes[sceneIndex])?scenes[sceneIndex]:(scenes&&scenes[0]),nodes=(sc&&sc.nodes)?sc.nodes:[];let mi=[1e9,1e9,1e9],ma=[-1e9,-1e9,-1e9];function upd(p){for(let i=0;i<3;i++){mi[i]=Math.min(mi[i],p[i]);ma[i]=Math.max(ma[i],p[i])}}function rec(ni,pm){let nd=g.j.nodes[ni],wm=MM(pm,NM(nd));if(nd.mesh!=null){let me=g.j.meshes[nd.mesh];for(const pr of me.primitives||[]){if(pr.mode!=null&&pr.mode!==4)continue;if(pr.extensions&&pr.extensions.KHR_draco_mesh_compression)throw Error('模型使用Draco压缩，请重新导出未压缩GLB');if(!pr.attributes||pr.attributes.POSITION==null)continue;let p=acc(g,pr.attributes.POSITION),ind=pr.indices!=null?ia(acc(g,pr.indices)):null,n=pr.attributes.NORMAL!=null?acc(g,pr.attributes.NORMAL):normals(p,ind);p.map(x=>tp(wm,x)).forEach(upd);let it={name:nd.name||me.name||'',meshName:me.name||'',model:wm,color:matColor(g,pr.material),count:ind?ind.length:p.length,indexed:!!ind};it.v=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.bufferData(gl.ARRAY_BUFFER,fl(p),gl.STATIC_DRAW);it.n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.bufferData(gl.ARRAY_BUFFER,fl(n),gl.STATIC_DRAW);if(ind){it.i=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,ind,gl.STATIC_DRAW)}meshes.push(it)}}for(const x of nd.children||[])rec(x,wm)}for(const n of nodes)rec(n,M());if(!meshes.length)throw Error('模型内没有普通网格或为空模型');B.min=mi;B.max=ma;B.cen=[(mi[0]+ma[0])/2,(mi[1]+ma[1])/2,(mi[2]+ma[2])/2];B.r=Math.max(...sub(ma,mi).map(Math.abs))/2||1;resetCamera()}
function match(name){let k=N(name);for(const[c,v]of Object.entries(state.pumps||{}))if(k==N(c)||k.includes(N(c)))return v.status;for(const[c,v]of Object.entries(state.pipes||{}))if(k==N(c)||k.includes(N(c)))return v.status;for(const[c,v]of Object.entries(state.meters||{}))if(k==N(c)||k.includes(N(c)))return v.status;return null}
function resize(){let r=window.devicePixelRatio||1,w=c.clientWidth*r,h=c.clientHeight*r;if(c.width!=w||c.height!=h){c.width=w;c.height=h}}function draw(){requestAnimationFrame(draw);resize();if(auto)cam.yaw+=.006;gl.viewport(0,0,c.width,c.height);gl.clearColor(.02,.04,.08,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);let r=cam.dist,cp=Math.cos(cam.pitch),eye=[B.cen[0]+r*cp*Math.sin(cam.yaw)+cam.pan[0],B.cen[1]+r*Math.sin(cam.pitch)+cam.pan[1],B.cen[2]+r*cp*Math.cos(cam.yaw)],view=LA(eye,[B.cen[0]+cam.pan[0],B.cen[1]+cam.pan[1],B.cen[2]],[0,1,0]),proj=P(Math.PI/4,c.width/c.height,Math.max(.01,B.r/1000),B.r*100+100);let ap=gl.getAttribLocation(prog,'p'),an=gl.getAttribLocation(prog,'n'),um=gl.getUniformLocation(prog,'mvp'),umo=gl.getUniformLocation(prog,'mo'),uc=gl.getUniformLocation(prog,'color'),up=gl.getUniformLocation(prog,'pulse'),t=Date.now()/400;for(const it of meshes){let st=match(it.name)||match(it.meshName),co=st?col(st):it.color,mvp=MM(proj,MM(view,it.model));gl.uniformMatrix4fv(um,false,new Float32Array(mvp));gl.uniformMatrix4fv(umo,false,new Float32Array(it.model));gl.uniform3fv(uc,new Float32Array(co));gl.uniform1f(up,st==='fault'?(Math.sin(t)+1)/2:0);gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.enableVertexAttribArray(ap);gl.vertexAttribPointer(ap,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.enableVertexAttribArray(an);gl.vertexAttribPointer(an,3,gl.FLOAT,false,0,0);if(it.indexed){gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.drawElements(gl.TRIANGLES,it.count,gl.UNSIGNED_INT,0)}else gl.drawArrays(gl.TRIANGLES,0,it.count)}}
async function loadState(){try{state=await(await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'})).json();applyState()}catch(e){}}function applyState(){document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||''}`;let pumps=Object.values(state.pumps||{}).slice(0,12).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||''}<br>状态：${p.statusText||p.status||'-'}　频率：${num(p.freq,1)}Hz　电流：${num(p.current,1)}A</div>`).join(''),pipes=Object.values(state.pipes||{}).slice(0,6).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||''}<br>流量：${num(p.flow,1)} m³/h　压力：${num(p.pressure,2)}MPa</div>`).join('');document.getElementById('stateBox').innerHTML=`<div class="item">控制状态：${state.controlState||'-'}<br>事件状态：${state.eventState||'-'}<br>当前动作：${state.currentAction||'-'}</div>${pumps}${pipes}`}
function resetCamera(){cam.dist=Math.max(2,B.r*3.2);cam.yaw=.75;cam.pitch=.9;cam.pan=[0,0]}window.resetCamera=resetCamera;window.toggleRotate=()=>auto=!auto;c.oncontextmenu=e=>e.preventDefault();c.onmousedown=e=>{drag=true;last=[e.clientX,e.clientY];btn=e.button};window.onmouseup=()=>drag=false;window.onmousemove=e=>{if(!drag)return;let dx=e.clientX-last[0],dy=e.clientY-last[1];last=[e.clientX,e.clientY];if(btn==2||btn==1){let s=B.r/350;cam.pan[0]+=dx*s;cam.pan[1]-=dy*s}else{cam.yaw+=dx*.008;cam.pitch=Math.max(-1.45,Math.min(1.45,cam.pitch+dy*.006))}};c.onwheel=e=>{e.preventDefault();cam.dist*=e.deltaY>0?1.12:.89;cam.dist=Math.max(B.r*.25,cam.dist)};
(async()=>{try{init();let g=await load();build(g);hide();await loadState();setInterval(loadState,1000);draw()}catch(e){console.error(e);show('<span class="err">三维模型加载失败：</span> '+(e.message||e)+'\n\n处理建议：\n1. 请优先导入 .glb 文件；\n2. 如果模型使用 Draco/压缩网格，请重新导出未压缩 GLB；\n3. 用 Windows 系统3D查看器确认模型本身是否正常；\n4. 本查看器不依赖外网，若仍失败，多半是模型格式问题。')}})();
</script></body></html>'''.replace('__MODEL__', model_rel)
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        messagebox.showwarning('GLB查看器准备失败', str(e));
        return None


class _TwinReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def _v5710_start_twin_http_server(self):
    viewer_dir = os.path.join(BASE_DIR, 'twin_viewer');
    os.makedirs(viewer_dir, exist_ok=True)
    if getattr(self, 'twin_httpd', None): return True
    last_err = None
    for port in [getattr(self, 'twin_http_port', 8765)] + list(range(8766, 8785)):
        try:
            handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=viewer_dir,
                                                                                   **kwargs)
            self.twin_httpd = _TwinReusableTCPServer(('127.0.0.1', int(port)), handler)
            self.twin_http_port = int(port)
            threading.Thread(target=self.twin_httpd.serve_forever, daemon=True).start();
            return True
        except OSError as e:
            last_err = e;
            continue
        except Exception as e:
            last_err = e;
            break
    messagebox.showwarning('GLB查看器启动失败', '本地HTTP服务启动失败：' + str(last_err));
    return False


App._prepare_twin_web_model = _v5710_prepare_twin_web_model
App._start_twin_http_server = _v5710_start_twin_http_server


def main():
    app = App();
    app.mainloop()


# ===================== V5.7.11: GLB object scan + twin binding table =====================
def _v5711_norm_name(s):
    import re
    return re.sub(r'[^A-Z0-9_]', '', str(s or '').upper())


def _v5711_read_gltf_json(path):
    """Read .glb/.gltf JSON chunk for object scanning. No external dependency."""
    ext = os.path.splitext(path or '')[1].lower()
    if ext == '.gltf':
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < 20 or data[:4] != b'glTF':
        raise ValueError('not a valid glb file')
    off = 12
    while off + 8 <= len(data):
        clen = int.from_bytes(data[off:off + 4], 'little')
        ctype = data[off + 4:off + 8]
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == b'JSON':
            return json.loads(chunk.decode('utf-8').rstrip('\x00 \t\r\n'))
    raise ValueError('glb json chunk not found')


def _v5711_classify_object_name(name):
    n = _v5711_norm_name(name)
    import re
    if not n:
        return 'unknown', ''
    if n.startswith('ANNO_'):
        return 'anchor', n[5:]
    if re.fullmatch(r'JP\d+', n):
        return 'feed_pump', n
    if re.fullmatch(r'P\d+', n):
        return 'pump', n
    if n.startswith('PIPE_') or n.startswith('PIPE') or n.startswith('MG_'):
        return 'pipe', n if n.startswith('PIPE_') else ('PIPE_' + n.replace('PIPE', '').strip('_'))
    if re.fullmatch(r'LT\d+', n) or n.startswith('LT_'):
        return 'level_meter', n.replace('LT_', 'LT')
    if re.fullmatch(r'FT\d+', n) or n.startswith('FT_') or n.startswith('FT'):
        return 'flow_meter', n.replace('FT_', 'FT')
    if re.fullmatch(r'PT\d+', n) or n.startswith('PT_') or n.startswith('PT'):
        return 'pressure_meter', n.replace('PT_', 'PT')
    if re.fullmatch(r'EM\d+', n) or n.startswith('EM_'):
        return 'energy_meter', n.replace('EM_', 'EM')
    if re.fullmatch(r'CAM\d+', n) or n.startswith('CAM_'):
        return 'camera', n.replace('CAM_', 'CAM')
    if n.startswith('CAB'):
        return 'cabinet', n
    if n.startswith('TANK'):
        return 'tank', n
    if n.startswith('ST') and n.endswith('NODE'):
        return 'station_node', n
    return 'unknown', n


def _v5711_type_label(t):
    return {
        'pump': '主泵', 'feed_pump': '补水泵', 'pipe': '母管',
        'level_meter': '液位计', 'flow_meter': '流量计', 'pressure_meter': '压力表',
        'energy_meter': '电表', 'camera': '摄像头', 'cabinet': '控制柜',
        'tank': '水箱/水仓', 'station_node': '泵站节点',
        'anchor': '标注锚点', 'unknown': '未识别'
    }.get(t, t)


def _v5711_scan_gltf_objects(self, path=None):
    path = path or (self.twin_model_path.get() if hasattr(self, 'twin_model_path') else '')
    if not path or not os.path.exists(path):
        raise FileNotFoundError(path or 'empty model path')
    j = _v5711_read_gltf_json(path)
    meshes = j.get('meshes') or []
    nodes = j.get('nodes') or []
    out = [];
    seen = set()
    for idx, node in enumerate(nodes):
        name = node.get('name') or ''
        mesh_name = ''
        if node.get('mesh') is not None and node.get('mesh') < len(meshes):
            mesh_name = meshes[node.get('mesh')].get('name') or ''
        show = name or mesh_name or ('NODE_%s' % idx)
        key = _v5711_norm_name(show)
        if not key or key in seen:
            continue
        seen.add(key)
        typ, code = _v5711_classify_object_name(show)
        out.append(
            {'objectName': show, 'normName': key, 'type': typ, 'code': code, 'hasMesh': node.get('mesh') is not None,
             'meshName': mesh_name, 'nodeIndex': idx})
    for idx, mesh in enumerate(meshes):
        name = mesh.get('name') or ''
        key = _v5711_norm_name(name)
        if key and key not in seen:
            seen.add(key)
            typ, code = _v5711_classify_object_name(name)
            out.append(
                {'objectName': name, 'normName': key, 'type': typ, 'code': code, 'hasMesh': True, 'meshName': name,
                 'nodeIndex': None})
    return out


def _v5711_data_path_for(t, code):
    if t in ('pump', 'feed_pump'):
        return 'pumps.%s' % code
    if t == 'pipe':
        return 'pipes.%s' % code
    if t in ('level_meter', 'flow_meter', 'pressure_meter', 'energy_meter'):
        return 'meters.%s' % code
    if t == 'camera':
        return 'cameras.%s' % code
    if t == 'station_node':
        return 'stations.%s' % code
    return ''


def _v5711_label_fields_for(t):
    if t in ('pump', 'feed_pump'):
        return ['status', 'freq', 'current']
    if t == 'pipe':
        return ['flow', 'pressure']
    if t in ('level_meter', 'flow_meter', 'pressure_meter', 'energy_meter'):
        return ['value', 'status']
    if t == 'camera':
        return ['status']
    return ['status']


def _v5711_existing_codes(self, sid):
    codes = set()
    try:
        for r in self.rows('SELECT pump_code FROM pump WHERE station_id=?', (sid,)):
            codes.add(_v5711_norm_name(r['pump_code']))
        for r in self.rows('SELECT pipe_code FROM main_pipe WHERE station_id=?', (sid,)):
            c = _v5711_norm_name(r['pipe_code']);
            codes.add(c)
            if c and not c.startswith('PIPE_'):
                codes.add('PIPE_' + c.replace('PIPE', '').strip('_'))
        for r in self.rows('SELECT instrument_code FROM instrument WHERE station_id=?', (sid,)):
            codes.add(_v5711_norm_name(r['instrument_code']))
        for r in self.rows('SELECT camera_code FROM camera WHERE station_id=?', (sid,)):
            codes.add(_v5711_norm_name(r['camera_code']))
    except Exception:
        pass
    return codes


def _v5711_generate_binding_dict(self, path=None):
    sid = self.twin_sid() or self.sid()
    st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
    station_code = (st['station_code'] if st else 'STATION') or 'STATION'
    path = path or (self.twin_model_path.get() if hasattr(self, 'twin_model_path') else '')
    objs = self._scan_gltf_objects(path)
    anchors = {o['normName'] for o in objs if o['type'] == 'anchor'}
    existing = _v5711_existing_codes(self, sid)
    bindings = {};
    unbound = [];
    anchor_count = 0
    for o in objs:
        typ = o['type'];
        code = o['code'];
        obj = o['objectName']
        if typ == 'anchor':
            continue
        if typ == 'unknown' or not code:
            unbound.append(o);
            continue
        anchor = 'ANNO_' + _v5711_norm_name(code)
        has_anchor = anchor in anchors
        if has_anchor: anchor_count += 1
        enabled = True
        # Matching is strict enough to avoid accidental unknown objects, but still allows station nodes.
        matched = (_v5711_norm_name(code) in existing) or typ in ('tank', 'station_node', 'cabinet')
        bindings[obj] = {
            'globalId': '%s.%s' % (station_code, code),
            'stationId': station_code,
            'modelObject': obj,
            'objectCode': code,
            'type': typ,
            'typeText': _v5711_type_label(typ),
            'name': code,
            'dataPath': _v5711_data_path_for(typ, code),
            'anchor': anchor if has_anchor else '',
            'anchorAuto': 'bbox_top' if not has_anchor else 'model_anchor',
            'labelFields': _v5711_label_fields_for(typ),
            'enabled': bool(enabled and (matched or typ != 'unknown')),
            'matchedInSystem': bool(matched),
        }
    return {
        'version': 'V5.7.11', 'stationId': station_code, 'stationDbId': sid,
        'modelFile': os.path.basename(path or ''), 'modelPath': path or '', 'generatedAt': now(),
        'summary': {'objects': len(objs), 'bindings': len(bindings), 'anchors': len(anchors),
                    'usedAnchors': anchor_count, 'unbound': len(unbound)},
        'bindings': bindings,
        'unboundObjects': unbound[:200]
    }


def _v5711_binding_paths(self):
    viewer_dir = os.path.join(BASE_DIR, 'twin_viewer');
    os.makedirs(viewer_dir, exist_ok=True)
    sid = self.twin_sid() or self.sid()
    st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
    code = (st['station_code'] if st else 'STATION') or 'STATION'
    safe = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in str(code)) or 'STATION'
    return viewer_dir, os.path.join(viewer_dir, 'twin_binding.json'), os.path.join(viewer_dir,
                                                                                   'twin_binding_%s.json' % safe), os.path.join(
        REPORT_DIR, 'twin_binding_%s.csv' % safe)


def _v5711_write_binding_files(self, binding=None, show_message=False):
    binding = binding or self._generate_twin_binding_dict()
    viewer_dir, common_path, station_path, csv_path = self._twin_binding_paths()
    for fp in (common_path, station_path):
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(binding, f, ensure_ascii=False, indent=2)
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['modelObject', 'objectCode', 'type', 'globalId', 'dataPath', 'anchor', 'anchorMode', 'enabled',
                    'matchedInSystem'])
        for obj, b in binding.get('bindings', {}).items():
            w.writerow(
                [obj, b.get('objectCode'), b.get('typeText'), b.get('globalId'), b.get('dataPath'), b.get('anchor'),
                 b.get('anchorAuto'), b.get('enabled'), b.get('matchedInSystem')])
    if show_message:
        messagebox.showinfo('生成成功', '已生成模型绑定表：\n%s\n\nCSV：\n%s' % (station_path, csv_path))
    return binding


def _v5711_show_binding_result(self, binding):
    if hasattr(self, 'twin_info'):
        s = binding.get('summary', {})
        lines = []
        lines.append('模型对象扫描 / 绑定表')
        lines.append('station: %s' % binding.get('stationId'))
        lines.append('objects: %s, bindings: %s, anchors: %s, used anchors: %s, unbound: %s' % (s.get('objects'),
                                                                                                s.get('bindings'),
                                                                                                s.get('anchors'),
                                                                                                s.get('usedAnchors'),
                                                                                                s.get('unbound')))
        lines.append('')
        for obj, b in list(binding.get('bindings', {}).items())[:80]:
            lines.append('%-20s | %-8s | %-16s | anchor=%s | %s' % (obj, b.get('typeText'), b.get('dataPath'),
                                                                    b.get('anchor') or b.get('anchorAuto'),
                                                                    'OK' if b.get('matchedInSystem') else 'MODEL'))
        if binding.get('unboundObjects'):
            lines.append('')
            lines.append('unbound objects:')
            for o in binding.get('unboundObjects', [])[:40]:
                lines.append('  - %s (%s)' % (o.get('objectName'), o.get('type')))
        self.twin_info.delete('1.0', 'end')
        self.twin_info.insert('end', '\n'.join(lines))
    if hasattr(self, 'twin_obj_list'):
        self.twin_obj_list.delete(0, 'end')
        for obj, b in binding.get('bindings', {}).items():
            self.twin_obj_list.insert('end', '%s | %s | %s | %s' % (b.get('typeText'), obj, b.get('objectCode'),
                                                                    b.get('dataPath')))
        if binding.get('unboundObjects'):
            for o in binding.get('unboundObjects', [])[:50]:
                self.twin_obj_list.insert('end', '未绑定 | %s | %s | ' % (o.get('objectName'), o.get('type')))


def _v5711_scan_twin_model_objects(self):
    path = (self.twin_model_path.get() or '').strip()
    if not path or not os.path.exists(path):
        messagebox.showwarning('提示', '请先导入 GLB/gltf 模型文件。');
        return
    try:
        binding = self._write_binding_files(self._generate_twin_binding_dict(path), show_message=False)
        self._show_binding_result(binding)
        messagebox.showinfo('扫描完成',
                            '已扫描模型对象，并生成绑定表。\n绑定数：%s\n标注锚点：%s' % (binding['summary']['bindings'],
                                                                                      binding['summary']['anchors']))
    except Exception as e:
        messagebox.showwarning('扫描失败', str(e))


def _v5711_generate_twin_binding(self):
    try:
        binding = self._write_binding_files(show_message=True)
        self._show_binding_result(binding)
    except Exception as e:
        messagebox.showwarning('生成失败', str(e))


def _v5711_save_twin_model(self):
    sid = self.twin_sid()
    path = (self.twin_model_path.get() or '').strip()
    if not sid:
        messagebox.showwarning('提示', '请先选择泵站')
        return
    name = os.path.basename(path) if path else ''
    old = self.row('SELECT id FROM twin_model WHERE station_id=?', (sid,))
    if old:
        self.db.execute('UPDATE twin_model SET model_name=?,model_path=?,updated_at=? WHERE station_id=?',
                        (name, path, now(), sid))
    else:
        self.db.execute(
            'INSERT INTO twin_model(station_id,model_name,model_path,created_at,updated_at) VALUES(?,?,?,?,?)',
            (sid, name, path, now(), now()))
    if path and os.path.exists(path):
        self._prepare_twin_web_model(path)
        try:
            binding = self._write_binding_files(self._generate_twin_binding_dict(path), show_message=False)
            self._show_binding_result(binding)
        except Exception:
            pass
        self.load_twin_in_page(force=True)
        messagebox.showinfo('保存成功', '模型绑定已保存，并生成 twin_binding.json。')
    else:
        self.draw_twin_scene()
        messagebox.showinfo('保存成功', '三维模型绑定信息已保存。')


def _v5711_select_twin_from_list(self):
    if not hasattr(self, 'twin_obj_list'): return
    sel = self.twin_obj_list.curselection()
    if not sel: return
    text = self.twin_obj_list.get(sel[0])
    if '|' in text and not text.strip().startswith(('水泵', '母管', '仪表')):
        if hasattr(self, 'twin_info'):
            self.twin_info.insert('end', '\n\nselected: ' + text)
            self.twin_info.see('end')
        return
    try:
        return _old_select_twin_from_list(self)
    except Exception:
        if hasattr(self, 'twin_info'):
            self.twin_info.insert('end', '\n\nselected: ' + text)
            self.twin_info.see('end')


def _v5711_open_twin_model_viewer(self):
    path = (self.twin_model_path.get() or '').strip()
    if not path or not os.path.exists(path):
        messagebox.showwarning('提示', '请先导入并保存 glb/gltf 模型文件。');
        return
    self._prepare_twin_web_model(path)
    try:
        self._write_binding_files(self._generate_twin_binding_dict(path), show_message=False)
    except Exception:
        pass
    if self._start_twin_http_server():
        webbrowser.open(f'http://127.0.0.1:{self.twin_http_port}/twin_viewer.html?ts={int(time.time())}')


_old_select_twin_from_list = App.select_twin_from_list
App._scan_gltf_objects = _v5711_scan_gltf_objects
App._generate_twin_binding_dict = _v5711_generate_binding_dict
App._twin_binding_paths = _v5711_binding_paths
App._write_binding_files = _v5711_write_binding_files
App._show_binding_result = _v5711_show_binding_result
App.scan_twin_model_objects = _v5711_scan_twin_model_objects
App.generate_twin_binding = _v5711_generate_twin_binding
App.save_twin_model = _v5711_save_twin_model
App.select_twin_from_list = _v5711_select_twin_from_list
App.open_twin_model_viewer = _v5711_open_twin_model_viewer

# ===================== V5.7.12 视频配置合并与 WebView 依赖修正 =====================
# 1) 主导航不再单独占用“视频配置”页；
# 2) “视频监控”内部增加两个子页：实时监控 / 摄像头配置；
# 3) 修正 optional WebView 安装脚本中 tkinterwebview2 不存在导致的误报；
# 说明：三维孪生外部 GLB 查看器继续作为稳定主方案，内嵌为可选增强。

_old_v5712_build_video_page = App.build_video_page
_old_v5712_build_camera_config_page = App.build_camera_config_page


def _v5712_build_video_page(self):
    f = self.pages['视频监控']
    # 清空原容器，避免重复构建时叠加控件。
    for child in list(f.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass
    self.video_inner_nb = ttk.Notebook(f)
    self.video_inner_nb.pack(fill='both', expand=True, padx=6, pady=6)
    monitor_frame = ttk.Frame(self.video_inner_nb)
    config_frame = ttk.Frame(self.video_inner_nb)
    self.video_inner_nb.add(monitor_frame, text='实时监控')
    self.video_inner_nb.add(config_frame, text='摄像头配置')

    # 复用原视频监控与视频配置构建函数，但把构建目标临时切到内部子页。
    outer_video = self.pages.get('视频监控')
    old_config = self.pages.get('视频配置')
    self.pages['视频监控'] = monitor_frame
    self.pages['视频配置'] = config_frame
    try:
        _old_v5712_build_video_page(self)
        _old_v5712_build_camera_config_page(self)
    finally:
        # 主页面仍指向外层视频监控页；视频配置作为内部虚拟页保留，便于后续刷新方法使用。
        self.pages['视频监控'] = outer_video
        self.pages['视频配置'] = config_frame if config_frame.winfo_exists() else old_config

    # 子页切换时自动刷新泵站与摄像头列表，避免进入配置页时数据为空。
    def _on_video_tab_changed(event=None):
        try:
            self.refresh_video_station_choices()
            self.refresh_camera_list()
            self.refresh_video_slots()
        except Exception:
            pass

    try:
        self.video_inner_nb.bind('<<NotebookTabChanged>>', _on_video_tab_changed)
    except Exception:
        pass


App.build_video_page = _v5712_build_video_page

# ===================== V5.7.14_TwinBindFix: GLB路径、权限、旧版本目录修复 =====================
# 目标：不再把模型写入 BASE_DIR/twin_viewer/models/STxx/model.glb，避免程序目录权限、旧版本路径残留、model.glb重名冲突。
# 新策略：模型、查看器、状态文件统一写入可写运行目录：优先 BASE_DIR/data；失败则 LOCALAPPDATA/TunnelPumpControl。

_V5713_VERSION = 'V5.7.14_TwinBindFix'

_V5713_OFFLINE_HTML_TEMPLATE = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>离线GLB三维孪生</title><style>\nhtml,body{margin:0;width:100%;height:100%;overflow:hidden;background:#050b16;color:#d7ecff;font-family:"Microsoft YaHei",Arial}canvas{position:fixed;inset:0;width:100%;height:100%;display:block;background:radial-gradient(circle,#12365a 0%,#07101f 55%,#020814 100%)}#hud{position:absolute;left:12px;right:12px;top:10px;height:48px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,22,38,.72);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:0 12px;z-index:5}.title{font-weight:bold;color:#fff;font-size:16px}.sub{font-size:12px;color:#8fd3ff}button{background:#0f6fb2;color:#fff;border:1px solid #69c9ff;border-radius:6px;padding:6px 12px;margin-left:6px}#panel{position:absolute;right:12px;top:76px;width:320px;max-height:calc(100vh - 96px);overflow:auto;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:10px;padding:12px;z-index:5}#panel h3{margin:0 0 8px;color:#fff}.item{border-bottom:1px solid rgba(143,211,255,.16);padding:5px 0;font-size:12px;line-height:1.55}#legend{position:absolute;left:12px;bottom:12px;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:8px 12px;font-size:12px;z-index:5}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px}.green{background:#18d06b}.blue{background:#2fa8ff}.yellow{background:#f6c343}.red{background:#ff4d4f}.gray{background:#7b8794}#msg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:760px;color:#8fd3ff;font-size:14px;line-height:1.8;z-index:7;background:rgba(8,22,38,.92);padding:18px 24px;border:1px solid rgba(68,188,255,.45);border-radius:10px;white-space:pre-line}.err{color:#ff7875}.warn{color:#f6c343}\n</style></head><body><canvas id="gl"></canvas><div id="hud"><div><div class="title">隧道泵站自动控制系统 V5.7.14_TwinBindFix · 离线路径修复三维孪生</div><div class="sub" id="stationLine">加载中...</div></div><div><button onclick="resetCamera()">复位视角</button><button onclick="toggleRotate()">自动旋转</button><button onclick="location.reload()">重新加载</button></div></div><div id="panel"><h3>实时状态</h3><div id="stateBox">等待数据...</div></div><div id="legend"><span class="dot green"></span>运行 <span class="dot blue"></span>备用 <span class="dot yellow"></span>检修 <span class="dot red"></span>故障 <span class="dot gray"></span>停止/未绑定</div><div id="msg">正在加载 GLB 模型...</div><script>\nconst MODEL_URL=\'__MODEL__\';let gl,prog,meshes=[],state={},auto=false;const c=document.getElementById(\'gl\'),msg=document.getElementById(\'msg\');let cam={yaw:.75,pitch:.8,dist:8,pan:[0,0]},B={min:[-1,-1,-1],max:[1,1,1],cen:[0,0,0],r:1};let drag=false,last=[0,0],btn=0;\nfunction show(x){msg.style.display=\'block\';msg.innerHTML=x}function hide(){msg.style.display=\'none\'}function N(s){return String(s||\'\').toUpperCase().replace(/[^A-Z0-9_]/g,\'\')}function num(v,d=2){v=Number(v||0);return isFinite(v)?v.toFixed(d):\'0.00\'}function col(st){return {running:[.06,.82,.38],standby:[.18,.66,1],fault:[1,.2,.2],maintenance:[.96,.76,.26],stopped:[.48,.53,.58],disabled:[.22,.25,.29],normal:[.06,.82,.38]}[st]||[.52,.62,.72]}\nfunction M(){return [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}function MM(a,b){let o=Array(16);for(let r=0;r<4;r++)for(let c=0;c<4;c++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o}function T(v){let m=M();m[12]=v[0];m[13]=v[1];m[14]=v[2];return m}function S(v){let m=M();m[0]=v[0];m[5]=v[1];m[10]=v[2];return m}function Q(q){let x=q[0],y=q[1],z=q[2],w=q[3],x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2;return [1-(yy+zz),xy+wz,xz-wy,0,xy-wz,1-(xx+zz),yz+wx,0,xz+wy,yz-wx,1-(xx+yy),0,0,0,0,1]}function NM(n){if(n.matrix)return n.matrix;let m=M();if(n.translation)m=MM(m,T(n.translation));if(n.rotation)m=MM(m,Q(n.rotation));if(n.scale)m=MM(m,S(n.scale));return m}function tp(m,p){let x=p[0],y=p[1],z=p[2];return [m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]]}\nfunction sub(a,b){return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}function add(a,b){return[a[0]+b[0],a[1]+b[1],a[2]+b[2]]}function cr(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}function dt(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}function nr(a){let l=Math.sqrt(dt(a,a))||1;return[a[0]/l,a[1]/l,a[2]/l]}function P(f,asp,n,fa){let q=1/Math.tan(f/2),nf=1/(n-fa);return[q/asp,0,0,0,0,q,0,0,0,0,(fa+n)*nf,-1,0,0,2*fa*n*nf,0]}function LA(e,ce,u){let z=nr(sub(e,ce)),x=nr(cr(u,z)),y=cr(z,x);return[x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dt(x,e),-dt(y,e),-dt(z,e),1]}\nfunction sh(t,s){let h=gl.createShader(t);gl.shaderSource(h,s);gl.compileShader(h);if(!gl.getShaderParameter(h,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(h));return h}function init(){gl=c.getContext(\'webgl\',{antialias:true})||c.getContext(\'experimental-webgl\');if(!gl)throw Error(\'当前浏览器/WebView不支持WebGL\');gl.getExtension(\'OES_element_index_uint\');let vs=\'attribute vec3 p,n;uniform mat4 mvp,mo;varying vec3 vn;void main(){vn=mat3(mo)*n;gl_Position=mvp*vec4(p,1.0);}\';let fs=\'precision mediump float;uniform vec3 color;uniform float pulse;varying vec3 vn;void main(){float d=max(dot(normalize(vn),normalize(vec3(.4,.8,.5))),0.0);gl_FragColor=vec4(color*(.35+.65*d)+color*pulse*.35,1.0);}\';prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,vs));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(prog));gl.useProgram(prog);gl.enable(gl.DEPTH_TEST)}\nfunction cs(t){return{SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[t]||1}function cb(t){return{5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[t]||4}function rc(d,o,t){if(t==5120)return d.getInt8(o);if(t==5121)return d.getUint8(o);if(t==5122)return d.getInt16(o,true);if(t==5123)return d.getUint16(o,true);if(t==5125)return d.getUint32(o,true);if(t==5126)return d.getFloat32(o,true);return 0}async function load(){let ab=await(await fetch(MODEL_URL)).arrayBuffer(),dv=new DataView(ab);if(dv.getUint32(0,true)!=0x46546c67)throw Error(\'当前离线查看器优先支持 .glb；如为 .gltf，请导出为未压缩 .glb 后再导入。\');let off=12,j=null,bin=null;while(off<ab.byteLength){let l=dv.getUint32(off,true),ty=dv.getUint32(off+4,true);off+=8;let ch=ab.slice(off,off+l);off+=l;if(ty==0x4e4f534a)j=JSON.parse(new TextDecoder().decode(ch));else if(ty==0x004e4942)bin=ch}return{j,b:[bin]}}\nfunction acc(g,i){let a=g.j.accessors[i],v=g.j.bufferViews[a.bufferView],buf=g.b[v.buffer||0],d=new DataView(buf),n=cs(a.type),b=cb(a.componentType),st=v.byteStride||n*b,off=(v.byteOffset||0)+(a.byteOffset||0),o=[];for(let x=0;x<a.count;x++){let r=[];for(let k=0;k<n;k++)r.push(rc(d,off+x*st+k*b,a.componentType));o.push(r)}return o}function fl(a){let o=[];for(const r of a)o.push(...r);return new Float32Array(o)}function ia(a){let o=[];for(const r of a)o.push(r[0]);return new Uint32Array(o)}function normals(p,ind){let n=Array(p.length).fill(0).map(()=>[0,0,0]),ids=ind?Array.from(ind):p.map((_,i)=>i);for(let i=0;i<ids.length;i+=3){let a=ids[i],b=ids[i+1],c=ids[i+2];if(a==null||b==null||c==null)continue;let nn=nr(cr(sub(p[b],p[a]),sub(p[c],p[a])));for(const x of[a,b,c])n[x]=add(n[x],nn)}return n.map(nr)}function matColor(g,i){try{let f=g.j.materials[i].pbrMetallicRoughness.baseColorFactor;return[f[0],f[1],f[2]]}catch(e){return[.45,.62,.82]}}\nfunction build(g){let scenes=g.j.scenes,sceneIndex=g.j.scene||0,sc=(scenes&&scenes[sceneIndex])?scenes[sceneIndex]:(scenes&&scenes[0]),nodes=(sc&&sc.nodes)?sc.nodes:[];let mi=[1e9,1e9,1e9],ma=[-1e9,-1e9,-1e9];function upd(p){for(let i=0;i<3;i++){mi[i]=Math.min(mi[i],p[i]);ma[i]=Math.max(ma[i],p[i])}}function rec(ni,pm){let nd=g.j.nodes[ni],wm=MM(pm,NM(nd));if(nd.mesh!=null){let me=g.j.meshes[nd.mesh];for(const pr of me.primitives||[]){if(pr.mode!=null&&pr.mode!==4)continue;if(pr.extensions&&pr.extensions.KHR_draco_mesh_compression)throw Error(\'模型使用Draco压缩，请重新导出未压缩GLB\');if(!pr.attributes||pr.attributes.POSITION==null)continue;let p=acc(g,pr.attributes.POSITION),ind=pr.indices!=null?ia(acc(g,pr.indices)):null,n=pr.attributes.NORMAL!=null?acc(g,pr.attributes.NORMAL):normals(p,ind);p.map(x=>tp(wm,x)).forEach(upd);let it={name:nd.name||me.name||\'\',meshName:me.name||\'\',model:wm,color:matColor(g,pr.material),count:ind?ind.length:p.length,indexed:!!ind};it.v=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.bufferData(gl.ARRAY_BUFFER,fl(p),gl.STATIC_DRAW);it.n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.bufferData(gl.ARRAY_BUFFER,fl(n),gl.STATIC_DRAW);if(ind){it.i=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,ind,gl.STATIC_DRAW)}meshes.push(it)}}for(const x of nd.children||[])rec(x,wm)}for(const n of nodes)rec(n,M());if(!meshes.length)throw Error(\'模型内没有普通网格或为空模型\');B.min=mi;B.max=ma;B.cen=[(mi[0]+ma[0])/2,(mi[1]+ma[1])/2,(mi[2]+ma[2])/2];B.r=Math.max(...sub(ma,mi).map(Math.abs))/2||1;resetCamera()}\nfunction match(name){let k=N(name);for(const[c,v]of Object.entries(state.pumps||{}))if(k==N(c)||k.includes(N(c)))return v.status;for(const[c,v]of Object.entries(state.pipes||{}))if(k==N(c)||k.includes(N(c)))return v.status;for(const[c,v]of Object.entries(state.meters||{}))if(k==N(c)||k.includes(N(c)))return v.status;return null}\nfunction resize(){let r=window.devicePixelRatio||1,w=c.clientWidth*r,h=c.clientHeight*r;if(c.width!=w||c.height!=h){c.width=w;c.height=h}}function draw(){requestAnimationFrame(draw);resize();if(auto)cam.yaw+=.006;gl.viewport(0,0,c.width,c.height);gl.clearColor(.02,.04,.08,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);let r=cam.dist,cp=Math.cos(cam.pitch),eye=[B.cen[0]+r*cp*Math.sin(cam.yaw)+cam.pan[0],B.cen[1]+r*Math.sin(cam.pitch)+cam.pan[1],B.cen[2]+r*cp*Math.cos(cam.yaw)],view=LA(eye,[B.cen[0]+cam.pan[0],B.cen[1]+cam.pan[1],B.cen[2]],[0,1,0]),proj=P(Math.PI/4,c.width/c.height,Math.max(.01,B.r/1000),B.r*100+100);let ap=gl.getAttribLocation(prog,\'p\'),an=gl.getAttribLocation(prog,\'n\'),um=gl.getUniformLocation(prog,\'mvp\'),umo=gl.getUniformLocation(prog,\'mo\'),uc=gl.getUniformLocation(prog,\'color\'),up=gl.getUniformLocation(prog,\'pulse\'),t=Date.now()/400;for(const it of meshes){let st=match(it.name)||match(it.meshName),co=st?col(st):it.color,mvp=MM(proj,MM(view,it.model));gl.uniformMatrix4fv(um,false,new Float32Array(mvp));gl.uniformMatrix4fv(umo,false,new Float32Array(it.model));gl.uniform3fv(uc,new Float32Array(co));gl.uniform1f(up,st===\'fault\'?(Math.sin(t)+1)/2:0);gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.enableVertexAttribArray(ap);gl.vertexAttribPointer(ap,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.enableVertexAttribArray(an);gl.vertexAttribPointer(an,3,gl.FLOAT,false,0,0);if(it.indexed){gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.drawElements(gl.TRIANGLES,it.count,gl.UNSIGNED_INT,0)}else gl.drawArrays(gl.TRIANGLES,0,it.count)}}\nasync function loadState(){try{state=await(await fetch(\'twin_state.json?ts=\'+Date.now(),{cache:\'no-store\'})).json();applyState()}catch(e){}}function applyState(){document.getElementById(\'stationLine\').textContent=`${state.station||\'\'} ${state.stationName||\'\'} | ${state.controlModeText||state.controlMode||\'\'} | ${state.controlState||\'\'} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||\'\'}`;let pumps=Object.values(state.pumps||{}).slice(0,12).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||\'\'}<br>状态：${p.statusText||p.status||\'-\'}\u3000频率：${num(p.freq,1)}Hz\u3000电流：${num(p.current,1)}A</div>`).join(\'\'),pipes=Object.values(state.pipes||{}).slice(0,6).map(p=>`<div class="item"><b>${p.code}</b> ${p.name||\'\'}<br>流量：${num(p.flow,1)} m³/h\u3000压力：${num(p.pressure,2)}MPa</div>`).join(\'\');document.getElementById(\'stateBox\').innerHTML=`<div class="item">控制状态：${state.controlState||\'-\'}<br>事件状态：${state.eventState||\'-\'}<br>当前动作：${state.currentAction||\'-\'}</div>${pumps}${pipes}`}\nfunction resetCamera(){cam.dist=Math.max(2,B.r*3.2);cam.yaw=.75;cam.pitch=.9;cam.pan=[0,0]}window.resetCamera=resetCamera;window.toggleRotate=()=>auto=!auto;c.oncontextmenu=e=>e.preventDefault();c.onmousedown=e=>{drag=true;last=[e.clientX,e.clientY];btn=e.button};window.onmouseup=()=>drag=false;window.onmousemove=e=>{if(!drag)return;let dx=e.clientX-last[0],dy=e.clientY-last[1];last=[e.clientX,e.clientY];if(btn==2||btn==1){let s=B.r/350;cam.pan[0]+=dx*s;cam.pan[1]-=dy*s}else{cam.yaw+=dx*.008;cam.pitch=Math.max(-1.45,Math.min(1.45,cam.pitch+dy*.006))}};c.onwheel=e=>{e.preventDefault();cam.dist*=e.deltaY>0?1.12:.89;cam.dist=Math.max(B.r*.25,cam.dist)};\n(async()=>{try{init();let g=await load();build(g);hide();await loadState();setInterval(loadState,1000);draw()}catch(e){console.error(e);show(\'<span class="err">三维模型加载失败：</span> \'+(e.message||e)+\'\\n\\n处理建议：\\n1. 请优先导入 .glb 文件；\\n2. 如果模型使用 Draco/压缩网格，请重新导出未压缩 GLB；\\n3. 用 Windows 系统3D查看器确认模型本身是否正常；\\n4. 本查看器不依赖外网，若仍失败，多半是模型格式问题。\')}})();\n</script></body></html>'


def _v5713_safe_name(value, default='STATION'):
    text = str(value or default)
    out = ''.join(ch if (ch.isalnum() or ch in ('_', '-')) else '_' for ch in text).strip('_')
    return out or default


def _v5713_now_stamp():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def _v5713_try_writable_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        test = os.path.join(path, '.write_test.tmp')
        with open(test, 'w', encoding='utf-8') as f:
            f.write('ok')
        try:
            os.remove(test)
        except Exception:
            pass
        return True
    except Exception:
        return False


def _v5713_runtime_root(self):
    primary = os.path.join(BASE_DIR, 'data')
    if _v5713_try_writable_dir(primary):
        return primary
    appdata = os.environ.get('LOCALAPPDATA') or os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
    fallback = os.path.join(appdata, 'TunnelPumpControl')
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _v5713_viewer_dir(self):
    d = os.path.join(self._twin_runtime_root(), 'twin_viewer')
    os.makedirs(d, exist_ok=True)
    return d


def _v5713_model_root(self):
    d = os.path.join(self._twin_runtime_root(), 'models')
    os.makedirs(d, exist_ok=True)
    return d


def _v5713_report_root(self):
    preferred = REPORT_DIR
    if _v5713_try_writable_dir(preferred):
        return preferred
    d = os.path.join(self._twin_runtime_root(), 'reports')
    os.makedirs(d, exist_ok=True)
    return d


def _v5713_log(self, title, err=None, extra=None):
    try:
        log_dir = os.path.join(self._twin_runtime_root(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        fp = os.path.join(log_dir, 'glb_viewer_error.log')
        with open(fp, 'a', encoding='utf-8') as f:
            f.write('\n' + '=' * 80 + '\n')
            f.write(now() + '  ' + str(title) + '\n')
            if extra:
                f.write(str(extra) + '\n')
            if err is not None:
                try:
                    import traceback
                    f.write('ERROR: ' + str(err) + '\n')
                    f.write(traceback.format_exc() + '\n')
                except Exception:
                    f.write('ERROR: ' + str(err) + '\n')
        return fp
    except Exception:
        return ''


def _v5713_station_safe_code(self, sid=None):
    sid = sid or self.twin_sid() or self.sid()
    st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
    return _v5713_safe_name(st['station_code'] if st else 'STATION')


def _v5713_resolve_model_path(self, path):
    path = (path or '').strip().strip('"')
    if not path:
        return ''
    # 数据库新格式：models/ST01/ST01.glb，相对运行目录。
    if not os.path.isabs(path):
        p1 = os.path.abspath(os.path.join(self._twin_runtime_root(), path.replace('/', os.sep)))
        if os.path.exists(p1):
            return p1
        p2 = os.path.abspath(os.path.join(BASE_DIR, path.replace('/', os.sep)))
        if os.path.exists(p2):
            return p2
        return p1
    return os.path.abspath(path)


def _v5713_rel_to_runtime(self, abs_path):
    try:
        root = os.path.abspath(self._twin_runtime_root())
        ap = os.path.abspath(abs_path)
        rel = os.path.relpath(ap, root)
        if not rel.startswith('..'):
            return rel.replace(os.sep, '/')
    except Exception:
        pass
    return abs_path


def _v5713_validate_model_file(self, path, allow_gltf=True):
    ap = self._resolve_twin_model_path(path)
    if not ap:
        raise FileNotFoundError('未选择模型文件。')
    if not os.path.exists(ap):
        raise FileNotFoundError('模型文件不存在：' + ap)
    if not os.path.isfile(ap):
        raise PermissionError('当前路径不是文件，可能 model.glb 实际是文件夹：' + ap)
    ext = os.path.splitext(ap)[1].lower()
    allowed = ('.glb', '.gltf') if allow_gltf else ('.glb',)
    if ext not in allowed:
        raise ValueError('模型文件格式不正确，请选择 .glb 或 .gltf 文件：' + ap)
    size = os.path.getsize(ap)
    if size <= 32:
        raise ValueError('模型文件大小异常，可能为空文件或损坏：' + ap)
    # 提前读一下，能把 PermissionError 明确暴露在导入阶段，而不是浏览器加载阶段。
    with open(ap, 'rb') as f:
        f.read(16)
    return ap


def _v5713_copy_model_to_safe_store(self, source_path, sid=None):
    source = self._validate_twin_model_file(source_path)
    sid = sid or self.twin_sid() or self.sid()
    safe_base = self._station_safe_code(sid)
    ext = os.path.splitext(source)[1].lower() or '.glb'
    station_dir = os.path.join(self._twin_model_root(), safe_base)
    os.makedirs(station_dir, exist_ok=True)
    target_name = safe_base + ext
    target = os.path.join(station_dir, target_name)

    if os.path.isdir(target):
        backup_dir = target + '_dir_backup_' + _v5713_now_stamp()
        os.rename(target, backup_dir)

    same_file = False
    try:
        same_file = os.path.abspath(source) == os.path.abspath(target) or os.path.samefile(source, target)
    except Exception:
        same_file = os.path.abspath(source) == os.path.abspath(target)

    if not same_file:
        need_copy = True
        if os.path.isfile(target):
            try:
                src_size = os.path.getsize(source)
                tgt_size = os.path.getsize(target)
                src_mtime = os.path.getmtime(source)
                tgt_mtime = os.path.getmtime(target)
                need_copy = (src_size != tgt_size) or (src_mtime > tgt_mtime)
            except Exception:
                need_copy = True
        if need_copy:
            if os.path.isfile(target):
                backup = os.path.join(station_dir, safe_base + '_' + _v5713_now_stamp() + '_backup' + ext)
                try:
                    shutil.copy2(target, backup)
                except Exception:
                    pass
            shutil.copy2(source, target)

        # gltf 依赖 bin / 贴图，复制同目录常见资源。
        if ext == '.gltf':
            src_dir = os.path.dirname(os.path.abspath(source))
            for fn in os.listdir(src_dir):
                low = fn.lower()
                if low.endswith(('.bin', '.png', '.jpg', '.jpeg', '.webp', '.ktx2', '.gif')):
                    sp = os.path.join(src_dir, fn)
                    dp = os.path.join(station_dir, fn)
                    if os.path.isfile(sp) and os.path.abspath(sp) != os.path.abspath(dp):
                        try:
                            shutil.copy2(sp, dp)
                        except Exception as e:
                            self._log_twin_error('复制 glTF 依赖资源失败', e, sp)

    rel = self._rel_to_twin_runtime(target)
    cfg = {
        'station_id': sid,
        'station_code': safe_base,
        'model_file': target_name,
        'model_relative_path': rel,
        'original_path': source,
        'saved_path': target,
        'import_time': now(),
        'version': _V5713_VERSION,
    }
    try:
        cfg_path = os.path.join(station_dir, 'model_config.json')
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        self._log_twin_error('写入模型配置失败', e, cfg)
    return target, rel, cfg


def _v5713_twin_viewer_url(self):
    return f'http://127.0.0.1:{self.twin_http_port}/twin_viewer/twin_viewer.html'


def _v5713_write_twin_state_json(self, sid=None):
    sid = sid or self.twin_sid() or self.sid()
    viewer_dir = self._twin_viewer_dir()
    st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
    try:
        ctrl = self.row('SELECT * FROM station_control_state WHERE station_id=?', (sid,)) if sid else None
    except Exception:
        ctrl = None
    state = {
        'stationId': sid,
        'station': st['station_code'] if st else '',
        'stationName': st['station_name'] if st else '',
        'controlMode': st['control_mode'] if st else '',
        'controlModeText': MODE_LABEL.get(st['control_mode'], st['control_mode']) if st else '',
        'controlState': ctrl['control_state'] if ctrl else '',
        'eventState': ctrl['event_state'] if ctrl else '',
        'currentAction': ctrl['current_action'] if ctrl else '',
        'nextAction': ctrl['next_action'] if ctrl else '',
        'reasonText': ctrl['reason_text'] if ctrl else '',
        'level': float(st['current_level'] or 0) if st else 0,
        'levelRate': float(st['level_rise_rate'] or 0) if st else 0,
        'pumps': {}, 'pipes': {}, 'meters': {}, 'alarms': [],
        'updatedAt': now(),
        'version': _V5713_VERSION,
    }
    try:
        for p in self.rows('SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id', (sid,)):
            code = str(p['pump_code'] or '')
            try:
                if int(p['disabled'] or 0):
                    status, label = 'disabled', '禁用'
                elif int(p['manual_fault'] or 0) or int(p['fault_feedback'] or 0):
                    status, label = 'fault', '故障'
                elif int(p['maintenance'] or 0):
                    status, label = 'maintenance', '检修'
                elif int(p['run_feedback'] or 0):
                    status, label = 'running', '运行'
                elif int(p['enabled'] or 1) and int(p['auto_enable'] or 1):
                    status, label = 'standby', '备用'
                else:
                    status, label = 'stopped', '停止'
            except Exception:
                status, label = 'unknown', '未知'
            state['pumps'][code] = {
                'code': code, 'name': p['pump_name'], 'type': PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type']),
                'status': status, 'statusText': label,
                'freq': float(p['frequency'] or 0), 'setFreq': float(p['set_frequency'] or 0),
                'current': float(p['current'] or 0), 'voltage': float(p['voltage'] or 0),
                'power': round(float(p['current'] or 0) * float(p['voltage'] or 0) * 1.732 * 0.85 / 1000, 2),
                'runtimeToday': int(p['run_seconds_today'] or 0), 'runtimeTotal': int(p['run_seconds_total'] or 0),
            }
        for pipe in self.rows('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)):
            code = str(pipe['pipe_code'] or '')
            flow = float(pipe['measured_flow'] or pipe['estimated_running_flow'] or 0)
            pressure = float(pipe['pressure'] or 0)
            status = 'running' if flow > 0.01 else 'stopped'
            val = {'code': code, 'name': pipe['pipe_name'], 'status': status,
                   'statusText': '有流量' if status == 'running' else '无流量', 'flow': flow, 'pressure': pressure,
                   'velocity': float(pipe['estimated_velocity'] or 0), 'dn': pipe['standard_dn']}
            state['pipes'][code] = val
            c = code.upper()
            if not c.startswith('PIPE_'):
                suffix = c.replace('母管', '').replace('PIPE', '').strip('_- ')
                if suffix:
                    state['pipes']['PIPE_' + suffix] = val
        for ins in self.rows('SELECT * FROM instrument WHERE station_id=? ORDER BY instrument_type,id', (sid,)):
            code = str(ins['instrument_code'] or '')
            state['meters'][code] = {
                'code': code, 'name': ins['instrument_name'], 'type': ins['instrument_type'],
                'status': 'bypassed' if int(ins['bypassed'] or 0) else str(ins['data_quality'] or 'normal'),
                'statusText': '屏蔽' if int(ins['bypassed'] or 0) else str(ins['data_quality'] or '正常'),
                'value': float(ins['current_value'] or 0),
                'unit': {'level': 'm', 'flow': 'm3/h', 'pressure': 'MPa', 'current': 'A', 'voltage': 'V',
                         'energy': 'kWh'}.get(str(ins['instrument_type'] or ''), '')
            }
        try:
            for ev in self.rows('SELECT * FROM station_control_event WHERE station_id=? ORDER BY id DESC LIMIT 5',
                                (sid,)):
                state['alarms'].append({'time': ev['event_time'], 'level': ev['event_level'], 'type': ev['event_type'],
                                        'device': ev['target_device'], 'message': ev['trigger_reason']})
        except Exception:
            pass
    except Exception as e:
        state['error'] = str(e)
        self._log_twin_error('生成 twin_state.json 失败', e)
    out = os.path.join(viewer_dir, 'twin_state.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return out


def _v5713_prepare_twin_web_model(self, path):
    try:
        source = self._resolve_twin_model_path(path)
        target, rel, cfg = self._copy_twin_model_to_safe_store(source)
        sid = cfg.get('station_id') or self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        viewer_dir = self._twin_viewer_dir()
        model_url = '/' + rel.replace('\\', '/')
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = _V5713_OFFLINE_HTML_TEMPLATE.replace('__MODEL__', model_url)
        # 给现场人员明确显示模型位置，便于排查。
        html_text = html_text.replace('正在加载 GLB 模型...', '正在加载 GLB 模型...\\n模型路径：' + model_url)
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        log = self._log_twin_error('GLB查看器准备失败', e, path)
        messagebox.showwarning('GLB查看器准备失败',
                               '三维模型加载前检查失败。\n\n'
                               '可能原因：\n'
                               '1. 模型文件被其他软件占用；\n'
                               '2. 当前路径不是文件，model.glb 可能是文件夹；\n'
                               '3. 模型路径仍指向旧版本目录；\n'
                               '4. 当前用户无权读取模型文件。\n\n'
                               '详细日志：\n' + (log or '未能写入日志') + '\n\n'
                                                                         '原始错误：\n' + str(e))
        return None


def _v5713_start_twin_http_server(self):
    root = self._twin_runtime_root()
    os.makedirs(root, exist_ok=True)
    if getattr(self, 'twin_httpd', None):
        return True
    last_err = None
    for port in [getattr(self, 'twin_http_port', 8765)] + list(range(8766, 8795)):
        try:
            handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=root, **kwargs)
            self.twin_httpd = _TwinReusableTCPServer(('127.0.0.1', int(port)), handler)
            self.twin_http_port = int(port)
            threading.Thread(target=self.twin_httpd.serve_forever, daemon=True).start()
            return True
        except OSError as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            break
    log = self._log_twin_error('GLB查看器HTTP服务启动失败', last_err, root)
    messagebox.showwarning('GLB查看器启动失败', '本地HTTP服务启动失败：' + str(last_err) + '\n日志：' + (log or ''))
    return False


def _v5713_load_twin_model_config(self):
    if not hasattr(self, 'twin_model_path'):
        return
    sid = self.twin_sid()
    row = self.row('SELECT * FROM twin_model WHERE station_id=?', (sid,)) if sid else None
    if row and row['model_path']:
        self.twin_model_path.set(self._resolve_twin_model_path(row['model_path']))
    else:
        self.twin_model_path.set('')


def _v5713_browse_twin_model(self):
    path = filedialog.askopenfilename(title='选择三维模型文件',
                                      filetypes=[('3D 模型', '*.glb *.gltf'), ('所有文件', '*.*')])
    if path:
        self.twin_model_path.set(path)
        self.save_twin_model()


def _v5713_save_twin_model(self):
    sid = self.twin_sid()
    path = (self.twin_model_path.get() or '').strip()
    if not sid:
        messagebox.showwarning('提示', '请先选择泵站')
        return
    if not path:
        messagebox.showwarning('提示', '请先导入 GLB/gltf 模型文件。')
        return
    try:
        target, rel, cfg = self._copy_twin_model_to_safe_store(path, sid=sid)
        name = os.path.basename(target)
        remark = json.dumps(
            {'original_path': cfg.get('original_path'), 'saved_path': target, 'model_relative_path': rel,
             'version': _V5713_VERSION}, ensure_ascii=False)
        old = self.row('SELECT id FROM twin_model WHERE station_id=?', (sid,))
        if old:
            self.db.execute(
                'UPDATE twin_model SET model_name=?,model_path=?,model_type=?,updated_at=?,remark=? WHERE station_id=?',
                (name, rel, os.path.splitext(name)[1].lstrip('.') or 'glb', now(), remark, sid))
        else:
            self.db.execute(
                'INSERT INTO twin_model(station_id,model_name,model_path,model_type,created_at,updated_at,remark) VALUES(?,?,?,?,?,?,?)',
                (sid, name, rel, os.path.splitext(name)[1].lstrip('.') or 'glb', now(), now(), remark))
        self.twin_model_path.set(target)
        html = self._prepare_twin_web_model(target)
        try:
            binding = self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
            self._show_binding_result(binding)
        except Exception as e:
            self._log_twin_error('模型对象扫描失败', e, target)
        try:
            self.load_twin_in_page(force=True)
        except Exception:
            self.draw_twin_scene()
        messagebox.showinfo('保存成功', '模型已保存到安全目录，旧版本路径不再作为运行依赖。\n\n保存位置：\n' + target)
        return html
    except Exception as e:
        log = self._log_twin_error('保存GLB模型失败', e, path)
        messagebox.showwarning('保存失败',
                               '模型保存失败。\n\n可能原因：文件被占用、无读取权限、model.glb 实际是文件夹或模型文件损坏。\n\n日志：\n' + (
                                       log or '') + '\n\n错误：\n' + str(e))
        return None


def _v5713_open_twin_model_viewer(self):
    path = (self.twin_model_path.get() or '').strip()
    if not path:
        messagebox.showwarning('提示', '请先导入并保存 glb/gltf 模型文件。')
        return
    html = self._prepare_twin_web_model(path)
    try:
        target = self._resolve_twin_model_path(path)
        self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
    except Exception as e:
        self._log_twin_error('打开查看器前扫描模型失败', e, path)
    if html and self._start_twin_http_server():
        webbrowser.open(self._twin_viewer_url() + f'?ts={int(time.time())}')


def _v5713_scan_twin_model_objects(self):
    path = (self.twin_model_path.get() or '').strip()
    try:
        ap = self._validate_twin_model_file(path)
        binding = self._write_binding_files(self._generate_twin_binding_dict(ap), show_message=False)
        self._show_binding_result(binding)
        messagebox.showinfo('扫描完成',
                            '已扫描模型对象，并生成绑定表。\n绑定数：%s\n标注锚点：%s' % (binding['summary']['bindings'],
                                                                                      binding['summary']['anchors']))
    except Exception as e:
        log = self._log_twin_error('扫描模型对象失败', e, path)
        messagebox.showwarning('扫描失败', str(e) + ('\n\n日志：' + log if log else ''))


def _v5713_generate_twin_binding(self):
    try:
        path = self._validate_twin_model_file((self.twin_model_path.get() or '').strip())
        binding = self._write_binding_files(self._generate_twin_binding_dict(path), show_message=True)
        self._show_binding_result(binding)
    except Exception as e:
        log = self._log_twin_error('生成模型绑定表失败', e)
        messagebox.showwarning('生成失败', str(e) + ('\n\n日志：' + log if log else ''))


def _v5713_twin_binding_paths(self):
    viewer_dir = self._twin_viewer_dir()
    sid = self.twin_sid() or self.sid()
    st = self.row('SELECT station_code FROM pump_station WHERE id=?', (sid,)) if sid else None
    code = _v5713_safe_name(st['station_code'] if st else 'STATION')
    common_path = os.path.join(viewer_dir, 'twin_binding.json')
    station_path = os.path.join(viewer_dir, f'twin_binding_{code}.json')
    report_dir = self._twin_report_root()
    csv_path = os.path.join(report_dir, f'twin_binding_{code}.csv')
    return common_path, station_path, csv_path


def _v5713_write_binding_files(self, binding=None, show_message=True):
    if binding is None:
        path = self._validate_twin_model_file((self.twin_model_path.get() or '').strip())
        binding = self._generate_twin_binding_dict(path)
    common_path, station_path, csv_path = self._twin_binding_paths()
    os.makedirs(os.path.dirname(common_path), exist_ok=True)
    for fp in (common_path, station_path):
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(binding, f, ensure_ascii=False, indent=2)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['modelObject', 'objectCode', 'type', 'globalId', 'dataPath', 'anchor', 'anchorMode', 'enabled',
                    'matchedInSystem'])
        for obj, b in binding.get('bindings', {}).items():
            w.writerow(
                [obj, b.get('objectCode'), b.get('typeText'), b.get('globalId'), b.get('dataPath'), b.get('anchor'),
                 b.get('anchorAuto'), b.get('enabled'), b.get('matchedInSystem')])
    if show_message:
        messagebox.showinfo('生成成功', '已生成模型绑定表：\n%s\n\nCSV：\n%s' % (station_path, csv_path))
    return binding


def _v5713_model_status_check(self):
    print("_v5713_model_status_check")
    path = (self.twin_model_path.get() or '').strip()
    lines = []
    ok = False
    try:
        ap = self._validate_twin_model_file(path)
        ok = True
        size_mb = os.path.getsize(ap) / 1024 / 1024
        runtime = self._twin_runtime_root()
        old_hint = ''
        low = ap.lower().replace('/', '\\')
        if 'tunnelpumpcontrol_python_v5_7_11' in low or 'tunnelpumpcontrol_python_v5_7_12' in low:
            old_hint = '警告：当前显示路径仍包含旧版本目录，建议点击“保存绑定”重新复制到安全目录。'
        objects = []
        missing = []
        expected = ['P1', 'P2', 'P3', 'P4', 'PIPE_A', 'LT01', 'FT01', 'PT01', 'CAM01', 'ANNO_P1', 'ANNO_P2', 'ANNO_P3',
                    'ANNO_P4', 'ANNO_PIPE_A', 'ANNO_LT01', 'ANNO_FT01', 'ANNO_PT01', 'ANNO_CAM01']
        try:
            data = _v5711_read_gltf_json(ap)
            for n in data.get('nodes', []) or []:
                if n.get('name'):
                    objects.append(str(n.get('name')))
            normed = {_v5711_norm_name(x) for x in objects}
            missing = [x for x in expected if _v5711_norm_name(x) not in normed]
        except Exception as e:
            self._log_twin_error('模型对象状态检查失败', e, ap)
        lines.append('模型状态检查')
        lines.append('版本：' + _V5713_VERSION)
        lines.append('当前泵站：' + self._station_safe_code())
        lines.append('模型文件：正常')
        lines.append('模型大小：%.2f MB' % size_mb)
        lines.append('当前路径：' + ap)
        lines.append('运行目录：' + runtime)
        if old_hint:
            lines.append(old_hint)
        lines.append('')
        lines.append('已识别对象数量：%s' % len(objects))
        if objects:
            lines.append('已识别对象：' + '、'.join(objects[:60]))
        if missing:
            lines.append('')
            lines.append('建议补充/确认命名：' + '、'.join(missing))
        else:
            lines.append('')
            lines.append('常用对象命名检查：完整')
    except Exception as e:
        log = self._log_twin_error('模型状态检查失败', e, path)
        lines.append('模型状态检查')
        lines.append('模型文件：异常')
        lines.append('当前路径：' + (path or '-'))
        lines.append('错误：' + str(e))
        if log:
            lines.append('日志：' + log)
    if hasattr(self, 'twin_info'):
        self.twin_info.delete('1.0', 'end')
        self.twin_info.insert('end', '\n'.join(lines))
    messagebox.showinfo('模型状态检查',
                        ('检查完成：模型文件正常。' if ok else '检查完成：模型文件异常。') + '\n\n详情已显示在右侧信息框。')


def _v5713_open_twin_model_dir(self):
    path = (self.twin_model_path.get() or '').strip()
    try:
        ap = self._resolve_twin_model_path(path)
        d = os.path.dirname(ap) if ap else self._twin_model_root()
        os.makedirs(d, exist_ok=True)
        if os.name == 'nt':
            os.startfile(d)
        else:
            webbrowser.open('file://' + os.path.abspath(d))
    except Exception as e:
        messagebox.showwarning('打开目录失败', str(e))


def _v5713_clear_twin_model(self):
    sid = self.twin_sid() or self.sid()
    if not sid:
        return
    if not messagebox.askyesno('确认', '是否清除当前泵站的模型绑定？\n不会删除已经保存的 GLB 文件。'):
        return
    old = self.row('SELECT id FROM twin_model WHERE station_id=?', (sid,))
    if old:
        self.db.execute('UPDATE twin_model SET model_path=?,model_name=?,updated_at=?,remark=? WHERE station_id=?',
                        ('', '', now(), 'cleared by V5.7.14_TwinBindFix', sid))
    if hasattr(self, 'twin_model_path'):
        self.twin_model_path.set('')
    self.draw_twin_scene()
    messagebox.showinfo('已清除', '当前泵站模型绑定已清除。')


# 应用 V5.7.13 覆盖。放在文件最后，确保覆盖 V5.7.10/5.7.11/5.7.12 的旧函数。
App._twin_runtime_root = _v5713_runtime_root
App._twin_viewer_dir = _v5713_viewer_dir
App._twin_model_root = _v5713_model_root
App._twin_report_root = _v5713_report_root
App._log_twin_error = _v5713_log
App._station_safe_code = _v5713_station_safe_code
App._resolve_twin_model_path = _v5713_resolve_model_path
App._rel_to_twin_runtime = _v5713_rel_to_runtime
App._validate_twin_model_file = _v5713_validate_model_file
App._copy_twin_model_to_safe_store = _v5713_copy_model_to_safe_store
App._twin_viewer_url = _v5713_twin_viewer_url
App._write_twin_state_json = _v5713_write_twin_state_json
App._prepare_twin_web_model = _v5713_prepare_twin_web_model
App._start_twin_http_server = _v5713_start_twin_http_server
App.load_twin_model_config = _v5713_load_twin_model_config
App.browse_twin_model = _v5713_browse_twin_model
App.save_twin_model = _v5713_save_twin_model
App.open_twin_model_viewer = _v5713_open_twin_model_viewer
App.scan_twin_model_objects = _v5713_scan_twin_model_objects
App.generate_twin_binding = _v5713_generate_twin_binding
App._twin_binding_paths = _v5713_twin_binding_paths
App._write_binding_files = _v5713_write_binding_files
App.model_status_check = _v5713_model_status_check
App.open_twin_model_dir = _v5713_open_twin_model_dir
App.clear_twin_model = _v5713_clear_twin_model

# ===================== V5.7.14: GLB 绑定显示修正 =====================
# 解决：模型能扫描到 P1/P2/PIPE_A/LT01 等对象，但动态查看器显示不联动的问题。
# 原因：GLB 中 P1/P2/PIPE_A 是父级空节点，实际网格在子节点，旧离线查看器只按叶子网格名匹配，导致状态颜色和标签不能绑定。
_V5714_VERSION = 'V5.7.14_TwinBindFix'

_V5714_OFFLINE_HTML_TEMPLATE = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>离线GLB三维孪生</title><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#050b16;color:#d7ecff;font-family:"Microsoft YaHei",Arial}canvas{position:fixed;inset:0;width:100%;height:100%;display:block;background:radial-gradient(circle,#12365a 0%,#07101f 55%,#020814 100%)}#hud{position:absolute;left:12px;right:12px;top:10px;height:48px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,22,38,.72);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:0 12px;z-index:5}.title{font-weight:bold;color:#fff;font-size:16px}.sub{font-size:12px;color:#8fd3ff}button{background:#0f6fb2;color:#fff;border:1px solid #69c9ff;border-radius:6px;padding:6px 12px;margin-left:6px;cursor:pointer}#panel{position:absolute;right:12px;top:76px;width:340px;max-height:calc(100vh - 96px);overflow:auto;background:rgba(7,18,32,.84);border:1px solid rgba(68,188,255,.35);border-radius:10px;padding:12px;z-index:5}#panel h3{margin:0 0 8px;color:#fff}.item{border-bottom:1px solid rgba(143,211,255,.16);padding:6px 0;font-size:12px;line-height:1.55;cursor:pointer}.item:hover{background:rgba(47,168,255,.12)}#detail{margin-top:8px;border:1px solid rgba(143,211,255,.25);background:rgba(12,32,55,.72);border-radius:8px;padding:9px;font-size:12px;line-height:1.7;color:#d7ecff;white-space:pre-line}#legend{position:absolute;left:12px;bottom:12px;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:8px 12px;font-size:12px;z-index:5}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px}.green{background:#18d06b}.blue{background:#2fa8ff}.yellow{background:#f6c343}.red{background:#ff4d4f}.gray{background:#7b8794}.purple{background:#a855f7}#msg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:820px;color:#8fd3ff;font-size:14px;line-height:1.8;z-index:7;background:rgba(8,22,38,.92);padding:18px 24px;border:1px solid rgba(68,188,255,.45);border-radius:10px;white-space:pre-line}.err{color:#ff7875}.warn{color:#f6c343}.ok{color:#18d06b}#labels{position:absolute;inset:0;pointer-events:none;z-index:6}.lbl{position:absolute;transform:translate(-50%,-100%);pointer-events:auto;background:rgba(5,15,28,.88);border:1px solid rgba(143,211,255,.65);color:#d7ecff;border-radius:7px;padding:4px 7px;font-size:12px;line-height:1.35;white-space:nowrap;box-shadow:0 0 12px rgba(47,168,255,.25);cursor:pointer}.lbl.running{border-color:#18d06b;color:#b8ffd2}.lbl.standby{border-color:#2fa8ff}.lbl.fault{border-color:#ff4d4f;color:#ffd2d2}.lbl.maintenance{border-color:#f6c343;color:#ffe7a3}.lbl.bypassed{border-color:#a855f7}.lbl.sel{box-shadow:0 0 18px rgba(255,255,255,.7);border-width:2px}.lbl small{opacity:.85;color:#8fd3ff}.cross{position:absolute;width:12px;height:12px;border-radius:50%;background:#8fd3ff;box-shadow:0 0 12px #8fd3ff;transform:translate(-50%,-50%);pointer-events:none}
</style></head><body><canvas id="gl"></canvas><div id="labels"></div><div id="hud"><div><div class="title">隧道泵站自动控制系统 V5.7.14 · 模型绑定显示修正版</div><div class="sub" id="stationLine">加载中...</div></div><div><button onclick="resetCamera()">复位视角</button><button onclick="toggleRotate()">自动旋转</button><button onclick="toggleLabels()">显示/隐藏标签</button><button onclick="location.reload()">重新加载</button></div></div><div id="panel"><h3>实时状态 / 点击对象查看</h3><div id="stateBox">等待数据...</div><div id="detail">提示：模型节点 P1/P2/P3/P4、PIPE_A、LT01、FT01、PT01、CAM01 已按父级对象绑定；点击蓝色标签可查看详细参数。</div></div><div id="legend"><span class="dot green"></span>运行 <span class="dot blue"></span>备用 <span class="dot yellow"></span>检修 <span class="dot red"></span>故障 <span class="dot purple"></span>屏蔽 <span class="dot gray"></span>停止/未绑定</div><div id="msg">正在加载 GLB 模型...</div><script>
const MODEL_URL='__MODEL__';let gl,prog,meshes=[],state={},auto=false,showLabels=true,selected='';const c=document.getElementById('gl'),msg=document.getElementById('msg'),labelsDiv=document.getElementById('labels');let cam={yaw:.75,pitch:.8,dist:8,pan:[0,0]},B={min:[-1,-1,-1],max:[1,1,1],cen:[0,0,0],r:1};let drag=false,last=[0,0],btn=0;let anchors={},bindBoxes={};
function show(x){msg.style.display='block';msg.innerHTML=x}function hide(){msg.style.display='none'}function N(s){return String(s||'').toUpperCase().replace(/[^A-Z0-9_]/g,'')}function num(v,d=2){v=Number(v||0);return isFinite(v)?v.toFixed(d):'0.00'}function col(st){return {running:[.06,.82,.38],standby:[.18,.66,1],fault:[1,.2,.2],maintenance:[.96,.76,.26],stopped:[.48,.53,.58],disabled:[.22,.25,.29],normal:[.06,.82,.38],good:[.06,.82,.38],bypassed:[.66,.33,.97],unknown:[.52,.62,.72]}[st]||[.52,.62,.72]}
function deviceCode(s){let n=N(s);if(!n||n.startsWith('ANNO_'))return '';if(/^P\d+$/.test(n)||/^PIPE_[A-Z0-9]+$/.test(n)||/^LT\d+$/.test(n)||/^FT\d+$/.test(n)||/^PT\d+$/.test(n)||/^CAM\d+$/.test(n)||/^TANK\d+$/.test(n)||/^JP\d+$/.test(n)||/^CAB\d+$/.test(n))return n;return ''}
function M(){return [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}function MM(a,b){let o=Array(16);for(let r=0;r<4;r++)for(let cc=0;cc<4;cc++)o[cc*4+r]=a[r]*b[cc*4]+a[4+r]*b[cc*4+1]+a[8+r]*b[cc*4+2]+a[12+r]*b[cc*4+3];return o}function T(v){let m=M();m[12]=v[0];m[13]=v[1];m[14]=v[2];return m}function S(v){let m=M();m[0]=v[0];m[5]=v[1];m[10]=v[2];return m}function Q(q){let x=q[0],y=q[1],z=q[2],w=q[3],x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2;return [1-(yy+zz),xy+wz,xz-wy,0,xy-wz,1-(xx+zz),yz+wx,0,xz+wy,yz-wx,1-(xx+yy),0,0,0,0,1]}function NM(n){if(n.matrix)return n.matrix;let m=M();if(n.translation)m=MM(m,T(n.translation));if(n.rotation)m=MM(m,Q(n.rotation));if(n.scale)m=MM(m,S(n.scale));return m}function tp(m,p){let x=p[0],y=p[1],z=p[2];return [m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]]}
function sub(a,b){return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}function add(a,b){return[a[0]+b[0],a[1]+b[1],a[2]+b[2]]}function cr(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}function dt(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}function nr(a){let l=Math.sqrt(dt(a,a))||1;return[a[0]/l,a[1]/l,a[2]/l]}function P(f,asp,n,fa){let q=1/Math.tan(f/2),nf=1/(n-fa);return[q/asp,0,0,0,0,q,0,0,0,0,(fa+n)*nf,-1,0,0,2*fa*n*nf,0]}function LA(e,ce,u){let z=nr(sub(e,ce)),x=nr(cr(u,z)),y=cr(z,x);return[x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dt(x,e),-dt(y,e),-dt(z,e),1]}function mv(m,p){let x=p[0],y=p[1],z=p[2],w=1;return [m[0]*x+m[4]*y+m[8]*z+m[12]*w,m[1]*x+m[5]*y+m[9]*z+m[13]*w,m[2]*x+m[6]*y+m[10]*z+m[14]*w,m[3]*x+m[7]*y+m[11]*z+m[15]*w]}
function sh(t,s){let h=gl.createShader(t);gl.shaderSource(h,s);gl.compileShader(h);if(!gl.getShaderParameter(h,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(h));return h}function init(){gl=c.getContext('webgl',{antialias:true})||c.getContext('experimental-webgl');if(!gl)throw Error('当前浏览器/WebView不支持WebGL');let ok=gl.getExtension('OES_element_index_uint');if(!ok)console.warn('OES_element_index_uint not available');let vs='attribute vec3 p,n;uniform mat4 mvp,mo;varying vec3 vn;void main(){vn=mat3(mo)*n;gl_Position=mvp*vec4(p,1.0);}';let fs='precision mediump float;uniform vec3 color;uniform float pulse;varying vec3 vn;void main(){float d=max(dot(normalize(vn),normalize(vec3(.4,.8,.5))),0.0);gl_FragColor=vec4(color*(.35+.65*d)+color*pulse*.42,1.0);}';prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,vs));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(prog));gl.useProgram(prog);gl.enable(gl.DEPTH_TEST)}
function cs(t){return{SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[t]||1}function cb(t){return{5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[t]||4}function rc(d,o,t){if(t==5120)return d.getInt8(o);if(t==5121)return d.getUint8(o);if(t==5122)return d.getInt16(o,true);if(t==5123)return d.getUint16(o,true);if(t==5125)return d.getUint32(o,true);if(t==5126)return d.getFloat32(o,true);return 0}async function load(){let ab=await(await fetch(MODEL_URL)).arrayBuffer(),dv=new DataView(ab);if(dv.getUint32(0,true)!=0x46546c67)throw Error('当前离线查看器优先支持 .glb；如为 .gltf，请导出为未压缩 .glb 后再导入。');let off=12,j=null,bin=null;while(off<ab.byteLength){let l=dv.getUint32(off,true),ty=dv.getUint32(off+4,true);off+=8;let ch=ab.slice(off,off+l);off+=l;if(ty==0x4e4f534a)j=JSON.parse(new TextDecoder().decode(ch));else if(ty==0x004e4942)bin=ch}return{j,b:[bin]}}
function acc(g,i){let a=g.j.accessors[i],v=g.j.bufferViews[a.bufferView],buf=g.b[v.buffer||0],d=new DataView(buf),n=cs(a.type),b=cb(a.componentType),st=v.byteStride||n*b,off=(v.byteOffset||0)+(a.byteOffset||0),o=[];for(let x=0;x<a.count;x++){let r=[];for(let k=0;k<n;k++)r.push(rc(d,off+x*st+k*b,a.componentType));o.push(r)}return o}function fl(a){let o=[];for(const r of a)o.push(...r);return new Float32Array(o)}function ia(a){let o=[];for(const r of a)o.push(r[0]);return new Uint32Array(o)}function normals(p,ind){let n=Array(p.length).fill(0).map(()=>[0,0,0]),ids=ind?Array.from(ind):p.map((_,i)=>i);for(let i=0;i<ids.length;i+=3){let a=ids[i],b=ids[i+1],cc=ids[i+2];if(a==null||b==null||cc==null)continue;let nn=nr(cr(sub(p[b],p[a]),sub(p[cc],p[a])));for(const x of[a,b,cc])n[x]=add(n[x],nn)}return n.map(nr)}function matColor(g,i){try{let f=g.j.materials[i].pbrMetallicRoughness.baseColorFactor;return[f[0],f[1],f[2]]}catch(e){return[.45,.62,.82]}}
function updBox(box,p){for(let i=0;i<3;i++){box.min[i]=Math.min(box.min[i],p[i]);box.max[i]=Math.max(box.max[i],p[i])}}function getBox(code){if(!bindBoxes[code])bindBoxes[code]={min:[1e9,1e9,1e9],max:[-1e9,-1e9,-1e9]};return bindBoxes[code]}
function build(g){let scenes=g.j.scenes,sceneIndex=g.j.scene||0,sc=(scenes&&scenes[sceneIndex])?scenes[sceneIndex]:(scenes&&scenes[0]),nodes=(sc&&sc.nodes)?sc.nodes:[];let mi=[1e9,1e9,1e9],ma=[-1e9,-1e9,-1e9];function upd(p){for(let i=0;i<3;i++){mi[i]=Math.min(mi[i],p[i]);ma[i]=Math.max(ma[i],p[i])}}function rec(ni,pm,inherited){let nd=g.j.nodes[ni],wm=MM(pm,NM(nd));let nm=nd.name||'';let dc=deviceCode(nm);let bind=dc||inherited||'';let nn=N(nm);if(nn.startsWith('ANNO_')){let ac=nn.replace(/^ANNO_/,'');anchors[ac]=[wm[12],wm[13],wm[14]]} if(nd.mesh!=null){let me=g.j.meshes[nd.mesh];for(const pr of me.primitives||[]){if(pr.mode!=null&&pr.mode!==4)continue;if(pr.extensions&&pr.extensions.KHR_draco_mesh_compression)throw Error('模型使用Draco压缩，请重新导出未压缩GLB');if(!pr.attributes||pr.attributes.POSITION==null)continue;let p=acc(g,pr.attributes.POSITION),ind=pr.indices!=null?ia(acc(g,pr.indices)):null,n=pr.attributes.NORMAL!=null?acc(g,pr.attributes.NORMAL):normals(p,ind);let transformed=p.map(x=>tp(wm,x));transformed.forEach(upd);if(bind)transformed.forEach(q=>updBox(getBox(bind),q));let it={name:nm||me.name||'',meshName:me.name||'',bind:bind||deviceCode(me.name)||'',model:wm,color:matColor(g,pr.material),count:ind?ind.length:p.length,indexed:!!ind};it.v=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.bufferData(gl.ARRAY_BUFFER,fl(p),gl.STATIC_DRAW);it.n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.bufferData(gl.ARRAY_BUFFER,fl(n),gl.STATIC_DRAW);if(ind){it.i=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,ind,gl.STATIC_DRAW)}meshes.push(it)}}for(const x of nd.children||[])rec(x,wm,bind)}for(const n of nodes)rec(n,M(),'');if(!meshes.length)throw Error('模型内没有普通网格或为空模型');B.min=mi;B.max=ma;B.cen=[(mi[0]+ma[0])/2,(mi[1]+ma[1])/2,(mi[2]+ma[2])/2];B.r=Math.max(...sub(ma,mi).map(Math.abs))/2||1;for(const [code,b] of Object.entries(bindBoxes)){if(!anchors[code])anchors[code]=[(b.min[0]+b.max[0])/2,b.max[1]+B.r*.12,(b.min[2]+b.max[2])/2]}resetCamera()}
function dataFor(code){let k=N(code);return (state.pumps&&state.pumps[k])||(state.pipes&&state.pipes[k])||(state.meters&&state.meters[k])||(state.cameras&&state.cameras[k])||(state.tanks&&state.tanks[k])||null}function statusFor(code){let d=dataFor(code);return d?d.status:null}function match(name,bind){let k=N(bind||name);let st=statusFor(k);if(st)return st;let nk=N(name);for(const group of [state.pumps,state.pipes,state.meters,state.cameras,state.tanks])for(const c of Object.keys(group||{}))if(nk==N(c)||nk.includes(N(c)))return group[c].status;return null}
function labelText(code){let d=dataFor(code)||{};let t=`${code}`;if(d.statusText||d.status)t+=` ${d.statusText||d.status}`;if(d.freq!==undefined)t+=`<br><small>${num(d.freq,1)}Hz ${num(d.current,1)}A</small>`;else if(d.flow!==undefined)t+=`<br><small>${num(d.flow,1)}m³/h ${num(d.pressure,2)}MPa</small>`;else if(d.value!==undefined)t+=`<br><small>${num(d.value,2)}${d.unit||''}</small>`;else if(d.position)t+=`<br><small>${d.position}</small>`;return t}function detailText(code){let d=dataFor(code);if(!d)return `模型对象：${code}\n未匹配系统实时数据。`;let lines=[`对象：${d.code||code}`,`名称：${d.name||''}`,`状态：${d.statusText||d.status||''}`];if(d.type)lines.push(`类型：${d.type}`);if(d.freq!==undefined)lines.push(`频率：${num(d.freq,1)} Hz`,`电流：${num(d.current,1)} A`,`电压：${num(d.voltage,1)} V`,`功率：${num(d.power,2)} kW`);if(d.flow!==undefined)lines.push(`流量：${num(d.flow,1)} m³/h`,`压力：${num(d.pressure,2)} MPa`,`管径：${d.dn||''}`);if(d.value!==undefined)lines.push(`数值：${num(d.value,2)} ${d.unit||''}`);if(d.position)lines.push(`位置：${d.position}`);return lines.join('\n')}
function selectCode(code){selected=N(code);document.getElementById('detail').textContent=detailText(selected);updateLabels()}window.selectCode=selectCode;
function project(pos,vp){let q=mv(vp,pos);if(!q||q[3]===0)return null;let x=q[0]/q[3],y=q[1]/q[3],z=q[2]/q[3];if(z<-1||z>1)return null;return [(x*.5+.5)*c.clientWidth,(-y*.5+.5)*c.clientHeight,z]}
function updateLabels(view,proj){labelsDiv.style.display=showLabels?'block':'none';if(!showLabels)return;let vp=view&&proj?MM(proj,view):null;let codes=Object.keys(anchors).filter(k=>dataFor(k)||/^P\d+$|^PIPE_|^LT\d+$|^FT\d+$|^PT\d+$|^CAM\d+$|^TANK/.test(k));let used={};for(const code of codes){let el=document.getElementById('lbl_'+code);if(!el){el=document.createElement('div');el.id='lbl_'+code;el.className='lbl';el.onclick=(ev)=>{ev.stopPropagation();selectCode(code)};labelsDiv.appendChild(el)}let d=dataFor(code)||{};el.className='lbl '+(d.status||'')+(selected===code?' sel':'');el.innerHTML=labelText(code);let pos=vp?project(anchors[code],vp):null;if(pos){el.style.left=pos[0]+'px';el.style.top=pos[1]+'px';el.style.display='block'}else el.style.display='none';used[el.id]=1}for(const el of Array.from(labelsDiv.children))if(!used[el.id])el.remove()}
function resize(){let r=window.devicePixelRatio||1,w=c.clientWidth*r,h=c.clientHeight*r;if(c.width!=w||c.height!=h){c.width=w;c.height=h}}function draw(){requestAnimationFrame(draw);resize();if(auto)cam.yaw+=.006;gl.viewport(0,0,c.width,c.height);gl.clearColor(.02,.04,.08,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);let r=cam.dist,cp=Math.cos(cam.pitch),eye=[B.cen[0]+r*cp*Math.sin(cam.yaw)+cam.pan[0],B.cen[1]+r*Math.sin(cam.pitch)+cam.pan[1],B.cen[2]+r*cp*Math.cos(cam.yaw)],view=LA(eye,[B.cen[0]+cam.pan[0],B.cen[1]+cam.pan[1],B.cen[2]],[0,1,0]),proj=P(Math.PI/4,c.width/c.height,Math.max(.01,B.r/1000),B.r*100+100);let ap=gl.getAttribLocation(prog,'p'),an=gl.getAttribLocation(prog,'n'),um=gl.getUniformLocation(prog,'mvp'),umo=gl.getUniformLocation(prog,'mo'),uc=gl.getUniformLocation(prog,'color'),up=gl.getUniformLocation(prog,'pulse'),t=Date.now()/360;for(const it of meshes){let st=match(it.name,it.bind),co=st?col(st):it.color,pulse=(selected&&it.bind===selected)?0.55:(st==='fault'?(Math.sin(t)+1)/2:0),mvp=MM(proj,MM(view,it.model));gl.uniformMatrix4fv(um,false,new Float32Array(mvp));gl.uniformMatrix4fv(umo,false,new Float32Array(it.model));gl.uniform3fv(uc,new Float32Array(co));gl.uniform1f(up,pulse);gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.enableVertexAttribArray(ap);gl.vertexAttribPointer(ap,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.enableVertexAttribArray(an);gl.vertexAttribPointer(an,3,gl.FLOAT,false,0,0);if(it.indexed){gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.drawElements(gl.TRIANGLES,it.count,gl.UNSIGNED_INT,0)}else gl.drawArrays(gl.TRIANGLES,0,it.count)}updateLabels(view,proj)}
async function loadState(){try{state=await(await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'})).json();applyState();updateLabels()}catch(e){console.warn(e)}}function clickable(code,html){return `<div class="item" onclick="selectCode('${N(code)}')">${html}</div>`}function applyState(){document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||''}`;let pumps=Object.values(state.pumps||{}).slice(0,12).map(p=>clickable(p.code,`<b>${p.code}</b> ${p.name||''}<br>状态：${p.statusText||p.status||'-'}　频率：${num(p.freq,1)}Hz　电流：${num(p.current,1)}A`)).join(''),pipes=Object.values(state.pipes||{}).filter((v,i,a)=>a.findIndex(x=>x.code===v.code)===i).slice(0,8).map(p=>clickable(p.code,`<b>${p.code}</b> ${p.name||''}<br>流量：${num(p.flow,1)} m³/h　压力：${num(p.pressure,2)}MPa`)).join(''),meters=Object.values(state.meters||{}).slice(0,8).map(m=>clickable(m.code,`<b>${m.code}</b> ${m.name||''}<br>数值：${num(m.value,2)} ${m.unit||''}　状态：${m.statusText||m.status||'-'}`)).join(''),cams=Object.values(state.cameras||{}).slice(0,4).map(v=>clickable(v.code,`<b>${v.code}</b> ${v.name||''}<br>位置：${v.position||''}　状态：${v.statusText||v.status||'-'}`)).join('');document.getElementById('stateBox').innerHTML=`<div class="item">控制状态：${state.controlState||'-'}<br>事件状态：${state.eventState||'-'}<br>当前动作：${state.currentAction||'-'}</div>${pumps}${pipes}${meters}${cams}`;if(selected)document.getElementById('detail').textContent=detailText(selected)}
function resetCamera(){cam.dist=Math.max(2,B.r*3.2);cam.yaw=.75;cam.pitch=.9;cam.pan=[0,0]}window.resetCamera=resetCamera;window.toggleRotate=()=>auto=!auto;window.toggleLabels=()=>{showLabels=!showLabels;updateLabels()};c.oncontextmenu=e=>e.preventDefault();c.onmousedown=e=>{drag=true;last=[e.clientX,e.clientY];btn=e.button};window.onmouseup=()=>drag=false;window.onmousemove=e=>{if(!drag)return;let dx=e.clientX-last[0],dy=e.clientY-last[1];last=[e.clientX,e.clientY];if(btn==2||btn==1){let s=B.r/350;cam.pan[0]+=dx*s;cam.pan[1]-=dy*s}else{cam.yaw+=dx*.008;cam.pitch=Math.max(-1.45,Math.min(1.45,cam.pitch+dy*.006))}};c.onwheel=e=>{e.preventDefault();cam.dist*=e.deltaY>0?1.12:.89;cam.dist=Math.max(B.r*.25,cam.dist)};
(async()=>{try{init();let g=await load();build(g);hide();await loadState();setInterval(loadState,1000);draw()}catch(e){console.error(e);show('<span class="err">三维模型加载失败：</span> '+(e.message||e)+'\n\n处理建议：\n1. 请优先导入 .glb 文件；\n2. 如果模型使用 Draco/压缩网格，请重新导出未压缩 GLB；\n3. 本查看器不依赖外网；\n4. 如果外部系统3D查看器能打开，但这里失败，请把错误截图发给开发者。')}})();
</script></body></html>'''


def _v5714_write_twin_state_json(self, sid=None):
    # 先复用 V5.7.13 原状态，再补充摄像头和水箱对象，保证 CAM01/TANK01 标签有数据可显示。
    out = _v5713_write_twin_state_json(self, sid)
    try:
        with open(out, 'r', encoding='utf-8') as f:
            state = json.load(f)
        sid = sid or self.twin_sid() or self.sid()
        state['version'] = _V5714_VERSION
        state.setdefault('cameras', {})
        state.setdefault('tanks', {})
        try:
            for cam in self.rows('SELECT * FROM camera WHERE station_id=? ORDER BY id', (sid,)):
                code = str(cam['camera_code'] or '')
                if code:
                    state['cameras'][code] = {
                        'code': code,
                        'name': cam['camera_name'],
                        'position': cam['camera_position'],
                        'type': cam['camera_type'],
                        'status': 'normal' if int(cam['enabled'] or 0) else 'disabled',
                        'statusText': cam['status'] or ('正常' if int(cam['enabled'] or 0) else '禁用')
                    }
        except Exception as e:
            self._log_twin_error('生成摄像头孪生状态失败', e)
        try:
            st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
            if st:
                state['tanks']['TANK01'] = {
                    'code': 'TANK01',
                    'name': '水仓/水箱',
                    'status': 'normal',
                    'statusText': '液位正常',
                    'value': float(st['current_level'] or 0),
                    'unit': 'm'
                }
        except Exception as e:
            self._log_twin_error('生成水箱孪生状态失败', e)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        self._log_twin_error('V5.7.14 修正 twin_state.json 失败', e)
    return out


def _v5714_prepare_twin_web_model(self, path):
    try:
        source = self._resolve_twin_model_path(path)
        target, rel, cfg = self._copy_twin_model_to_safe_store(source)
        sid = cfg.get('station_id') or self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        # 同时刷新模型对象绑定表，供右侧检查和现场排查。
        try:
            self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
        except Exception as e:
            self._log_twin_error('V5.7.14 生成绑定表失败', e, target)
        viewer_dir = self._twin_viewer_dir()
        model_url = '/' + rel.replace('\\', '/')
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = _V5714_OFFLINE_HTML_TEMPLATE.replace('__MODEL__', model_url)
        html_text = html_text.replace('正在加载 GLB 模型...', '正在加载 GLB 模型...\\n模型路径：' + model_url)
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        log = self._log_twin_error('V5.7.14 GLB查看器准备失败', e, path)
        messagebox.showwarning('GLB查看器准备失败',
                               '三维模型加载前检查失败。\\n\\n'
                               '可能原因：模型被占用、路径无权限、文件损坏，或旧版本路径仍在数据库中。\\n\\n'
                               '详细日志：\\n' + (log or '未能写入日志') + '\\n\\n错误：\\n' + str(e))
        return None


def _v5714_load_twin_in_page(self, force=False):
    # Tkinter 自身不能直接渲染 WebGL。优先尝试可用的 WebView；不可用时自动打开外部动态查看器，避免“按钮无反应”。
    print("_v5714_load_twin_in_page")
    path = (self.twin_model_path.get() or '').strip()
    if not path or not os.path.exists(self._resolve_twin_model_path(path)):
        self._show_twin_placeholder('未找到 GLB/gltf 模型。请先导入模型并保存绑定。')
        return False
    html = self._prepare_twin_web_model(path)
    if not html or not self._start_twin_http_server():
        self._show_twin_placeholder('GLB 查看器准备失败。请检查模型文件路径。')
        return False
    url = self._twin_viewer_url() + f'?ts={int(time.time())}'

    if hasattr(self, 'browser') and self.browser:
        try:
            self.browser.LoadUrl(url)
            self.twin_loaded_url = url
            return True
        except Exception as e:
            print(f">>> 重新加载 URL 失败，尝试重新创建浏览器: {e}")

    for child in getattr(self, 'twin_view_frame', tk.Frame()).winfo_children():
        try:
            child.destroy()
        except Exception:
            pass
    errors = []
    self.twin_view_frame.pack(fill="both", expand=True)
    self.update_idletasks()
    try:
        from cefpython3 import cefpython as cef
        """
        LOGSEVERITY_VERBOSE - 记录详细信息，包括调试和运行时信息。
        LOGSEVERITY_INFO - 记录信息性消息，但不包括调试和运行时信息。
        LOGSEVERITY_WARNING - 记录警告和错误信息。
        LOGSEVERITY_ERROR - 只记录错误信息。
        LOGSEVERITY_DISABLE - 禁用日志记录。
        LOGSEVERITY_FATAL - 记录致命错误信息。
        """
        if not getattr(self, '_cef_initialized', False):
            cef.Initialize(settings={
                "windowless_rendering_enabled": False,
                "log_severity": cef.LOGSEVERITY_INFO,
                # "log_file": "../log/cefpython.log"  # 日志文件路径
            })
            self._cef_initialized = True
        self.update()
        hwnd = self.twin_view_frame.winfo_id()

        width = self.twin_view_frame.winfo_width()
        height = self.twin_view_frame.winfo_height()
        if width < 10 or height < 10:
            width, height = 900, 600
        rect = [0, 0, width, height]
        window_info = cef.WindowInfo()
        window_info.SetAsChild(hwnd, rect)
        self.browser = cef.CreateBrowserSync(window_info, url=url)

        if not getattr(self, '_cef_loop_running', False):
            self._cef_loop_running = True

            def cef_loop():
                try:
                    cef.MessageLoopWork()
                except Exception:
                    pass
                if hasattr(self, 'browser') and self.browser:
                    self.after(10, cef_loop)
                else:
                    self._cef_loop_running = False

            self.after(10, cef_loop)
        import win32gui

        def _resize_browser(event=None):
            if not getattr(self, "browser", None):
                return
            w = self.twin_view_frame.winfo_width()
            h = self.twin_view_frame.winfo_height()
            if w < 10 or h < 10:
                return
            try:
                hwnd = self.browser.GetWindowHandle()
                win32gui.MoveWindow(
                    hwnd,
                    0,
                    0,
                    w,
                    h,
                    True
                )
                print("BrowserRect:", win32gui.GetWindowRect(hwnd))
                self.browser.NotifyMoveOrResizeStarted()
                self.browser.WasResized()
            except Exception as e:
                print("Resize Error:", e)

        print("Frame hwnd =", self.twin_view_frame.winfo_id())
        print("Browser hwnd =", self.browser.GetWindowHandle())
        print("Browser Parent =",
              win32gui.GetParent(
                  self.browser.GetWindowHandle()
              ))
        self.twin_view_frame.bind("<Configure>", _resize_browser)
        self.after(100, _resize_browser)
        self.twin_embedded_widget = self.browser
        self.twin_loaded_url = url
        self.twin_embed_status = 'cefpython3'
        return True
    except Exception as e:
        print(e)
        errors.append(str(e))
        try:
            from tkwebview2.tkwebview2 import WebView2
            w = WebView2(self.twin_view_frame, 900, 600, url=url)
            w.pack(fill='both', expand=True)
            w.load_url(url)
            self.twin_embedded_widget = w
            self.twin_loaded_url = url
            self.twin_embed_status = 'tkwebview2'
            return True
        except Exception as e2:
            errors.append(f"WebView2: {str(e2)}")

    msg = '当前环境未安装可嵌入 WebGL 的浏览器组件，暂不能在本页内直接旋转/缩放。\n\n已生成动态查看器和 twin_state.json；可点击“外部GLB查看器”查看完整效果。\n\n安装可选组件后再点“加载内嵌动态查看器”。\n' + '\n'.join(
        errors[:1])
    self._show_twin_placeholder(msg)
    self.twin_loaded_url = ''
    self.twin_embed_status = 'failed'
    return False


def _v5714_model_status_check(self):
    print("_v5714_model_status_check")
    path = (self.twin_model_path.get() or '').strip()
    lines = []
    ok = False
    try:
        ap = self._validate_twin_model_file(path)
        ok = True
        size_mb = os.path.getsize(ap) / 1024 / 1024
        data = _v5711_read_gltf_json(ap)
        names = [str(n.get('name')) for n in data.get('nodes', []) or [] if n.get('name')]
        normed = {_v5711_norm_name(x) for x in names}
        expected = ['P1', 'P2', 'P3', 'P4', 'PIPE_A', 'LT01', 'FT01', 'PT01', 'CAM01', 'TANK01', 'ANNO_P1', 'ANNO_P2',
                    'ANNO_P3', 'ANNO_P4', 'ANNO_PIPE_A', 'ANNO_LT01', 'ANNO_FT01', 'ANNO_PT01', 'ANNO_CAM01']
        missing = [x for x in expected if _v5711_norm_name(x) not in normed]
        parent_nodes = [x for x in names if _v5711_norm_name(x) in ['P1', 'P2', 'P3', 'P4', 'PIPE_A']]
        anchors = [x for x in names if _v5711_norm_name(x).startswith('ANNO_')]
        lines += [
            '模型状态检查',
            '版本：' + _V5714_VERSION,
            '当前泵站：' + self._station_safe_code(),
            '模型文件：正常',
            '模型大小：%.2f MB' % size_mb,
            '当前路径：' + ap,
            '',
            '关键父级对象：' + ('、'.join(parent_nodes) if parent_nodes else '未识别'),
            '标注锚点：' + ('、'.join(anchors) if anchors else '未识别'),
            '已识别对象数量：%s' % len(names),
        ]
        if missing:
            lines.append('缺少/需确认命名：' + '、'.join(missing))
        else:
            lines.append('常用对象命名检查：完整')
        lines += ['', 'V5.7.14 已修正：父级节点 P1/P2/PIPE_A 下的所有子网格会继承父级编号，实现整台泵/整根母管颜色联动。']
    except Exception as e:
        log = self._log_twin_error('V5.7.14 模型状态检查失败', e, path)
        lines += ['模型状态检查', '模型文件：异常', '当前路径：' + (path or '-'), '错误：' + str(e)]
        if log: lines.append('日志：' + log)
    if hasattr(self, 'twin_info'):
        self.twin_info.delete('1.0', 'end')
        self.twin_info.insert('end', '\n'.join(lines))
    messagebox.showinfo('模型状态检查',
                        ('检查完成：模型文件正常。' if ok else '检查完成：模型文件异常。') + '\n\n详情已显示在右侧信息框。')


# 最终覆盖：保证 V5.7.14 的绑定显示逻辑生效。
App._write_twin_state_json = _v5714_write_twin_state_json
App._prepare_twin_web_model = _v5714_prepare_twin_web_model
App.load_twin_in_page = _v5714_load_twin_in_page

# V5.7.16 TwinRenderFix
# 解决：GLB 在专业软件/外部查看器中材质美观，但导入程序后失真、发灰、被状态颜色覆盖的问题。
# 思路：保留 GLB 原始材质和贴图，读取 baseColorTexture/TEXCOORD_0，状态只作轻量叠加，不再直接替换设备材质。
_V5716_VERSION = 'V5.7.16_TwinRenderFix'
_V5716_OFFLINE_HTML_TEMPLATE = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>离线GLB三维孪生</title><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#050b16;color:#d7ecff;font-family:"Microsoft YaHei",Arial}canvas{position:fixed;inset:0;width:100%;height:100%;display:block;background:radial-gradient(circle,#12365a 0%,#07101f 55%,#020814 100%)}#hud{position:absolute;left:12px;right:12px;top:10px;height:48px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,22,38,.72);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:0 12px;z-index:5}.title{font-weight:bold;color:#fff;font-size:16px}.sub{font-size:12px;color:#8fd3ff}button,select{background:#0f6fb2;color:#fff;border:1px solid #69c9ff;border-radius:6px;padding:6px 10px;margin-left:6px;cursor:pointer}select{background:#0b2744}#panel{position:absolute;right:12px;top:76px;width:340px;max-height:calc(100vh - 96px);overflow:auto;background:rgba(7,18,32,.84);border:1px solid rgba(68,188,255,.35);border-radius:10px;padding:12px;z-index:5}#panel h3{margin:0 0 8px;color:#fff}.item{border-bottom:1px solid rgba(143,211,255,.16);padding:6px 0;font-size:12px;line-height:1.55;cursor:pointer}.item:hover{background:rgba(47,168,255,.12)}#detail{margin-top:8px;border:1px solid rgba(143,211,255,.25);background:rgba(12,32,55,.72);border-radius:8px;padding:9px;font-size:12px;line-height:1.7;color:#d7ecff;white-space:pre-line}#legend{position:absolute;left:12px;bottom:12px;background:rgba(7,18,32,.82);border:1px solid rgba(68,188,255,.35);border-radius:8px;padding:8px 12px;font-size:12px;z-index:5}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px}.green{background:#18d06b}.blue{background:#2fa8ff}.yellow{background:#f6c343}.red{background:#ff4d4f}.gray{background:#7b8794}.purple{background:#a855f7}#msg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:820px;color:#8fd3ff;font-size:14px;line-height:1.8;z-index:7;background:rgba(8,22,38,.92);padding:18px 24px;border:1px solid rgba(68,188,255,.45);border-radius:10px;white-space:pre-line}.err{color:#ff7875}.warn{color:#f6c343}.ok{color:#18d06b}#labels{position:absolute;inset:0;pointer-events:none;z-index:6}.lbl{position:absolute;transform:translate(-50%,-100%);pointer-events:auto;background:rgba(5,15,28,.88);border:1px solid rgba(143,211,255,.65);color:#d7ecff;border-radius:7px;padding:4px 7px;font-size:12px;line-height:1.35;white-space:nowrap;box-shadow:0 0 12px rgba(47,168,255,.25);cursor:pointer}.lbl.running{border-color:#18d06b;color:#b8ffd2}.lbl.standby{border-color:#2fa8ff}.lbl.fault{border-color:#ff4d4f;color:#ffd2d2}.lbl.maintenance{border-color:#f6c343;color:#ffe7a3}.lbl.bypassed{border-color:#a855f7}.lbl.sel{box-shadow:0 0 18px rgba(255,255,255,.7);border-width:2px}.lbl small{opacity:.85;color:#8fd3ff}.cross{position:absolute;width:12px;height:12px;border-radius:50%;background:#8fd3ff;box-shadow:0 0 12px #8fd3ff;transform:translate(-50%,-50%);pointer-events:none}
</style></head><body><canvas id="gl"></canvas><div id="labels"></div><div id="hud"><div><div class="title">隧道泵站自动控制系统 V5.7.16 · 渲染质量修正版</div><div class="sub" id="stationLine">加载中...</div></div><div><button onclick="resetCamera()">复位视角</button><button onclick="toggleRotate()">自动旋转</button><select id="labelMode" onchange="setLabelMode(this.value)" title="标签模式"><option value="status">状态标签</option><option value="compact">简洁标签</option><option value="detail">选中详情</option><option value="alarm">只看报警</option></select><select id="renderMode" onchange="setRenderMode(this.value)" title="渲染模式"><option value="industrial">工业美化</option><option value="quality">高质量</option><option value="standard">标准</option></select><button onclick="toggleLabels()">显示/隐藏标签</button><button onclick="location.reload()">重新加载</button></div></div><div id="panel"><h3>实时状态 / 点击对象查看</h3><div id="stateBox">等待数据...</div><div id="detail">提示：V5.7.16 已保留模型原材质，状态只以轻量色彩叠加、标签和选中高亮表达；点击对象或标签查看详细参数。</div></div><div id="legend"><span class="dot green"></span>运行 <span class="dot blue"></span>备用 <span class="dot yellow"></span>检修 <span class="dot red"></span>故障 <span class="dot purple"></span>屏蔽 <span class="dot gray"></span>停止/未绑定</div><div id="msg">正在加载 GLB 模型...</div><script>
const MODEL_URL='__MODEL__';let gl,prog,meshes=[],state={},auto=false,showLabels=true,selected='',labelMode='status',renderMode='industrial';const c=document.getElementById('gl'),msg=document.getElementById('msg'),labelsDiv=document.getElementById('labels');let cam={yaw:.75,pitch:.8,dist:8,pan:[0,0]},B={min:[-1,-1,-1],max:[1,1,1],cen:[0,0,0],r:1};let drag=false,last=[0,0],btn=0;let anchors={},bindBoxes={};
function show(x){msg.style.display='block';msg.innerHTML=x}function hide(){msg.style.display='none'}function N(s){return String(s||'').toUpperCase().replace(/[^A-Z0-9_]/g,'')}function num(v,d=2){v=Number(v||0);return isFinite(v)?v.toFixed(d):'0.00'}function col(st){return {running:[.06,.82,.38],standby:[.18,.66,1],fault:[1,.2,.2],maintenance:[.96,.76,.26],stopped:[.48,.53,.58],disabled:[.22,.25,.29],normal:[.06,.82,.38],good:[.06,.82,.38],bypassed:[.66,.33,.97],unknown:[.52,.62,.72]}[st]||[.52,.62,.72]}
function deviceCode(s){let n=N(s);if(!n||n.startsWith('ANNO_'))return '';if(/^P\d+$/.test(n)||/^PIPE_[A-Z0-9]+$/.test(n)||/^LT\d+$/.test(n)||/^FT\d+$/.test(n)||/^PT\d+$/.test(n)||/^CAM\d+$/.test(n)||/^TANK\d+$/.test(n)||/^JP\d+$/.test(n)||/^CAB\d+$/.test(n))return n;return ''}
function M(){return [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}function MM(a,b){let o=Array(16);for(let r=0;r<4;r++)for(let cc=0;cc<4;cc++)o[cc*4+r]=a[r]*b[cc*4]+a[4+r]*b[cc*4+1]+a[8+r]*b[cc*4+2]+a[12+r]*b[cc*4+3];return o}function T(v){let m=M();m[12]=v[0];m[13]=v[1];m[14]=v[2];return m}function S(v){let m=M();m[0]=v[0];m[5]=v[1];m[10]=v[2];return m}function Q(q){let x=q[0],y=q[1],z=q[2],w=q[3],x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2;return [1-(yy+zz),xy+wz,xz-wy,0,xy-wz,1-(xx+zz),yz+wx,0,xz+wy,yz-wx,1-(xx+yy),0,0,0,0,1]}function NM(n){if(n.matrix)return n.matrix;let m=M();if(n.translation)m=MM(m,T(n.translation));if(n.rotation)m=MM(m,Q(n.rotation));if(n.scale)m=MM(m,S(n.scale));return m}function tp(m,p){let x=p[0],y=p[1],z=p[2];return [m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]]}
function sub(a,b){return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}function add(a,b){return[a[0]+b[0],a[1]+b[1],a[2]+b[2]]}function cr(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}function dt(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}function nr(a){let l=Math.sqrt(dt(a,a))||1;return[a[0]/l,a[1]/l,a[2]/l]}function P(f,asp,n,fa){let q=1/Math.tan(f/2),nf=1/(n-fa);return[q/asp,0,0,0,0,q,0,0,0,0,(fa+n)*nf,-1,0,0,2*fa*n*nf,0]}function LA(e,ce,u){let z=nr(sub(e,ce)),x=nr(cr(u,z)),y=cr(z,x);return[x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dt(x,e),-dt(y,e),-dt(z,e),1]}function mv(m,p){let x=p[0],y=p[1],z=p[2],w=1;return [m[0]*x+m[4]*y+m[8]*z+m[12]*w,m[1]*x+m[5]*y+m[9]*z+m[13]*w,m[2]*x+m[6]*y+m[10]*z+m[14]*w,m[3]*x+m[7]*y+m[11]*z+m[15]*w]}
function sh(t,s){let h=gl.createShader(t);gl.shaderSource(h,s);gl.compileShader(h);if(!gl.getShaderParameter(h,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(h));return h}function init(){gl=c.getContext('webgl',{antialias:true,alpha:false,premultipliedAlpha:false})||c.getContext('experimental-webgl',{antialias:true});if(!gl)throw Error('当前浏览器/WebView不支持WebGL');let ok=gl.getExtension('OES_element_index_uint');if(!ok)console.warn('OES_element_index_uint not available');let vs='attribute vec3 p,n;attribute vec2 uv;uniform mat4 mvp,mo;varying vec3 vn;varying vec2 vuv;void main(){vuv=uv;vn=normalize(mat3(mo)*n);gl_Position=mvp*vec4(p,1.0);}';let fs='precision mediump float;uniform vec3 color,statusColor;uniform float pulse,statusAlpha,useMap,exposure;uniform sampler2D tex;varying vec3 vn;varying vec2 vuv;void main(){vec3 n=normalize(vn);vec3 l1=normalize(vec3(.45,.85,.38));vec3 l2=normalize(vec3(-.55,.35,-.70));float d=max(dot(n,l1),0.0);float fill=max(dot(n,l2),0.0);float rim=pow(1.0-max(abs(n.z),0.0),2.0);vec3 base=color;if(useMap>.5){base=texture2D(tex,vuv).rgb;}vec3 lit=base*(.46+.78*d+.22*fill)+vec3(.11,.20,.32)*rim;lit=mix(lit,statusColor,statusAlpha);lit+=statusColor*pulse*.30;lit=vec3(1.0)-exp(-lit*exposure);lit=pow(max(lit,0.0),vec3(1.0/2.2));gl_FragColor=vec4(lit,1.0);}';prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,vs));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(prog));gl.useProgram(prog);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE)}
function cs(t){return{SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[t]||1}function cb(t){return{5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[t]||4}function rc(d,o,t){if(t==5120)return d.getInt8(o);if(t==5121)return d.getUint8(o);if(t==5122)return d.getInt16(o,true);if(t==5123)return d.getUint16(o,true);if(t==5125)return d.getUint32(o,true);if(t==5126)return d.getFloat32(o,true);return 0}async function load(){let ab=await(await fetch(MODEL_URL)).arrayBuffer(),dv=new DataView(ab);if(dv.getUint32(0,true)!=0x46546c67)throw Error('当前离线查看器优先支持 .glb；如为 .gltf，请导出为未压缩 .glb 后再导入。');let off=12,j=null,bin=null;while(off<ab.byteLength){let l=dv.getUint32(off,true),ty=dv.getUint32(off+4,true);off+=8;let ch=ab.slice(off,off+l);off+=l;if(ty==0x4e4f534a)j=JSON.parse(new TextDecoder().decode(ch));else if(ty==0x004e4942)bin=ch}return{j,b:[bin]}}
function acc(g,i){let a=g.j.accessors[i],v=g.j.bufferViews[a.bufferView],buf=g.b[v.buffer||0],d=new DataView(buf),n=cs(a.type),b=cb(a.componentType),st=v.byteStride||n*b,off=(v.byteOffset||0)+(a.byteOffset||0),o=[];for(let x=0;x<a.count;x++){let r=[];for(let k=0;k<n;k++)r.push(rc(d,off+x*st+k*b,a.componentType));o.push(r)}return o}function fl(a){let o=[];for(const r of a)o.push(...r);return new Float32Array(o)}function ia(a){let o=[];for(const r of a)o.push(r[0]);return new Uint32Array(o)}function normals(p,ind){let n=Array(p.length).fill(0).map(()=>[0,0,0]),ids=ind?Array.from(ind):p.map((_,i)=>i);for(let i=0;i<ids.length;i+=3){let a=ids[i],b=ids[i+1],cc=ids[i+2];if(a==null||b==null||cc==null)continue;let nn=nr(cr(sub(p[b],p[a]),sub(p[cc],p[a])));for(const x of[a,b,cc])n[x]=add(n[x],nn)}return n.map(nr)}let texCache={};function solidTex(){if(texCache.__solid)return texCache.__solid;let tx=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tx);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([255,255,255,255]));gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);texCache.__solid=tx;return tx}function textureFromImage(g,idx){if(idx==null)return null;if(texCache[idx])return texCache[idx];let imd=g.j.images&&g.j.images[idx];if(!imd||imd.bufferView==null)return null;let bv=g.j.bufferViews[imd.bufferView],buf=g.b[bv.buffer||0],blob=new Blob([buf.slice(bv.byteOffset||0,(bv.byteOffset||0)+(bv.byteLength||0))],{type:imd.mimeType||'image/png'}),url=URL.createObjectURL(blob),tx=solidTex();let img=new Image();img.onload=()=>{gl.bindTexture(gl.TEXTURE_2D,tx);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.generateMipmap(gl.TEXTURE_2D);URL.revokeObjectURL(url)};img.src=url;texCache[idx]=tx;return tx}function matInfo(g,i){let m=(g.j.materials||[])[i]||{},p=m.pbrMetallicRoughness||{},f=p.baseColorFactor||[.45,.62,.82,1],tex=null;if(p.baseColorTexture&&g.j.textures){let ti=g.j.textures[p.baseColorTexture.index];if(ti&&ti.source!=null)tex=textureFromImage(g,ti.source)}return{color:[f[0],f[1],f[2]],texture:tex,metallic:p.metallicFactor||0,roughness:(p.roughnessFactor==null?0.5:p.roughnessFactor)}}
function updBox(box,p){for(let i=0;i<3;i++){box.min[i]=Math.min(box.min[i],p[i]);box.max[i]=Math.max(box.max[i],p[i])}}function getBox(code){if(!bindBoxes[code])bindBoxes[code]={min:[1e9,1e9,1e9],max:[-1e9,-1e9,-1e9]};return bindBoxes[code]}
function build(g) {
    // 原代码: let sc=g.j.scenes?.[g.j.scene||0]||g.j.scenes?.[0],nodes=sc?.nodes||[];
    // 修改为 ES6 兼容写法
    let scenes = g.j.scenes;
    let sceneIndex = g.j.scene || 0;
    // 安全获取场景对象
    let sc = (scenes && scenes[sceneIndex]) ? scenes[sceneIndex] : (scenes && scenes[0]);
    // 安全获取节点数组
    let nodes = (sc && sc.nodes) ? sc.nodes : [];

    let mi = [1e9, 1e9, 1e9], ma = [-1e9, -1e9, -1e9];

    function upd(p) {
        for (let i = 0; i < 3; i++) {
            mi[i] = Math.min(mi[i], p[i]);
            ma[i] = Math.max(ma[i], p[i]);
        }
    }

    function rec(ni, pm, inherited) {
        let nd = g.j.nodes[ni];
        // 假设 MM 和 NM 是外部定义的矩阵运算函数，保持不变
        let wm = MM(pm, NM(nd)); 
        let nm = nd.name || '';
        let dc = deviceCode(nm);
        let bind = dc || inherited || '';
        let nn = N(nm);

        if (nn.startsWith('ANNO_')) {
            let ac = nn.replace(/^ANNO_/, '');
            // 确保 anchors 已定义
            if (typeof anchors !== 'undefined') {
                anchors[ac] = [wm[12], wm[13], wm[14]];
            }
        }

        if (nd.mesh != null) {
            let me = g.j.meshes[nd.mesh];
            // 安全获取 primitives
            let primitives = me.primitives || [];

            for (const pr of primitives) {
                // 检查 mode，如果不是 TRIANGLES (4) 则跳过
                if (pr.mode != null && pr.mode !== 4) continue;

                // 检查 Draco 压缩
                if (pr.extensions && pr.extensions.KHR_draco_mesh_compression) {
                    throw Error('模型使用Draco压缩，请重新导出未压缩GLB');
                }

                // 安全获取 attributes
                if (!pr.attributes || pr.attributes.POSITION == null) continue;

                let p = acc(g, pr.attributes.POSITION);
                let ind = pr.indices != null ? ia(acc(g, pr.indices)) : null;
                let n = pr.attributes.NORMAL != null ? acc(g, pr.attributes.NORMAL) : normals(p, ind);
                let uv = pr.attributes.TEXCOORD_0 != null ? acc(g, pr.attributes.TEXCOORD_0) : p.map(_ => [0, 0]);
                let miData = matInfo(g, pr.material); // 重命名变量避免与外层 mi 冲突

                let transformed = p.map(x => tp(wm, x));
                transformed.forEach(upd);

                if (bind) {
                    transformed.forEach(q => updBox(getBox(bind), q));
                }

                let it = {
                    name: nm || me.name || '',
                    meshName: me.name || '',
                    bind: bind || deviceCode(me.name) || '',
                    model: wm,
                    color: miData.color,
                    texture: miData.texture,
                    metallic: miData.metallic,
                    roughness: miData.roughness,
                    count: ind ? ind.length : p.length,
                    indexed: !!ind
                };

                it.v = gl.createBuffer();
                gl.bindBuffer(gl.ARRAY_BUFFER, it.v);
                gl.bufferData(gl.ARRAY_BUFFER, fl(p), gl.STATIC_DRAW);

                it.n = gl.createBuffer();
                gl.bindBuffer(gl.ARRAY_BUFFER, it.n);
                gl.bufferData(gl.ARRAY_BUFFER, fl(n), gl.STATIC_DRAW);

                it.u = gl.createBuffer();
                gl.bindBuffer(gl.ARRAY_BUFFER, it.u);
                gl.bufferData(gl.ARRAY_BUFFER, fl(uv), gl.STATIC_DRAW);

                if (ind) {
                    it.i = gl.createBuffer();
                    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, it.i);
                    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ind, gl.STATIC_DRAW);
                }

                // 确保 meshes 数组已定义
                if (typeof meshes !== 'undefined') {
                    meshes.push(it);
                }
            }
        }

        // 安全遍历子节点
        let children = nd.children || [];
        for (const x of children) {
            rec(x, wm, bind);
        }
    }

    for (const n of nodes) {
        rec(n, M(), ''); // 假设 M() 是单位矩阵生成函数
    }

    // 假设 meshes 和 B 是外部定义的全局变量
    if (!meshes || !meshes.length) {
        throw Error('模型内没有普通网格或为空模型');
    }

    B.min = mi;
    B.max = ma;
    B.cen = [(mi[0] + ma[0]) / 2, (mi[1] + ma[1]) / 2, (mi[2] + ma[2]) / 2];

    let diff = sub(ma, mi);
    B.r = Math.max(...diff.map(Math.abs)) / 2 || 1;

    // 安全遍历 bindBoxes
    if (typeof bindBoxes !== 'undefined') {
        for (const [code, b] of Object.entries(bindBoxes)) {
            if (!anchors[code]) {
                anchors[code] = [(b.min[0] + b.max[0]) / 2, b.max[1] + B.r * .12, (b.min[2] + b.max[2]) / 2];
            }
        }
    }

    resetCamera();
}
function dataFor(code){let k=N(code);return (state.pumps&&state.pumps[k])||(state.pipes&&state.pipes[k])||(state.meters&&state.meters[k])||(state.cameras&&state.cameras[k])||(state.tanks&&state.tanks[k])||null}function statusFor(code){let d=dataFor(code);return d?d.status:null}function match(name,bind){let k=N(bind||name);let st=statusFor(k);if(st)return st;let nk=N(name);for(const group of [state.pumps,state.pipes,state.meters,state.cameras,state.tanks])for(const c of Object.keys(group||{}))if(nk==N(c)||nk.includes(N(c)))return group[c].status;return null}
function labelText(code){let d=dataFor(code)||{},st=d.statusText||d.status||'';let t=`${code}${st?' '+st:''}`;if(labelMode==='compact')return t;if(labelMode==='detail'&&selected===N(code)){return detailText(code).split('\n').slice(0,6).join('<br><small>')+'</small>'}if(d.freq!==undefined)t+=`<br><small>${num(d.freq,1)}Hz</small>`;else if(d.flow!==undefined)t+=`<br><small>${num(d.flow,1)}m³/h</small>`;else if(d.value!==undefined)t+=`<br><small>${num(d.value,2)}${d.unit||''}</small>`;else if(d.position)t+=`<br><small>${d.position}</small>`;return t}function detailText(code){let d=dataFor(code);if(!d)return `模型对象：${code}\n未匹配系统实时数据。`;let lines=[`对象：${d.code||code}`,`名称：${d.name||''}`,`状态：${d.statusText||d.status||''}`];if(d.type)lines.push(`类型：${d.type}`);if(d.freq!==undefined)lines.push(`频率：${num(d.freq,1)} Hz`,`电流：${num(d.current,1)} A`,`电压：${num(d.voltage,1)} V`,`功率：${num(d.power,2)} kW`);if(d.flow!==undefined)lines.push(`流量：${num(d.flow,1)} m³/h`,`压力：${num(d.pressure,2)} MPa`,`管径：${d.dn||''}`);if(d.value!==undefined)lines.push(`数值：${num(d.value,2)} ${d.unit||''}`);if(d.position)lines.push(`位置：${d.position}`);return lines.join('\n')}
function selectCode(code){selected=N(code);document.getElementById('detail').textContent=detailText(selected);updateLabels()}window.selectCode=selectCode;
function project(pos,vp){let q=mv(vp,pos);if(!q||q[3]===0)return null;let x=q[0]/q[3],y=q[1]/q[3],z=q[2]/q[3];if(z<-1||z>1)return null;return [(x*.5+.5)*c.clientWidth,(-y*.5+.5)*c.clientHeight,z]}
function updateLabels(view,proj){labelsDiv.style.display=showLabels?'block':'none';if(!showLabels)return;let vp=view&&proj?MM(proj,view):null;let codes=Object.keys(anchors).filter(k=>dataFor(k)||/^P\d+$|^PIPE_|^LT\d+$|^FT\d+$|^PT\d+$|^CAM\d+$|^TANK/.test(k));if(labelMode==='alarm')codes=codes.filter(k=>['fault','alarm','maintenance','bypassed'].includes((dataFor(k)||{}).status));if(labelMode==='detail'&&selected)codes=codes.filter(k=>N(k)===selected||['fault','alarm'].includes((dataFor(k)||{}).status));let used={};for(const code of codes){let el=document.getElementById('lbl_'+code);if(!el){el=document.createElement('div');el.id='lbl_'+code;el.className='lbl';el.onclick=(ev)=>{ev.stopPropagation();selectCode(code)};labelsDiv.appendChild(el)}let d=dataFor(code)||{};el.className='lbl '+(d.status||'')+(selected===code?' sel':'');el.innerHTML=labelText(code);let pos=vp?project(anchors[code],vp):null;if(pos){el.style.left=pos[0]+'px';el.style.top=pos[1]+'px';el.style.display='block'}else el.style.display='none';used[el.id]=1}for(const el of Array.from(labelsDiv.children))if(!used[el.id])el.remove()}
function resize(){let r=window.devicePixelRatio||1,w=c.clientWidth*r,h=c.clientHeight*r;if(c.width!=w||c.height!=h){c.width=w;c.height=h}}function draw(){requestAnimationFrame(draw);resize();if(auto)cam.yaw+=.006;gl.viewport(0,0,c.width,c.height);let bg=renderMode==='standard'?[.02,.04,.08,1]:[.015,.028,.052,1];gl.clearColor(bg[0],bg[1],bg[2],bg[3]);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);let r=cam.dist,cp=Math.cos(cam.pitch),eye=[B.cen[0]+r*cp*Math.sin(cam.yaw)+cam.pan[0],B.cen[1]+r*Math.sin(cam.pitch)+cam.pan[1],B.cen[2]+r*cp*Math.cos(cam.yaw)],view=LA(eye,[B.cen[0]+cam.pan[0],B.cen[1]+cam.pan[1],B.cen[2]],[0,1,0]),proj=P(Math.PI/4,c.width/c.height,Math.max(.01,B.r/1000),B.r*100+100);let ap=gl.getAttribLocation(prog,'p'),an=gl.getAttribLocation(prog,'n'),auv=gl.getAttribLocation(prog,'uv'),um=gl.getUniformLocation(prog,'mvp'),umo=gl.getUniformLocation(prog,'mo'),uc=gl.getUniformLocation(prog,'color'),usc=gl.getUniformLocation(prog,'statusColor'),usa=gl.getUniformLocation(prog,'statusAlpha'),up=gl.getUniformLocation(prog,'pulse'),uum=gl.getUniformLocation(prog,'useMap'),ue=gl.getUniformLocation(prog,'exposure'),utex=gl.getUniformLocation(prog,'tex'),t=Date.now()/360;gl.uniform1i(utex,0);for(const it of meshes){let st=match(it.name,it.bind),scol=st?col(st):[0,0,0],alpha=st?(st==='fault'?0.30:(st==='running'?0.10:(st==='maintenance'?0.18:0.08))):0;if(renderMode==='standard')alpha*=1.45;if(renderMode==='quality')alpha*=0.75;let pulse=(selected&&it.bind===selected)?0.42:(st==='fault'?(Math.sin(t)+1)/2:0),mvp=MM(proj,MM(view,it.model));gl.uniformMatrix4fv(um,false,new Float32Array(mvp));gl.uniformMatrix4fv(umo,false,new Float32Array(it.model));gl.uniform3fv(uc,new Float32Array(it.color));gl.uniform3fv(usc,new Float32Array(scol));gl.uniform1f(usa,alpha);gl.uniform1f(up,pulse);gl.uniform1f(uum,it.texture?1:0);gl.uniform1f(ue,renderMode==='quality'?1.25:(renderMode==='standard'?0.95:1.12));gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,it.texture||solidTex());gl.bindBuffer(gl.ARRAY_BUFFER,it.v);gl.enableVertexAttribArray(ap);gl.vertexAttribPointer(ap,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,it.n);gl.enableVertexAttribArray(an);gl.vertexAttribPointer(an,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,it.u);gl.enableVertexAttribArray(auv);gl.vertexAttribPointer(auv,2,gl.FLOAT,false,0,0);if(it.indexed){gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,it.i);gl.drawElements(gl.TRIANGLES,it.count,gl.UNSIGNED_INT,0)}else gl.drawArrays(gl.TRIANGLES,0,it.count)}updateLabels(view,proj)}
async function loadState(){try{state=await(await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'})).json();applyState();updateLabels()}catch(e){console.warn(e)}}function clickable(code,html){return `<div class="item" onclick="selectCode('${N(code)}')">${html}</div>`}function applyState(){document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||''}`;let pumps=Object.values(state.pumps||{}).slice(0,12).map(p=>clickable(p.code,`<b>${p.code}</b> ${p.name||''}<br>状态：${p.statusText||p.status||'-'}　频率：${num(p.freq,1)}Hz　电流：${num(p.current,1)}A`)).join(''),pipes=Object.values(state.pipes||{}).filter((v,i,a)=>a.findIndex(x=>x.code===v.code)===i).slice(0,8).map(p=>clickable(p.code,`<b>${p.code}</b> ${p.name||''}<br>流量：${num(p.flow,1)} m³/h　压力：${num(p.pressure,2)}MPa`)).join(''),meters=Object.values(state.meters||{}).slice(0,8).map(m=>clickable(m.code,`<b>${m.code}</b> ${m.name||''}<br>数值：${num(m.value,2)} ${m.unit||''}　状态：${m.statusText||m.status||'-'}`)).join(''),cams=Object.values(state.cameras||{}).slice(0,4).map(v=>clickable(v.code,`<b>${v.code}</b> ${v.name||''}<br>位置：${v.position||''}　状态：${v.statusText||v.status||'-'}`)).join('');document.getElementById('stateBox').innerHTML=`<div class="item">控制状态：${state.controlState||'-'}<br>事件状态：${state.eventState||'-'}<br>当前动作：${state.currentAction||'-'}</div>${pumps}${pipes}${meters}${cams}`;if(selected)document.getElementById('detail').textContent=detailText(selected)}
function resetCamera(){cam.dist=Math.max(2,B.r*3.2);cam.yaw=.75;cam.pitch=.9;cam.pan=[0,0]}window.resetCamera=resetCamera;window.toggleRotate=()=>auto=!auto;window.toggleLabels=()=>{showLabels=!showLabels;updateLabels()};window.setLabelMode=(v)=>{labelMode=v||'status';updateLabels()};window.setRenderMode=(v)=>{renderMode=v||'industrial'};c.oncontextmenu=e=>e.preventDefault();c.onmousedown=e=>{drag=true;last=[e.clientX,e.clientY];btn=e.button};window.onmouseup=()=>drag=false;window.onmousemove=e=>{if(!drag)return;let dx=e.clientX-last[0],dy=e.clientY-last[1];last=[e.clientX,e.clientY];if(btn==2||btn==1){let s=B.r/350;cam.pan[0]+=dx*s;cam.pan[1]-=dy*s}else{cam.yaw+=dx*.008;cam.pitch=Math.max(-1.45,Math.min(1.45,cam.pitch+dy*.006))}};c.onwheel=e=>{e.preventDefault();cam.dist*=e.deltaY>0?1.12:.89;cam.dist=Math.max(B.r*.25,cam.dist)};
(async()=>{try{init();let g=await load();build(g);hide();await loadState();setInterval(loadState,1000);draw()}catch(e){console.error(e);show('<span class="err">三维模型加载失败：</span> '+(e.message||e)+'\n\n处理建议：\n1. 请优先导入 .glb 文件；\n2. 如果模型使用 Draco/压缩网格，请重新导出未压缩 GLB；\n3. 本查看器不依赖外网；\n4. 如果外部系统3D查看器能打开，但这里失败，请把错误截图发给开发者。')}})();
</script></body></html>'''


def _v5716_write_twin_state_json(self, sid=None):
    out = _v5714_write_twin_state_json(self, sid)
    try:
        with open(out, 'r', encoding='utf-8') as f:
            state = json.load(f)
        state['version'] = _V5716_VERSION
        state['renderHint'] = {
            'material_policy': 'preserve_original_material',
            'status_policy': 'overlay_not_replace',
            'refresh_interval_ms': 1000
        }
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        self._log_twin_error('V5.7.16 写入渲染状态失败', e)
    return out


def _v5716_prepare_twin_web_model(self, path):
    try:
        source = self._resolve_twin_model_path(path)
        target, rel, cfg = self._copy_twin_model_to_safe_store(source)
        sid = cfg.get('station_id') or self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        try:
            self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
        except Exception as e:
            self._log_twin_error('V5.7.16 生成绑定表失败', e, target)
        viewer_dir = self._twin_viewer_dir()
        model_url = '/' + rel.replace('\\', '/')
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = _V5716_OFFLINE_HTML_TEMPLATE.replace('__MODEL__', model_url)
        html_text = html_text.replace('正在加载 GLB 模型...', '正在加载 GLB 模型...\n模型路径：' + model_url)
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        log = self._log_twin_error('V5.7.16 GLB查看器准备失败', e, path)
        messagebox.showwarning('GLB查看器准备失败',
                               '三维模型加载前检查失败。\n\n'
                               '可能原因：模型被占用、路径无权限、文件损坏，或旧版本路径仍在数据库中。\n\n'
                               '详细日志：\n' + (log or '未能写入日志') + '\n\n错误：\n' + str(e))
        return None


# 最终覆盖：保证 V5.7.16 的材质保真、贴图读取、标签分层和状态轻量叠加逻辑生效。
App._write_twin_state_json = _v5716_write_twin_state_json
App._prepare_twin_web_model = _v5716_prepare_twin_web_model

# ===================== V5.7.17_TwinStateRenderPro =====================
# 解决：主程序内部参数已经刷新，但三维孪生侧仍显示备用/0Hz/0A。
# 根因：三维查看器读取的 twin_state.json 没有跟随主程序每秒刷新，或读取到了旧路径状态文件。
# 修正：每个主程序刷新周期同步写入状态桥接文件，并同时镜像到旧路径；查看器增加序号/时间戳/超时提示。
_V5717_VERSION = 'V5.7.17_TwinStateRenderPro'
_V5717_OLD_PERIODIC = App.periodic
_V5717_OLD_WRITE_TWIN_STATE_JSON = App._write_twin_state_json
_V5717_OLD_PREPARE_TWIN_WEB_MODEL = App._prepare_twin_web_model


def _v5717_status_from_row(self, p):
    try:
        if int(p['disabled'] or 0): return 'disabled', '禁用'
        if int(p['manual_fault'] or 0) or int(p['fault_feedback'] or 0): return 'fault', '故障'
        if int(p['maintenance'] or 0): return 'maintenance', '检修'
        if int(p['run_feedback'] or 0): return 'running', '运行'
        if int(p['enabled'] or 1) and int(p['auto_enable'] or 1): return 'standby', '备用'
        return 'stopped', '停止'
    except Exception:
        return 'unknown', '未知'


def _v5717_sec_to_text(seconds):
    try:
        s = int(seconds or 0)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h: return f'{h}h{m}m{sec}s'
        if m: return f'{m}m{sec}s'
        return f'{sec}s'
    except Exception:
        return '0s'


def _v5717_runtime_total(self, p):
    try:
        return self.pump_total_run_seconds(p)
    except Exception:
        try:
            return int(p['run_seconds_total'] or 0)
        except Exception:
            return 0


def _v5717_runtime_once(self, p):
    try:
        return self.pump_this_run_seconds(p)
    except Exception:
        try:
            return int(p['run_seconds_current'] or p['run_seconds_today'] or 0)
        except Exception:
            return 0


def _v5717_alias_pipe_code(code):
    c = str(code or '').upper().strip()
    out = []
    if c and not c.startswith('PIPE_'):
        suffix = c.replace('母管', '').replace('PIPE', '').strip('_- ')
        if suffix:
            out.append('PIPE_' + suffix)
    return out


def _v5717_write_twin_state_json(self, sid=None):
    """实时状态桥接层。
    直接从数据库实时表生成状态，确保主界面显示值与三维查看器读取值一致。
    同时写入 data/twin_viewer/twin_state.json 和旧版 BASE_DIR/twin_viewer/twin_state.json，避免查看器读错路径。
    """
    sid = sid or self.twin_sid() or self.sid()
    viewer_dir = self._twin_viewer_dir()
    os.makedirs(viewer_dir, exist_ok=True)
    st = self.row('SELECT * FROM pump_station WHERE id=?', (sid,)) if sid else None
    try:
        ctrl = self.row('SELECT * FROM station_control_state WHERE station_id=?', (sid,)) if sid else None
    except Exception:
        ctrl = None
    seq = int(getattr(self, '_twin_state_sequence', 0) or 0) + 1
    self._twin_state_sequence = seq
    ts = now()
    state = {
        'version': _V5717_VERSION,
        'stationId': sid,
        'station': st['station_code'] if st else '',
        'stationName': st['station_name'] if st else '',
        'controlMode': st['control_mode'] if st else '',
        'controlModeText': MODE_LABEL.get(st['control_mode'], st['control_mode']) if st else '',
        'controlState': ctrl['control_state'] if ctrl else '',
        'eventState': ctrl['event_state'] if ctrl else '',
        'currentAction': ctrl['current_action'] if ctrl else '',
        'nextAction': ctrl['next_action'] if ctrl else '',
        'reasonText': ctrl['reason_text'] if ctrl else '',
        'level': float(st['current_level'] or 0) if st else 0,
        'levelRate': float(st['level_rise_rate'] or 0) if st else 0,
        'updatedAt': ts,
        'timestamp': ts,
        'sequence': seq,
        'source': 'main_program_realtime_state',
        'sync': {'ok': True, 'interval_ms': 1000, 'sequence': seq, 'updatedAt': ts},
        'renderHint': {
            'material_policy': 'preserve_original_material',
            'status_policy': 'overlay_not_replace',
            'refresh_interval_ms': 1000,
            'viewer': 'offline_webgl_pbr_like'
        },
        'pumps': {}, 'pipes': {}, 'meters': {}, 'cameras': {}, 'tanks': {}, 'alarms': []
    }
    try:
        # 水泵：以主程序数据库实时值为唯一来源。
        pumps = self.rows('SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id', (sid,)) if sid else []
        for idx, p in enumerate(pumps, start=1):
            code = str(p['pump_code'] or f'P{idx}')
            status, label = _v5717_status_from_row(self, p)
            run_freq = float(p['frequency'] or 0)
            set_freq = float(p['set_frequency'] or 0)
            current = float(p['current'] or 0)
            voltage = float(p['voltage'] or 0)
            once = _v5717_runtime_once(self, p)
            total = _v5717_runtime_total(self, p)
            item = {
                'code': code,
                'name': p['pump_name'],
                'type': PUMP_TYPE_LABEL.get(p['pump_type'], p['pump_type']),
                'status': status,
                'statusText': label,
                'status_code': status,
                'status_text': label,
                'freq': run_freq,
                'runFreq': run_freq,
                'run_freq': run_freq,
                'frequency': run_freq,
                'setFreq': set_freq,
                'set_freq': set_freq,
                'current': current,
                'current_a': current,
                'voltage': voltage,
                'power': round(current * voltage * 1.732 * 0.85 / 1000, 2),
                'runtimeToday': int(p['run_seconds_today'] or 0),
                'runtimeTotal': int(total),
                'runtimeOnce': int(once),
                'runtime_once_text': _v5717_sec_to_text(once),
                'runtime_total_text': _v5717_sec_to_text(total),
                'updatedAt': ts,
            }
            state['pumps'][code] = item
            # 若模型对象为 P1/P2/P3/P4，而数据库水泵编号不是 P1 格式，则自动增加别名。
            alias = f'P{idx}'
            if alias not in state['pumps']:
                state['pumps'][alias] = dict(item, code=alias, sourceCode=code)

        # 母管/管道。
        pipes = self.rows('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)) if sid else []
        for pipe in pipes:
            code = str(pipe['pipe_code'] or '')
            if not code:
                continue
            flow = float(pipe['measured_flow'] or pipe['estimated_running_flow'] or 0)
            pressure = float(pipe['pressure'] or 0)
            status = 'running' if flow > 0.01 else 'stopped'
            val = {
                'code': code,
                'name': pipe['pipe_name'],
                'status': status,
                'statusText': '有流量' if status == 'running' else '无流量',
                'flow': flow,
                'pressure': pressure,
                'velocity': float(pipe['estimated_velocity'] or 0),
                'dn': pipe['standard_dn'],
                'updatedAt': ts,
            }
            state['pipes'][code] = val
            for alias in _v5717_alias_pipe_code(code):
                state['pipes'][alias] = dict(val, code=alias, sourceCode=code)

        # 仪表。
        instruments = self.rows('SELECT * FROM instrument WHERE station_id=? ORDER BY instrument_type,id',
                                (sid,)) if sid else []
        for ins in instruments:
            code = str(ins['instrument_code'] or '')
            if not code:
                continue
            typ = str(ins['instrument_type'] or '')
            status = 'bypassed' if int(ins['bypassed'] or 0) else str(ins['data_quality'] or 'good')
            item = {
                'code': code,
                'name': ins['instrument_name'],
                'type': typ,
                'status': status,
                'statusText': '屏蔽' if int(ins['bypassed'] or 0) else str(ins['data_quality'] or 'good'),
                'value': float(ins['current_value'] or 0),
                'unit': {'level': 'm', 'flow': 'm³/h', 'pressure': 'MPa', 'current': 'A', 'voltage': 'V',
                         'energy': 'kWh'}.get(typ, ''),
                'updatedAt': ts,
            }
            state['meters'][code] = item

        # 摄像头。
        try:
            for cam in self.rows('SELECT * FROM camera WHERE station_id=? ORDER BY id', (sid,)):
                code = str(cam['camera_code'] or '')
                if code:
                    state['cameras'][code] = {
                        'code': code,
                        'name': cam['camera_name'],
                        'position': cam['camera_position'],
                        'type': cam['camera_type'],
                        'status': 'normal' if int(cam['enabled'] or 0) else 'disabled',
                        'statusText': cam['status'] or ('正常' if int(cam['enabled'] or 0) else '禁用'),
                        'updatedAt': ts,
                    }
        except Exception as e:
            self._log_twin_error('V5.7.17 生成摄像头状态失败', e)

        # 水仓/水箱对象。
        if st:
            state['tanks']['TANK01'] = {
                'code': 'TANK01',
                'name': '水仓/水箱',
                'status': 'normal',
                'statusText': '液位正常',
                'value': float(st['current_level'] or 0),
                'unit': 'm',
                'updatedAt': ts,
            }

        # 最近事件/报警。
        try:
            for ev in self.rows('SELECT * FROM station_control_event WHERE station_id=? ORDER BY id DESC LIMIT 8',
                                (sid,)):
                state['alarms'].append({
                    'time': ev['event_time'],
                    'level': ev['event_level'],
                    'type': ev['event_type'],
                    'device': ev['target_device'],
                    'message': ev['trigger_reason'],
                })
        except Exception:
            pass
    except Exception as e:
        state['sync'] = {'ok': False, 'error': str(e), 'sequence': seq, 'updatedAt': ts}
        state['error'] = str(e)
        self._log_twin_error('V5.7.17 生成实时孪生状态失败', e)

    out = os.path.join(viewer_dir, 'twin_state.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 兼容旧 HTML/旧 HTTP 根目录，避免外部查看器读到旧的示例状态文件。
    try:
        legacy_dir = os.path.join(BASE_DIR, 'twin_viewer')
        os.makedirs(legacy_dir, exist_ok=True)
        legacy_out = os.path.join(legacy_dir, 'twin_state.json')
        if os.path.abspath(legacy_out) != os.path.abspath(out):
            with open(legacy_out, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        self._log_twin_error('V5.7.17 镜像旧路径 twin_state.json 失败', e)
    return out


def _v5717_make_viewer_html(html_text):
    html_text = html_text.replace('隧道泵站自动控制系统 V5.7.16 · 渲染质量修正版',
                                  '隧道泵站自动控制系统 V5.7.17 · 状态同步与专业渲染增强版')
    html_text = html_text.replace(
        '提示：V5.7.16 已保留模型原材质，状态只以轻量色彩叠加、标签和选中高亮表达；点击对象或标签查看详细参数。',
        '提示：V5.7.17 已打通主程序实时状态桥接；每秒读取 twin_state.json，状态超时会提示。模型原材质保留，状态只以轻量叠加、标签和选中高亮表达。')
    html_text = html_text.replace('V5.7.16', 'V5.7.17')
    # 给界面增加同步状态提示条。
    html_text = html_text.replace(
        '<div id="panel"><h3>实时状态 / 点击对象查看</h3><div id="stateBox">等待数据...</div>',
        '<div id="panel"><h3>实时状态 / 点击对象查看</h3><div id="syncBox" class="item">状态同步：等待主程序数据...</div><div id="stateBox">等待数据...</div>')
    old = "async function loadState(){try{state=await(await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'})).json();applyState();updateLabels()}catch(e){console.warn(e)}}"
    new = "async function loadState(){try{let r=await fetch('twin_state.json?ts='+Date.now(),{cache:'no-store'});state=await r.json();state._clientReadAt=Date.now();applyState();updateLabels()}catch(e){console.warn(e);let sb=document.getElementById('syncBox');if(sb)sb.innerHTML='状态同步：读取失败，请确认主程序是否运行 / twin_state.json 是否生成';}}"
    html_text = html_text.replace(old, new)
    old2 = "function applyState(){document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||''}`;"
    new2 = "function applyState(){let sb=document.getElementById('syncBox');let age=0;if(state.updatedAt){let t=Date.parse(String(state.updatedAt).replace(/-/g,'/'));if(!isNaN(t))age=(Date.now()-t)/1000;}let stale=age>5; if(sb)sb.innerHTML=`状态同步：${stale?'超时':'正常'}　序号：${state.sequence||'-'}　更新时间：${state.updatedAt||'-'}　${stale?'请检查主程序是否还在刷新':''}`;document.getElementById('stationLine').textContent=`${state.station||''} ${state.stationName||''} | ${state.controlModeText||state.controlMode||''} | ${state.controlState||''} | 液位 ${num(state.level,2)} m | 速率 ${num(state.levelRate,3)} m/min | ${state.updatedAt||''}`;"
    html_text = html_text.replace(old2, new2)
    return html_text


def _v5717_prepare_twin_web_model(self, path):
    try:
        source = self._resolve_twin_model_path(path)
        target, rel, cfg = self._copy_twin_model_to_safe_store(source)
        sid = cfg.get('station_id') or self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        try:
            self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
        except Exception as e:
            self._log_twin_error('V5.7.17 生成绑定表失败', e, target)
        viewer_dir = self._twin_viewer_dir()
        model_url = '/' + rel.replace('\\', '/')
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        html_text = _v5717_make_viewer_html(_V5716_OFFLINE_HTML_TEMPLATE).replace('__MODEL__', model_url)
        html_text = html_text.replace('正在加载 GLB 模型...',
                                      '正在加载 GLB 模型...\n模型路径：' + model_url + '\n状态文件：/twin_viewer/twin_state.json')
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        log = self._log_twin_error('V5.7.17 GLB查看器准备失败', e, path)
        messagebox.showwarning('GLB查看器准备失败',
                               '三维模型加载前检查失败。\n\n'
                               '可能原因：模型被占用、路径无权限、文件损坏，或旧版本路径仍在数据库中。\n\n'
                               '详细日志：\n' + (log or '未能写入日志') + '\n\n错误：\n' + str(e))
        return None


def _v5717_sync_twin_state_once(self):
    try:
        sid = self.twin_sid() if hasattr(self, 'twin_station_var') else self.sid()
    except Exception:
        sid = self.sid()
    if not sid:
        return
    try:
        self._write_twin_state_json(sid)
    except Exception as e:
        try:
            self._log_twin_error('V5.7.17 周期同步 twin_state.json 失败', e)
        except Exception:
            pass


def _v5717_periodic(self):
    # 复用原周期刷新逻辑，再额外把同一份实时状态同步给三维查看器。
    try:
        _V5717_OLD_PERIODIC(self)
    finally:
        try:
            self._sync_twin_state_once()
        except Exception:
            pass


def _v5717_refresh_twin_scene(self):
    try:
        self._sync_twin_state_once()
        # 当前页已打开 WebView 时无需重建，只刷新状态文件；外部/内嵌页面会每秒读取。
        if hasattr(self, 'twin_info'):
            self.twin_info.delete('1.0', 'end')
            sid = self.twin_sid() or self.sid()
            out = os.path.join(self._twin_viewer_dir(), 'twin_state.json')
            self.twin_info.insert('end', 'V5.7.17 状态同步检查\n')
            self.twin_info.insert('end', '当前泵站ID：{}\n'.format(sid))
            self.twin_info.insert('end', '状态文件：{}\n'.format(out))
            self.twin_info.insert('end', '同步序号：{}\n'.format(getattr(self, '_twin_state_sequence', '-')))
            self.twin_info.insert('end',
                                  '说明：主程序每秒把泵状态/频率/电流写入 twin_state.json；三维查看器每秒读取一次。\n')
    except Exception as e:
        self._log_twin_error('V5.7.17 手动刷新孪生状态失败', e)


# 应用 V5.7.17 最终覆盖。
App._write_twin_state_json = _v5717_write_twin_state_json
App._prepare_twin_web_model = _v5717_prepare_twin_web_model
App._sync_twin_state_once = _v5717_sync_twin_state_once
App.periodic = _v5717_periodic
App.refresh_twin_scene = _v5717_refresh_twin_scene

# V5.7.18 TwinRenderPBRPro
# 目标：继续提升数字孪生 GLB 渲染效果，尽量接近专业 3D 查看器：PBR 金属/粗糙度、环境反射模拟、贴图 sRGB、透明/自发光材质、状态不覆盖原材质。
_V5718_VERSION = 'V5.7.18_TwinRenderPBRPro'


def _v5718_template_path():
    return os.path.join(BASE_DIR, 'templates', 'twin_viewer_pbrpro.html')


def _v5718_write_twin_state_json(self, sid=None):
    # 继续复用 V5.7.17 的每秒状态同步与双路径镜像逻辑，只增加渲染提示信息。
    out = _v5717_write_twin_state_json(self, sid)
    try:
        with open(out, 'r', encoding='utf-8') as f:
            state = json.load(f)
        state['version'] = _V5718_VERSION
        state['renderHint'] = {
            'viewer': 'offline_webgl_pbr_pro',
            'material_policy': 'preserve_original_pbr_material',
            'status_policy': 'outline_label_light_overlay_not_replace_material',
            'features': [
                'baseColorTexture_sRGB',
                'metallicFactor',
                'roughnessFactor',
                'emissiveFactor',
                'alphaMode_light_support',
                'doubleSided_no_culling',
                'procedural_HDR_environment_reflection',
                'ACES_like_tonemapping',
                'one_second_state_refresh'
            ],
            'refresh_interval_ms': 1000
        }
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        # 同步镜像旧路径，避免外部查看器仍读取旧 twin_viewer/twin_state.json。
        try:
            legacy_dir = os.path.join(BASE_DIR, 'twin_viewer')
            os.makedirs(legacy_dir, exist_ok=True)
            with open(os.path.join(legacy_dir, 'twin_state.json'), 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    except Exception as e:
        try:
            self._log_twin_error('V5.7.18 写入PBR渲染提示失败', e)
        except Exception:
            pass
    return out


def _v5718_prepare_twin_web_model(self, path):
    try:
        source = self._resolve_twin_model_path(path)
        target, rel, cfg = self._copy_twin_model_to_safe_store(source)
        sid = cfg.get('station_id') or self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        try:
            self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
        except Exception as e:
            self._log_twin_error('V5.7.18 生成绑定表失败', e, target)
        viewer_dir = self._twin_viewer_dir()
        model_url = '/' + rel.replace('\\', '/')
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        tpl_path = _v5718_template_path()
        if os.path.exists(tpl_path):
            with open(tpl_path, 'r', encoding='utf-8') as f:
                html_text = f.read()
        else:
            html_text = _V5716_OFFLINE_HTML_TEMPLATE
            html_text = html_text.replace('隧道泵站自动控制系统 V5.7.16 · 渲染质量修正版',
                                          '隧道泵站自动控制系统 V5.7.18 · PBR专业渲染增强版')
        html_text = html_text.replace('__MODEL__', model_url)
        html_text = html_text.replace('正在加载 GLB 模型...',
                                      '正在加载 GLB 模型...\n模型路径：' + model_url + '\n状态文件：/twin_viewer/twin_state.json\n渲染模式：V5.7.18 PBRPro')
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        log = self._log_twin_error('V5.7.18 PBRPro GLB查看器准备失败', e, path)
        messagebox.showwarning('GLB查看器准备失败',
                               '三维模型加载前检查失败。\n\n'
                               '可能原因：模型被占用、路径无权限、文件损坏，或旧版本路径仍在数据库中。\n\n'
                               '详细日志：\n' + (log or '未能写入日志') + '\n\n错误：\n' + str(e))
        return None


# 最终覆盖：保证 V5.7.18 的 PBR 专业渲染增强和 V5.7.17 状态同步同时生效。
App._write_twin_state_json = _v5718_write_twin_state_json
App._prepare_twin_web_model = _v5718_prepare_twin_web_model

# V5.7.22 TwinContrastLightFix
# 目标：在 V5.7.18 PBRPro 基础上继续增强数字孪生显示效果：离线 HDR 环境贴图、阴影地台、故障/选中轮廓描边，同时保留 V5.7.17 的实时状态同步。
_V5719_VERSION = 'V5.7.25_TwinStateHighlightPro'


def _v5719_template_path():
    return os.path.join(BASE_DIR, 'templates', 'twin_viewer_hdrpro.html')


def _v5719_install_viewer_assets(self):
    """把离线环境贴图复制到运行期 twin_viewer 目录，保证客户电脑无外网也能加载。"""
    try:
        viewer_dir = self._twin_viewer_dir()
        env_dir = os.path.join(viewer_dir, 'assets', 'env')
        os.makedirs(env_dir, exist_ok=True)
        src = os.path.join(BASE_DIR, 'templates', 'assets', 'env', 'industrial_hdr_env.png')
        dst = os.path.join(env_dir, 'industrial_hdr_env.png')
        if os.path.isfile(src):
            if (not os.path.isfile(dst)) or os.path.getsize(src) != os.path.getsize(dst):
                shutil.copy2(src, dst)
        return dst
    except Exception as e:
        try:
            self._log_twin_error('V5.7.25 复制环境贴图失败', e)
        except Exception:
            pass
        return ''


def _v5719_write_twin_state_json(self, sid=None):
    out = _v5718_write_twin_state_json(self, sid)
    try:
        with open(out, 'r', encoding='utf-8') as f:
            state = json.load(f)
        state['version'] = _V5719_VERSION
        state['renderHint'] = {
            'viewer': 'offline_webgl_hdr_pbr_outline_pro',
            'material_policy': 'preserve_original_pbr_material',
            'status_policy': 'outline_label_light_overlay_not_replace_material',
            'features': [
                'offline_industrial_HDR_environment_map_png',
                'environment_reflection_sampled_by_normal',
                'shadow_ground_platform',
                'soft_under_model_shadow',
                'fault_maintenance_selected_outline',
                'baseColorTexture_sRGB',
                'metallicFactor',
                'roughnessFactor',
                'emissiveFactor',
                'alphaMode_light_support',
                'doubleSided_no_culling',
                'ACES_like_tonemapping',
                'one_second_state_refresh'
            ],
            'refresh_interval_ms': 1000
        }
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        try:
            legacy_dir = os.path.join(BASE_DIR, 'twin_viewer')
            os.makedirs(legacy_dir, exist_ok=True)
            with open(os.path.join(legacy_dir, 'twin_state.json'), 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    except Exception as e:
        try:
            self._log_twin_error('V5.7.25 写入状态高亮增强提示失败', e)
        except Exception:
            pass
    return out


def _v5719_prepare_twin_web_model(self, path):
    try:
        source = self._resolve_twin_model_path(path)
        target, rel, cfg = self._copy_twin_model_to_safe_store(source)
        sid = cfg.get('station_id') or self.twin_sid() or self.sid()
        self._write_twin_state_json(sid)
        self._v5719_install_viewer_assets()
        try:
            self._write_binding_files(self._generate_twin_binding_dict(target), show_message=False)
        except Exception as e:
            self._log_twin_error('V5.7.25 生成绑定表失败', e, target)
        viewer_dir = self._twin_viewer_dir()
        model_url = '/' + rel.replace('\\', '/')
        html = os.path.join(viewer_dir, 'twin_viewer.html')
        tpl_path = _v5719_template_path()
        if os.path.exists(tpl_path):
            with open(tpl_path, 'r', encoding='utf-8') as f:
                html_text = f.read()
        else:
            html_text = _V5716_OFFLINE_HTML_TEMPLATE
            html_text = html_text.replace('隧道泵站自动控制系统 V5.7.16 · 渲染质量修正版',
                                          '隧道泵站自动控制系统 V5.7.25 · 状态高亮增强版')
        html_text = html_text.replace('__MODEL__', model_url)
        html_text = html_text.replace('正在加载 GLB 模型...',
                                      '正在加载 GLB 模型...\n模型路径：' + model_url + '\n状态文件：/twin_viewer/twin_state.json\n渲染模式：V5.7.25 StateHighlightPro\n增强：HDR环境贴图 + 阴影地台 + 轮廓描边')
        with open(html, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return html
    except Exception as e:
        log = self._log_twin_error('V5.7.25 StateHighlightPro GLB查看器准备失败', e, path)
        messagebox.showwarning('GLB查看器准备失败',
                               '三维模型加载前检查失败。\n\n'
                               '可能原因：模型被占用、路径无权限、文件损坏，或旧版本路径仍在数据库中。\n\n'
                               '详细日志：\n' + (log or '未能写入日志') + '\n\n错误：\n' + str(e))
        return None


def _v5719_model_status_check(self):
    _v5714_model_status_check(self)
    try:
        self._sync_twin_state_once()
        out = os.path.join(self._twin_viewer_dir(), 'twin_state.json')
        data = {}
        try:
            with open(out, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
        self._v5719_install_viewer_assets()
        if hasattr(self, 'twin_info'):
            for code, p in list(data.get('pumps', {}).items())[:6]:
                self.twin_info.insert('end', '   {}：{}  频率 {:.1f}Hz  电流 {:.1f}A\n'.format(code, p.get(
                    'statusText') or p.get('status'), float(p.get('freq') or 0), float(p.get('current') or 0)))
            self.twin_info.insert('end', '\n\nV5.7.25 状态高亮增强渲染检查：\n')
            self.twin_info.insert('end', '1. 已加入离线工业 HDR 环境贴图：assets/env/industrial_hdr_env.png。\n')
            self.twin_info.insert('end', '2. 已加入阴影地台和模型底部柔和投影，增强模型落地感。\n')
            self.twin_info.insert('end', '3. 已加入故障、检修、屏蔽、选中对象轮廓描边。\n')
            self.twin_info.insert('end', '4. 模型本体仍保留原 GLB 材质，状态不再覆盖原始材质。\n')
            self.twin_info.insert('end', '5. 三维查看器顶部可单独开关：HDR环境、阴影地台、轮廓描边。\n')
            self.twin_info.insert('end', '6. 状态同步链路沿用 V5.7.17/V5.7.18，每秒刷新 twin_state.json。\n')
    except Exception:
        pass


App._v5719_install_viewer_assets = _v5719_install_viewer_assets
App._write_twin_state_json = _v5719_write_twin_state_json
App._prepare_twin_web_model = _v5719_prepare_twin_web_model
App.model_status_check = _v5719_model_status_check
