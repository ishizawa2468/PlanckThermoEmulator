
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import norm

class HistogramFitter():

    # フィッティング用のガウス関数
    @staticmethod
    def gaussian(x, amplitude, mean, stddev):
        return amplitude * norm.pdf(x, loc=mean, scale=stddev)

    # 渡されたndarrayデータの分布の統計を取得する
    def fit_nd_histogram(self, data, bins=10):
        """
        任意次元データを1次元に展開し、ヒストグラムを作成してフィッティングを行う関数。
        外部ライブラリ（scipy.stats.norm）を使用してガウス関数を扱う。
        # FIXME 返り値が異なる
        :param data: ndarray - 任意次元のデータ
        :param bins: int - ヒストグラムのビン数
        :return: dict - フィッティング結果のパラメータ（振幅、平均、標準偏差）とそのエラー
        """
        # データを1次元に展開
        flattened_data = data.ravel()

        # ヒストグラムを作成
        bin_counts, bin_edges = np.histogram(flattened_data, bins=bins, density=True)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # 初期値の推定とフィッティング
        p0 = [1, np.mean(flattened_data), np.std(flattened_data)]
        popt, pcov = curve_fit(self.gaussian, bin_centers, bin_counts, p0=p0)

        # フィッティング結果のパラメータとエラー
        perr = np.sqrt(np.diag(pcov))  # 標準誤差を計算
        result = {
            "amplitude": {"value": popt[0], "error": perr[0]},
            "mean": {"value": popt[1], "error": perr[1]},
            "stddev": {"value": popt[2], "error": perr[2]},
        }

        # フィッティング結果のプロット
        x_fit = np.linspace(flattened_data.min(), flattened_data.max(), 100)
        y_fit = self.gaussian(x_fit, *popt)

        # フィールドに設定して図示などで使い回せるようにする
        self.result = result
        self.data = flattened_data
        self.bins = bins
        self.x_fit = x_fit
        self.y_fit = y_fit
        # 結果を整理した文字列を作っておく
        result_str = "Fitting Results: \n"
        for param, values in result.items():
            result_str += f"{param.capitalize()}: {values['value']:.3f} ± {values['error']:.3f}\n"
        self.result_str = result_str

        return None
