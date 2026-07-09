import os, sqlite3, datetime, csv, threading

APP_TITLE = '隧道泵站自动控制系统 V5.7.25_TwinStateHighlightPro'
COPYRIGHT = '山西河海科技有限公司'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pump_station.db')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')

PUMP_TYPES = [('submersible','潜污泵'), ('centrifugal','多级离心泵'), ('feed','给水泵')]
STATION_TYPES = ['隧道排水','污水','清水','施工临排']
CONTROL_MODES = [('manual','手动'), ('auto','自动')]


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class Database:
    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        os.makedirs(REPORT_DIR, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()
        self.ensure_seed()

    def _commit(self):
        try:
            self.conn.commit()
        except sqlite3.OperationalError as e:
            # 多线程模拟采集和界面操作同时写库时，SQLite 偶发返回该提示。
            # 这里使用全局锁后一般不会出现；若出现且没有活动事务，忽略即可。
            if 'no transaction is active' not in str(e):
                raise

    def execute(self, sql, params=()):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(sql, params)
            self._commit()
            return cur

    def executemany(self, sql, seq):
        with self.lock:
            cur = self.conn.cursor()
            cur.executemany(sql, seq)
            self._commit()
            return cur

    def query(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def one(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params).fetchone()

    def init_schema(self):
        c = self.conn.cursor()
        c.executescript('''
        CREATE TABLE IF NOT EXISTS twin_model_asset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,     
            file_path TEXT NOT NULL,
            preview_path TEXT,
            version TEXT DEFAULT '1.0',
            is_active INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            node_count INTEGER DEFAULT 0,
            remark TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(station_id,model_name)
        );
        CREATE TABLE IF NOT EXISTS twin_model_node (
        
            id INTEGER PRIMARY KEY AUTOINCREMENT,
        
            model_id INTEGER NOT NULL,
        
            node_name TEXT NOT NULL,
        
            node_path TEXT,
        
            parent_name TEXT,
        
            node_type TEXT,
            depth INTEGER DEFAULT 0,
            visible INTEGER DEFAULT 1,
        
            created_at TEXT
        
        );
        CREATE INDEX IF NOT EXISTS idx_twin_node_model ON twin_model_node(model_id);
        CREATE TABLE IF NOT EXISTS twin_node_binding (

            id INTEGER PRIMARY KEY AUTOINCREMENT,
        
            station_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            node_name TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id INTEGER,
            object_code TEXT,
            role TEXT DEFAULT 'body',
            clickable INTEGER DEFAULT 1,
            animation_type TEXT DEFAULT 'none',
            highlight_rule TEXT DEFAULT 'status',
            visible INTEGER DEFAULT 1,
            remark TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_twin_binding_station
        ON twin_node_binding(station_id);
        CREATE TABLE IF NOT EXISTS twin_hotspot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            object_type TEXT,
            object_id INTEGER,
            node_name TEXT,
            position_x REAL DEFAULT 0,
            position_y REAL DEFAULT 0,
            position_z REAL DEFAULT 0,
            icon TEXT,
            visible INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS twin_camera_bookmark (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position_x REAL NOT NULL,
            position_y REAL NOT NULL,
            position_z REAL NOT NULL,
            target_x REAL NOT NULL,
            target_y REAL NOT NULL,
            target_z REAL NOT NULL,
            fov REAL DEFAULT 45,
            sort_order INTEGER DEFAULT 0,
            is_default INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS system_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            software_name TEXT, software_version TEXT, copyright_owner TEXT, build_time TEXT, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT NOT NULL UNIQUE,
            config_value TEXT,
            value_type TEXT DEFAULT 'string',
            config_group TEXT,
            description TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS pump_station (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_code TEXT NOT NULL UNIQUE,
            station_name TEXT NOT NULL,
            station_type TEXT DEFAULT '隧道排水',
            enabled INTEGER DEFAULT 1,
            control_mode TEXT DEFAULT 'manual',
            pump_count INTEGER DEFAULT 4,
            pipe_count INTEGER DEFAULT 1,
            level_sensor_count INTEGER DEFAULT 2,
            min_running_count INTEGER DEFAULT 1,
            max_running_count INTEGER DEFAULT 3,
            emergency_max_running_count INTEGER DEFAULT 3,
            data_source_mode TEXT DEFAULT 'simulation',
            current_level REAL DEFAULT 0,
            level_rise_rate REAL DEFAULT 0,
            emergency_level TEXT DEFAULT '无',
            default_pump_type TEXT DEFAULT 'submersible',
            default_rated_flow REAL DEFAULT 300,
            default_rated_head REAL DEFAULT 60,
            default_rated_power REAL DEFAULT 55,
            default_rated_current REAL DEFAULT 100,
            created_at TEXT, updated_at TEXT, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS pump (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            pump_code TEXT NOT NULL,
            pump_name TEXT NOT NULL,
            pump_type TEXT NOT NULL DEFAULT 'submersible',
            enabled INTEGER DEFAULT 1,
            auto_enable INTEGER DEFAULT 1,
            emergency_enable INTEGER DEFAULT 1,
            standby INTEGER DEFAULT 0,
            maintenance INTEGER DEFAULT 0,
            manual_fault INTEGER DEFAULT 0,
            disabled INTEGER DEFAULT 0,
            rated_power REAL DEFAULT 0,
            rated_current REAL DEFAULT 100,
            rated_voltage REAL DEFAULT 380,
            rated_flow REAL DEFAULT 300,
            rated_head REAL DEFAULT 60,
            rated_frequency REAL DEFAULT 50,
            min_frequency REAL DEFAULT 30,
            max_frequency REAL DEFAULT 50,
            start_frequency REAL DEFAULT 30,
            flow_correction_factor REAL DEFAULT 0.95,
            feed_pump_id INTEGER,
            run_feedback INTEGER DEFAULT 0,
            fault_feedback INTEGER DEFAULT 0,
            current REAL DEFAULT 0,
            voltage REAL DEFAULT 380,
            frequency REAL DEFAULT 0,
            set_frequency REAL DEFAULT 0,
            energy REAL DEFAULT 0,
            run_seconds_today INTEGER DEFAULT 0,
            run_seconds_total INTEGER DEFAULT 0,
            start_count INTEGER DEFAULT 0,
            stop_count INTEGER DEFAULT 0,
            fault_count INTEGER DEFAULT 0,
            display_order INTEGER DEFAULT 0,
            created_at TEXT, updated_at TEXT, remark TEXT,
            UNIQUE(station_id,pump_code)
        );
        CREATE TABLE IF NOT EXISTS main_pipe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            pipe_code TEXT NOT NULL,
            pipe_name TEXT NOT NULL,
            standard_dn TEXT DEFAULT 'DN400',
            dn_value INTEGER DEFAULT 400,
            inner_diameter_mm REAL DEFAULT 400,
            pipe_material TEXT DEFAULT '钢管',
            pipe_length_m REAL DEFAULT 0,
            theoretical_flow REAL DEFAULT 0,
            corrected_theoretical_flow REAL DEFAULT 0,
            estimated_running_flow REAL DEFAULT 0,
            estimated_velocity REAL DEFAULT 0,
            measured_flow REAL DEFAULT 0,
            pressure REAL DEFAULT 0,
            diameter_check_status TEXT DEFAULT '未校核',
            show_in_model INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT, updated_at TEXT, remark TEXT,
            UNIQUE(station_id,pipe_code)
        );
        CREATE TABLE IF NOT EXISTS pump_pipe_relation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            pump_id INTEGER NOT NULL,
            pipe_id INTEGER NOT NULL,
            relation_type TEXT DEFAULT 'main_drain',
            enabled INTEGER DEFAULT 1,
            UNIQUE(pump_id,pipe_id,relation_type)
        );
        CREATE TABLE IF NOT EXISTS instrument (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            pipe_id INTEGER,
            pump_id INTEGER,
            instrument_code TEXT NOT NULL,
            instrument_name TEXT NOT NULL,
            instrument_type TEXT NOT NULL,
            owner_type TEXT DEFAULT 'station',
            owner_id INTEGER,
            instant_point_id INTEGER,
            total_point_id INTEGER,
            power_point_id INTEGER,
            voltage_point_id INTEGER,
            current_point_id INTEGER,
            correction_factor REAL DEFAULT 1.0,
            report_priority INTEGER DEFAULT 1,
            enabled INTEGER DEFAULT 1,
            bypassed INTEGER DEFAULT 0,
            control_enable INTEGER DEFAULT 1,
            alarm_enable INTEGER DEFAULT 1,
            report_enable INTEGER DEFAULT 1,
            data_quality TEXT DEFAULT 'good',
            data_source TEXT DEFAULT 'measured',
            current_value REAL DEFAULT 0,
            min_valid_value REAL DEFAULT 0,
            max_valid_value REAL DEFAULT 999999,
            abnormal_timeout INTEGER DEFAULT 60,
            created_at TEXT, updated_at TEXT, remark TEXT,
            UNIQUE(station_id,instrument_code)
        );
        CREATE TABLE IF NOT EXISTS modbus_device (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER,
            device_code TEXT NOT NULL UNIQUE,
            device_name TEXT NOT NULL,
            device_type TEXT DEFAULT 'PLC',
            ip_address TEXT DEFAULT '192.168.1.10',
            port INTEGER DEFAULT 502,
            slave_id INTEGER DEFAULT 1,
            timeout_ms INTEGER DEFAULT 3000,
            poll_interval_ms INTEGER DEFAULT 1000,
            enabled INTEGER DEFAULT 1,
            communication_status TEXT DEFAULT 'online',
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS modbus_point (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER,
            station_id INTEGER,
            object_type TEXT,
            object_id INTEGER,
            object_code TEXT,
            point_code TEXT NOT NULL UNIQUE,
            point_name TEXT NOT NULL,
            point_category TEXT,
            data_code TEXT,
            point_usage TEXT DEFAULT 'analog',
            status_true_value REAL DEFAULT 1,
            status_false_value REAL DEFAULT 0,
            function_code INTEGER DEFAULT 3,
            register_address INTEGER DEFAULT 0,
            register_count INTEGER DEFAULT 2,
            bit_index INTEGER,
            data_type TEXT DEFAULT 'float32',
            byte_order TEXT DEFAULT 'ABCD',
            scale REAL DEFAULT 1.0,
            offset_value REAL DEFAULT 0,
            unit TEXT,
            decimal_places INTEGER DEFAULT 2,
            read_write TEXT DEFAULT 'read_write',
            command_start_value TEXT DEFAULT '1',
            command_stop_value TEXT DEFAULT '5',
            command_value TEXT,
            poll_interval_ms INTEGER DEFAULT 1000,
            enabled INTEGER DEFAULT 1,
            bypassed INTEGER DEFAULT 0,
            alarm_high REAL,
            alarm_low REAL,
            quality TEXT DEFAULT 'good',
            last_value TEXT DEFAULT '0',
            last_update_time TEXT,
            remark TEXT
        );



        CREATE TABLE IF NOT EXISTS twin_model (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL UNIQUE,
            model_name TEXT,
            model_path TEXT,
            model_type TEXT DEFAULT 'glb',
            enabled INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS camera (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            camera_code TEXT NOT NULL,
            camera_name TEXT NOT NULL,
            camera_position TEXT,
            camera_type TEXT DEFAULT 'RTSP',
            ip_address TEXT,
            port INTEGER DEFAULT 554,
            username TEXT,
            password TEXT,
            rtsp_url TEXT,
            onvif_url TEXT,
            enabled INTEGER DEFAULT 0,
            record_enabled INTEGER DEFAULT 0,
            snapshot_enabled INTEGER DEFAULT 1,
            status TEXT DEFAULT '未启用',
            last_frame_time TEXT,
            created_at TEXT,
            updated_at TEXT,
            remark TEXT,
            UNIQUE(station_id,camera_code)
        );
        CREATE TABLE IF NOT EXISTS forward_driver_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enabled INTEGER DEFAULT 0,
            bind_ip TEXT DEFAULT '0.0.0.0',
            port INTEGER DEFAULT 1502,
            slave_id INTEGER DEFAULT 1,
            register_area TEXT DEFAULT '4区-保持寄存器',
            start_address INTEGER DEFAULT 40001,
            byte_order TEXT DEFAULT 'ABCD',
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS parameter_value (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            scope_id INTEGER NOT NULL,
            param_group TEXT NOT NULL,
            param_code TEXT NOT NULL,
            param_name TEXT NOT NULL,
            param_value TEXT NOT NULL,
            value_type TEXT DEFAULT 'real',
            unit TEXT,
            min_value TEXT,
            max_value TEXT,
            updated_at TEXT,
            remark TEXT,
            UNIQUE(scope_type,scope_id,param_group,param_code)
        );
        CREATE TABLE IF NOT EXISTS operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_time TEXT, operation_type TEXT, object_type TEXT, object_id INTEGER,
            object_name TEXT, before_value TEXT, after_value TEXT, result TEXT, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS fault_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fault_code TEXT, station_id INTEGER, object_type TEXT, object_id INTEGER, device_name TEXT,
            fault_type TEXT, fault_name TEXT, fault_level TEXT, fault_source TEXT,
            start_time TEXT, end_time TEXT, duration_seconds INTEGER DEFAULT 0, recovered INTEGER DEFAULT 0,
            confirmed INTEGER DEFAULT 0, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS emergency_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT, station_id INTEGER, start_time TEXT, end_time TEXT, duration_seconds INTEGER DEFAULT 0,
            trigger_reason TEXT, emergency_level TEXT, max_level REAL DEFAULT 0, max_level_rise_rate REAL DEFAULT 0,
            before_running_count INTEGER DEFAULT 0, max_running_count INTEGER DEFAULT 0, added_pump_count INTEGER DEFAULT 0,
            max_frequency REAL DEFAULT 0, result TEXT, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS pump_run_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            pump_id INTEGER NOT NULL,
            pump_code TEXT,
            pump_name TEXT,
            pump_type TEXT,
            start_time TEXT,
            end_time TEXT,
            start_date TEXT,
            start_month TEXT,
            duration_seconds INTEGER DEFAULT 0,
            start_mode TEXT,
            stop_mode TEXT,
            start_frequency REAL DEFAULT 0,
            stop_frequency REAL DEFAULT 0,
            start_energy REAL DEFAULT 0,
            end_energy REAL DEFAULT 0,
            energy_delta REAL DEFAULT 0,
            start_source TEXT,
            stop_source TEXT,
            result TEXT DEFAULT 'running',
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS runtime_sample (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_time TEXT NOT NULL,
            sample_date TEXT NOT NULL,
            sample_month TEXT NOT NULL,
            station_id INTEGER NOT NULL,
            sample_type TEXT NOT NULL,
            pump_id INTEGER,
            pipe_id INTEGER,
            instrument_id INTEGER,
            device_code TEXT,
            device_name TEXT,
            run_status INTEGER DEFAULT 0,
            flow_value REAL DEFAULT 0,
            pressure_value REAL DEFAULT 0,
            current_value REAL DEFAULT 0,
            voltage_value REAL DEFAULT 0,
            frequency_value REAL DEFAULT 0,
            power_value REAL DEFAULT 0,
            energy_value REAL DEFAULT 0,
            level_value REAL DEFAULT 0,
            emergency_level TEXT,
            data_source TEXT DEFAULT 'simulated',
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS station_control_state (
            station_id INTEGER PRIMARY KEY,
            control_mode TEXT,
            control_state TEXT DEFAULT '未知',
            event_state TEXT DEFAULT '无事件',
            adopted_level REAL DEFAULT 0,
            level_rate REAL DEFAULT 0,
            running_pump_count INTEGER DEFAULT 0,
            standby_pump_count INTEGER DEFAULT 0,
            fault_pump_count INTEGER DEFAULT 0,
            maintenance_pump_count INTEGER DEFAULT 0,
            avg_frequency REAL DEFAULT 0,
            current_action TEXT,
            next_action TEXT,
            reason_text TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS station_control_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            event_time TEXT,
            event_type TEXT,
            event_level TEXT DEFAULT 'info',
            control_state TEXT,
            trigger_reason TEXT,
            action_type TEXT,
            target_device TEXT,
            result TEXT DEFAULT '记录',
            remark TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_station_control_event ON station_control_event(station_id,event_time);
        CREATE INDEX IF NOT EXISTS idx_runtime_sample_date ON runtime_sample(station_id,sample_date,sample_type);
        CREATE INDEX IF NOT EXISTS idx_runtime_sample_month ON runtime_sample(station_id,sample_month,sample_type);
        CREATE INDEX IF NOT EXISTS idx_pump_run_record_date ON pump_run_record(station_id,start_date,pump_id);
        ''')
        self.conn.commit()
        self.migrate_schema()

    def migrate_schema(self):
        """Upgrade old test databases without requiring a full reset."""
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(instrument)").fetchall()]
        add_cols = {
            'owner_type': "TEXT DEFAULT 'station'",
            'owner_id': "INTEGER",
            'instant_point_id': "INTEGER",
            'total_point_id': "INTEGER",
            'power_point_id': "INTEGER",
            'voltage_point_id': "INTEGER",
            'current_point_id': "INTEGER",
            'correction_factor': "REAL DEFAULT 1.0",
            'report_priority': "INTEGER DEFAULT 1"
        }
        for name, spec in add_cols.items():
            if name not in cols:
                self.conn.execute(f"ALTER TABLE instrument ADD COLUMN {name} {spec}")
        # Add station default-generation fields to old test databases.
        st_cols = [r[1] for r in self.conn.execute("PRAGMA table_info(pump_station)").fetchall()]
        station_add_cols = {
            'default_pump_type': "TEXT DEFAULT 'submersible'",
            'default_rated_flow': "REAL DEFAULT 300",
            'default_rated_head': "REAL DEFAULT 60",
            'default_rated_power': "REAL DEFAULT 55",
            'default_rated_current': "REAL DEFAULT 100",
            'data_source_mode': "TEXT DEFAULT 'simulation'"
        }
        for name, spec in station_add_cols.items():
            if name not in st_cols:
                self.conn.execute(f"ALTER TABLE pump_station ADD COLUMN {name} {spec}")

        # Add Modbus point communication/control fields to old test databases.
        pt_cols = [r[1] for r in self.conn.execute("PRAGMA table_info(modbus_point)").fetchall()]
        point_add_cols = {
            'byte_order': "TEXT DEFAULT 'ABCD'",
            'command_start_value': "TEXT DEFAULT '1'",
            'command_stop_value': "TEXT DEFAULT '3'",
            'command_value': "TEXT",
            'bypassed': "INTEGER DEFAULT 0",
            'point_usage': "TEXT DEFAULT 'analog'",
            'status_true_value': "REAL DEFAULT 1",
            'status_false_value': "REAL DEFAULT 0"
        }
        for name, spec in point_add_cols.items():
            if name not in pt_cols:
                self.conn.execute(f"ALTER TABLE modbus_point ADD COLUMN {name} {spec}")
        # V5.7.2：变量点位允许现场修改功能码、地址、数据类型、寄存器数量、字节序和读写类型。
        # 因此启动/迁移时不再强制把所有点位改回 4区/float32/40001递增，只补齐空字段。
        self.conn.execute("UPDATE modbus_point SET data_type=COALESCE(NULLIF(data_type,''),'float32'), register_count=COALESCE(NULLIF(register_count,0),2), function_code=COALESCE(NULLIF(function_code,0),3), byte_order=COALESCE(NULLIF(byte_order,''),'ABCD'), read_write=COALESCE(NULLIF(read_write,''),'read_write'), command_stop_value=COALESCE(NULLIF(command_stop_value,''),'5')")
        self.conn.execute("UPDATE modbus_point SET point_usage='状态量' WHERE (point_usage IS NULL OR point_usage='' OR point_usage='analog') AND (point_code LIKE '%_RUN_FB' OR point_code LIKE '%_FAULT_FB' OR point_code LIKE '%_STOP_FB' OR point_code LIKE '%_MAINT%')")
        self.conn.execute("UPDATE modbus_point SET point_usage='控制指令', command_value=COALESCE(NULLIF(command_value,''),'1') WHERE (point_usage IS NULL OR point_usage='' OR point_usage='analog') AND point_code LIKE '%_START_CMD'")
        self.conn.execute("UPDATE modbus_point SET point_usage='控制指令', command_value=COALESCE(NULLIF(command_value,''),'5') WHERE (point_usage IS NULL OR point_usage='' OR point_usage='analog') AND point_code LIKE '%_STOP_CMD'")
        self.conn.execute("UPDATE modbus_point SET point_usage='频率设定' WHERE (point_usage IS NULL OR point_usage='' OR point_usage='analog') AND point_code LIKE '%_FREQ_SET'")
        self.conn.execute("INSERT INTO forward_driver_config(id,enabled,bind_ip,port,slave_id,register_area,start_address,byte_order,remark) SELECT 1,0,'0.0.0.0',1502,1,'4区-保持寄存器',40001,'ABCD','上级系统转发驱动默认配置' WHERE NOT EXISTS(SELECT 1 FROM forward_driver_config WHERE id=1)")
        # Backfill owner relation for older records.
        self.conn.execute("UPDATE instrument SET owner_type='pipe', owner_id=pipe_id WHERE instrument_type IN ('flow','pressure') AND pipe_id IS NOT NULL AND (owner_type IS NULL OR owner_type='station')")
        self.conn.execute("UPDATE instrument SET owner_type='pump', owner_id=pump_id WHERE instrument_type IN ('current','voltage') AND pump_id IS NOT NULL")
        self.conn.execute("UPDATE instrument SET owner_type='station', owner_id=station_id WHERE instrument_type IN ('level','energy') AND (owner_id IS NULL OR owner_id=0)")
        self.conn.execute("UPDATE pump_station SET control_mode='manual' WHERE control_mode NOT IN ('manual','auto') OR control_mode IS NULL OR control_mode=''")
        self.conn.execute("UPDATE pump_station SET data_source_mode='simulation' WHERE data_source_mode IS NULL OR data_source_mode=''")
        self.conn.execute("UPDATE pump_station SET data_source_mode='simulation' WHERE data_source_mode IN ('模拟','模拟数据','仿真')")
        self.conn.execute("UPDATE pump_station SET data_source_mode='realtime' WHERE data_source_mode IN ('实时采集','实际采集','真实采集')")
        self.conn.execute("UPDATE pump_station SET data_source_mode='simulation' WHERE data_source_mode NOT IN ('simulation','realtime')")
        # =================================================
        # V5.8 数字孪生数据库迁移
        # =================================================

        # 老版本不存在时创建孪生资产表

        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS twin_model_asset
                          (

                              id
                              INTEGER
                              PRIMARY
                              KEY
                              AUTOINCREMENT,

                              station_id
                              INTEGER
                              NOT
                              NULL,

                              model_name
                              TEXT
                              NOT
                              NULL,

                              file_path
                              TEXT
                              NOT
                              NULL,

                              preview_path
                              TEXT,

                              version
                              TEXT
                              DEFAULT
                              '1.0',

                              is_active
                              INTEGER
                              DEFAULT
                              0,

                              file_size
                              INTEGER
                              DEFAULT
                              0,

                              node_count
                              INTEGER
                              DEFAULT
                              0,

                              remark
                              TEXT,

                              created_at
                              TEXT,

                              updated_at
                              TEXT

                          )
                          """)

        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS twin_model_node
                          (

                              id
                              INTEGER
                              PRIMARY
                              KEY
                              AUTOINCREMENT,

                              model_id
                              INTEGER
                              NOT
                              NULL,

                              node_name
                              TEXT
                              NOT
                              NULL,

                              node_path
                              TEXT,

                              parent_name
                              TEXT,

                              node_type
                              TEXT,

                              depth
                              INTEGER
                              DEFAULT
                              0,

                              visible
                              INTEGER
                              DEFAULT
                              1,

                              created_at
                              TEXT

                          )
                          """)

        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS twin_node_binding
                          (

                              id
                              INTEGER
                              PRIMARY
                              KEY
                              AUTOINCREMENT,

                              station_id
                              INTEGER
                              NOT
                              NULL,

                              model_id
                              INTEGER
                              NOT
                              NULL,

                              node_name
                              TEXT
                              NOT
                              NULL,

                              object_type
                              TEXT
                              NOT
                              NULL,

                              object_id
                              INTEGER,

                              object_code
                              TEXT,

                              role
                              TEXT
                              DEFAULT
                              'body',

                              clickable
                              INTEGER
                              DEFAULT
                              1,

                              animation_type
                              TEXT
                              DEFAULT
                              'none',

                              highlight_rule
                              TEXT
                              DEFAULT
                              'status',

                              visible
                              INTEGER
                              DEFAULT
                              1,

                              remark
                              TEXT,

                              created_at
                              TEXT,

                              updated_at
                              TEXT

                          )
                          """)

        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS twin_hotspot
                          (

                              id
                              INTEGER
                              PRIMARY
                              KEY
                              AUTOINCREMENT,

                              station_id
                              INTEGER
                              NOT
                              NULL,

                              model_id
                              INTEGER
                              NOT
                              NULL,

                              name
                              TEXT
                              NOT
                              NULL,

                              object_type
                              TEXT,

                              object_id
                              INTEGER,

                              node_name
                              TEXT,

                              position_x
                              REAL
                              DEFAULT
                              0,

                              position_y
                              REAL
                              DEFAULT
                              0,

                              position_z
                              REAL
                              DEFAULT
                              0,

                              icon
                              TEXT,

                              visible
                              INTEGER
                              DEFAULT
                              1,

                              created_at
                              TEXT,

                              updated_at
                              TEXT

                          )
                          """)

        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS twin_camera_bookmark
                          (

                              id
                              INTEGER
                              PRIMARY
                              KEY
                              AUTOINCREMENT,

                              station_id
                              INTEGER
                              NOT
                              NULL,

                              model_id
                              INTEGER
                              NOT
                              NULL,

                              name
                              TEXT
                              NOT
                              NULL,

                              position_x
                              REAL
                              NOT
                              NULL,

                              position_y
                              REAL
                              NOT
                              NULL,

                              position_z
                              REAL
                              NOT
                              NULL,

                              target_x
                              REAL
                              NOT
                              NULL,

                              target_y
                              REAL
                              NOT
                              NULL,

                              target_z
                              REAL
                              NOT
                              NULL,

                              fov
                              REAL
                              DEFAULT
                              45,

                              sort_order
                              INTEGER
                              DEFAULT
                              0,

                              is_default
                              INTEGER
                              DEFAULT
                              0,

                              created_at
                              TEXT,

                              updated_at
                              TEXT

                          )
                          """)
        self.conn.commit()

    def ensure_seed(self):
        if not self.one('SELECT id FROM system_info LIMIT 1'):
            self.execute('INSERT INTO system_info(software_name,software_version,copyright_owner,build_time) VALUES(?,?,?,?)',
                         ('隧道泵站自动控制系统','V5.7',COPYRIGHT,now()))
        if not self.one('SELECT id FROM pump_station LIMIT 1'):
            sid = self.add_station({'station_code':'ST01','station_name':'1号隧道泵站','station_type':'隧道排水','enabled':1,'control_mode':'manual','pump_count':4,'pipe_count':1,'level_sensor_count':2,'min_running_count':1,'max_running_count':3,'emergency_max_running_count':3,'remark':'样例泵站'}, auto_generate=True)
            self.set_current_station(sid)


    def upsert_control_state(self, station_id, data):
        """新增/更新泵站自动控制状态，用于泵站监控页显示当前控制阶段。"""
        row = self.one("SELECT station_id FROM station_control_state WHERE station_id=?", (station_id,))
        vals = {
            "control_mode": data.get("control_mode", ""),
            "control_state": data.get("control_state", "未知"),
            "event_state": data.get("event_state", "无事件"),
            "adopted_level": self._float(data.get("adopted_level", 0), 0),
            "level_rate": self._float(data.get("level_rate", 0), 0),
            "running_pump_count": self._int(data.get("running_pump_count", 0), 0),
            "standby_pump_count": self._int(data.get("standby_pump_count", 0), 0),
            "fault_pump_count": self._int(data.get("fault_pump_count", 0), 0),
            "maintenance_pump_count": self._int(data.get("maintenance_pump_count", 0), 0),
            "avg_frequency": self._float(data.get("avg_frequency", 0), 0),
            "current_action": data.get("current_action", ""),
            "next_action": data.get("next_action", ""),
            "reason_text": data.get("reason_text", ""),
            "updated_at": now(),
        }
        if row:
            self.execute("""UPDATE station_control_state SET control_mode=?,control_state=?,event_state=?,adopted_level=?,level_rate=?,running_pump_count=?,standby_pump_count=?,fault_pump_count=?,maintenance_pump_count=?,avg_frequency=?,current_action=?,next_action=?,reason_text=?,updated_at=? WHERE station_id=?""",
                         (vals["control_mode"],vals["control_state"],vals["event_state"],vals["adopted_level"],vals["level_rate"],vals["running_pump_count"],vals["standby_pump_count"],vals["fault_pump_count"],vals["maintenance_pump_count"],vals["avg_frequency"],vals["current_action"],vals["next_action"],vals["reason_text"],vals["updated_at"],station_id))
        else:
            self.execute("""INSERT INTO station_control_state(station_id,control_mode,control_state,event_state,adopted_level,level_rate,running_pump_count,standby_pump_count,fault_pump_count,maintenance_pump_count,avg_frequency,current_action,next_action,reason_text,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (station_id,vals["control_mode"],vals["control_state"],vals["event_state"],vals["adopted_level"],vals["level_rate"],vals["running_pump_count"],vals["standby_pump_count"],vals["fault_pump_count"],vals["maintenance_pump_count"],vals["avg_frequency"],vals["current_action"],vals["next_action"],vals["reason_text"],vals["updated_at"]))

    def add_control_event(self, station_id, event_type, trigger_reason="", action_type="", target_device="", control_state="", event_level="info", result="记录", remark=""):
        self.execute("""INSERT INTO station_control_event(station_id,event_time,event_type,event_level,control_state,trigger_reason,action_type,target_device,result,remark) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                     (station_id, now(), event_type, event_level, control_state, trigger_reason, action_type, target_device, result, remark))

    def log(self, op, obj_type='', obj_id=None, obj_name='', before='', after='', result='success', remark=''):
        self.execute('INSERT INTO operation_log(operation_time,operation_type,object_type,object_id,object_name,before_value,after_value,result,remark) VALUES(?,?,?,?,?,?,?,?,?)',
                     (now(),op,obj_type,obj_id,obj_name,before,after,result,remark))

    def get_current_station_id(self):
        row = self.one("SELECT config_value FROM system_config WHERE config_key='current_station_id'")
        if row and row['config_value'] not in (None, '', 'None'):
            try:
                sid = int(row['config_value'])
                exists = self.one('SELECT id FROM pump_station WHERE id=?', (sid,))
                if exists:
                    return sid
            except Exception:
                pass
        row = self.one('SELECT id FROM pump_station ORDER BY id LIMIT 1')
        if row:
            self.set_current_station(row['id'])
            return row['id']
        self.set_current_station(None)
        return None

    def set_current_station(self, sid):
        value = '' if sid in (None, '', 'None') else str(sid)
        cur = self.one("SELECT id FROM system_config WHERE config_key='current_station_id'")
        if cur:
            self.execute("UPDATE system_config SET config_value=?, updated_at=? WHERE config_key='current_station_id'", (value, now()))
        else:
            self.execute("INSERT INTO system_config(config_key,config_value,value_type,config_group,description,updated_at) VALUES('current_station_id',?,'int','runtime','当前泵站',?)", (value, now()))

    def next_station_code(self):
        nums = []
        for r in self.query('SELECT station_code FROM pump_station'):
            code = r['station_code'] or ''
            if code.upper().startswith('ST'):
                try: nums.append(int(code[2:]))
                except: pass
        n = 1
        while n in nums: n += 1
        return f'ST{n:02d}'



    def next_pump_code(self, station_id, prefix='P'):
        """Return the next available pump code for a station, e.g. P1, P2, P3.
        This checks actual existing pump_code values instead of relying on row count,
        so deleted/hidden/previous test records will not cause duplicate-code errors.
        """
        nums = []
        prefix_upper = prefix.upper()
        for r in self.query('SELECT pump_code FROM pump WHERE station_id=?', (station_id,)):
            code = (r['pump_code'] or '').upper().strip()
            if code.startswith(prefix_upper):
                tail = code[len(prefix_upper):]
                if tail.isdigit():
                    nums.append(int(tail))
        n = 1
        while n in nums:
            n += 1
        return f'{prefix_upper}{n}'

    def next_feed_pump_code(self, station_id):
        nums = []
        for r in self.query('SELECT pump_code FROM pump WHERE station_id=?', (station_id,)):
            code = (r['pump_code'] or '').upper().strip()
            if code.startswith('JP'):
                tail = code[2:]
                if tail.isdigit():
                    nums.append(int(tail))
        n = 1
        while n in nums:
            n += 1
        return f'JP{n}'


    def next_pipe_code(self, station_id):
        """Return next pipe code. Supports old PIPEA/PIPE1 and user-facing 母管A/母管1 formats."""
        nums = []
        for r in self.query('SELECT pipe_code, pipe_name FROM main_pipe WHERE station_id=?', (station_id,)):
            for raw in (r['pipe_code'], r['pipe_name']):
                code = (raw or '').upper().strip()
                if not code:
                    continue
                tails = []
                if code.startswith('PIPE') and len(code) > 4:
                    tails.append(code[4:])
                if code.startswith('母管') and len(code) > 2:
                    tails.append(code[2:])
                tails.append(code[-1:])
                for tail in tails:
                    if len(tail) == 1 and 'A' <= tail <= 'Z':
                        nums.append(ord(tail) - 64)
                    elif tail.isdigit():
                        nums.append(int(tail))
        n = 1
        while n in nums:
            n += 1
        return f'母管{chr(64+n)}' if 1 <= n <= 26 else f'母管{n}'

    def next_instrument_code(self, station_id, instrument_type='level'):
        prefix_map = {'level':'LT', 'flow':'FT', 'pressure':'PT', 'energy':'EM', 'current':'AI', 'voltage':'VI'}
        prefix = prefix_map.get(instrument_type, 'INS')
        nums=[]
        for r in self.query('SELECT instrument_code FROM instrument WHERE station_id=?', (station_id,)):
            code=(r['instrument_code'] or '').upper().strip()
            if code.startswith(prefix):
                tail=code[len(prefix):]
                if tail.isdigit(): nums.append(int(tail))
        n=1
        while n in nums: n+=1
        return f'{prefix}{n:02d}'


    def next_modbus_device_code(self, station_code, sid=None):
        """Return a globally unique Modbus device code.
        Old test databases may still contain orphan PLC_STxx rows after a station was deleted,
        so the code must be checked against the whole modbus_device table, not only this station.
        """
        base = f"PLC_{str(station_code or 'ST').strip()}"
        candidates = []
        if sid is not None:
            candidates.append(f"{base}_ID{sid}")
        candidates.append(base)
        existing = {str(r['device_code']).upper() for r in self.query('SELECT device_code FROM modbus_device') if r['device_code']}
        for c in candidates:
            if c.upper() not in existing:
                return c
        n = 1
        while f"{base}_{n:02d}".upper() in existing:
            n += 1
        return f"{base}_{n:02d}"

    def add_station(self, data, auto_generate=True):
        t = now()
        cur = self.execute('''INSERT INTO pump_station(station_code,station_name,station_type,enabled,control_mode,pump_count,pipe_count,level_sensor_count,min_running_count,max_running_count,emergency_max_running_count,data_source_mode,default_pump_type,default_rated_flow,default_rated_head,default_rated_power,default_rated_current,created_at,updated_at,remark)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (data['station_code'], data['station_name'], data.get('station_type','隧道排水'), int(data.get('enabled',1)), data.get('control_mode','manual'), int(data.get('pump_count',4)), int(data.get('pipe_count',1)), int(data.get('level_sensor_count',2)), int(data.get('min_running_count',1)), int(data.get('max_running_count',3)), int(data.get('emergency_max_running_count',3)), self._data_mode_code(data.get('data_source_mode','simulation')), self._pump_type_code(data.get('default_pump_type','submersible')), self._float(data.get('default_rated_flow',300),300), self._float(data.get('default_rated_head',60),60), self._float(data.get('default_rated_power',55),55), self._float(data.get('default_rated_current',100),100), t, t, data.get('remark','')))
        sid = cur.lastrowid
        self.ensure_station_parameters(sid)
        self.ensure_station_cameras(sid)
        if auto_generate:
            self.generate_defaults_for_station(sid, data)
        self.log('新增泵站','station',sid,data['station_name'])
        return sid

    def update_station(self, sid, data):
        self.execute('''UPDATE pump_station SET station_code=?,station_name=?,station_type=?,enabled=?,control_mode=?,pump_count=?,pipe_count=?,level_sensor_count=?,min_running_count=?,max_running_count=?,emergency_max_running_count=?,data_source_mode=?,default_pump_type=?,default_rated_flow=?,default_rated_head=?,default_rated_power=?,default_rated_current=?,updated_at=?,remark=? WHERE id=?''',
            (data['station_code'], data['station_name'], data.get('station_type','隧道排水'), int(data.get('enabled',1)), data.get('control_mode','manual'), int(data.get('pump_count',4)), int(data.get('pipe_count',1)), int(data.get('level_sensor_count',2)), int(data.get('min_running_count',1)), int(data.get('max_running_count',3)), int(data.get('emergency_max_running_count',3)), self._data_mode_code(data.get('data_source_mode','simulation')), self._pump_type_code(data.get('default_pump_type','submersible')), self._float(data.get('default_rated_flow',300),300), self._float(data.get('default_rated_head',60),60), self._float(data.get('default_rated_power',55),55), self._float(data.get('default_rated_current',100),100), now(), data.get('remark',''), sid))
        self.ensure_station_parameters(sid)
        self.ensure_station_cameras(sid)
        self.generate_defaults_for_station(sid, data)
        self.log('修改泵站','station',sid,data['station_name'])

    def delete_station(self, sid):
        # 泵站是主表。删除泵站时，必须同步删除依赖该泵站的所有配置和运行数据，
        # 否则界面会出现“泵站已删除但监控仍显示水泵/母管”的孤儿数据。
        st = self.one('SELECT station_name FROM pump_station WHERE id=?', (sid,))
        # 先关闭该泵站仍在运行的水泵记录，保留日志可追溯。
        for p in self.query('SELECT id FROM pump WHERE station_id=? AND run_feedback=1', (sid,)):
            self.close_pump_run_record(p['id'], 'station_delete')
        # 关系表可能只记录 pump_id/pipe_id，也同步按子表 ID 删除。
        self.execute('DELETE FROM pump_pipe_relation WHERE station_id=? OR pump_id IN (SELECT id FROM pump WHERE station_id=?) OR pipe_id IN (SELECT id FROM main_pipe WHERE station_id=?)', (sid, sid, sid))
        for tbl in ['runtime_sample','pump_run_record','fault_record','emergency_event','station_control_event','station_control_state','modbus_point','modbus_device','instrument','camera','main_pipe','pump']:
            self.execute(f'DELETE FROM {tbl} WHERE station_id=?', (sid,))
        self.execute("DELETE FROM parameter_value WHERE scope_type='station' AND scope_id=?", (sid,))
        self.execute('DELETE FROM pump_station WHERE id=?', (sid,))
        self.log('删除泵站','station',sid, st['station_name'] if st else '')
        row = self.one('SELECT id FROM pump_station ORDER BY id LIMIT 1')
        self.set_current_station(row['id'] if row else None)


    def ensure_station_cameras(self, sid):
        """每个泵站默认预留 4 个摄像头位，默认未启用。"""
        defaults = [
            ('CAM01','摄像头1','集水池/水仓'),
            ('CAM02','摄像头2','水泵房'),
            ('CAM03','摄像头3','控制柜/配电柜'),
            ('CAM04','摄像头4','出水口/管路区'),
        ]
        t = now()
        for code, name, pos in defaults:
            if not self.one('SELECT id FROM camera WHERE station_id=? AND camera_code=?',(sid,code)):
                self.execute("""INSERT INTO camera(station_id,camera_code,camera_name,camera_position,camera_type,ip_address,port,username,password,rtsp_url,onvif_url,enabled,record_enabled,snapshot_enabled,status,created_at,updated_at,remark)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                             (sid,code,name,pos,'模拟摄像头','',554,'admin','','','',1,1,1,'模拟待机',t,t,''))

    def next_camera_code(self, station_id):
        nums=[]
        for r in self.query('SELECT camera_code FROM camera WHERE station_id=?',(station_id,)):
            code=(r['camera_code'] or '').upper().strip()
            if code.startswith('CAM'):
                tail=code[3:]
                if tail.isdigit(): nums.append(int(tail))
        n=1
        while n in nums: n+=1
        return f'CAM{n:02d}'

    def add_camera(self, station_id, data):
        t=now()
        cur=self.execute("""INSERT INTO camera(station_id,camera_code,camera_name,camera_position,camera_type,ip_address,port,username,password,rtsp_url,onvif_url,enabled,record_enabled,snapshot_enabled,status,created_at,updated_at,remark)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (station_id,data.get('camera_code'),data.get('camera_name'),data.get('camera_position',''),data.get('camera_type','模拟摄像头'),data.get('ip_address',''),self._int(data.get('port',554),554),data.get('username',''),data.get('password',''),data.get('rtsp_url',''),data.get('onvif_url',''),self._int(data.get('enabled',0),0),self._int(data.get('record_enabled',0),0),self._int(data.get('snapshot_enabled',1),1),'未启用',t,t,data.get('remark','')))
        return cur.lastrowid

    def update_camera(self, camera_id, data):
        self.execute("""UPDATE camera SET camera_code=?,camera_name=?,camera_position=?,camera_type=?,ip_address=?,port=?,username=?,password=?,rtsp_url=?,onvif_url=?,enabled=?,record_enabled=?,snapshot_enabled=?,updated_at=?,remark=? WHERE id=?""",
                     (data.get('camera_code'),data.get('camera_name'),data.get('camera_position',''),data.get('camera_type','模拟摄像头'),data.get('ip_address',''),self._int(data.get('port',554),554),data.get('username',''),data.get('password',''),data.get('rtsp_url',''),data.get('onvif_url',''),self._int(data.get('enabled',0),0),self._int(data.get('record_enabled',0),0),self._int(data.get('snapshot_enabled',1),1),now(),data.get('remark',''),camera_id))

    def set_camera_status(self, camera_id, status):
        self.execute('UPDATE camera SET status=?, last_frame_time=?, updated_at=? WHERE id=?', (status, now(), now(), camera_id))

    def ensure_station_parameters(self, sid):
        defaults = [
            ('level_control','level_min','最低保护液位','0.80','real','m'),
            ('level_control','level_low','低液位','1.20','real','m'),
            ('level_control','target_level','目标控制液位','2.00','real','m'),
            ('level_control','target_level_low','目标液位下限','1.80','real','m'),
            ('level_control','target_level_high','目标液位上限','2.20','real','m'),
            ('level_control','level_normal_high','正常液位上限','2.50','real','m'),
            ('level_control','level_high','高液位','3.20','real','m'),
            ('level_control','level_high_high','超高液位','4.00','real','m'),
            ('level_control','upper_level','上限液位','2.50','real','m'),
            ('level_control','lower_level','下限液位','1.50','real','m'),
            ('level_control','control_deadband','控制死区','0.10','real','m'),
            ('level_control','rise_sample_period_seconds','上涨速率采样周期','60','real','s'),
            ('level_control','rise_rate_trigger','上涨速率触发值','0.05','real','m/min'),
            ('level_control','fall_sample_period_seconds','下降速率采样周期','60','real','s'),
            ('level_control','fall_rate_trigger','下降速率触发值','0.03','real','m/min'),
            ('level_control','stable_deadband','液位稳定死区','0.01','real','m/min'),
            ('level_select','level_select_mode','液位计选择方式','主用优先','text',''),
            ('level_select','primary_level_instrument_code','主用液位计编号','LT01','text',''),
            ('level_select','backup_level_instrument_code','备用液位计编号','LT02','text',''),
            ('level_select','level_diff_alarm_m','双液位偏差报警值','0.20','real','m'),
            ('level_control','freq_min','最低频率','30','real','Hz'),
            ('level_control','freq_economic','经济频率','35','real','Hz'),
            ('level_control','freq_normal','正常频率','38','real','Hz'),
            ('level_control','freq_high','高频率','45','real','Hz'),
            ('level_control','freq_max','最高频率','50','real','Hz'),
            ('level_control','freq_step','频率调整步长','1','real','Hz'),
            ('level_control','freq_adjust_interval_seconds','调节刷新周期','1','real','s'),
            ('level_control','add_pump_min_interval_seconds','加泵最小间隔','30','real','s'),
            ('level_control','reduce_pump_min_interval_seconds','减泵最小间隔','120','real','s'),
            ('level_control','min_run_seconds_before_stop','减泵前最小运行时间','180','real','s'),
            ('level_control','min_stop_seconds_before_start','加泵前最小停机时间','120','real','s'),
            ('emergency','rise_rate_1','一级增长速率','0.05','real','m/min'),
            ('emergency','rise_rate_2','二级增长速率','0.15','real','m/min'),
            ('emergency','rise_rate_3','三级增长速率','0.30','real','m/min'),
            ('emergency','time_to_high_1','一级到高液位时间','10','real','min'),
            ('emergency','time_to_high_2','二级到高液位时间','5','real','min'),
            ('emergency','time_to_high_3','三级到高液位时间','3','real','min'),
            ('emergency','emergency_freq_1','一级应急频率','40','real','Hz'),
            ('emergency','emergency_freq_2','二级应急频率','45','real','Hz'),
            ('emergency','emergency_freq_3','三级应急频率','50','real','Hz'),
            ('pipe_check','target_velocity','目标流速','2.0','real','m/s'),
            ('pipe_check','min_velocity','最低建议流速','0.8','real','m/s'),
            ('pipe_check','max_velocity','最高建议流速','3.0','real','m/s'),
            ('manual_control','feed_start_delay_seconds','离心泵启动前给水泵预运行延时','3','real','s'),
            ('manual_control','feed_stop_delay_seconds','离心泵启动后给水泵停止延时','5','real','s'),
            ('manual_control','start_feedback_timeout_seconds','启动反馈超时判定','10','real','s'),
            ('manual_control','stop_feedback_timeout_seconds','停止反馈超时判定','10','real','s'),
            ('current_check','current_low_value','电流低值','30','real','A'),
            ('current_check','current_high_value','电流高值','120','real','A'),
            ('current_check','current_check_delay_seconds','电流判断延时','8','real','s'),
            
        ]
        for g,code,name,val,typ,unit in defaults:
            row = self.one('SELECT id,param_value,param_name FROM parameter_value WHERE scope_type=? AND scope_id=? AND param_group=? AND param_code=?',('station',sid,g,code))
            if not row:
                self.execute('''INSERT INTO parameter_value(scope_type,scope_id,param_group,param_code,param_name,param_value,value_type,unit,updated_at)
                                VALUES('station',?,?,?,?,?,?,?,?)''',(sid,g,code,name,val,typ,unit,now()))
            else:
                # V5.7.6：调节刷新周期统一为 1s；旧版本若仍为 10s，自动迁移为 1s。
                if g == 'level_control' and code == 'freq_adjust_interval_seconds':
                    try:
                        old_val = float(row['param_value'] or 0)
                    except Exception:
                        old_val = 0
                    if old_val >= 10 or not row['param_value']:
                        self.execute('UPDATE parameter_value SET param_name=?, param_value=?, updated_at=? WHERE id=?', (name, '1', now(), row['id']))
                    elif row['param_name'] != name:
                        self.execute('UPDATE parameter_value SET param_name=?, updated_at=? WHERE id=?', (name, now(), row['id']))

    def _int(self, value, default=0):
        try:
            return int(float(value))
        except Exception:
            return default

    def _float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _pump_type_code(self, value):
        text = str(value or '').strip()
        mapping = {'潜污泵':'submersible', '多级离心泵':'centrifugal', '离心泵':'centrifugal', '给水泵':'feed'}
        return mapping.get(text, text if text in ('submersible','centrifugal','feed') else text)

    def _pump_label(self, ptype):
        return {'submersible':'潜污泵', 'centrifugal':'多级离心泵', 'feed':'给水泵'}.get(ptype, ptype)

    def _data_mode_code(self, value):
        text = str(value or '').strip()
        mapping = {'模拟':'simulation', '模拟数据':'simulation', '仿真':'simulation', 'simulation':'simulation',
                   '实时采集':'realtime', '实际采集':'realtime', '真实采集':'realtime', 'realtime':'realtime', 'real':'realtime'}
        return mapping.get(text, text if text in ('simulation','realtime') else 'simulation')

    def _ensure_pipe_instruments(self, sid, pipe_id, pipe_code):
        for typ, prefix_name in [('flow','流量计'), ('pressure','压力表')]:
            exists = self.one('SELECT id FROM instrument WHERE station_id=? AND instrument_type=? AND pipe_id=?', (sid, typ, pipe_id))
            if exists:
                self.execute('UPDATE instrument SET owner_type=?, owner_id=?, pipe_id=?, updated_at=? WHERE id=?', ('pipe', pipe_id, pipe_id, now(), exists['id']))
                continue
            code = self.next_instrument_code(sid, typ)
            self.execute("""INSERT INTO instrument(station_id,pipe_id,pump_id,instrument_code,instrument_name,instrument_type,owner_type,owner_id,enabled,bypassed,control_enable,alarm_enable,report_enable,current_value,correction_factor,created_at,updated_at,remark)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (sid, pipe_id, None, code, f'{pipe_code}{prefix_name}', typ, 'pipe', pipe_id, 1, 0, 0, 1, 1, 0, 1.0, now(), now(), '母管自动生成仪表'))

    def _ensure_station_instruments(self, sid, level_count=2):
        for i in range(1, max(1, int(level_count))+1):
            code = f'LT{i:02d}'
            if not self.one('SELECT id FROM instrument WHERE station_id=? AND instrument_code=?', (sid, code)):
                self.execute("""INSERT INTO instrument(station_id,instrument_code,instrument_name,instrument_type,owner_type,owner_id,enabled,bypassed,control_enable,alarm_enable,report_enable,current_value,correction_factor,created_at,updated_at,remark)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                             (sid, code, f'液位计{i}', 'level', 'station', sid, 1, 0, 1, 1, 1, 0, 1.0, now(), now(), '泵站自动生成液位计'))
        if not self.one("SELECT id FROM instrument WHERE station_id=? AND instrument_type='energy' AND owner_type='station'", (sid,)):
            code = self.next_instrument_code(sid, 'energy')
            self.execute("""INSERT INTO instrument(station_id,instrument_code,instrument_name,instrument_type,owner_type,owner_id,enabled,bypassed,control_enable,alarm_enable,report_enable,current_value,correction_factor,created_at,updated_at,remark)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (sid, code, '泵站总电表', 'energy', 'station', sid, 1, 0, 0, 1, 1, 0, 1.0, now(), now(), '泵站自动生成总电表'))

    def _ensure_feed_for_centrifugal(self, sid, pump_id, main_code):
        pump = self.one('SELECT * FROM pump WHERE id=?', (pump_id,))
        if pump and pump['feed_pump_id']:
            return pump['feed_pump_id']
        jp_code = self.next_feed_pump_code(sid)
        cur = self.execute("""INSERT INTO pump(station_id,pump_code,pump_name,pump_type,enabled,auto_enable,emergency_enable,rated_power,rated_current,rated_voltage,rated_flow,rated_head,min_frequency,max_frequency,start_frequency,display_order,created_at,updated_at,remark)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (sid, jp_code, f'{jp_code}给水泵（对应{main_code}）', 'feed', 1, 1, 1, 7.5, 20, 380, 30, 35, 30, 50, 30, 900+self._int(jp_code[2:], 1), now(), now(), f'自动生成：1台离心泵对应1台给水泵，服务{main_code}'))
        fid = cur.lastrowid
        self.execute('UPDATE pump SET feed_pump_id=?, updated_at=? WHERE id=?', (fid, now(), pump_id))
        return fid

    def generate_defaults_for_station(self, sid, data=None):
        st = self.one('SELECT * FROM pump_station WHERE id=?', (sid,))
        if not st:
            return
        data = data or {}
        pump_count = self._int(data.get('pump_count', st['pump_count']), 4)
        pipe_count = self._int(data.get('pipe_count', st['pipe_count']), 1)
        level_count = self._int(data.get('level_sensor_count', st['level_sensor_count']), 2)
        default_type = self._pump_type_code(data.get('default_pump_type', st['default_pump_type'] if 'default_pump_type' in st.keys() else data.get('pump_type_template', 'submersible')))
        rated_power = self._float(data.get('default_rated_power', st['default_rated_power'] if 'default_rated_power' in st.keys() else data.get('rated_power', 55)), 55)
        rated_current = self._float(data.get('default_rated_current', st['default_rated_current'] if 'default_rated_current' in st.keys() else data.get('rated_current', 100)), 100)
        rated_flow = self._float(data.get('default_rated_flow', st['default_rated_flow'] if 'default_rated_flow' in st.keys() else data.get('rated_flow', 300)), 300)
        rated_head = self._float(data.get('default_rated_head', st['default_rated_head'] if 'default_rated_head' in st.keys() else data.get('rated_head', 60)), 60)
        min_freq = self._float(data.get('default_min_frequency', data.get('min_frequency', 30)), 30)
        max_freq = self._float(data.get('default_max_frequency', data.get('max_frequency', 50)), 50)
        start_freq = self._float(data.get('default_start_frequency', data.get('start_frequency', 30)), 30)

        existing_pipes = list(self.query('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)))
        while len(existing_pipes) < max(1, pipe_count):
            idx = len(existing_pipes) + 1
            code = self.next_pipe_code(sid)
            self.execute("""INSERT INTO main_pipe(station_id,pipe_code,pipe_name,standard_dn,dn_value,inner_diameter_mm,pipe_material,created_at,updated_at,display_order,remark)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                         (sid, code, code, 'DN400', 400, 400, '钢管', now(), now(), idx, '泵站管理自动生成母管'))
            existing_pipes = list(self.query('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)))

        pipes = list(self.query('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)))
        for idx, pipe in enumerate(pipes, 1):
            if not pipe['display_order']:
                self.execute('UPDATE main_pipe SET display_order=? WHERE id=?', (idx, pipe['id']))
            self._ensure_pipe_instruments(sid, pipe['id'], pipe['pipe_code'])

        main_pumps = list(self.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id", (sid,)))
        while len(main_pumps) < max(0, pump_count):
            idx = len(main_pumps) + 1
            code = self.next_pump_code(sid, 'P')
            ptype = default_type if default_type in ('submersible','centrifugal') else 'submersible'
            name = f'{code}{self._pump_label(ptype)}'
            cur = self.execute("""INSERT INTO pump(station_id,pump_code,pump_name,pump_type,enabled,auto_enable,emergency_enable,standby,maintenance,manual_fault,rated_power,rated_current,rated_voltage,rated_flow,rated_head,min_frequency,max_frequency,start_frequency,display_order,created_at,updated_at,remark)
                                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                               (sid, code, name, ptype, 1, 1, 1, 0, 0, 0, rated_power, rated_current, 380, rated_flow, rated_head, min_freq, max_freq, start_freq, idx, now(), now(), '泵站管理自动生成主排水泵'))
            pid = cur.lastrowid
            pipes = list(self.query('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)))
            if pipes:
                pipe_id = pipes[(idx-1) % len(pipes)]['id']
                self.execute('INSERT OR IGNORE INTO pump_pipe_relation(station_id,pump_id,pipe_id,relation_type,enabled) VALUES(?,?,?,?,1)', (sid, pid, pipe_id, 'main_drain'))
            if ptype == 'centrifugal':
                self._ensure_feed_for_centrifugal(sid, pid, code)
            main_pumps = list(self.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id", (sid,)))

        for cp in self.query("SELECT * FROM pump WHERE station_id=? AND pump_type='centrifugal' ORDER BY display_order,id", (sid,)):
            if not cp['feed_pump_id']:
                self._ensure_feed_for_centrifugal(sid, cp['id'], cp['pump_code'])

        first_pipe = self.one('SELECT id FROM main_pipe WHERE station_id=? ORDER BY display_order,id LIMIT 1', (sid,))
        if first_pipe:
            for p in self.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id", (sid,)):
                rel = self.one('SELECT id FROM pump_pipe_relation WHERE pump_id=? AND enabled=1', (p['id'],))
                if not rel:
                    self.execute('INSERT OR IGNORE INTO pump_pipe_relation(station_id,pump_id,pipe_id,relation_type,enabled) VALUES(?,?,?,?,1)', (sid, p['id'], first_pipe['id'], 'main_drain'))

        self._ensure_station_instruments(sid, level_count)
        self.generate_default_points(sid)
        self.recalculate_pipe(sid)


    def dashboard_summary(self):
        stations = self.query('SELECT * FROM pump_station ORDER BY id')
        pump_rows = self.query("SELECT * FROM pump WHERE pump_type!='feed' ORDER BY station_id, display_order, id")
        running = fault = maintenance = standby = 0
        total_current = total_power = total_flow = total_energy = 0.0
        voltages = []
        for p in pump_rows:
            is_fault = bool(p['fault_feedback'] or p['manual_fault'])
            is_maint = bool(p['maintenance'])
            is_run = bool(p['run_feedback'])
            if is_fault:
                fault += 1
            elif is_maint:
                maintenance += 1
            elif is_run:
                running += 1
            else:
                standby += 1
            if is_run:
                total_current += float(p['current'] or 0)
                total_power += float(p['rated_power'] or 0)
                if p['voltage'] is not None:
                    voltages.append(float(p['voltage'] or 0))
            total_energy += float(p['energy'] or 0)
        for r in self.query('SELECT estimated_running_flow FROM main_pipe'):
            total_flow += float(r['estimated_running_flow'] or 0)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        row = self.one("SELECT AVG(flow_value) avg_flow FROM runtime_sample WHERE record_time>=? AND sample_type='pipe'", (today+' 00:00:00',))
        day_flow = float(row['avg_flow'] or 0) * 24.0 if row else 0.0
        voltage = sum(voltages) / len(voltages) if voltages else 380.0
        devices = self.query('SELECT enabled, communication_status FROM modbus_device')
        online = 0; offline = 0; disabled = 0
        for d in devices:
            if not d['enabled']:
                disabled += 1
            elif str(d['communication_status'] or '').lower() in ('online','normal','good','connected','通讯正常'):
                online += 1
            else:
                offline += 1
        return {'station_count': len(stations), 'pump_count': len(pump_rows), 'running': running, 'standby': standby, 'fault': fault, 'maintenance': maintenance, 'total_current': total_current, 'total_voltage': voltage, 'total_power': total_power, 'total_flow': total_flow, 'day_flow': day_flow, 'day_energy': total_energy, 'comm_online': online, 'comm_offline': offline, 'comm_disabled': disabled, 'comm_total': len(devices)}

    def station_cards_summary(self):
        result=[]
        for st in self.query('SELECT * FROM pump_station ORDER BY id'):
            pumps=self.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id",(st['id'],))
            pipes=self.query('SELECT * FROM main_pipe WHERE station_id=?',(st['id'],))
            running=fault=maintenance=standby=0
            current=power=energy=0.0; volts=[]
            for p in pumps:
                is_fault=bool(p['fault_feedback'] or p['manual_fault']); is_maint=bool(p['maintenance']); is_run=bool(p['run_feedback'])
                if is_fault: fault+=1
                elif is_maint: maintenance+=1
                elif is_run: running+=1
                else: standby+=1
                if is_run:
                    current+=float(p['current'] or 0); power+=float(p['rated_power'] or 0); volts.append(float(p['voltage'] or 0))
                energy+=float(p['energy'] or 0)
            flow=sum(float(x['estimated_running_flow'] or 0) for x in pipes)
            devs = self.query('SELECT enabled, communication_status FROM modbus_device WHERE station_id=?',(st['id'],))
            online=offline=disabled=0
            for d in devs:
                if not d['enabled']:
                    disabled += 1
                elif str(d['communication_status'] or '').lower() in ('online','normal','good','connected','通讯正常'):
                    online += 1
                else:
                    offline += 1
            result.append({'id':st['id'],'code':st['station_code'],'name':st['station_name'],'mode':st['control_mode'],'emergency':st['emergency_level'],'running':running,'standby':standby,'fault':fault,'maintenance':maintenance,'current':current,'voltage':(sum(volts)/len(volts) if volts else 380.0),'power':power,'flow':flow,'energy':energy,'comm_online':online,'comm_offline':offline,'comm_disabled':disabled,'comm_total':len(devs)})
        return result


    def _safe_int(self, value, default=0):
        try:
            if value is None or str(value).strip() == '':
                return default
            return int(float(str(value).strip()))
        except Exception:
            return default

    def update_modbus_device(self, did, data):
        data = dict(data)
        data['port'] = self._safe_int(data.get('port'), 502)
        data['slave_id'] = self._safe_int(data.get('slave_id'), 1)
        data['timeout_ms'] = self._safe_int(data.get('timeout_ms'), 3000)
        data['poll_interval_ms'] = self._safe_int(data.get('poll_interval_ms'), 1000)
        data['enabled'] = self._safe_int(data.get('enabled'), 1)
        self.execute("""UPDATE modbus_device SET device_code=?, device_name=?, device_type=?, ip_address=?, port=?, slave_id=?, timeout_ms=?, poll_interval_ms=?, enabled=?, communication_status=?, remark=? WHERE id=?""",
                     (data.get('device_code',''), data.get('device_name',''), data.get('device_type','PLC'), data.get('ip_address',''), data['port'], data['slave_id'], data['timeout_ms'], data['poll_interval_ms'], data['enabled'], self._auto_comm_status(data), data.get('remark',''), did))

    def _row_get(self, data, key, default=None):
        # sqlite3.Row 不支持 dict.get；统一兼容 dict / sqlite3.Row。
        try:
            if data is None:
                return default
            if hasattr(data, 'keys') and key in data.keys():
                return data[key]
            if isinstance(data, dict):
                return data.get(key, default)
            return data[key]
        except Exception:
            return default

    def _auto_comm_status(self, data):
        # 模拟版自动判断通讯状态：启用且 IP/端口有效则认为在线；未启用为 disabled；无 IP 为 offline。
        # 注意：data 可能是 dict，也可能是 sqlite3.Row，不能直接使用 data.get。
        try:
            if int(self._row_get(data, 'enabled', 1) or 0) == 0:
                return 'disabled'
        except Exception:
            pass
        ip = str(self._row_get(data, 'ip_address', '') or '').strip()
        port = str(self._row_get(data, 'port', '') or '').strip()
        if not ip or not port:
            return 'offline'
        return 'online'

    def auto_update_comm_status(self):
        for d in self.query('SELECT * FROM modbus_device'):
            status = self._auto_comm_status(d)
            self.execute('UPDATE modbus_device SET communication_status=? WHERE id=?',(status, d['id']))

    def add_modbus_device(self, sid, data):
        data = dict(data)
        data['port'] = self._safe_int(data.get('port'), 502)
        data['slave_id'] = self._safe_int(data.get('slave_id'), 1)
        data['timeout_ms'] = self._safe_int(data.get('timeout_ms'), 3000)
        data['poll_interval_ms'] = self._safe_int(data.get('poll_interval_ms'), 1000)
        data['enabled'] = self._safe_int(data.get('enabled'), 1)
        cur=self.execute("""INSERT INTO modbus_device(station_id,device_code,device_name,device_type,ip_address,port,slave_id,timeout_ms,poll_interval_ms,enabled,communication_status,remark) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (sid, data.get('device_code',''), data.get('device_name',''), data.get('device_type','PLC'), data.get('ip_address',''), data['port'], data['slave_id'], data['timeout_ms'], data['poll_interval_ms'], data['enabled'], self._auto_comm_status(data), data.get('remark','')))
        return cur.lastrowid

    def generate_default_points(self, sid):
        st = self.one('SELECT * FROM pump_station WHERE id=?',(sid,))
        if not st: return
        dev = self.one('SELECT id, device_code FROM modbus_device WHERE station_id=? ORDER BY id LIMIT 1',(sid,))
        if not dev:
            device_code = self.next_modbus_device_code(st['station_code'], sid)
            cur=self.execute('''INSERT INTO modbus_device(station_id,device_code,device_name,device_type,ip_address,port,slave_id,enabled) VALUES(?,?,?,?,?,?,?,1)''',(sid,device_code,f"{st['station_name']} PLC",'PLC','192.168.1.10',502,1))
            dev_id=cur.lastrowid
        else:
            dev_id=dev['id']
        addr=40001
        # instrument points
        for inst in self.query('SELECT * FROM instrument WHERE station_id=?',(sid,)):
            dc={'level':'level_value','flow':'pipe_flow_instant','pressure':'pipe_pressure','energy':'energy'}.get(inst['instrument_type'],'value')
            unit={'level':'m','flow':'m³/h','pressure':'MPa','energy':'kWh'}.get(inst['instrument_type'],'')
            pc=f"{st['station_code']}_{inst['instrument_code']}_VALUE"
            self.execute('''INSERT OR IGNORE INTO modbus_point(device_id,station_id,object_type,object_id,object_code,point_code,point_name,point_category,data_code,function_code,register_address,register_count,data_type,byte_order,scale,unit,read_write,point_usage,enabled,last_update_time)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(dev_id,sid,'instrument',inst['id'],inst['instrument_code'],pc,inst['instrument_name']+'数值',inst['instrument_type'],dc,3,addr,2,'float32','ABCD',1,'','read_write','模拟量',1,now()))
            addr += 2
        for p in self.query('SELECT * FROM pump WHERE station_id=?',(sid,)):
            rows=[
                ('RUN_FB','运行反馈','run_feedback','状态量',''),
                ('FAULT_FB','故障反馈','fault_feedback','状态量',''),
                ('CURRENT','电流','current','模拟量',''),
                ('VOLTAGE','电压','voltage','模拟量',''),
                ('FREQ_FB','频率反馈','frequency_feedback','模拟量',''),
                ('START_CMD','启动命令','start_command','控制指令','1'),
                ('STOP_CMD','停止命令','stop_command','控制指令','5'),
                ('FREQ_SET','频率设定','frequency_set','频率设定','')
            ]
            for suf,name,dc,usage,cmd_val in rows:
                pc=f"{st['station_code']}_{p['pump_code']}_{suf}"
                self.execute('''INSERT OR IGNORE INTO modbus_point(device_id,station_id,object_type,object_id,object_code,point_code,point_name,point_category,data_code,function_code,register_address,register_count,data_type,byte_order,scale,unit,read_write,point_usage,command_value,enabled,last_update_time)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(dev_id,sid,'pump',p['id'],p['pump_code'],pc,p['pump_code']+name,'pump',dc,3,addr,2,'float32','ABCD',1,'','read_write',usage,cmd_val,1,now()))
                addr += 2

    def _normalize_modbus_addresses(self):
        # 保留兼容方法：只给没有地址的老点位补默认地址，不再覆盖用户已配置的地址/数据类型。
        rows = self.conn.execute('''
            SELECT id, station_id, COALESCE(device_id,0) AS device_id, register_address, register_count
            FROM modbus_point
            ORDER BY station_id, COALESCE(device_id,0), id
        ''').fetchall()
        current_key = None
        addr = 40001
        for r in rows:
            key = (r['station_id'], r['device_id'])
            if key != current_key:
                current_key = key
                addr = 40001
            try:
                existing=int(r['register_address'] or 0)
            except Exception:
                existing=0
            if existing>0:
                try: cnt=max(1,int(r['register_count'] or 2))
                except Exception: cnt=2
                addr=max(addr, existing+cnt)
                continue
            self.conn.execute('''
                UPDATE modbus_point
                SET register_address=?, register_count=COALESCE(NULLIF(register_count,0),2), data_type=COALESCE(NULLIF(data_type,''),'float32'), function_code=COALESCE(NULLIF(function_code,0),3),
                    byte_order=COALESCE(NULLIF(byte_order,''),'ABCD'), read_write=COALESCE(NULLIF(read_write,''),'read_write')
                WHERE id=?
            ''', (addr, r['id']))
            addr += 2

    def get_param(self, sid, group, code, default=0.0):
        row = self.one('SELECT param_value FROM parameter_value WHERE scope_type="station" AND scope_id=? AND param_group=? AND param_code=?',(sid,group,code))
        if row:
            try: return float(row['param_value'])
            except: return row['param_value']
        return default

    def set_param(self, sid, group, code, value):
        self.execute('UPDATE parameter_value SET param_value=?, updated_at=? WHERE scope_type="station" AND scope_id=? AND param_group=? AND param_code=?', (str(value), now(), sid, group, code))

    def recalculate_pipe(self, sid):
        for pipe in self.query('SELECT * FROM main_pipe WHERE station_id=?',(sid,)):
            pumps = self.query('''SELECT p.* FROM pump p JOIN pump_pipe_relation r ON r.pump_id=p.id WHERE r.pipe_id=? AND r.enabled=1 AND p.pump_type!='feed' ''',(pipe['id'],))
            theoretical = sum(float(p['rated_flow'] or 0) for p in pumps)
            running_pumps = [p for p in pumps if p['run_feedback']]
            running_count=len(running_pumps)
            factor = 1.0 if running_count<=1 else 0.95 if running_count==2 else 0.90 if running_count==3 else 0.85
            est_flow=sum(float(p['rated_flow'] or 0) * float(p['frequency'] or 0) / max(float(p['rated_frequency'] or 50),1) * float(p['flow_correction_factor'] or 1) for p in running_pumps)*factor
            dia=float(pipe['inner_diameter_mm'] or pipe['dn_value'] or 0)
            velocity=0
            if dia>0 and est_flow>0:
                import math
                D=dia/1000.0
                area=math.pi*D*D/4
                velocity=(est_flow/3600.0)/area
            max_v=float(self.get_param(sid,'pipe_check','max_velocity',3.0))
            min_v=float(self.get_param(sid,'pipe_check','min_velocity',0.8))
            status='未校核'
            if velocity>0:
                status='偏小' if velocity>max_v else '偏大' if velocity<min_v else '正常'
            # If a non-bypassed flow meter is bound to this pipe, keep its measured value too.
            ft = self.one("SELECT * FROM instrument WHERE station_id=? AND instrument_type='flow' AND pipe_id=? AND enabled=1 AND bypassed=0 ORDER BY report_priority,id LIMIT 1", (sid, pipe['id']))
            measured_flow = float(ft['current_value'] or 0) * float(ft['correction_factor'] or 1) if ft else 0
            pt = self.one("SELECT * FROM instrument WHERE station_id=? AND instrument_type='pressure' AND pipe_id=? AND enabled=1 AND bypassed=0 ORDER BY report_priority,id LIMIT 1", (sid, pipe['id']))
            pressure = float(pt['current_value'] or 0) if pt else float(pipe['pressure'] or 0)
            self.execute('''UPDATE main_pipe SET theoretical_flow=?, corrected_theoretical_flow=?, estimated_running_flow=?, estimated_velocity=?, measured_flow=?, pressure=?, diameter_check_status=?, updated_at=? WHERE id=?''',
                         (theoretical, theoretical*factor, est_flow, velocity, measured_flow, pressure, status, now(), pipe['id']))


    def open_pump_run_record(self, pump_id, source='manual', frequency=0):
        p = self.one('SELECT * FROM pump WHERE id=?', (pump_id,))
        if not p:
            return
        exists = self.one("SELECT id FROM pump_run_record WHERE pump_id=? AND result='running' ORDER BY id DESC LIMIT 1", (pump_id,))
        if exists:
            return
        st = self.one('SELECT control_mode FROM pump_station WHERE id=?', (p['station_id'],))
        t = now(); d = t[:10]; m = t[:7]
        self.execute('''INSERT INTO pump_run_record(station_id,pump_id,pump_code,pump_name,pump_type,start_time,start_date,start_month,start_mode,start_frequency,start_energy,start_source,result,remark)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                     (p['station_id'], p['id'], p['pump_code'], p['pump_name'], p['pump_type'], t, d, m, st['control_mode'] if st else '', float(frequency or p['set_frequency'] or p['frequency'] or 0), float(p['energy'] or 0), source, 'running', '启动自动记录'))

    def close_pump_run_record(self, pump_id, source='manual'):
        p = self.one('SELECT * FROM pump WHERE id=?', (pump_id,))
        if not p:
            return
        rec = self.one("SELECT * FROM pump_run_record WHERE pump_id=? AND result='running' ORDER BY id DESC LIMIT 1", (pump_id,))
        if not rec:
            return
        st = self.one('SELECT control_mode FROM pump_station WHERE id=?', (p['station_id'],))
        t = now()
        try:
            start_dt = datetime.datetime.strptime(rec['start_time'], '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
            dur = max(0, int((end_dt - start_dt).total_seconds()))
        except Exception:
            dur = 0
        end_energy = float(p['energy'] or 0)
        start_energy = float(rec['start_energy'] or 0)
        self.execute('''UPDATE pump_run_record SET end_time=?,duration_seconds=?,stop_mode=?,stop_frequency=?,end_energy=?,energy_delta=?,stop_source=?,result=?,remark=? WHERE id=?''',
                     (t, dur, st['control_mode'] if st else '', float(p['frequency'] or p['set_frequency'] or 0), end_energy, max(0, end_energy-start_energy), source, 'stopped', '停止自动记录', rec['id']))

    def repair_running_records(self, sid):
        for p in self.query('SELECT * FROM pump WHERE station_id=?', (sid,)):
            rec = self.one("SELECT id FROM pump_run_record WHERE pump_id=? AND result='running' ORDER BY id DESC LIMIT 1", (p['id'],))
            if p['run_feedback'] and not rec:
                self.open_pump_run_record(p['id'], 'state_repair', p['set_frequency'] or p['frequency'] or p['start_frequency'])
            elif (not p['run_feedback']) and rec:
                self.close_pump_run_record(p['id'], 'state_repair')

    def record_runtime_snapshot(self, sid, sample_source='simulated'):
        st = self.one('SELECT * FROM pump_station WHERE id=?', (sid,))
        if not st:
            return
        t = now(); d = t[:10]; m = t[:7]
        em = self.one("SELECT * FROM instrument WHERE station_id=? AND instrument_type='energy' AND owner_type='station' AND enabled=1 AND bypassed=0 ORDER BY report_priority,id LIMIT 1", (sid,))
        if em:
            station_energy = float(em['current_value'] or 0)
            energy_source = 'station_total_meter'
        else:
            row = self.one("SELECT SUM(energy) v FROM pump WHERE station_id=? AND pump_type!='feed'", (sid,))
            station_energy = float(row['v'] or 0)
            energy_source = 'pump_energy_sum'
        self.execute('''INSERT INTO runtime_sample(record_time,sample_date,sample_month,station_id,sample_type,device_code,device_name,run_status,energy_value,level_value,emergency_level,data_source,remark)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                     (t,d,m,sid,'station',st['station_code'],st['station_name'],1,station_energy,float(st['current_level'] or 0),st['emergency_level'],energy_source,'泵站总览快照'))
        for p in self.query('SELECT * FROM pump WHERE station_id=? ORDER BY display_order,id', (sid,)):
            run = int(p['run_feedback'] or 0)
            flow = 0.0
            if run and p['pump_type'] != 'feed':
                flow = float(p['rated_flow'] or 0) * float(p['frequency'] or p['set_frequency'] or 0) / max(float(p['rated_frequency'] or 50), 1) * float(p['flow_correction_factor'] or 1)
            self.execute('''INSERT INTO runtime_sample(record_time,sample_date,sample_month,station_id,sample_type,pump_id,device_code,device_name,run_status,flow_value,current_value,voltage_value,frequency_value,energy_value,level_value,emergency_level,data_source,remark)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                         (t,d,m,sid,'pump',p['id'],p['pump_code'],p['pump_name'],run,flow,float(p['current'] or 0),float(p['voltage'] or 0),float(p['frequency'] or 0),float(p['energy'] or 0),float(st['current_level'] or 0),st['emergency_level'],sample_source,'水泵运行参数快照'))
        for pipe in self.query('SELECT * FROM main_pipe WHERE station_id=? ORDER BY display_order,id', (sid,)):
            ft = self.one("SELECT * FROM instrument WHERE station_id=? AND instrument_type='flow' AND pipe_id=? AND enabled=1 ORDER BY report_priority,id LIMIT 1", (sid, pipe['id']))
            pt = self.one("SELECT * FROM instrument WHERE station_id=? AND instrument_type='pressure' AND pipe_id=? AND enabled=1 ORDER BY report_priority,id LIMIT 1", (sid, pipe['id']))
            if ft and not ft['bypassed']:
                flow = float(ft['current_value'] or 0) * float(ft['correction_factor'] or 1)
                src = 'measured_flow_meter'
            else:
                flow = float(pipe['estimated_running_flow'] or 0)
                src = 'estimated_by_frequency'
            pressure = float(pt['current_value'] or 0) if pt and not pt['bypassed'] else float(pipe['pressure'] or 0)
            self.execute('''INSERT INTO runtime_sample(record_time,sample_date,sample_month,station_id,sample_type,pipe_id,device_code,device_name,run_status,flow_value,pressure_value,level_value,emergency_level,data_source,remark)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                         (t,d,m,sid,'pipe',pipe['id'],pipe['pipe_code'],pipe['pipe_name'],1 if flow>0 else 0,flow,pressure,float(st['current_level'] or 0),st['emergency_level'],src,'母管流量压力快照'))

    def _period_seconds_for_samples(self):
        row = self.one("SELECT config_value FROM system_config WHERE config_key='runtime_sample_interval_seconds'")
        if row:
            try:
                return max(1, int(float(row['config_value'])))
            except Exception:
                pass
        return 10

    def export_runtime_log_csv(self, sid=None, date_text=None):
        sid = sid or self.get_current_station_id()
        date_text = date_text or now()[:10]
        rows=[]
        for r in self.query('''SELECT * FROM runtime_sample WHERE station_id=? AND sample_date=? ORDER BY record_time DESC,id DESC LIMIT 5000''', (sid, date_text)):
            rows.append([r['record_time'], r['sample_type'], r['device_code'], r['device_name'], r['run_status'], r['flow_value'], r['pressure_value'], r['current_value'], r['voltage_value'], r['frequency_value'], r['energy_value'], r['level_value'], r['emergency_level'], r['data_source'], r['remark']])
        return self.export_csv(f'runtime_log_{date_text}.csv', rows, ['时间','类型','设备编号','设备名称','运行状态','流量m3/h','压力MPa','电流A','电压V','频率Hz','累计电量kWh','液位m','应急状态','数据来源','备注'])

    def export_daily_summary_csv(self, sid=None, date_text=None):
        sid = sid or self.get_current_station_id()
        date_text = date_text or now()[:10]
        sec = self._period_seconds_for_samples()
        stations = self.query('SELECT * FROM pump_station WHERE id=?' if sid else 'SELECT * FROM pump_station', (sid,) if sid else ())
        rows=[]
        for st in stations:
            s_id = st['id']
            flow_row = self.one("SELECT SUM(flow_value) v, COUNT(*) c FROM runtime_sample WHERE station_id=? AND sample_date=? AND sample_type='pipe'", (s_id, date_text))
            discharge = float(flow_row['v'] or 0) * sec / 3600.0
            energy_row = self.one("SELECT MIN(energy_value) mn, MAX(energy_value) mx FROM runtime_sample WHERE station_id=? AND sample_date=? AND sample_type='station'", (s_id, date_text))
            energy = max(0.0, float(energy_row['mx'] or 0) - float(energy_row['mn'] or 0)) if energy_row else 0.0
            run_row = self.one("SELECT COUNT(*) c FROM runtime_sample WHERE station_id=? AND sample_date=? AND sample_type='pump' AND run_status=1", (s_id, date_text))
            run_hours = float(run_row['c'] or 0) * sec / 3600.0
            starts = self.one("SELECT COUNT(*) c FROM operation_log WHERE object_type='pump' AND operation_type='启动水泵' AND substr(operation_time,1,10)=? AND object_id IN (SELECT id FROM pump WHERE station_id=?)", (date_text, s_id))['c']
            stops = self.one("SELECT COUNT(*) c FROM operation_log WHERE object_type='pump' AND operation_type='停止水泵' AND substr(operation_time,1,10)=? AND object_id IN (SELECT id FROM pump WHERE station_id=?)", (date_text, s_id))['c']
            max_level = self.one("SELECT MAX(level_value) v FROM runtime_sample WHERE station_id=? AND sample_date=? AND sample_type='station'", (s_id, date_text))['v']
            rows.append([date_text, st['station_code'], st['station_name'], round(discharge,3), round(energy,3), round(run_hours,3), starts, stops, round(float(max_level or 0),3), sec, flow_row['c'] or 0])
        return self.export_csv(f'daily_summary_{date_text}.csv', rows, ['日期','泵站编号','泵站名称','当日排水量m3','当日电量kWh','水泵合计运行小时','启动次数','停止次数','最高液位m','采样间隔s','母管采样条数'])

    def export_monthly_summary_csv(self, sid=None, month_text=None):
        sid = sid or self.get_current_station_id()
        month_text = month_text or now()[:7]
        sec = self._period_seconds_for_samples()
        stations = self.query('SELECT * FROM pump_station WHERE id=?' if sid else 'SELECT * FROM pump_station', (sid,) if sid else ())
        rows=[]
        for st in stations:
            s_id = st['id']
            flow_row = self.one("SELECT SUM(flow_value) v, COUNT(*) c FROM runtime_sample WHERE station_id=? AND sample_month=? AND sample_type='pipe'", (s_id, month_text))
            discharge = float(flow_row['v'] or 0) * sec / 3600.0
            energy = 0.0
            for r in self.query("SELECT sample_date, MIN(energy_value) mn, MAX(energy_value) mx FROM runtime_sample WHERE station_id=? AND sample_month=? AND sample_type='station' GROUP BY sample_date", (s_id, month_text)):
                energy += max(0.0, float(r['mx'] or 0) - float(r['mn'] or 0))
            run_row = self.one("SELECT COUNT(*) c FROM runtime_sample WHERE station_id=? AND sample_month=? AND sample_type='pump' AND run_status=1", (s_id, month_text))
            run_hours = float(run_row['c'] or 0) * sec / 3600.0
            starts = self.one("SELECT COUNT(*) c FROM operation_log WHERE object_type='pump' AND operation_type='启动水泵' AND substr(operation_time,1,7)=? AND object_id IN (SELECT id FROM pump WHERE station_id=?)", (month_text, s_id))['c']
            stops = self.one("SELECT COUNT(*) c FROM operation_log WHERE object_type='pump' AND operation_type='停止水泵' AND substr(operation_time,1,7)=? AND object_id IN (SELECT id FROM pump WHERE station_id=?)", (month_text, s_id))['c']
            rows.append([month_text, st['station_code'], st['station_name'], round(discharge,3), round(energy,3), round(run_hours,3), starts, stops, sec, flow_row['c'] or 0])
        return self.export_csv(f'monthly_summary_{month_text}.csv', rows, ['月份','泵站编号','泵站名称','当月排水量m3','当月电量kWh','水泵合计运行小时','启动次数','停止次数','采样间隔s','母管采样条数'])

    def export_pump_run_records_csv(self, sid=None, date_text=None):
        sid = sid or self.get_current_station_id()
        date_text = date_text or now()[:10]
        rows=[]
        for r in self.query('''SELECT * FROM pump_run_record WHERE station_id=? AND start_date=? ORDER BY start_time DESC,id DESC''', (sid, date_text)):
            rows.append([r['start_date'], r['pump_code'], r['pump_name'], r['pump_type'], r['start_time'], r['end_time'] or '', r['duration_seconds'], round(float(r['duration_seconds'] or 0)/3600,3), r['start_frequency'], r['stop_frequency'], r['energy_delta'], r['start_source'], r['stop_source'] or '', r['result']])
        return self.export_csv(f'pump_run_records_{date_text}.csv', rows, ['日期','水泵编号','水泵名称','类型','启动时间','停止时间','运行秒','运行小时','启动频率','停止频率','本次电量kWh','启动来源','停止来源','状态'])

    def export_csv(self, filename, rows, headers):
        path=os.path.join(REPORT_DIR, filename)
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f); w.writerow(headers)
            for row in rows: w.writerow(row)
        return path

    def add_twin_model_asset(
            self,
            station_id,
            model_name,
            file_path):

        size = os.path.getsize(file_path) \
            if os.path.exists(file_path) else 0

        cur = self.execute("""
                           INSERT INTO twin_model_asset
                           (station_id,
                            model_name,
                            file_path,
                            file_size,
                            created_at,
                            updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)
                         """,
                           (
                               station_id,
                               model_name,
                               file_path,
                               size,
                               now(),
                               now()
                           ))

        return cur.lastrowid

    def save_twin_nodes(self, model_id,nodes):
        self.execute(
            "DELETE FROM twin_model_node WHERE model_id=?",
            (model_id,)
        )
        for n in nodes:
            self.execute("""
                         INSERT INTO twin_model_node
                         (model_id,
                          node_name,
                          node_path,
                          parent_name,
                          node_type,
                          depth,
                          created_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?)
                         """,
                         (
                             model_id,
                             n.get("name"),
                             n.get("path"),
                             n.get("parent"),
                             n.get("type"),
                             n.get("depth", 0),
                             now()
                         ))

    def get_twin_binding(self, station_id):
        return self.query(
            """
            SELECT *
            FROM twin_node_binding
            WHERE station_id = ?
            """,
            (station_id,)
        )

    def save_twin_binding(self, data):
        self.execute("""
                     INSERT INTO twin_node_binding
                     (station_id,
                      model_id,
                      node_name,
                      object_type,
                      object_id,
                      object_code,
                      role,
                      animation_type,
                      created_at,
                      updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     """,
                     (
                         data["station_id"],
                         data["model_id"],
                         data["node_name"],
                         data["object_type"],
                         data.get("object_id"),
                         data.get("object_code"),
                         data.get("role", "body"),
                         data.get("animation_type", "none"),
                         now(),
                         now()
                     ))