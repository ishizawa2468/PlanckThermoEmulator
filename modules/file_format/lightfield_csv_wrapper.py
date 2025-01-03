
import pandas as pd
from enum import Enum

class LightfieldCsvOption(Enum):
    DIST = 'dist'
    CALIB = 'calib'

    @classmethod
    def from_str(cls, option_str):
        try:
            return cls(option_str.lower())
        except ValueError:
            raise ValueError(f"ファイルオプションが不正です: {option_str}\n以下で指定してください: {', '.join(o.value for o in cls)}")

class LightfieldCsv:
    """
    calib, distを.csvで出力したときに読み込むためのクラス

    NOTE: 以下のようにデータの種類によってヘッダーの使われ方が違うので注意
    header = ['ROI', 'Frame', 'Row', 'Column', 'Wavelength', 'Intensity']
    dist(distribution, 温度分布)では、
        Row        : 時間(フレーム)
        Column     : 位置(ピクセル)
        Intensity  : 温度(K)
    calib(calibrated spectrum, 校正されたスペクトル)では、
        Frame      : 時間(フレーム)
        Row        : 位置(ピクセル)
        Column     : 波長(ピクセル)
        Wavelength : 波長(nm) / Columnと連動
        Intensity  : 強度(a.u.)

    NOTE: ROIを設定したことがないのでROIの挙動は考慮されていない
    """

    def __init__(self, file_path, file_option):
        if not file_path.endswith('.csv'):
            raise ValueError('file_path should end with .csv')

        file_option = LightfieldCsvOption.from_str(file_option) # 不正な場合は弾かれる

        self.file_path = file_path
        self.file_option = file_option

    """ dist用メソッド """
    def set_dist_pixel(self, position_pixel_num):
        self.allow_only_dist()
        self.position_pixel_num = position_pixel_num

    def get_frame_temperature(self, frame):
        # NOTE: frameは1始まり
        self.allow_only_dist()
        return pd.read_csv(
            self.file_path,
            names=['ROI', 'Frame', 'Row', 'Column', 'Wavelength', 'Intensity'],
            skiprows= (frame-1) * self.position_pixel_num + 1, # header分1行飛ばす
            nrows=self.position_pixel_num
        )['Intensity']

    def get_all_temperature(self):
        self.allow_only_dist()
        return pd.read_csv(self.file_path)['Intensity']

    """ calib用メソッド """
    def set_calib_pixel(self, position_pixel_num, wavelength_pixel_num):
        self.allow_only_calib()
        self.position_pixel_num = position_pixel_num
        self.wavelength_pixel_num = wavelength_pixel_num

    def get_spectrum(self, frame, position_pixel):
        # NOTE: frame, position_pixelは1始まり
        self.allow_only_calib()
        return pd.read_csv(
            self.file_path,
            names=['ROI', 'Frame', 'Row', 'Column', 'Wavelength', 'Intensity'],
            skiprows=
                (frame-1) * self.position_pixel_num * self.wavelength_pixel_num + # 前frameまでをすべてskip
                (position_pixel - 1) * self.wavelength_pixel_num + 1, # 前positionまで, header分をskip
            nrows=self.wavelength_pixel_num,
            usecols=['Wavelength', 'Intensity']  # 必要な列のみを読み込む
        )

    def get_frame_spectra(self, frame):
        # NOTE: frameは1始まり
        self.allow_only_calib()
        return pd.read_csv(
            self.file_path,
            names=['ROI', 'Frame', 'Row', 'Column', 'Wavelength', 'Intensity'],
            skiprows= (frame-1) * self.position_pixel_num * self.wavelength_pixel_num + 1,
            nrows=self.position_pixel_num * self.wavelength_pixel_num,
            usecols = ['Row', 'Wavelength', 'Intensity']  # 必要な列のみを読み込む
        )

    """ validation """
    def allow_only_dist(self):
       if self.file_option is not LightfieldCsvOption.DIST:
           raise AssertionError("このメソッドはdist専用です。")

    def allow_only_calib(self):
        if self.file_option is not LightfieldCsvOption.CALIB:
            raise AssertionError("このメソッドはcalib専用です。")
