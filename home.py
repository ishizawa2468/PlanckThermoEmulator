import streamlit as st

import app_utils.setting_handler as setting_handler

from log_util import logger

# デフォルトのサイドバーを隠して、加工したサイドバーを表示する処理
def hide_sidebar():
    # 初回実行を判定するためのフラグを session_state に用意
    if "sidebar_navigation_disabled" not in st.session_state:
        st.session_state.sidebar_navigation_disabled = False  # まだ無効化していない状態

    # もし無効化していないなら、オプションを False に書き換えて rerun する
    if st.session_state.sidebar_navigation_disabled is False:
        st.set_option('client.showSidebarNavigation', False) # デフォルトのサイドバー表示を一旦無効にする。自分でlabelをつけるため。
        st.session_state.sidebar_navigation_disabled = True  # これ以上変更しないようフラグを更新
        st.rerun()

# ================
# メイン処理
# =================
hide_sidebar()

setting_handler.set_common_setting()

logger.info('Home画面のロード開始')
st.title("Welcome to PlanckThermometer Emulator!")
st.markdown(
    """
    ### 【概要】
    - 校正されたスペクトルデータから温度を計算します。
        - 現在 `.spe` のみに対応しています。
        - `.spe` ファイルの中にスペクトルの波長配列が含まれている必要があります。
    - 以下のようにページが分かれています。←から選択してください。
        1. Calibrate Spectra: 
        2. Fit by Planck: PlanckThermometerの計算をだいたい再現します。fittingのスケールや誤差も吐き出します。
        3. 2 Color Pyrometer: 二色法による温度評価を行います。
    """
)

