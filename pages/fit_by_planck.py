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
setting_handler.set_common_setting()
# まず設定インスタンスを作成しておく。これを通してフォルダパスを読み込んだり保存したりする
setting = setting_handler.Setting()

st.title("🌈 Fit by Planck")
st.divider()

st.markdown('') # 表示上のスペース確保
# 波長配列を取得しておく
st.stop()
# wavelength_arr = original_radiation.get_wavelength_arr()
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
st.markdown('##### 計算するpositionをしきい値によって決定')

