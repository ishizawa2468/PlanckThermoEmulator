import os
from datetime import datetime

import pandas as pd
import streamlit as st

from app_utils import setting_handler
from app_utils import display_handler
from app_utils.file_handler import FileHandler
from app_utils.writer import CalibrateSpectraWriter
from modules.file_format.spe_wrapper import SpeWrapper
from modules.data_model.raw_spectrum_data import RawSpectrumData

# 共通の設定(このページ内ではページ内リンクを設定する)
setting_handler.set_common_setting(has_link_in_page=True)

st.title("📈 Calibrate Spectra")
st.divider()

# 調査するファイルを選択
display_handler.display_title_with_link(
    title="1. 露光ファイル選択",
    link_title="1. 露光ファイル選択",
    tag="select_file"
)

# 設定インスタンスを作成しておく。これを通してフォルダパスを読み込んだり保存したりする
setting = setting_handler.Setting()

st.markdown('') # 表示上のスペース確保
st.markdown('##### 読み込むフォルダを設定')
st.markdown(
    """
    - ここで設定したフォルダから`.spe`ファイルを選択できます。
        - Macの場合、Finderでフォルダを選択して `option + command + c`
        - Windowsの場合、エクスプローラーでフォルダを選択して `shift + control + c`
    - オリジナルのファイルは読み込むのみで変更されません。
    """
)
read_radiation_path = st.text_input(label='オリジナルの`.spe`があるフォルダまでのfull path', value=setting.setting_json['read_radiation_path'])
if st.button('読み込み先を更新'):
    setting.update_read_spe_path(read_radiation_path)

st.divider()
st.markdown('') # 表示上のスペース確保
st.markdown('##### ファイルを選択')
setting = setting_handler.Setting() # オブジェクトを作り直して読み込み直す

path_to_files = setting.setting_json['read_radiation_path'] # 別ページで設定した読み込みpathを取得
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
spe_display_data = FileHandler.get_file_list_with_OD(path_to_files, files)
for od in (set(spe_display_data['OD'])):
    st.table(spe_display_data[spe_display_data['OD'] == od])

# .speのみ
file_name = st.selectbox("ファイルを選択", files)

# もしspeファイルが選択されたらファイル情報を表示し、そうでなければ描画を終了する
if file_name.endswith('.spe'):
    # speファイルオブジェクトを作成する
    path_to_spe = os.path.join(path_to_files, file_name)
    spe = SpeWrapper(path_to_spe)
    # radiationにもしておく
    try:
        # おそらくspe ver.3 以上でないとできない。あと設定されていないと取得できない。
        # 失敗した場合はターミナルにログを吐き出してskipされる
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
    title="2. 校正設定",
    link_title="2. 校正設定",
    tag="set_parameter"
)

st.markdown('') # 表示上のスペース確保
st.markdown('##### 校正データ読み込みフォルダを設定')
calib_setting_path = st.text_input(label='校正データフォルダまでのfull path', value=setting.setting_json['calib_setting_path'])
if st.button('データ読み込み先を更新 '):
    setting.update_calib_spe_path(calib_setting_path)

setting = setting_handler.Setting() # オブジェクトを作り直して読み込み直す
path_to_calib = setting.setting_json['calib_setting_path']

# 校正用ファイルを取得する
lamp_files = {} # key=filename, value=fullpath
filter_files = {} # 階層化した辞書で、key1=period, key2=OD, key3=stream, key4=filename, value=filename
all_calib_files = [] # 仕様が変わったときに選択できるように作っておく
for dirpath, dirnames, filenames in os.walk(path_to_calib):
    for filename in filenames:
        # .始まりは最初にskip
        if filename.startswith('.'):
            continue
        # 仕分ける
        if filename.endswith('.csv'): # ランプデータ
            lamp_files[filename] = os.path.join(dirpath, filename)
        elif 'std.spe' in filename:
            # NOTE: かなりファイル名依存性が高い。少し仕様が変わると使えなくなる
            period = dirpath.split('/')[-2] # FIXME もしかしたらwindowsだめかも。OSによって区切り文字を辞書にして利用する必要がある
            OD = filename[0]
            stream = filename[2:-8]
            # filter_files内でODとstreamがすでに存在するか確認して追加
            if period not in filter_files:
                filter_files[period] = {} # たとえば2024_0403がなければkeyに追加する。いきなり複数keyを追加しようとすると失敗する
            if OD not in filter_files[period]:
                filter_files[period][OD] = {}
            if stream not in filter_files[period][OD]:
                filter_files[period][OD][stream] = {}

            filter_files[period][OD][stream][filename] = os.path.join(dirpath, filename)
            # うまく指定できないときのため
            all_calib_files.append(os.path.join(dirpath, filename))
        else:
            continue

st.markdown('') # 表示上のスペース確保
st.markdown('##### 校正ファイルを選択')
# ランプデータ
selected_lamp_file = st.selectbox(
    label='参照ランプデータ',
    options=lamp_files.keys()
)
selected_lamp_path = lamp_files[selected_lamp_file] # fullpathにしておく
# フィルターデータ
calibration_select_option = st.radio(
    label='選択オプション',
    options=['時期とODから選択', 'ファイルから選択(時期・ODで指定できなかったとき用)'],
)
match calibration_select_option:
    case '時期とODから選択':
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
                    label='Up',
                    options=filter_files[selected_period][selected_OD]['Up'].keys()
                )
                selected_up_filter_path = filter_files[selected_period][selected_OD]['Up'][selected_up_filter_file] # fullpathにしておく
            with down_col:
                selected_down_filter_file = st.selectbox(
                    label='Down',
                    options=filter_files[selected_period][selected_OD]['Down'].keys()
                )
                selected_down_filter_path = filter_files[selected_period][selected_OD]['Down'][selected_down_filter_file] # fullpathにしておく
        except Exception as e:
            st.write(e.__repr__())
            st.stop()
    case 'ファイルから選択(時期・ODで指定できなかったとき用)':
        # 校正ファイルの選択肢を取得
        up_col, down_col = st.columns(2)
        with up_col:
            st.selectbox(
                label='Up 応答補正データ (時期, OD)',
                options=all_calib_files
            )
        with down_col:
            st.selectbox(
                label='Down 応答補正データ (時期, OD)',
                options=all_calib_files
            )
    case _:
        st.write('想定外の挙動')
        st.stop()

st.divider()
display_handler.display_title_with_link(
    title="3. 確認して校正実行",
    link_title="3. 確認して校正実行",
    tag="calibrate"
)

st.markdown('') # 表示上のスペース確保
st.markdown('##### 元データの確認')
st.write(f'ファイル名: `{spe.file_name}.spe`') # speでないとエラーになる
try:
    # おそらくspe ver.3 以上でないとできない。あと設定されていないと取得できない。
    # 失敗した場合はターミナルにログを吐き出してskipされる
    spe.get_params_from_xml()
    # メタ情報を表示
    # FIXME: 辞書にして表示で揃える
    st.write(f'フィルター: {spe.OD}')
    st.write(f'Framerate: {spe.framerate} fps')
    # HACK: chatgpt -> Pythonのdatetime.fromisoformatは標準のISO 8601形式に従い、ミリ秒部分は最大6桁までしか対応していません。
    date_obj = datetime.fromisoformat(spe.date[:26] + spe.date[-6:])
    calibration_date_obj = datetime.fromisoformat(spe.calibration_date[:26] + spe.calibration_date[-6:])
    st.write(f'取得日時: {date_obj.strftime("%Y年%m月%d日 %H時%M分%S秒")}')
except Exception as e:
    print(e)

st.markdown('') # 表示上のスペース確保
st.markdown('##### 校正データの確認')
selected_calib_files = {
    'lamp': selected_lamp_path,
    'Up': selected_up_filter_path,
    'Down': selected_down_filter_path
}
st.write(selected_calib_files)

st.markdown('') # 表示上のスペース確保
st.markdown('##### 保存先の設定')
save_calib_path = st.text_input(label='保存フォルダまでのfull path', value=setting.setting_json['save_calib_path'])
if st.button('保存先を更新'):
    setting.update_save_spe_path(save_calib_path)

st.divider()
output_file_option = st.radio(
    label='出力するファイル形式を選択',
    options=['`.hdf5`', '`.spe`'],
)

match output_file_option:
    case '`.hdf5`':
        if st.button('`.hdf5`に書き出し'):
            st.write('書き込み開始')
            # 保存するhdf5ファイル名
            saved_hdf5_name = spe.file_name + '_calib.hdf'

            # 必要なオブジェクト化
            original_radiation = RawSpectrumData(spe) # spe -> radiationデータクラスへ
            lamp_spectrum = pd.read_csv( # ["wavelength", "intensity"]を列に持つpd.DataFrameへ
                selected_lamp_path,
                header=None,
                names=["wavelength", "intensity"]
            )
            # up, downは、応答補正値の配列を渡す
            up_filter_spe = SpeWrapper(filepath=selected_up_filter_path)
            up_response_arr = up_filter_spe.get_frame_data(frame=0)[0]
            down_filter_spe = SpeWrapper(filepath=selected_down_filter_path)
            down_response_arr = down_filter_spe.get_frame_data(frame=0)[0]

            path_to_hdf5 = os.path.join(save_calib_path, saved_hdf5_name)
            st.write(f'{path_to_hdf5} が出力されます。')
            # FIXME: ログはクラスにしてまとめる
            # ログ
            if not os.path.isdir('log'):
                os.mkdir('log')
            if not os.path.exists('log/calibration_log.txt'):
                with open('log/calibration_log.txt', 'w') as f:
                    pass
            with open('log/calibration_log.txt', 'a') as f:
                f.write(
                    str(datetime.now())
                    + f"\n\tfrom {spe.filepath}"
                    + f"\n\t  to {path_to_hdf5}"
                    + f"\n\twith {selected_lamp_path}"
                    + f"\n\t     {selected_up_filter_path}"
                    + f"\n\t     {selected_down_filter_path}"
                    + "\n"
                )

            # 書き出し処理
            CalibrateSpectraWriter.output_to_hdf5(
                original_radiation=original_radiation,
                lamp_spectrum=lamp_spectrum,
                up_response=up_response_arr,
                down_response=down_response_arr,
                path_to_hdf5=path_to_hdf5
            )
            st.write(f'完了: {path_to_hdf5}')
    case '`.spe`':
        st.write('実装されていません（LightFieldでできます）')
        st.stop()
    case _:
        st.write('想定外の挙動')
        st.stop()