import streamlit as st

import app_utils.setting_handler as setting_handler

st.set_option('client.showSidebarNavigation', False) # デフォルトのサイドバー表示を一旦無効にする。自分でlabelをつけるため。
setting_handler.set_common_setting()

print('log: Homeを表示')

# 共通の表示
st.title("Welcome to PlanckThermometer Emulator!")
st.markdown(
    """
    ### 【概要】
    - 校正されたスペクトルデータから温度を計算します。
        - 現在 `.spe` のみに対応しています。
        - `.spe` ファイルの中にスペクトルの波長配列が含まれている必要があります。
    - 以下のようにページが分かれています。←から選択してください。
        1. **(必須)** Set folder: `.spe`があるフォルダを選ぶページ
        2. Calibrate Spectra: 
        3. Fit by Planck: PlanckThermometerの計算をだいたい再現します。fittingのスケールや誤差も吐き出します。
        4. 2 Color Pyrometer: 二色法による温度評価を行います。
    """
)

