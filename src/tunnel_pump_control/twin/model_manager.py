


def import_glb_model(station_id: int, source_path: str, model_name: str) -> int:
    pass

def set_active_model(station_id: int, model_id: int) -> None:
    pass

def get_active_model(station_id: int):
    pass


def build_station_twin_state(db, station_id: int):
    """
    职责：构建三维界面需要的实时状态数据。
    pump_station
    pump
    main_pipe
    instrument
    camera
    station_control_state
    station_control_event

    data/twin_viewer/twin_state.json
    """
    return

def write_twin_state_file(state: dict, output_path: str) -> None:
    pass