import time
import os
import gc
import streamlit as st
import numpy as np
from matplotlib import pyplot as plt

from app_utils import setting_handler
from app_utils import display_handler
from modules.histogram_fitter import HistogramFitter
from modules.file_format.HDF5 import HDF5Writer
from modules.file_format.spe_wrapper import SpeWrapper
from modules.data_model.spectrum_data import SpectrumData
from modules.planck_fitter import PlanckFitter
from modules.color_pyrometer import ColorPyrometer
from modules.radiation_fitter import RadiationFitter
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
        plt.close(fig)


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
st.markdown('')
st.markdown('##### 計算する(Frame, Position)を選択')
selected_frame = st.number_input(
    label='計算するFrame',
    min_value=0,
    max_value=calibrated_spectrum.frame_num-1,
    value=0,
    step=1
)
selected_position = st.number_input(
    label='計算するPosition pixel',
    min_value=0,
    max_value=calibrated_spectrum.position_pixel_num-1,
    value=0,
    step=1
)
# 波長範囲を示すmask配列を作成
mask = (wavelength_arr >= lower_wavelength) & (wavelength_arr <= upper_wavelength)  # boolean配列が作成される
wavelength_fit = wavelength_arr[mask]  # boolean配列を入れてあげると、trueのところだけ抽出できる
# 対応するスペクトルデータを取得
intensity_spectrum = calibrated_spectrum.get_frame_data(frame=selected_frame)[selected_position]
intensity_fit = intensity_spectrum[mask]

# FIXME: スペクトルを表示
if st.checkbox(label='スペクトルとPlanck fitを表示', value=True):
    fig, ax = plt.subplots(figsize=(8, 4), dpi=300)
    ax.scatter(wavelength_fit, intensity_fit, color='royalblue', s=3, label='Measured')
    try:
        # フィッティングを実行
        fit_result = PlanckFitter.fit_by_planck(wavelength_fit, intensity_fit)
        ax.plot(
            wavelength_fit,
            PlanckFitter.planck_function(wavelength_fit, fit_result['T'], fit_result['scale']),
            color='red', alpha=0.8,
            label=f'Planck fit\n  {round(fit_result['T'], 1)} K\n  ± {round(fit_result['T_error'], 1) } K\n  (± {round(fit_result['T_error']/fit_result['T']*100, 2)} %)'
        )
    except Exception as e:
        pass
    ax.legend(fontsize='small')
    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel('Intensity (a.u.)')
    ax.set_title(f'{selected_calib_file}\nFrame = {selected_frame} frame, Position = {selected_position} pixel')
    st.pyplot(fig)
    plt.close(fig)

# fitting
display_handler.display_title_with_link(
    title="3. 計算を実行",
    link_title="3. 計算を実行",
    tag="start_fitting"
)

fit_model = st.radio(
    label='Fitting関数',
    options=['lorentzian', 'pseudo_voigt']
)

# if st.button("計算開始", type='primary'):
start_time = time.time() # 時間測っておく
# 与えた波長配列における温度を強度比から計算
T, warning_pairs, expected_pairs = ColorPyrometer.calculate_temperature_all_pairs(wavelength_fit, intensity_fit)
T = T[ # 0 < T < 10_000 のみを残す
    (T > 0) & (T < 10_000)
]
# fitterを作成して、温度分布から推定値と誤差などを計算
fitter = HistogramFitter(T)
fitter.compute_histogram()
fitter.fit(model=fit_model) # TODO 選べるようにする
end_time = time.time()
print(f' -> かかった時間: {round(end_time-start_time, 2)} seconds') # ログに出す

# 結果を表示
st.markdown("### フィッティング結果")
fig = fitter.get_figure(model=fit_model)
ax = fig.get_axes()[0] # titleを書き換えるために、axを取得し直す
ax.set_title(f'{selected_calib_file}\nFrame = {selected_frame} frame, Position = {selected_position} pixel')
st.pyplot(fig)
plt.close(fig)

if st.checkbox(label='警告が出たペアを可視化する', value=True):
    # plot
    fig, ax = plt.subplots(figsize=(8, 4))
    # ペアを作成
    try:
        warning_lambda1, warning_lambda2 = zip(*warning_pairs)
        plt.scatter(warning_lambda1, warning_lambda2, c='red', alpha=0.5, edgecolor='black')
        st.warning('警告が発生しました。')
    except Exception as e:
        st.success('警告は発生しませんでした。')

    try:
        excepted_lambda1, excepted_lambda2 = zip(*expected_pairs)
        plt.scatter(excepted_lambda1, excepted_lambda2, c='blue', alpha=0.5, edgecolor='black')
        st.warning('例外が発生しました。')
    except Exception as e:
        st.success('例外は発生しませんでした。')
    plt.xlabel("Wavelength 1 (nm)")
    plt.ylabel("Wavelength 2 (nm)")
    plt.title("Warning Pairs Scatter Plot")
    plt.grid(True)
    st.pyplot(fig)
    plt.close(fig)

display_handler.display_title_with_link(
    title="4. 一括計算",
    link_title="4. 一括計算",
    tag="batch_fitting"
)
st.info('(Frame, Position)のうち、どちらかを配列して計算します。比較をプロットします。', icon='✅')
st.warning('処理は重たいです')

gc.collect()

if st.checkbox(label='一括で計算を行う', value=False):
    extend_option = st.radio(label='可変にする方を選択(↑の設定から伸ばす)', options=['frame', 'position'])

    if extend_option == 'frame':
        extended_frame = st.slider(
            label=f'ゴールを設定 (Frame)',
            min_value=selected_frame+1,
            max_value=calibrated_spectrum.frame_num-1,
            value=min(selected_frame+10, calibrated_spectrum.frame_num-1)
        )
        loop_range = range(selected_frame, extended_frame+1)
    else:
        extended_position = st.slider(
            label=f'ゴールを設定 (Position)',
            min_value=selected_position+1,
            max_value=calibrated_spectrum.position_pixel_num-1,
            value=min(selected_position+10, calibrated_spectrum.position_pixel_num-1)
        )
        loop_range = range(selected_position, extended_position+1)

    if st.button(label='一括計算を実行', type='primary'):
        # Progress bar
        progress_bar = st.progress(0)
        batch_start_time = time.time()

        planck_T = []
        planck_T_error = []
        color_T = []
        color_T_error = []
        x = []

        for idx, i in enumerate(loop_range):
            if extend_option == 'frame':
                intensity_spectrum = calibrated_spectrum.get_frame_data(frame=i)[selected_position]
            else:
                intensity_spectrum = calibrated_spectrum.get_frame_data(frame=selected_frame)[i]

            intensity_fit = intensity_spectrum[mask]

            # Planck fit
            try:
                fit_result = PlanckFitter.fit_by_planck(wavelength_fit, intensity_fit)
                planck_T.append(fit_result['T'])
                planck_T_error.append(fit_result['T_error'])
            except Exception:
                planck_T.append(None)
                planck_T_error.append(None)

            # Color pyrometry
            try:
                T, _, _ = ColorPyrometer.calculate_temperature_all_pairs(wavelength_fit, intensity_fit)
                T = T[(T > 0) & (T < 10_000)]  # Filtering
                fitter = HistogramFitter(T)
                fitter.compute_histogram()
                fitter.fit(model=fit_model)
                color_T.append(fitter.fit_params[1]) # ローレンチアン、pseudo-voigtで共通
                color_T_error.append(fitter.fit_params[2])
            except Exception:
                color_T.append(np.nan)
                color_T_error.append(np.nan)

            x.append(i)
            progress_bar.progress((idx + 1) / len(loop_range))
            gc.collect()

        planck_T = np.array(planck_T)
        planck_T_error = np.array(planck_T_error)
        planck_error_ratio = planck_T_error / planck_T * 100
        color_T = np.array(color_T)
        color_T[color_T < 1_000] = np.nan
        color_T_error = np.array(color_T_error)
        color_error_ratio = color_T_error / color_T * 100
        color_error_ratio[color_error_ratio > 20] = np.nan
        x = np.array(x)

        batch_end_time = time.time()
        print(f'log: {len(loop_range)} iteratorでかかった時間 {round(batch_end_time - batch_start_time, 2)} seconds')

        # Plot results
        # 温度の比較
        fig, ax = plt.subplots(figsize=(8, 6))
        # ax.errorbar(x, planck_T, yerr=planck_T_error, fmt='o', label='Planck Fit Temperature', color='red')
        # ax.errorbar(x, color_T, yerr=color_T_error, fmt='x', label='Color Pyrometry Temperature', color='blue')
        ax.scatter(x, planck_T, marker='o', label='Planck Fit', color='red', alpha=0.9, edgecolor='black', s=20)
        ax.scatter(x, color_T, marker='^', label='Color Pyrometry', color='blue', alpha=0.9, edgecolor='black', s=20)
        ax.set_xlabel('Frame' if extend_option == 'frame' else 'Position')
        ax.set_ylabel('Temperature (K)')
        ax.set_title('Temperature Comparison')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)
        plt.close(fig)

        # 誤差の絶対値比較
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(x, planck_error_ratio, marker='o', label='Planck Fit', color='red', alpha=0.9, edgecolor='black', s=20)
        ax.scatter(x, color_error_ratio, marker='^', label='Color Pyrometry', color='blue', alpha=0.9, edgecolor='black', s=20)
        ax.set_xlabel('Frame' if extend_option == 'frame' else 'Position')
        ax.set_ylabel('Ratio (%)')
        ax.set_title('Error Comparison')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)
        plt.close(fig)

        # 誤差の割合比較
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(x, color_error_ratio/planck_error_ratio, marker='*', label='Pyrometry / Planck', color='red', alpha=0.9, edgecolor='black', s=20)
        ax.set_xlabel('Frame' if extend_option == 'frame' else 'Position')
        ax.set_ylabel('Ratio (%)')
        ax.set_title('Error Ratio')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)
        plt.close(fig)

        gc.collect()
