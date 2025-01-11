import os

import streamlit as st

import app_utils.setting_handler as setting_handler
from app_utils.file_handler import FileHander
from modules.file_format.spe_wrapper import SpeWrapper

# 共通の設定
setting_handler.set_common_setting()

# ファイル選択をする画面
# まず設定インスタンスを作成しておく。これを通してフォルダパスを読み込んだり保存したりする
setting = setting_handler.Setting()

# ここから画面と操作
st.title("📂Set folder")

st.divider()

st.subheader("読み込むフォルダ")
st.markdown(
    """
    - ここで設定したフォルダから`.spe`ファイルを選択できます。
        - Macの場合、Finderでフォルダを選択して `option + command + c`
        - Windowsの場合、エクスプローラーでフォルダを選択して `shift + control + c`
    - オリジナルのファイルは読み込むのみで変更されません。
    """
)
read_path = st.text_input(label='オリジナルの`.spe`があるフォルダまでのfull path', value=setting.setting_json['read_path'])
if st.button('読み込み先を更新'):
    setting.update_read_spe_path(read_path)

st.subheader("見つかったFiles")
setting = setting_handler.Setting() # オブジェクトを作り直して読み込み直す
# FIXME: 関数化
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
filtered_files = [] # .speで終わるもののみを入れるリスト
for file in files:
    if file.endswith('.spe') and not file.startswith('.'):
        filtered_files.append(file)
# 一通り終わったら、filesを置き換える
files = filtered_files
# 表示
spe_display_data = FileHander.get_file_list_with_OD(path_to_files, files)
for od in (set(spe_display_data['OD'])):
    st.table(spe_display_data[spe_display_data['OD'] == od])


st.divider()

st.subheader("保存先フォルダ")
st.write("- ここに計算された温度分布などのファイルが保存されます。")
save_path = st.text_input(label='保存フォルダまでのfull path', value=setting.setting_json['save_path'])
if st.button('保存先を更新'):
    setting.update_save_spe_path(save_path)
