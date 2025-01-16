import json

import h5py
import numpy as np
import pandas as pd
from tqdm import tqdm

from modules.data_model.spectrum_data import SpectrumData
from modules.file_format.HDF5 import HDF5Writer


class CalibrateSpectraWriter():
    @staticmethod
    def output_to_hdf5(
            original_radiation: SpectrumData,
            lamp_spectrum: pd.DataFrame,
            up_response: np.ndarray,
            down_response: np.ndarray,
            path_to_hdf5: str
    ):
        print(f'log: Writing calibrated spectra to {path_to_hdf5}')

        # hdfファイルを生成し、書き込み先のpathを作成
        HDF5Writer(path_to_hdf5) # ファイルが存在しなければ作成し、あればそれを読み込む
        path_to_calibrated_spectra = 'entry/calibrated_spectra'
        path_to_wavelength_arr = 'entry/wavelength_arr'

        # frame数やpixel数などを取得
        shape_data = original_radiation.get_data_shape()
        frame_num = shape_data['frame_num']
        position_pixel_num = shape_data['position_pixel_num']
        center_pixel = shape_data['center_pixel'] # upとdownの境目
        wavelength_pixel_num = shape_data['wavelength_pixel_num']
        wavelength_arr = original_radiation.get_wavelength_arr()

        # NumPy の補間関数を使用して、ランプデータのデータ点の波長を揃える
        lamp_intensity_interpolated = np.interp(
            wavelength_arr,
            lamp_spectrum['wavelength'],
            lamp_spectrum['intensity']
        )

        # ここまでの情報をもとに校正用のimage(2次元配列)を作成する
        filter_image = np.zeros((position_pixel_num, wavelength_pixel_num))
        lamp_image = np.zeros((position_pixel_num, wavelength_pixel_num))
        # まずup, downのフィルター補正を展開
        filter_image[:center_pixel, :] = up_response[:, np.newaxis].T  # 256は含まれない。
        filter_image[center_pixel:, :] = down_response[:, np.newaxis].T
        # 加えてlamp_spectrumを展開
        lamp_image[:, :] = lamp_intensity_interpolated[:, np.newaxis].T
        # これが校正用image。元データに掛けて使う
        calibration_image = lamp_image / filter_image

        # 校正して書き込み
        with h5py.File(path_to_hdf5, 'w') as f:
            # 波長データ
            f.create_dataset(path_to_wavelength_arr, data=wavelength_arr)

            # imageデータ
            calib_dataset = f.create_dataset(path_to_calibrated_spectra, shape=(frame_num, position_pixel_num, wavelength_pixel_num))
            for frame in tqdm(range(frame_num)):
                calibrated_image = original_radiation.get_frame_data(frame=frame) * calibration_image
                calib_dataset[frame, :, :] = calibrated_image

        print('log: Finished writing calibrated spectra to hdf5')

class TemperatureDistributionWriter():
    @staticmethod
    def output_to_hdf5():
        pass