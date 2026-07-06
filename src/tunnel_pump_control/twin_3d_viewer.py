import os
import json
import threading
import time


STATUS_COLORS = {
    'running': (0.06, 0.82, 0.38, 1.0),
    'standby': (0.18, 0.66, 1.0, 1.0),
    'fault': (1.0, 0.2, 0.2, 1.0),
    'maintenance': (0.96, 0.76, 0.26, 1.0),
    'stopped': (0.55, 0.58, 0.62, 1.0),
    'disabled': (0.34, 0.37, 0.42, 1.0),
    'normal': (0.06, 0.82, 0.38, 1.0),
    'good': (0.06, 0.82, 0.38, 1.0),
    'bypassed': (0.66, 0.33, 0.97, 1.0),
    'unknown': (0.52, 0.62, 0.72, 1.0),
}


def normalize_status(st):
    raw = str(st or '')
    x = raw.upper()
    if raw.find('故障') != -1 or raw.find('报警') != -1 or x.find('FAULT') != -1 or x.find('ALARM') != -1:
        return 'fault'
    if raw.find('检修') != -1 or raw.find('维护') != -1 or x.find('MAINT') != -1:
        return 'maintenance'
    if raw.find('备用') != -1 or raw.find('待机') != -1 or x.find('STANDBY') != -1 or x.find('SPARE') != -1:
        return 'standby'
    if raw.find('运行') != -1 or x.find('RUNNING') != -1 or x == 'RUN' or x.find('START') != -1:
        return 'running'
    if raw.find('屏蔽') != -1 or x.find('BYPASS') != -1 or x.find('SHIELD') != -1:
        return 'bypassed'
    if raw.find('停止') != -1 or raw.find('停机') != -1 or raw.find('未绑定') != -1 or x.find('STOP') != -1 or x.find('DISABLED') != -1 or x.find('OFFLINE') != -1:
        return 'stopped'
    if x.find('GOOD') != -1 or x.find('NORMAL') != -1:
        return 'normal'
    return x.lower() if x else ''


def get_device_code(name):
    n = str(name or '').upper().replace(' ', '')
    if not n or n.startswith('ANNO_'):
        return ''
    if n.startswith('P') and n[1:].isdigit():
        return n
    if n.startswith('JP') and n[2:].isdigit():
        return n
    patterns = ['PIPE_', 'LT', 'FT', 'PT', 'CAM', 'TANK', 'CAB']
    for pat in patterns:
        if n.startswith(pat):
            return n
    return ''


def load_twin_state(state_path):
    if not state_path or not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def get_status_for_code(state, code):
    k = str(code).upper()
    for group_name in ['pumps', 'pipes', 'meters', 'cameras', 'tanks']:
        group = state.get(group_name, {})
        if k in group:
            d = group[k]
            return normalize_status(d.get('status') or d.get('statusText'))
    return None


def set_mesh_status_color(mesh, status):
    if not hasattr(mesh, 'visual'):
        return
    status_key = normalize_status(status)
    color = STATUS_COLORS.get(status_key, STATUS_COLORS['unknown'])
    if hasattr(mesh.visual, 'vertex_colors'):
        mesh.visual.vertex_colors = color
    elif hasattr(mesh.visual, 'face_colors'):
        mesh.visual.face_colors = color


def show_glb_model(model_path, state_path=None, title='泵站数字孪生3D查看器'):
    try:
        import trimesh
        import pyglet
        from trimesh.viewer.windowed import SceneViewer
        
        scene = trimesh.load(model_path, force='scene')
        
        if state_path:
            state = load_twin_state(state_path)
            
            for name, mesh in scene.geometry.items():
                code = get_device_code(name)
                if code:
                    status = get_status_for_code(state, code)
                    if status:
                        set_mesh_status_color(mesh, status)
        
        viewer = SceneViewer(scene, title=title)
        viewer.run()
        
        return True
    except ImportError as e:
        print(f'3D查看器依赖缺失: {e}')
        print('请运行: pip install trimesh pyglet')
        return False
    except Exception as e:
        print(f'3D查看器启动失败: {e}')
        return False


def show_glb_in_thread(model_path, state_path=None, title='泵站数字孪生3D查看器'):
    thread = threading.Thread(
        target=show_glb_model,
        args=(model_path, state_path, title),
        daemon=True
    )
    thread.start()
    return thread