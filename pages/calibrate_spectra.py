import os
from datetime import datetime
import pandas as pd
import streamlit as st

from app_utils import setting_handler, display_handler
from app_utils.file_handler import FileHandler
from app_utils.writer import CalibrateSpectraWriter
from modules.file_format.spe_wrapper import SpeWrapper
from modules.data_model.spectrum_data import SpectrumData
from log_util import logger


def configure():
    setting_handler.set_common_setting(has_link_in_page=True)
    st.title("📈 Calibrate Spectra")
    logger.info("Calibrate Spectra 画面を開始")

def display_path_input(label: str, setting_key: str, update_callback):
    setting = setting_handler.Setting()
    default_value = setting.setting_json[setting_key]
    user_input = st.text_input(label=label, value=default_value)
    if st.button(f"{label} を更新"):
        update_callback(user_input)
        logger.info(f"{label} を更新: {user_input}")
    return user_input

def load_spe_files(path):
    try:
        files = sorted(
            [f for f in os.listdir(path) if f.endswith(".spe") and not f.startswith(".")]
        )
        if not files:
            st.warning(f"有効な `.spe` ファイルが {path} にありません。")
            st.stop()
        return files
    except Exception as e:
        st.error("パスが不正です。存在するフォルダを指定してください。")
        logger.error(f"ファイル読み込みエラー: {e}")
        st.stop()

def display_spe_metadata(spe: SpeWrapper):
    try:
        spe.get_params_from_xml()
        st.write(f"フィルター: `{spe.OD}`")
        st.write(f"Framerate: `{spe.framerate}` fps")
        date_obj = datetime.fromisoformat(spe.date[:26]+spe.date[-6:])
        st.write(f"取得日時: `{date_obj.strftime('%Y年%m月%d日 %H時%M分%S秒')}`")
    except Exception as e:
        logger.warning(f"メタデータ取得に失敗: {e}")

def collect_calibration_files(path_to_calib):
    lamp_files = {}
    filter_files = {}
    all_calib_files = []
    for dirpath, _, filenames in os.walk(path_to_calib):
        for filename in filenames:
            if filename.startswith('.'):
                continue
            full_path = os.path.join(dirpath, filename)
            if filename.endswith('.csv'):
                lamp_files[filename] = full_path
            elif 'std.spe' in filename:
                period = os.path.normpath(dirpath).split(os.sep)[-2]
                OD = filename[0]
                stream = filename[2:-8]
                filter_files.setdefault(period, {}).setdefault(OD, {}).setdefault(stream, {})[filename] = full_path
                all_calib_files.append(full_path)
    return lamp_files, filter_files, all_calib_files

def display_calibration_selection(lamp_files, filter_files):
    st.info('時期とODを選択してください ↓', icon='💡')

    selected_lamp_file = st.selectbox('参照ランプデータ', options=lamp_files.keys())
    selected_lamp_path = lamp_files[selected_lamp_file]

    try:
        # period, OD
        period_col, OD_col = st.columns(2)
        with period_col:
            selected_period = st.selectbox(label='時期', options=filter_files.keys())
        with OD_col:
            selected_OD = st.selectbox(label='OD', options=filter_files[selected_period].keys())
        # up, down
        up_col, down_col = st.columns(2)
        with up_col:
            selected_up_filter_file = st.selectbox(
                label='Up (自動)',
                options=filter_files[selected_period][selected_OD]['Up'].keys()
            )
            selected_up_filter_path = filter_files[selected_period][selected_OD]['Up'][selected_up_filter_file]
        with down_col:
            selected_down_filter_file = st.selectbox(
                label='Down (自動)',
                options=filter_files[selected_period][selected_OD]['Down'].keys()
            )
            selected_down_filter_path = filter_files[selected_period][selected_OD]['Down'][selected_down_filter_file]
    except Exception as e:
        st.write(e.__repr__())
        st.stop()

    return selected_lamp_path, selected_up_filter_path, selected_down_filter_path

def execute_calibration(spe: SpeWrapper, path_to_spe: str, lamp_path: str, up_path: str, down_path: str, save_path: str):
    st.info('書き込み開始', icon='➡️')
    output_name = spe.file_name + '_calib.hdf'
    path_to_hdf5 = os.path.join(save_path, output_name)

    radiation = SpectrumData(path_to_spe)
    lamp_spectrum = pd.read_csv(lamp_path, header=None, names=["wavelength", "intensity"])
    up_response = SpeWrapper(up_path).get_frame_data(frame=0)[0]
    down_response = SpeWrapper(down_path).get_frame_data(frame=0)[0]

    # ログ出力
    os.makedirs('log', exist_ok=True)
    with open('log/calibration_log.txt', 'a') as f:
        f.write(f"{datetime.now()}\n\tfrom {spe.filepath}\n\tto {path_to_hdf5}\n\twith {lamp_path}\n\t     {up_path}\n\t     {down_path}\n\n")

    CalibrateSpectraWriter.output_to_hdf5(
        original_radiation=radiation,
        lamp_spectrum=lamp_spectrum,
        up_response=up_response,
        down_response=down_response,
        path_to_hdf5=path_to_hdf5
    )

    st.success(f'完了: `{path_to_hdf5}`', icon='🎊')
    logger.info(f'校正結果を出力: {path_to_hdf5}')


# ------------------------ MAIN ------------------------
configure()

display_handler.display_title_with_link("1. 露光ファイル選択", "1. 露光ファイル選択", "select_file")
read_path = display_path_input("オリジナルの.speフォルダパス", 'read_radiation_path', setting_handler.Setting().update_read_radiation_path)
files = load_spe_files(read_path)
spe_display_data = FileHandler.get_file_list_with_OD(read_path, files)
for od in set(spe_display_data['OD']):
    st.table(spe_display_data[spe_display_data['OD'] == od])
st.divider()
file_name = st.selectbox("ファイルを選択", files)

path_to_spe = os.path.join(read_path, file_name)
spe = SpeWrapper(path_to_spe)
display_spe_metadata(spe)

# 校正設定
display_handler.display_title_with_link("2. 校正設定", "2. 校正設定", "set_parameter")
calib_path = display_path_input("校正データフォルダパス", 'calib_setting_path', setting_handler.Setting().update_calib_setting_path)
lamp_files, filter_files, all_calib_files = collect_calibration_files(calib_path) # all_calib_files は display_calibration_selection で使わなくなった
lamp_path, up_path, down_path = display_calibration_selection(lamp_files, filter_files)

# 保存先と出力設定
display_handler.display_title_with_link("3. 確認して校正実行", "3. 確認して校正実行", "calibrate")
save_path = display_path_input("保存フォルダパス", 'save_calibrated_path', setting_handler.Setting().update_save_calibrated_path)
file_format = st.radio('出力ファイル形式', ['`.hdf5`', '`.spe`'])

if file_format == '`.hdf5`':
    if st.button('`.hdf5` として書き出し', type='primary'):
        execute_calibration(spe, path_to_spe, lamp_path, up_path, down_path, save_path)
else:
    st.warning('`.spe`形式での出力は未対応です。必要なら実装してください')
    st.stop()
