import numpy as np
from scipy.constants import h, c, k  # プランク定数, 光速, ボルツマン定数
from scipy.optimize import curve_fit
from scipy.optimize import fsolve
import warnings

class ColorPyrometer:
    # 二色法で温度を求める関数を定義
    @staticmethod
    def equation_to_solve(T, lambda1, lambda2, R):
        """
        強度比 R の式から温度を求めるための方程式

        Parameters:
        ----------
        T : float
            温度 (K)
        lambda1 : float
            波長1 (nm)
        lambda2 : float
            波長2 (nm)
        R : float
            強度比 R = I(lambda1) / I(lambda2)

        Returns:
        -------
        difference : float
            左辺と右辺の差（ゼロに近い値を探す）
        """
        # 波長を nm -> m 単位に変換
        lambda1_m = lambda1 * 1e-9
        lambda2_m = lambda2 * 1e-9

        # 分子と分母を計算
        numerator = lambda2_m**5 * (np.exp(h * c / (lambda2_m * k * T)) - 1)
        denominator = lambda1_m**5 * (np.exp(h * c / (lambda1_m * k * T)) - 1)

        # 強度比を計算
        R_calculated = numerator / denominator

        # 左辺と右辺の差を返す
        return R_calculated - R


    @classmethod
    def calculate_temperature_all_pairs(cls, wavelength_fit, intensity_fit):
        """
        波長の大小関係を満たすすべてのペアに対して温度を数値的に解き、警告が発生したペアを記録

        Parameters:
        ----------
        wavelength_fit : ndarray
            波長の配列（nm単位）
        intensity_fit : ndarray
            強度の配列

        Returns:
        -------
        temperatures : list of floats
            各ペアに対応する温度のリスト
        warning_pairs : list of tuples
            警告が発生した波長ペアのリスト
        """
        temperatures = []
        warning_pairs = []  # 警告が発生したペアを記録
        excepted_pairs = [] # 例外が発生したペアも記録
        n = len(wavelength_fit)

        for i in range(n):
            for j in range(i + 1, n):
                lambda1 = wavelength_fit[i]
                lambda2 = wavelength_fit[j]
                I1 = intensity_fit[i]
                I2 = intensity_fit[j]

                # 強度比 R を計算
                R = I1 / I2

                # 初期値を仮定
                T_initial_guess = 3000  # K

                # 警告・例外をキャッチしながら数値解を求める
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")  # すべての警告をキャッチ

                    try:
                        T_solution = fsolve(cls.equation_to_solve, T_initial_guess, args=(lambda1, lambda2, R))[0]
                        temperatures.append(T_solution)

                        # 警告が発生した場合、そのペアを記録
                        if w:
                            warning_pairs.append((lambda1, lambda2))

                    except Exception as e:
                        # 例外が発生した場合もペアを記録
                        excepted_pairs.append((lambda1, lambda2))

        return np.array(temperatures), warning_pairs, excepted_pairs
