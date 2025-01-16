import numpy as np
from scipy.constants import h, c, k  # プランク定数, 光速, ボルツマン定数
from scipy.optimize import curve_fit

class PlanckFitter:
    # プランク関数の定義
    @staticmethod
    def planck_function(wavelength, T, A):
        """
        wavelength: 波長 (nm単位), T: 温度 (K), A: スケール因子
        """
        wavelength_m = wavelength * 1e-9  # nm -> m
        intensity = (2 * h * c**2) / (wavelength_m**5) * (1 / (np.exp((h * c) / (wavelength_m * k * T)) - 1))
        return A * intensity

    @classmethod
    def fit_by_planck(cls, wavelength_fit, intensity_fit):
        initial_temperature = 3000  # 初期温度を 3000 K に設定
        initial_scale = 1e-10       # 初期スケール因子を適当に設定
        params, covariance = curve_fit(cls.planck_function, wavelength_fit, intensity_fit, p0=[initial_temperature, initial_scale])
        # フィッティング結果と標準誤差
        T, scale = params
        T_error, scale_error = np.sqrt(np.diag(covariance))
        return {
            'T': T,
            'scale': scale,
            'T_error': T_error,
            'scale_error': scale_error
        }
