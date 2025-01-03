
import numpy as np
from scipy.optimize import curve_fit

class RadiationFitter:
    @staticmethod
    def asymmetric_gaussian(x, A, mu, sigma1, sigma2):
        """
        非対称ガウシアン関数
        """
        return np.where(
            x <= mu,
            A * np.exp(-((x - mu) ** 2) / (2 * sigma1 ** 2)),
            A * np.exp(-((x - mu) ** 2) / (2 * sigma2 ** 2))
        )

    @staticmethod
    def estimate_initial_guess(x_data, y_data):
        """
        x_data と y_data からフィッティングの初期値を推定します。

        Parameters:
            x_data (array-like): 入力のxデータ
            y_data (array-like): 入力のyデータ

        Returns:
            list: 初期値 [A, mu, sigma1, sigma2]
        """
        A = np.max(y_data)  # y_dataの最大値をピークの高さとする
        mu = x_data[np.argmax(y_data)]  # y_dataの最大値に対応するxの値を取得
        half_max = A / 2

        # ピーク幅（半値全幅 FWHM）を推定
        left_idx = np.where(y_data >= half_max)[0][0]  # 左側の半値
        right_idx = np.where(y_data >= half_max)[0][-1]  # 右側の半値
        sigma1 = (mu - x_data[left_idx]) / 2  # 左側の幅
        sigma2 = (x_data[right_idx] - mu) / 2  # 右側の幅

        # 初期値
        return [A, mu, sigma1, sigma2]

    @staticmethod
    def fit_by_asymmetric_gaussian(x_data, y_data, initial_guess=None):
        """
        データに対して非対称ガウシアンをフィッティングします。

        Parameters:
            x_data (array-like): 入力のxデータ
            y_data (array-like): 入力のyデータ
            initial_guess (list): フィッティングの初期値 [A, mu, sigma1, sigma2]

        Returns:
            dict: フィッティング結果のパラメータと共分散行列
        """
        # 初期値が指定されていない場合は推定する
        if initial_guess is None:
            initial_guess = RadiationFitter.estimate_initial_guess(x_data, y_data)

        # フィッティング
        try:
            popt, pcov = curve_fit(
                RadiationFitter.asymmetric_gaussian,
                x_data,
                y_data,
                p0=initial_guess
            )
            result = {
                "parameters": {
                    "A": popt[0],
                    "mu": popt[1],
                    "sigma1": popt[2],
                    "sigma2": popt[3]
                },
                "covariance": pcov
            }
        except RuntimeError as e:
            result = {
                "error": str(e)
            }

        return result
