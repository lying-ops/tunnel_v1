import threading, time, random, math, socket, struct, datetime
from .db import now

def row_value(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        try:
            return row.get(key, default)
        except Exception:
            return default


class SimService:
    def __init__(self, db):
        self.db=db
        self.running=False
        self.thread=None
        self.heartbeat='--:--:--'
        self.tick=0
        self.last_levels={}
        self.sample_interval_seconds=10
        self.pending_centrifugal_starts=set()
        # 按泵站独立保存液位历史和自动控制动作时间，避免不同泵站互相影响。
        self.level_history={}
        self.last_auto_add_time={}
        self.last_auto_reduce_time={}
        self.last_freq_adjust_time={}
        self.low_protect_active={}
        self.emergency_active={}
        self.last_control_event_sig={}
        self.last_control_event_time={}

    def start(self):
        if self.running: return
        self.running=True
        self.thread=threading.Thread(target=self.loop,daemon=True)
        self.thread.start()

    def stop(self):
        self.running=False

    def loop(self):
        while self.running:
            try:
                self.tick += 1
                self.heartbeat=time.strftime('%H:%M:%S')
                self.db.auto_update_comm_status()
                self.simulate_all()
            except Exception as e:
                print('service error', e)
            time.sleep(1)

    def simulate_all(self):
        stations=self.db.query('SELECT * FROM pump_station WHERE enabled=1')
        for st in stations:
            sid=st['id']
            data_mode=str(row_value(st,'data_source_mode','simulation') or 'simulation')
            if data_mode in ('realtime','实时采集','实际采集','真实采集'):
                self.read_actual_modbus_points(sid)
                self.apply_actual_points_to_objects(sid)
            else:
                self.simulate_station(sid)
            mode=row_value(self.db.one('SELECT control_mode FROM pump_station WHERE id=?',(sid,)), 'control_mode', 'manual')
            if mode=='auto':
                self.auto_control(sid)
            else:
                st_now=self.db.one('SELECT current_level,level_rise_rate FROM pump_station WHERE id=?',(sid,))
                self._set_station_decision(sid, float(row_value(st_now,'level_rise_rate',0) or 0), '手动模式，自动控制未投入', control_state='手动模式', event_state='手动待命', action_type='无自动动作', next_action='等待人工操作或切换自动')
            self.db.recalculate_pipe(sid)
            self.db.repair_running_records(sid)
            if self.tick % self.sample_interval_seconds == 0:
                self.db.record_runtime_snapshot(sid)

    def simulate_station(self, sid):
        mode_row=self.db.one('SELECT control_mode FROM pump_station WHERE id=?',(sid,))
        mode=mode_row['control_mode'] if mode_row else 'manual'
        pumps=self.db.query('SELECT * FROM pump WHERE station_id=?',(sid,))
        running=sum(1 for p in pumps if p['run_feedback'] and p['pump_type']!='feed')
        # water coming wave, higher when less pumps running
        base_inflow=0.025 + 0.02*math.sin(self.tick/20.0)
        pump_out=running*0.015
        row=self.db.one('SELECT current_level FROM pump_station WHERE id=?',(sid,))
        level=float(row['current_level'] or 1.5)
        level += base_inflow - pump_out + random.uniform(-0.005,0.005)
        level=max(0.5,min(level,4.8))
        # 记录液位历史，用可设定采样周期计算上涨/下降速率；各泵站独立。
        now_ts=time.time()
        rise_period=float(self.db.get_param(sid,'level_control','rise_sample_period_seconds',60) or 60)
        fall_period=float(self.db.get_param(sid,'level_control','fall_sample_period_seconds',60) or 60)
        keep_period=max(rise_period, fall_period, 300) + 30
        hist=self.level_history.setdefault(sid, [])
        hist.append((now_ts, level))
        self.level_history[sid]=[(t,v) for t,v in hist if now_ts-t <= keep_period]
        erate=self._level_rate(sid, rise_period)
        auto_state='手动待命' if mode!='auto' else '自动平衡待命'
        self.db.execute('UPDATE pump_station SET current_level=?, level_rise_rate=?, emergency_level=?, updated_at=? WHERE id=?',(level, erate, auto_state, now(), sid))
        # instruments
        for inst in self.db.query('SELECT * FROM instrument WHERE station_id=?',(sid,)):
            # 屏蔽只表示该仪表不参与自动控制/保护判断；采集值仍继续刷新和显示。
            val=inst['current_value'] or 0
            typ=inst['instrument_type']
            if typ=='level': val=level + random.uniform(-0.03,0.03)
            elif typ=='flow': val=max(0, running*250+random.uniform(-30,30))
            elif typ=='pressure': val=max(0, 0.15 + running*0.05 + random.uniform(-0.01,0.01))
            elif typ=='energy': val=float(val or 0)+running*0.02
            self.db.execute('UPDATE instrument SET current_value=?, data_quality=?, data_source=?, updated_at=? WHERE id=?',(val,'good','measured',now(),inst['id']))
        # 液位二选一：根据参数选择主用/备用/平均/自动切换的有效液位。屏蔽或禁用的液位计不参与选择。
        level = self.select_effective_level(sid, level)
        try:
            hist=self.level_history.setdefault(sid, [])
            if hist:
                hist[-1]=(now_ts, level)
        except Exception:
            pass
        erate=self._level_rate(sid, rise_period)
        self.db.execute('UPDATE pump_station SET current_level=?, level_rise_rate=?, emergency_level=?, updated_at=? WHERE id=?',(level, erate, auto_state, now(), sid))
        # pumps analog values
        for p in pumps:
            if p['run_feedback']:
                freq=float(p['set_frequency'] or p['start_frequency'] or 30)
                current=float(p['rated_current'] or 100)*(0.45+0.55*freq/50)+random.uniform(-2,2)
                voltage=380+random.uniform(-3,3)
                # 电量计算核实：模拟版优先按三相电功率估算；缺少有效电流时，按额定功率和频率比例估算。
                # P(kW)=1.732*U(V)*I(A)*PF/1000，默认功率因数0.85；每秒增量=P/3600 kWh。
                pf=0.85
                try:
                    power_kw=1.732*float(voltage)*max(0.0,float(current))*pf/1000.0
                    if power_kw <= 0.01:
                        power_kw=float(p['rated_power'] or 30)*freq/50.0
                except Exception:
                    power_kw=float(p['rated_power'] or 30)*freq/50.0
                energy=float(p['energy'] or 0)+power_kw/3600.0
                self.db.execute('UPDATE pump SET frequency=?, current=?, voltage=?, energy=?, run_seconds_today=run_seconds_today+1, run_seconds_total=run_seconds_total+1, updated_at=? WHERE id=?',(freq,current,voltage,energy,now(),p['id']))
            else:
                self.db.execute('UPDATE pump SET frequency=0,current=0 WHERE id=?',(p['id'],))
        # V5.7.5：变量/点位是否采集由泵站“系统数据”选项决定。
        # 模拟模式只仿真泵站/水泵运行，不再阻塞读取现场 Modbus。


    def read_actual_modbus_points(self, sid):
        """Read enabled variables from their bound Modbus TCP devices.
        This replaces earlier simulated variable values. If a device is unreachable, the
        previous last_value is kept and the point quality is marked bad/offline.
        """
        sql = """SELECT p.*, d.ip_address, d.port, d.slave_id, d.timeout_ms, d.enabled AS device_enabled, d.communication_status
                 FROM modbus_point p LEFT JOIN modbus_device d ON p.device_id=d.id
                 WHERE p.station_id=? AND p.enabled=1"""
        points=self.db.query(sql,(sid,))
        for pt in points:
            if not pt['device_id'] or not pt['device_enabled']:
                self.db.execute('UPDATE modbus_point SET quality=?, last_update_time=? WHERE id=?',('device_disabled',now(),pt['id']))
                continue
            try:
                value=self._read_modbus_point(pt)
                if value is None:
                    self.db.execute('UPDATE modbus_point SET quality=?, last_update_time=? WHERE id=?',('bad',now(),pt['id']))
                else:
                    self.db.execute('UPDATE modbus_point SET last_value=?, quality=?, last_update_time=? WHERE id=?',(str(value),'good',now(),pt['id']))
            except Exception:
                self.db.execute('UPDATE modbus_point SET quality=?, last_update_time=? WHERE id=?',('offline',now(),pt['id']))

    def apply_actual_points_to_objects(self, sid):
        """Apply realtime Modbus point values to instruments, pumps and station values."""
        points=self.db.query("SELECT * FROM modbus_point WHERE station_id=? AND enabled=1 AND quality='good'", (sid,))
        for pt in points:
            try:
                val=float(pt['last_value'] or 0)
            except Exception:
                continue
            obj_type=str(pt['object_type'] or '')
            data_code=str(pt['data_code'] or '')
            oid=pt['object_id']
            if obj_type=='instrument' and oid:
                self.db.execute('UPDATE instrument SET current_value=?, data_quality=?, data_source=?, updated_at=? WHERE id=?', (val,'good','realtime',now(),oid))
            elif obj_type=='pump' and oid:
                if data_code=='run_feedback':
                    self.db.execute('UPDATE pump SET run_feedback=?, updated_at=? WHERE id=?', (1 if val else 0, now(), oid))
                elif data_code=='fault_feedback':
                    self.db.execute('UPDATE pump SET fault_feedback=?, updated_at=? WHERE id=?', (1 if val else 0, now(), oid))
                elif data_code=='current':
                    self.db.execute('UPDATE pump SET current=?, updated_at=? WHERE id=?', (val, now(), oid))
                elif data_code=='voltage':
                    self.db.execute('UPDATE pump SET voltage=?, updated_at=? WHERE id=?', (val, now(), oid))
                elif data_code in ('frequency_feedback','frequency'):
                    self.db.execute('UPDATE pump SET frequency=?, updated_at=? WHERE id=?', (val, now(), oid))
                elif data_code=='frequency_set':
                    self.db.execute('UPDATE pump SET set_frequency=?, updated_at=? WHERE id=?', (val, now(), oid))
        st=self.db.one('SELECT current_level FROM pump_station WHERE id=?',(sid,))
        fallback=float(row_value(st,'current_level',0) or 0)
        level=self.select_effective_level(sid, fallback)
        now_ts=time.time()
        hist=self.level_history.setdefault(sid, [])
        hist.append((now_ts, level))
        self.level_history[sid]=[(t,v) for t,v in hist if now_ts-t <= 360]
        rise_period=float(self.db.get_param(sid,'level_control','rise_sample_period_seconds',60) or 60)
        rate=self._level_rate(sid, rise_period)
        self.db.execute('UPDATE pump_station SET current_level=?, level_rise_rate=?, emergency_level=?, updated_at=? WHERE id=?', (level, rate, '实时采集', now(), sid))

    def _read_modbus_point(self, pt):
        ip=str(pt['ip_address'] or '').strip()
        if not ip:
            return None
        port=int(pt['port'] or 502)
        unit=int(pt['slave_id'] or 1)
        fc=int(pt['function_code'] or 3)
        addr=int(pt['register_address'] or 0)
        count=int(pt['register_count'] or 1)
        dtype=str(pt['data_type'] or 'float32')
        order=str(pt['byte_order'] or 'ABCD')
        timeout=max(0.2, min(3.0, float(pt['timeout_ms'] or 1000)/1000.0))
        start_addr=addr
        if addr>=40001 and fc in (3,6,16): start_addr=addr-40001
        elif addr>=30001 and fc==4: start_addr=addr-30001
        elif addr>=10001 and fc==2: start_addr=addr-10001
        elif addr>=1 and fc in (1,5,15): start_addr=addr-1
        if fc in (3,4):
            regs=self._modbus_read_registers(ip,port,unit,fc,start_addr,count,timeout)
            if regs is None:
                return None
            return self._decode_registers(regs,dtype,order,float(pt['scale'] or 1),float(pt['offset_value'] or 0))
        if fc in (1,2):
            bits=self._modbus_read_bits(ip,port,unit,fc,start_addr,max(1,count),timeout)
            if bits is None:
                return None
            return 1 if bits[0] else 0
        return None

    def _modbus_request(self, ip, port, unit, pdu, timeout):
        tid=int(time.time()*1000) & 0xffff
        header=struct.pack('>HHHB',tid,0,len(pdu)+1,unit)
        with socket.create_connection((ip,port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(header+pdu)
            mbap=sock.recv(7)
            if len(mbap)<7:
                return None
            _tid,_pid,length,unit_id=struct.unpack('>HHHB',mbap)
            data=b''
            remain=max(0,length-1)
            while len(data)<remain:
                chunk=sock.recv(remain-len(data))
                if not chunk: break
                data+=chunk
            if not data or (data[0] & 0x80):
                return None
            return data

    def _modbus_read_registers(self, ip, port, unit, fc, addr, count, timeout):
        pdu=struct.pack('>BHH',fc,addr,count)
        data=self._modbus_request(ip,port,unit,pdu,timeout)
        if not data or data[0]!=fc or len(data)<2:
            return None
        byte_count=data[1]
        raw=data[2:2+byte_count]
        if len(raw)<2*count:
            return None
        return list(struct.unpack('>'+'H'*count, raw[:2*count]))

    def _modbus_read_bits(self, ip, port, unit, fc, addr, count, timeout):
        pdu=struct.pack('>BHH',fc,addr,count)
        data=self._modbus_request(ip,port,unit,pdu,timeout)
        if not data or data[0]!=fc or len(data)<2:
            return None
        raw=data[2:2+data[1]]
        bits=[]
        for b in raw:
            for i in range(8): bits.append(bool(b & (1<<i)))
        return bits[:count]

    def _decode_registers(self, regs, dtype, order, scale, offset):
        if dtype in ('int16','uint16'):
            v=regs[0]
            if dtype=='int16' and v>=32768: v-=65536
            return round(v*scale+offset,6)
        if dtype in ('int32','uint32','float32'):
            if len(regs)<2: return None
            b=struct.pack('>HH', regs[0], regs[1])
            if order=='CDAB': b=b[2:4]+b[0:2]
            elif order=='BADC': b=bytes([b[1],b[0],b[3],b[2]])
            elif order=='DCBA': b=b[::-1]
            if dtype=='float32':
                v=struct.unpack('>f',b)[0]
            else:
                v=struct.unpack('>I',b)[0]
                if dtype=='int32' and v>=2147483648: v-=4294967296
            return round(v*scale+offset,6)
        if dtype=='bool':
            return 1 if regs[0] else 0
        return regs[0]

    def select_effective_level(self, sid, fallback_level):
        """液位计二选一/平均/自动切换。
        仪表屏蔽在这里体现：被屏蔽、禁用或无效的液位计不参与自动控制液位判断，
        但其采集值仍可在仪表/变量页面显示。
        """
        mode=str(self.db.get_param(sid,'level_select','level_select_mode','主用优先') or '主用优先')
        primary=str(self.db.get_param(sid,'level_select','primary_level_instrument_code','LT01') or 'LT01')
        backup=str(self.db.get_param(sid,'level_select','backup_level_instrument_code','LT02') or 'LT02')
        instruments=self.db.query("SELECT * FROM instrument WHERE station_id=? AND instrument_type='level' ORDER BY instrument_code,id",(sid,))
        valid=[]
        by_code={}
        for inst in instruments:
            try:
                if not inst['enabled'] or inst['bypassed']:
                    continue
                v=float(inst['current_value'] or fallback_level)
                if -1 <= v <= 20:
                    valid.append((inst['instrument_code'],v))
                    by_code[inst['instrument_code']]=v
            except Exception:
                continue
        if not valid:
            return fallback_level
        if '平均' in mode and len(valid)>=2:
            return sum(v for _,v in valid)/len(valid)
        if '备用' in mode and backup in by_code:
            return by_code[backup]
        if primary in by_code:
            return by_code[primary]
        if backup in by_code:
            return by_code[backup]
        return valid[0][1]

    def _level_rate(self, sid, period_seconds):
        """Return smoothed level change rate in m/min.

        V5.7.4: 不再用 1~2 秒瞬时差值直接换算 m/min，避免刚启动或刷新初期出现
        0.7m/min 这类被放大的假速率。采样时间不足时返回 0.0，等历史数据累计后
        再按指定窗口计算平均变化率。
        """
        hist=self.level_history.get(sid, [])
        if len(hist)<2:
            return 0.0
        now_ts, cur=hist[-1]
        period=max(1.0,float(period_seconds or 60))
        # 至少累计 30 秒，或达到采样周期的一半，才认为速率有效。
        min_dt=max(10.0, min(30.0, period*0.5))
        target=now_ts-period
        candidates=[item for item in hist if item[0] <= target]
        old=candidates[-1] if candidates else hist[0]
        dt=now_ts-old[0]
        if dt < min_dt:
            return 0.0
        return (cur-old[1])*60.0/max(1.0,dt)

    def _available_auto_pumps(self, sid):
        pumps=self.db.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY run_seconds_total ASC,start_count ASC,display_order ASC,id ASC",(sid,))
        return [p for p in pumps if (not p['run_feedback']) and self.can_start(p)]

    def _running_main_pumps(self, sid, order='asc'):
        sort='ASC' if order=='asc' else 'DESC'
        return self.db.query(f"SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' AND run_feedback=1 ORDER BY run_seconds_total {sort},id {sort}",(sid,))

    def _remove_unavailable_running(self, sid):
        for p in self.db.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' AND run_feedback=1",(sid,)):
            if p['maintenance'] or p['manual_fault'] or p['fault_feedback'] or p['disabled'] or (not p['enabled']):
                self.stop_pump(p['id'],'auto_remove_unavailable')

    def can_start(self,p):
        if not p:
            return False
        return bool(row_value(p,'enabled',1)) and bool(row_value(p,'auto_enable',1)) and not bool(row_value(p,'maintenance',0)) and not bool(row_value(p,'manual_fault',0)) and not bool(row_value(p,'disabled',0)) and not bool(row_value(p,'fault_feedback',0))

    def _start_direct(self, pump_id, freq, source):
        p=self.db.one('SELECT * FROM pump WHERE id=?',(pump_id,))
        if not p:
            return False, '水泵不存在'
        if not self.can_start(p) and not p['run_feedback']:
            return False, '水泵不可启动，可能故障/检修/禁用'
        if p['run_feedback']:
            self.set_freq(pump_id, freq)
            return True, '水泵已运行，已更新频率'
        self.db.execute('UPDATE pump SET run_feedback=1,set_frequency=?,start_count=start_count+1,updated_at=? WHERE id=?',(freq,now(),pump_id))
        self.db.open_pump_run_record(pump_id, source, freq)
        self.db.log('启动水泵','pump',pump_id,p['pump_name'],'','频率 '+str(freq),'success',source)
        return True, '启动成功'

    def _finish_centrifugal_start(self, pump_id, freq, source, feed_id, feed_stop_delay):
        try:
            self._start_direct(pump_id, freq, source)
            p=self.db.one('SELECT * FROM pump WHERE id=?',(pump_id,))
            self.db.log('离心泵启动流程','pump',pump_id,p['pump_name'] if p else '','给水泵已预运行','离心泵已启动','success',source)
            if feed_id:
                def stop_feed():
                    fp=self.db.one('SELECT * FROM pump WHERE id=?',(feed_id,))
                    if fp and fp['run_feedback']:
                        self.stop_pump(feed_id, 'feed_delay_stop')
                threading.Timer(max(0, float(feed_stop_delay or 0)), stop_feed).start()
        finally:
            self.pending_centrifugal_starts.discard(pump_id)

    def start_pump(self, pump_id, freq=None, source='manual'):
        p=self.db.one('SELECT * FROM pump WHERE id=?',(pump_id,))
        if not p: return False,'水泵不存在'
        if not self.can_start(p): return False,'水泵不可启动，可能故障/检修/禁用'
        freq=freq or p['start_frequency'] or 30
        if p['pump_type']=='centrifugal' and p['feed_pump_id']:
            if pump_id in self.pending_centrifugal_starts:
                return False, '该离心泵正在启动流程中，请稍候'
            fp=self.db.one('SELECT * FROM pump WHERE id=?',(p['feed_pump_id'],))
            if not fp:
                return False, '离心泵未找到对应给水泵'
            if not self.can_start(fp) and not bool(row_value(fp,'run_feedback',0)):
                return False, '对应给水泵不可启动，离心泵禁止启动'
            pre_delay=self.db.get_param(p['station_id'],'manual_control','feed_start_delay_seconds',3)
            stop_delay=self.db.get_param(p['station_id'],'manual_control','feed_stop_delay_seconds',5)
            feed_already_running = bool(row_value(fp,'run_feedback',0))
            if not feed_already_running:
                self._start_direct(row_value(fp,'id'), row_value(fp,'start_frequency',30) or 30, 'feed_before_centrifugal')
            self.pending_centrifugal_starts.add(pump_id)
            # 如果给水泵已经在运行，离心泵立即启动，不再等待预运行延时；
            # 如果给水泵未运行，则先启动给水泵，再按参数延时启动离心泵。
            delay = 0 if feed_already_running else max(0, float(pre_delay or 0))
            threading.Timer(delay, self._finish_centrifugal_start, args=(pump_id, freq, source, row_value(fp,'id'), stop_delay)).start()
            if feed_already_running:
                self.db.log('离心泵启动流程','pump',pump_id,p['pump_name'],'给水泵已运行','立即启动离心泵','success',source)
                return True, f'对应给水泵已运行，离心泵立即启动；离心泵启动后{stop_delay}秒停止给水泵'
            self.db.log('离心泵启动流程','pump',pump_id,p['pump_name'],'启动给水泵','等待延时后启动离心泵','success',source)
            return True, f'已启动给水泵，{pre_delay}秒后启动离心泵，离心泵启动后{stop_delay}秒停止给水泵'
        ok,msg=self._start_direct(pump_id, freq, source)
        return ok,msg

    def stop_pump(self,pump_id,source='manual'):
        p=self.db.one('SELECT * FROM pump WHERE id=?',(pump_id,))
        if not p: return False,'水泵不存在'
        self.db.close_pump_run_record(pump_id, source)
        self.db.execute('UPDATE pump SET run_feedback=0,set_frequency=0,frequency=0,stop_count=stop_count+1,updated_at=? WHERE id=?',(now(),pump_id))
        self.db.log('停止水泵','pump',pump_id,p['pump_name'],'','停止','success',source)
        return True,'停止成功'

    def set_freq(self,pump_id,freq):
        p=self.db.one('SELECT * FROM pump WHERE id=?',(pump_id,))
        if not p: return False,'水泵不存在'
        freq=max(float(p['min_frequency'] or 30),min(float(p['max_frequency'] or 50),float(freq)))
        self.db.execute('UPDATE pump SET set_frequency=?,updated_at=? WHERE id=?',(freq,now(),pump_id))
        self.db.log('设定频率','pump',pump_id,p['pump_name'],'',str(freq),'success','manual')
        return True,'频率已设定'

    def _seconds_since(self, text_time):
        if not text_time:
            return 10**9
        try:
            dt=datetime.datetime.strptime(str(text_time), '%Y-%m-%d %H:%M:%S')
            return max(0, (datetime.datetime.now()-dt).total_seconds())
        except Exception:
            return 10**9

    def _current_run_seconds(self, pump_id):
        rec=self.db.one("SELECT start_time FROM pump_run_record WHERE pump_id=? AND result='running' ORDER BY id DESC LIMIT 1", (pump_id,))
        return self._seconds_since(rec['start_time']) if rec else 0

    def _last_stop_seconds(self, pump_id):
        rec=self.db.one("SELECT end_time FROM pump_run_record WHERE pump_id=? AND result='stopped' ORDER BY id DESC LIMIT 1", (pump_id,))
        return self._seconds_since(rec['end_time']) if rec else 10**9

    def _available_pumps_with_stop_guard(self, sid, min_stop_seconds=0, emergency=False):
        pumps=self.db.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY run_seconds_total ASC,start_count ASC,display_order ASC,id ASC",(sid,))
        result=[]
        for p in pumps:
            if p['run_feedback']:
                continue
            if not self.can_start(p):
                continue
            if emergency and not bool(row_value(p,'emergency_enable',1)):
                continue
            if self._last_stop_seconds(p['id']) < float(min_stop_seconds or 0):
                continue
            result.append(p)
        return result

    def _running_pumps_can_stop(self, sid, min_run_seconds=0):
        pumps=list(self._running_main_pumps(sid,'desc'))
        return [p for p in pumps if self._current_run_seconds(p['id']) >= float(min_run_seconds or 0)]

    def _classify_control_decision(self, decision):
        text=str(decision or '')
        if '最低液位保护' in text or '低液位保护' in text:
            return ('低液位保护','保护事件','保护执行','待液位恢复')
        if '超高液位' in text or '应急' in text:
            return ('超高液位应急','应急事件','应急抢排','液位回落后退出应急')
        if '加泵' in text or '启动' in text or '最小运行台数' in text:
            return ('加泵调节','加泵事件','启动水泵','加泵后观察')
        if '减泵' in text or '退出运行' in text or '停止' in text:
            return ('减泵调节','减泵事件','停止水泵','减泵后观察')
        if '升频' in text:
            return ('升频调节','调频事件','提高频率','继续观察液位')
        if '降频' in text or '频率向经济' in text or '频率平滑' in text:
            return ('降频/平衡调节','调频事件','调整频率','继续观察液位')
        if '稳定' in text or '保持当前' in text or '轻微波动' in text or '待命' in text:
            return ('稳定运行','稳定维持','无动作','继续观察')
        return ('自动判断','运行事件','状态更新','继续观察')

    def _set_station_decision(self, sid, rise_rate, decision, control_state=None, event_state=None, action_type=None, target_device='', next_action=None, event_level='info'):
        """同步泵站控制状态，同时写入简化控制事件。

        pump_station.emergency_level 保持兼容老页面；station_control_state / station_control_event
        用于泵站监控页显示控制过程：稳定、升频、加泵、减泵、保护、应急等。
        """
        self.db.execute('UPDATE pump_station SET level_rise_rate=?, emergency_level=?, updated_at=? WHERE id=?', (rise_rate, decision, now(), sid))
        try:
            st=self.db.one('SELECT * FROM pump_station WHERE id=?',(sid,))
            pumps=self.db.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed'",(sid,))
            running=[p for p in pumps if row_value(p,'run_feedback',0)]
            standby=[p for p in pumps if (not row_value(p,'run_feedback',0)) and (not row_value(p,'fault_feedback',0)) and (not row_value(p,'manual_fault',0)) and (not row_value(p,'maintenance',0)) and row_value(p,'enabled',1) and row_value(p,'auto_enable',1)]
            fault=[p for p in pumps if row_value(p,'fault_feedback',0) or row_value(p,'manual_fault',0)]
            maint=[p for p in pumps if row_value(p,'maintenance',0)]
            avg_freq=sum(float(row_value(p,'set_frequency',0) or row_value(p,'frequency',0) or 0) for p in running)/len(running) if running else 0
            cs, es, act, nxt = self._classify_control_decision(decision)
            cs=control_state or cs
            es=event_state or es
            act=action_type or act
            nxt=next_action if next_action is not None else nxt
            self.db.upsert_control_state(sid,{
                'control_mode': row_value(st,'control_mode',''),
                'control_state': cs,
                'event_state': es,
                'adopted_level': row_value(st,'current_level',0),
                'level_rate': rise_rate,
                'running_pump_count': len(running),
                'standby_pump_count': len(standby),
                'fault_pump_count': len(fault),
                'maintenance_pump_count': len(maint),
                'avg_frequency': avg_freq,
                'current_action': act,
                'next_action': nxt,
                'reason_text': decision,
            })
            # 控制事件不要每秒刷屏：状态/决策变化时记录；稳定状态至少间隔 60 秒才再记录一次。
            sig=(cs, es, act, str(decision)[:80], str(target_device or ''))
            now_ts=time.time()
            last_sig=self.last_control_event_sig.get(sid)
            last_t=self.last_control_event_time.get(sid,0)
            min_gap=60 if cs=='稳定运行' else 8
            if sig!=last_sig or now_ts-last_t>=min_gap:
                self.db.add_control_event(sid, es, decision, act, target_device, cs, event_level, '记录')
                self.last_control_event_sig[sid]=sig
                self.last_control_event_time[sid]=now_ts
        except Exception as e:
            print('control state update error', e)

    def auto_control(self,sid):
        """V5.7.5 simplified level control.

        New strategy:
        - 超高液位：启动全部可用备用主排水泵，频率提升到最高运行频率；
        - 上限液位：加泵，运行台数控制在主泵总数的 60% 以内；
        - 下限液位：减泵，运行台数控制在主泵总数的 30% 附近；
        - 控制液位±控制死区：不调节；
        - 非死区且未触发上下限时，只做频率平滑调节。
        """
        st=self.db.one('SELECT * FROM pump_station WHERE id=?',(sid,))
        if not st:
            return
        self._remove_unavailable_running(sid)
        level=float(st['current_level'] or 0)
        rise_period=float(self.db.get_param(sid,'level_control','rise_sample_period_seconds',60) or 60)
        fall_period=float(self.db.get_param(sid,'level_control','fall_sample_period_seconds',60) or 60)
        rise_rate=float(self._level_rate(sid, rise_period))
        fall_rate=float(self._level_rate(sid, fall_period))

        control_level=float(self.db.get_param(sid,'level_control','target_level',2.0) or 2.0)
        upper_level=float(self.db.get_param(sid,'level_control','upper_level', self.db.get_param(sid,'level_control','target_level_high',2.5)) or 2.5)
        lower_level=float(self.db.get_param(sid,'level_control','lower_level', self.db.get_param(sid,'level_control','target_level_low',1.5)) or 1.5)
        high_high=float(self.db.get_param(sid,'level_control','level_high_high',4.0) or 4.0)
        deadband=max(0.0,float(self.db.get_param(sid,'level_control','control_deadband',0.10) or 0.10))
        rise_trigger=float(self.db.get_param(sid,'level_control','rise_rate_trigger',0.05) or 0.05)
        fall_trigger=float(self.db.get_param(sid,'level_control','fall_rate_trigger',0.03) or 0.03)

        fmin=float(self.db.get_param(sid,'level_control','freq_min',30) or 30)
        fnormal=float(self.db.get_param(sid,'level_control','freq_normal',38) or 38)
        fmax=float(self.db.get_param(sid,'level_control','freq_max',50) or 50)
        step=max(0.1,float(self.db.get_param(sid,'level_control','freq_step',1) or 1))
        freq_interval=max(1.0, float(self.db.get_param(sid,'level_control','freq_adjust_interval_seconds',1) or 1))
        add_interval=float(self.db.get_param(sid,'level_control','add_pump_min_interval_seconds',30) or 30)
        reduce_interval=float(self.db.get_param(sid,'level_control','reduce_pump_min_interval_seconds',120) or 120)
        min_run_seconds=float(self.db.get_param(sid,'level_control','min_run_seconds_before_stop',180) or 180)
        min_stop_seconds=float(self.db.get_param(sid,'level_control','min_stop_seconds_before_start',120) or 120)

        all_main=self.db.query("SELECT * FROM pump WHERE station_id=? AND pump_type!='feed' ORDER BY display_order,id",(sid,))
        total_main=len(all_main)
        min_count=max(0,int(st['min_running_count'] or 0))
        add_target=max(min_count, int(math.ceil(total_main*0.60))) if total_main else 0
        reduce_target=max(min_count, int(total_main*0.30)) if total_main else 0
        if total_main and reduce_target < 1:
            reduce_target=1
        now_ts=time.time()
        decision='自动平衡待命'

        def running():
            return list(self._running_main_pumps(sid,'asc'))
        def avg_freq_of(items):
            return sum(float(p['set_frequency'] or p['frequency'] or 0) for p in items)/len(items) if items else 0
        def can_freq():
            return (time.time()-self.last_freq_adjust_time.get(sid,0)) >= freq_interval
        def can_add_now():
            return (time.time()-self.last_auto_add_time.get(sid,0)) >= add_interval
        def can_reduce_now():
            return (time.time()-self.last_auto_reduce_time.get(sid,0)) >= reduce_interval
        def set_running_freq(target, reason):
            nonlocal decision
            r=running()
            if not r:
                return False
            target=max(fmin,min(fmax,float(target)))
            for rp in r:
                self.set_freq(rp['id'], target)
            self.last_freq_adjust_time[sid]=time.time()
            decision=reason
            return True
        def start_some(target_count, freq, source):
            r=running()
            if len(r) >= target_count:
                return []
            av=self._available_pumps_with_stop_guard(sid, min_stop_seconds)
            started=[]
            for pmp in av[:max(0,target_count-len(r))]:
                ok,msg=self.start_pump(pmp['id'], freq, source)
                if ok:
                    started.append(pmp['pump_code'])
            if started:
                self.last_auto_add_time[sid]=time.time()
            return started

        # 1. 超高液位：开启全部备用可用主泵。
        if level >= high_high:
            self.emergency_active[sid]=True
        if self.emergency_active.get(sid,False):
            started=start_some(total_main, fmax, 'auto_high_high_all_start')
            r=running()
            if r and can_freq():
                set_running_freq(fmax, f'超高液位 {level:.2f}m，全部运行泵提升至最高频率 {fmax:.1f}Hz')
            if started:
                decision=f'超高液位 {level:.2f}m，开启全部可用备用主泵：' + ','.join(started)
            elif not decision.startswith('超高液位'):
                decision=f'超高液位 {level:.2f}m，全部可用主泵已投入或无可用备用泵'
            if level <= upper_level:
                self.emergency_active[sid]=False
                decision=f'液位 {level:.2f}m 已回落到上限液位以下，退出超高液位应急'
            self._set_station_decision(sid, rise_rate, decision)
            return

        # 2. 控制死区：不加泵、不减泵、不调频。
        if abs(level-control_level) <= deadband:
            decision=f'液位 {level:.2f}m 位于控制死区 {control_level-deadband:.2f}~{control_level+deadband:.2f}m 内，不调节'
            self._set_station_decision(sid, rise_rate, decision, control_state='稳定运行', event_state='稳定维持', action_type='无动作', next_action='继续观察')
            return

        r=running()
        avg_freq=avg_freq_of(r)

        # 3. 上限液位：加泵，台数控制在总数 60%。
        if level >= upper_level or (level > control_level+deadband and rise_rate >= rise_trigger):
            if len(r) < add_target and can_add_now():
                # 按冷却时间一次启动一台，避免瞬间大幅过冲；下一轮继续补到 60%。
                started=start_some(len(r)+1, fnormal, 'auto_upper_level_add')
                if started:
                    decision=f'液位达到上限/上涨，启动 {started[0]}；运行台数目标 {add_target} 台（总数60%）'
                else:
                    decision=f'液位达到上限/上涨，但暂无可用备用泵；目标运行 {add_target} 台'
            elif r and can_freq() and avg_freq < fmax-0.2:
                newf=min(fmax, max(fnormal, avg_freq+step))
                set_running_freq(newf, f'液位高于控制区，运行台数已达到或等待加泵，频率提升至 {newf:.1f}Hz')
            else:
                decision=f'液位高于控制区，当前运行 {len(r)} 台，目标上限 {add_target} 台，继续观察'
            self._set_station_decision(sid, rise_rate, decision)
            return

        # 4. 下限液位：减泵，台数控制在总数 30%。
        if level <= lower_level or (level < control_level-deadband and fall_rate <= -fall_trigger):
            if r and len(r) > reduce_target:
                if can_reduce_now():
                    candidates=self._running_pumps_can_stop(sid, min_run_seconds)
                    if candidates:
                        pmp=candidates[0]
                        self.stop_pump(pmp['id'],'auto_lower_level_reduce')
                        self.last_auto_reduce_time[sid]=time.time()
                        decision=f'液位达到下限/下降，停止 {pmp["pump_code"]}；运行台数目标 {reduce_target} 台（总数30%）'
                    else:
                        decision=f'液位达到下限/下降，但运行泵未达到最小运行时间 {min_run_seconds:.0f}s，暂不减泵'
                else:
                    decision=f'液位达到下限/下降，等待减泵间隔；目标运行 {reduce_target} 台'
            elif r and can_freq() and avg_freq > fmin+0.2:
                newf=max(fmin, avg_freq-step)
                set_running_freq(newf, f'液位低于控制区，运行台数已到30%目标或等待减泵，频率降低至 {newf:.1f}Hz')
            else:
                decision=f'液位低于控制区，当前运行 {len(r)} 台，目标下限 {reduce_target} 台，继续观察'
            self._set_station_decision(sid, rise_rate, decision)
            return

        # 5. 控制液位外、上下限内：只做频率平滑，不启停泵。
        if r and can_freq():
            target=fnormal if level > control_level else fmin
            if abs(avg_freq-target) > 0.3:
                newf=avg_freq + step if avg_freq < target else avg_freq - step
                set_running_freq(max(fmin,min(fmax,newf)), f'液位未到上下限，按控制液位平滑调频至 {newf:.1f}Hz')
            else:
                decision=f'液位未到上下限，频率接近目标，保持当前运行状态'
        else:
            decision='液位未到上下限，保持当前状态'
        self._set_station_decision(sid, rise_rate, decision)
