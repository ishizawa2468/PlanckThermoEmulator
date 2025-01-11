import sys
import time
import os
from datetime import datetime

import streamlit as st
import numpy as np

from app_utils import setting_handler
from app_utils import display_handler
from modules.file_format.spe_wrapper import SpeWrapper
from modules.data_model.raw_spectrum_data import RawSpectrumData
from modules.radiation_fitter import RadiationFitter
from modules.figure_maker import FigureMaker

# 共通の設定
# ページリンクを設定する
setting_handler.set_common_setting(has_link_in_page=True)
# まず設定インスタンスを作成しておく。これを通してフォルダパスを読み込んだり保存したりする
setting = setting_handler.Setting()

st.title("📈 Calibrate Spectra")
st.divider()

# 調査するファイルを選択
display_handler.display_title_with_link(
    title="1. 温度を計算するファイルを選択",
    link_title="1. 露光ファイル選択",
    tag="select_file"
)

path_to_files = setting.setting_json['read_path'] # 別ページで設定した読み込みpathを取得
# ファイルが得られるpathかどうか確認
try:
    files = os.listdir(path_to_files)
    if not any(file.endswith('.spe') and not file.startswith('.') for file in files):
        st.write(f'有効なファイルが {path_to_files} にありません。')
        st.stop()
except Exception as e:
    st.subheader('Error: pathが正しく設定されていません。ファイルが存在するフォルダを指定してください。')
    st.subheader('現在の設定されているpath: {}'.format(path_to_files))
    st.stop() # 以降の処理をしない

# ファイルが見つかった場合
files.sort() # 見やすいようにソートしておく
if st.checkbox('.spe拡張子のみを選択肢にする', value=True):
    filtered_files = [] # .speで終わるもののみを入れるリスト
    for file in files:
        if file.endswith('.spe') and not file.startswith('.'):
            filtered_files.append(file)
    # 一通り終わったら、filesを置き換える
    files = filtered_files
file_name = st.selectbox("ファイルを選択", files)

# もしspeファイルが選択されたらファイル情報を表示し、そうでなければ描画を終了する
if file_name.endswith('.spe'):
    # speファイルオブジェクトを作成する
    path_to_spe = os.path.join(path_to_files, file_name)
    spe = SpeWrapper(path_to_spe)
    # radiationにもしておく
    original_radiation = RawSpectrumData(spe)
    try:
        # おそらくspe ver.3 以上でないとできない。あと設定されていないと取得できない。
        spe.get_params_from_xml()
        # メタ情報を表示
        # FIXME: 辞書にして表示で揃える
        st.write(f'フィルター: {spe.OD}')
        st.write(f'Framerate: {spe.framerate} fps')
        # HACK: chatgpt -> Pythonのdatetime.fromisoformatは標準のISO 8601形式に従い、ミリ秒部分は最大6桁までしか対応していません。
        date_obj = datetime.fromisoformat(spe.date[:26]+spe.date[-6:])
        calibration_date_obj = datetime.fromisoformat(spe.calibration_date[:26]+spe.calibration_date[-6:])
        st.write(f'取得日時: {date_obj.strftime("%Y年%m月%d日 %H時%M分%S秒")}')

    except Exception as e:
        print(e)
else:
    st.stop()

st.divider()

display_handler.display_title_with_link(
    title="2. パラメータを設定",
    link_title="2. パラメータを設定",
    tag="set_parameter"
)

st.markdown('') # 表示上のスペース確保
# 波長配列を取得しておく
wavelength_arr = original_radiation.get_wavelength_arr()
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
    upper = st.number_input(
        label=f'上限 ({int_max_wavelength} nm 以下)',
        min_value=lower_wavelength+1,
        max_value=int_max_wavelength,
        value=800 if 800>=int_min_wavelength and 800<=int_max_wavelength else int_max_wavelength,
        step=1
    )

st.markdown('') # 表示上のスペース確保
st.markdown('##### 校正ファイルを選択')
# ランプデータ
ramp_data_files = ['demo']
st.selectbox(
    label='参照ランプデータ',
    options=ramp_data_files
)
# フィルターデータ
calibration_select_option = st.radio(
    label='選択オプション',
    options=['ファイルから選択', '日時とODから選択'],
)
match calibration_select_option:
    case '日時とODから選択':
        st.write('実装されていません')
        st.stop()
    case 'ファイルから選択':
        # 校正ファイルの選択肢を取得
        up_col, down_col = st.columns(2)
        up_stream_data_files = ['demo']
        down_stream_data_files = ['demo']
        with up_col:
            st.selectbox(
                label='Up 応答補正データ (時期, OD)',
                options=up_stream_data_files
            )
        with down_col:
            st.selectbox(
                label='Down 応答補正データ (時期, OD)',
                options=down_stream_data_files
            )
    case _:
        st.write('想定外の挙動')
        st.stop()

st.markdown('') # 表示上のスペース確保
st.markdown('##### 計算するpositionをしきい値によって決定')

