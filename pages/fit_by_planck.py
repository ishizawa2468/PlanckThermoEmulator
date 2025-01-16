import sys
import time
import os
from datetime import datetime

import streamlit as st
import numpy as np
from matplotlib import pyplot as plt

from app_utils import setting_handler
from app_utils import display_handler
from modules.file_format.HDF5 import HDF5Writer
from modules.file_format.spe_wrapper import SpeWrapper
from modules.data_model.spectrum_data import SpectrumData
from modules.radiation_fitter import RadiationFitter
from modules.planck_fitter import PlanckFitter
from modules.figure_maker import FigureMaker

# 共通の設定(このページ内ではページ内リンクを設定する)
setting_handler.set_common_setting(has_link_in_page=True)
# まず設定インスタンスを作成しておく。これを通してフォルダパスを読み込んだり保存したりする
setting = setting_handler.Setting()

st.title("🌈 Fit by Planck")

# 調査するファイルを選択
display_handler.display_title_with_link(
    title="1. ファイル選択",
    link_title="1. ファイル選択",
    tag="select_file"
)
st.markdown('') # 表示上のスペース確保
st.markdown('##### 校正されたスペクトルを選択')
# 'read_calib_path'に保存する
read_calib_path = st.text_input(
    label='校正されたスペクトルデータがあるフォルダまでのfull path',
    value=setting.setting_json['read_calibrated_path']
)
if st.button('読み込み先を更新'):
    print("読み込み先を更新")
    setting.update_read_calibrated_path(read_calib_path)

setting = setting_handler.Setting() # オブジェクトを作り直して読み込み直す
selected_files = []
for file in os.listdir(read_calib_path):
    if file.startswith('.'): # .はじまりは除く
        pass
    else:
        selected_files.append(file)

selected_calib_file = st.selectbox(
    label='`.hdf`を選択',
    options=selected_files
)

# 校正されたスペクトルファイル選択
calibrated_spectrum_path = os.path.join(read_calib_path, selected_calib_file)
calibrated_spectrum = SpectrumData(file_path=calibrated_spectrum_path)

# 元のspeと組み合わせてしきい値を決めたい場合
# FIXME: デフォルトでTrueにしているが、デフォルトでFalseにできるようにしておく。set_folder.py → setting_page.pyにして、そこに書く
need_raw_spectrum = st.checkbox(label='計算箇所を露光データをもとに選択する', value=True)
if need_raw_spectrum:
    st.markdown('')  # 表示上のスペース確保
    st.markdown('##### 参照用の露光データを選択')
    if st.checkbox(label='Raw Spectraで保存されたフォルダを参照する', value=True):
        raw_spectrum_path = os.path.join(setting.setting_json['read_radiation_path'])
        raw_spectrum_files = []
        count, default_count = 0, 0
        for file in os.listdir(raw_spectrum_path):
            if not file.startswith('.') and file.endswith('.spe'):
                try:  # ファイル名が14文字未満の場合に例外
                    if selected_calib_file[:14] in file:
                        default_count = count
                except:
                    pass
                raw_spectrum_files.append(file)
                count += 1

        selected_reference_file = st.selectbox(
            label='Raw Spectra',
            options=raw_spectrum_files,
            index=default_count
        )
        # インスタンス化して最大強度配列を取得
        raw_spectrum = SpectrumData(file_path=os.path.join(raw_spectrum_path, selected_reference_file))
        max_intensity_arr = raw_spectrum.get_max_intensity_2d_arr()
        # 強度を表示。しきい値を選択できるようにして、計算範囲の表示も行う。
        # TODO: figure makerへ
        # まず元強度のプロット
        fig, ax = plt.subplots(figsize=(8, 4))
        plt.imshow(max_intensity_arr.T, cmap='jet')
        plt.colorbar()
        plt.tight_layout()
        plt.xlabel('Time (frame)')
        plt.ylabel('Position (pixel)')
        st.pyplot(fig)


# fitting情報を設定
display_handler.display_title_with_link(
    title="2. 計算設定",
    link_title="2. 計算設定",
    tag="adjust_setting"
)

# 波長配列を取得しておく
wavelength_arr = calibrated_spectrum.get_wavelength_arr()
min_wavelength = min(wavelength_arr) # 端の値を取得
max_wavelength = max(wavelength_arr)
int_min_wavelength = int(min_wavelength) # 整数としても持っておく
int_max_wavelength = int(max_wavelength)
# 波長範囲を設定 / 範囲波長を表示
st.markdown(f'##### 採用する波長領域を設定 / {round(min_wavelength, 1)} - {round(max_wavelength, 1)} nm')
# 設定するための入力フィールド
wl_col_1, wl_col_2 = st.columns(2)
with wl_col_1:
    lower_wavelength = st.number_input(
        label=f'下限 ({int_min_wavelength} nm 以上)',
        min_value=int_min_wavelength,
        max_value=int_max_wavelength-1,
        value=600 if ((600>=int_min_wavelength) and (600<=int_max_wavelength)) else int_min_wavelength, # 読みづらくてすみませんが三項演算子です
        step=1
    )
with wl_col_2:
    upper_wavelength = st.number_input(
        label=f'上限 ({int_max_wavelength} nm 以下)',
        min_value=lower_wavelength+1,
        max_value=int_max_wavelength,
        value=800 if 800>=int_min_wavelength and 800<=int_max_wavelength else int_max_wavelength,
        step=1
    )

if need_raw_spectrum:
    st.markdown('') # 表示上のスペース確保
    st.markdown('##### 計算するpositionをしきい値によって決定')
    calculation_threshold = st.slider(
        " (これ以上の値があるframeを0にする)",
        min_value=0,
        max_value=round(max_intensity_arr.max()/10),
        value=1000,
        step=100
    )
    fig, ax = plt.subplots(figsize=(8, 4))
    filterd_intensity = max_intensity_arr.copy()
    filterd_intensity[max_intensity_arr < calculation_threshold] = np.nan
    plt.imshow(filterd_intensity.T, cmap='jet')
    plt.colorbar()
    plt.tight_layout()
    plt.xlabel('Time (frame)')
    plt.ylabel('Position (pixel)')
    st.pyplot(fig)

# fitting
display_handler.display_title_with_link(
    title="3. 計算を実行",
    link_title="3. 計算を実行",
    tag="start_fitting"
)

# 保存先ファイルを選択
save_fit_dist_path = st.text_input(
    label='温度を保存するフォルダまでのfull path',
    value=setting.setting_json['save_fit_dist_path']
)
if st.button('保存先を更新'):
    print("保存先を更新")
    setting.update_save_fit_dist_path(save_fit_dist_path)
    setting = setting_handler.Setting() # オブジェクトを作り直して読み込み直す

st.markdown('##### 以下のファイルが生成されます。')
saved_file_name = selected_calib_file[:-9] + 'dist.hdf' # calib.hdfを取り除いて、dist.hdfにする
st.write(f'`{saved_file_name}`')

if st.button("計算開始", type='primary'):
    st.markdown("### 保存先ファイルを作成")
    writer = HDF5Writer(os.path.join(save_fit_dist_path, saved_file_name)) # ファイルを作成

    st.markdown("### フィッティング中...")
    start_time = time.time() # 時間測っておく
    progress_bar = st.progress(0)

    # fittingする領域を絞る
    if need_raw_spectrum:
        # 計算対象の (frame, position) ペアを取得
        target_indices = np.argwhere(max_intensity_arr >= calculation_threshold)
    else:
        target_indices = np.array([(i, j) for i in range(max_intensity_arr.shape[0]) for j in range(max_intensity_arr.shape[1])])

    # フィッティング結果を格納するリスト
    T_result = np.zeros((calibrated_spectrum.frame_num, calibrated_spectrum.position_pixel_num))
    scale_result = np.zeros((calibrated_spectrum.frame_num, calibrated_spectrum.position_pixel_num))
    T_error_result = np.zeros((calibrated_spectrum.frame_num, calibrated_spectrum.position_pixel_num))
    scale_error_result = np.zeros((calibrated_spectrum.frame_num, calibrated_spectrum.position_pixel_num))

    # 波長範囲を示すmask配列を作成
    mask = (wavelength_arr >= lower_wavelength) & (wavelength_arr <= upper_wavelength) # boolean配列が作成される
    wavelength_fit = wavelength_arr[mask] # boolean配列を入れてあげると、trueのところだけ抽出できる

    # 全ペアに対してプランクフィッティングを実行
    total_points = len(target_indices)
    for idx, (frame, position) in enumerate(target_indices):
        try:
            # 対応するスペクトルデータを取得
            intensity_spectrum = calibrated_spectrum.get_frame_data(frame=frame)[position]
            intensity_fit = intensity_spectrum[mask]

            # フィッティングを実行
            fit_result = PlanckFitter.fit_by_planck(wavelength_fit, intensity_fit)

            # 結果を格納
            T_result[frame, position] = fit_result['T']
            scale_result[frame, position] = fit_result['scale']
            T_error_result[frame, position] = fit_result['T_error']
            scale_error_result[frame, position] = fit_result['scale_error']
        except Exception as e:
            print(f"フィッティング失敗: frame={frame}, position={position}, エラー: {e}")

        # プログレスバーを更新
        progress_bar.progress((idx + 1) / total_points)

    st.markdown("### フィッティング完了")
    end_time = time.time()
    print(f' -> かかった時間: {round(end_time-start_time, 2)} seconds') # ログに出す

    st.markdown("### 書き込み開始")
    result_list = [
        T_result,
        scale_result,
        T_error_result,
        scale_error_result,
        max_intensity_arr if need_raw_spectrum else None
    ]
    save_data_path = {
        'T': 'entry/value/T',
        'scale': 'entry/value/scale',
        'T_error': 'entry/error/T',
        'scale_error': 'entry/error/scale',
        '2d_max_intensity': 'entry/spe/2d_max_intensity',
    }
    for i, key in enumerate(save_data_path.keys()):
        if result_list[i] is not None:
            writer.write(
                data_path=save_data_path[key],
                data=result_list[i]
            )

    st.success("保存完了")

    # 結果を表示
    st.markdown("### フィッティング結果")

    fig, ax = plt.subplots(figsize=(8, 4))
    plt.imshow(T_result.T, cmap='jet')
    plt.colorbar()
    st.pyplot(fig)