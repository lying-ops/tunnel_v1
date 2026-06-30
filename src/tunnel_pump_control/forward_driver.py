"""Modbus TCP forward driver.

This optional driver makes the software act as a Modbus TCP server for an upper-level
SCADA/dispatch system. It exposes the local modbus_point last_value table as 4x holding
registers. All values are float32 and use two registers.

Default bind: 0.0.0.0:1502, unit id 1. Port 502 usually requires administrator privileges.
"""
import os, sys, time, socket, struct, threading
from .db import Database, now

class ModbusForwardServer:
    def __init__(self, db=None, host='0.0.0.0', port=1502, unit_id=1, byte_order='ABCD'):
        self.db = db or Database()
        self.host = host
        self.port = int(port)
        self.unit_id = int(unit_id)
        self.byte_order = byte_order or 'ABCD'
        self.running = False
        self.sock = None

    def _load_config(self):
        try:
            r = self.db.one('SELECT * FROM forward_driver_config WHERE id=1')
            if r:
                self.host = r['bind_ip'] or self.host
                self.port = int(r['port'] or self.port)
                self.unit_id = int(r['slave_id'] or self.unit_id)
                self.byte_order = r['byte_order'] or self.byte_order
        except Exception:
            pass

    def start(self):
        self._load_config()
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(8)
        print(f'Forward Modbus TCP server listening on {self.host}:{self.port}, unit {self.unit_id}')
        while self.running:
            conn, addr = self.sock.accept()
            t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
            t.start()

    def stop(self):
        self.running = False
        try:
            if self.sock: self.sock.close()
        except Exception:
            pass

    def _addr_to_point(self, address):
        # Address is protocol 0-based holding register offset; UI address = 40001 + offset.
        ui_addr = 40001 + int(address)
        return self.db.one('SELECT * FROM modbus_point WHERE register_address=? ORDER BY id LIMIT 1', (ui_addr,))

    def _float_to_regs(self, value):
        try: v = float(value)
        except Exception: v = 0.0
        b = struct.pack('>f', v)
        if self.byte_order == 'CDAB': b = b[2:4] + b[0:2]
        elif self.byte_order == 'BADC': b = bytes([b[1], b[0], b[3], b[2]])
        elif self.byte_order == 'DCBA': b = b[::-1]
        return list(struct.unpack('>HH', b))

    def _regs_to_float(self, regs):
        b = struct.pack('>HH', int(regs[0]) & 0xffff, int(regs[1]) & 0xffff)
        if self.byte_order == 'CDAB': b = b[2:4] + b[0:2]
        elif self.byte_order == 'BADC': b = bytes([b[1], b[0], b[3], b[2]])
        elif self.byte_order == 'DCBA': b = b[::-1]
        return struct.unpack('>f', b)[0]

    def _read_holding(self, start, count):
        regs = []
        for off in range(count):
            pt = self._addr_to_point(start + off)
            if pt:
                # Only the first register address of each float32 has a point; the next one is its low word.
                pair = self._float_to_regs(pt['last_value'])
                regs.append(pair[0])
            else:
                # Check whether this is the second word of previous float32.
                prev = self._addr_to_point(start + off - 1)
                if prev:
                    regs.append(self._float_to_regs(prev['last_value'])[1])
                else:
                    regs.append(0)
        return regs

    def _write_registers(self, start, values):
        # For float32 writes, write only when two registers are available at the mapped start address.
        if len(values) >= 2:
            pt = self._addr_to_point(start)
            if pt:
                v = self._regs_to_float(values[:2])
                self.db.execute('UPDATE modbus_point SET last_value=?, command_value=?, quality=?, last_update_time=? WHERE id=?',
                                (str(round(v, 6)), str(round(v, 6)), 'written_by_forward', now(), pt['id']))
                return True
        # Single-register write fallback, stored as numeric value.
        pt = self._addr_to_point(start)
        if pt:
            v = float(values[0])
            self.db.execute('UPDATE modbus_point SET last_value=?, command_value=?, quality=?, last_update_time=? WHERE id=?',
                            (str(v), str(v), 'written_by_forward', now(), pt['id']))
            return True
        return False

    def handle_client(self, conn, addr):
        with conn:
            while True:
                mbap = conn.recv(7)
                if not mbap or len(mbap) < 7: return
                tid, pid, length, unit = struct.unpack('>HHHB', mbap)
                pdu = conn.recv(max(0, length - 1))
                if not pdu: return
                fc = pdu[0]
                try:
                    if fc == 3 and len(pdu) >= 5:
                        start, count = struct.unpack('>HH', pdu[1:5])
                        regs = self._read_holding(start, count)
                        data = struct.pack('>BB', fc, len(regs)*2) + struct.pack('>' + 'H'*len(regs), *regs)
                    elif fc == 6 and len(pdu) >= 5:
                        start, val = struct.unpack('>HH', pdu[1:5])
                        self._write_registers(start, [val])
                        data = pdu[:5]
                    elif fc == 16 and len(pdu) >= 6:
                        start, count, byte_count = struct.unpack('>HHB', pdu[1:6])
                        raw = pdu[6:6+byte_count]
                        vals = list(struct.unpack('>' + 'H'*(len(raw)//2), raw))
                        self._write_registers(start, vals)
                        data = struct.pack('>BHH', fc, start, count)
                    else:
                        data = struct.pack('>BB', fc | 0x80, 1)
                    header = struct.pack('>HHHB', tid, 0, len(data)+1, unit)
                    conn.sendall(header + data)
                except Exception:
                    data = struct.pack('>BB', fc | 0x80, 4)
                    header = struct.pack('>HHHB', tid, 0, len(data)+1, unit)
                    conn.sendall(header + data)

def main():
    server = ModbusForwardServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

if __name__ == '__main__':
    main()
