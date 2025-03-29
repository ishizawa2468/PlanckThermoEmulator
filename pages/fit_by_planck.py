import os
import time
import gc
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

from app_utils import setting_handler, display_handler
from modules.file_format.HDF5 import HDF5Writer
from modules.data_model.spectrum_data import SpectrumData
from modules.planck_fitter import PlanckFitter
from log_util import logger


def configure_app():
    # 共通設定とタイトルの表示
    setting_handler.set_common_setting(has_link_in_page=True)
    st.title("🌈 Fit by Planck")
    logger.info("Fit by Planck 画面を開始")

def select_calibrated_file():
    # 校正済みスペクトルファイルの選択セクション
    display_handler.display_title_with_link("1. ファイル選択", "1. ファイル選択", "select_file")
    setting = setting_handler.Setting()
    read_calib_path = st.text_input("校正されたスペクトルデータのパス", value=setting.setting_json['read_calibrated_path'])
    if st.button("読み込み先を更新"):
        setting.update_read_calibrated_path(read_calib_path)
        logger.info(f"読み込み先を更新: {read_calib_path}")

    files = [f for f in os.listdir(read_calib_path) if not f.startswith('.')]
    selected_file = st.selectbox("`.hdf`を選択", options=files)
    return os.path.join(read_calib_path, selected_file), selected_file

def load_reference_data(setting, selected_calib_file):
    # Raw露光データをもとにフィッティング位置を選ぶオプション
    need_raw = st.checkbox("計算箇所を露光データをもとに選択する", value=True)
    max_intensity_arr = None
    if need_raw:
        st.markdown("##### 参照用の露光データを選択")
        if st.checkbox("Raw Spectraで保存されたフォルダを参照する", value=True):
            raw_path = setting.setting_json['read_radiation_path']
            raw_files = [f for f in os.listdir(raw_path) if f.endswith('.spe') and not f.startswith('.')]
            index = next((i for i, f in enumerate(raw_files) if selected_calib_file[:14] in f), 0)
            selected_raw = st.selectbox("Raw Spectra", options=raw_files, index=index)
            raw_spectrum = SpectrumData(file_path=os.path.join(raw_path, selected_raw))
            st.write('ファイル読み込み')
            max_intensity_arr = raw_spectrum.get_max_intensity_2d_arr()
            # 最大強度マップを描画
            fig, ax = plt.subplots(figsize=(8, 4))
            img = ax.imshow(max_intensity_arr.T, cmap='jet')
            plt.colorbar(img, ax=ax)
            st.pyplot(fig)
    return need_raw, max_intensity_arr

def wavelength_range_ui(wavelength_arr):
    # 波長範囲の設定UI
    display_handler.display_title_with_link("2. 採用する波長領域を設定", "2. 採用する波長領域を設定", "set_wavelength_range")
    min_wl, max_wl = int(min(wavelength_arr)), int(max(wavelength_arr))
    wl1, wl2 = st.columns(2)
    with wl1:
        lower = st.number_input("下限 (nm)", min_value=min_wl, max_value=max_wl-1, value=600 if 600 in range(min_wl, max_wl) else min_wl)
    with wl2:
        upper = st.number_input("上限 (nm)", min_value=lower+1, max_value=max_wl, value=800 if 800 in range(min_wl, max_wl) else max_wl)
    return lower, upper

def filter_positions_by_threshold(max_intensity_arr):
    # 強度しきい値に基づいて対象位置を絞り込む
    st.markdown("##### 計算するpositionをしきい値によって決定")
    threshold = st.slider("Intensity Threshold", 0, round(max_intensity_arr.max()/10), 1000, step=100)
    return threshold

def run_fitting(calibrated_spectrum, mask, lower, upper, need_raw, max_intensity_arr, save_path, output_filename):
    # プランクフィッティングの実行
    writer = HDF5Writer(os.path.join(save_path, output_filename))
    st.markdown("### フィッティング中...")
    start = time.time()
    progress = st.progress(0)

    # 対象位置の抽出
    if need_raw:
        target_indices = np.argwhere(max_intensity_arr >= mask)
    else:
        target_indices = np.array([(i, j) for i in range(calibrated_spectrum.frame_num) for j in range(calibrated_spectrum.position_pixel_num)])

    # 結果格納用配列の初期化
    T = np.zeros((calibrated_spectrum.frame_num, calibrated_spectrum.position_pixel_num))
    scale = np.zeros_like(T)
    T_err = np.zeros_like(T)
    scale_err = np.zeros_like(T)

    # 波長フィルタリング
    wl_arr = calibrated_spectrum.get_wavelength_arr()
    fit_mask = (wl_arr >= lower) & (wl_arr <= upper)
    fit_wl = wl_arr[fit_mask]

    for idx, (frame, pos) in enumerate(target_indices):
        try:
            intensity = calibrated_spectrum.get_frame_data(frame=frame)[pos][fit_mask]
            result = PlanckFitter.fit_by_planck(fit_wl, intensity)
            T[frame, pos] = result['T']
            scale[frame, pos] = result['scale']
            T_err[frame, pos] = result['T_error']
            scale_err[frame, pos] = result['scale_error']
        except Exception as e:
            logger.warning(f"Fit failed: frame={frame}, pos={pos}, error={e}")
        progress.progress((idx + 1) / len(target_indices))

    logger.info(f"Fitting completed in {round(time.time()-start, 2)} seconds")
    return T, scale, T_err, scale_err

def save_results(writer: HDF5Writer, result_dict: dict):
    # フィッティング結果をHDF5に保存する
    for path, data in result_dict.items():
        if data is not None:
            writer.write(data_path=path, data=data)

def show_results(T_result):
    # T 分布の可視化
    fig, ax = plt.subplots(figsize=(8, 4))
    img = ax.imshow(T_result.T, cmap='jet')
    plt.colorbar(img, ax=ax)
    st.pyplot(fig)

# --------------------- Main 処理フロー ---------------------
configure_app()
path, filename = select_calibrated_file()
calibrated = SpectrumData(file_path=path)
setting = setting_handler.Setting()
need_raw, max_intensity = load_reference_data(setting, filename)

wavelengths = calibrated.get_wavelength_arr()
lower_wl, upper_wl = wavelength_range_ui(wavelengths)

threshold = None
if need_raw:
    threshold = filter_positions_by_threshold(max_intensity)

# 実行セクション（保存先とボタン）
display_handler.display_title_with_link("3. 計算を実行", "3. 計算を実行", "start_fitting")
save_path = st.text_input("保存先フォルダ", value=setting_handler.Setting().setting_json['save_fit_dist_path'])
# ディレクトリ存在チェック
if st.button("保存先を更新"):
    if os.path.isdir(save_path):
        setting_handler.Setting().update_save_fit_dist_path(save_path)
        st.success("保存先を更新しました。")
        logger.info(f"保存先を更新: {save_path}")
    else:
        st.error("指定されたパスは存在しないか、フォルダではありません。")
        logger.warning(f"無効な保存先が指定されました: {save_path}")
output_file = filename.replace("_calib.hdf", "_dist.hdf")
st.write(f"出力ファイル: `{output_file}`")

# フィッティング処理の実行と保存
if st.button("計算開始", type='primary'):
    # 保存先パスがフォルダかチェック
    if os.path.isdir(save_path):
        T, scale, T_err, scale_err = run_fitting(calibrated, threshold, lower_wl, upper_wl, need_raw, max_intensity,
                                                 save_path, output_file)
        dist_path = os.path.join(save_path, output_file)
        writer = HDF5Writer(dist_path)
        save_results(writer, {
            "entry/value/T": T,
            "entry/value/scale": scale,
            "entry/error/T": T_err,
            "entry/error/scale": scale_err,
            "entry/spe/2d_max_intensity": max_intensity if need_raw else None
        })
        st.success(f"保存完了: `{dist_path}`")
        show_results(T)
        gc.collect()
    else:
        st.error("指定されたパスは存在しないか、ディレクトリではありません。")
        logger.warning(f"無効な保存先が指定されました: {save_path}")
        st.stop()
