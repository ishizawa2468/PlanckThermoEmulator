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

