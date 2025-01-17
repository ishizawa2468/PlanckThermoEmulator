import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import norm, cauchy
import matplotlib.pyplot as plt

class HistogramFitter():
    def __init__(self, data, bins=200):
        """
        Initialize the HistogramFitter with data and bin size.

        Parameters:
        data (array-like): The input data for histogram fitting.
        bins (int): Number of bins for the histogram.
        """
        self.data = data
        self.bins = bins
        self.hist_values = None
        self.bin_edges = None
        self.bin_centers = None
        self.fit_params = None
        self.fit_errors = None

    @staticmethod
    def lorentzian(x, A, x0, gamma):
        """
        Lorentzian (Cauchy) distribution PDF.

        Parameters:
        x (array-like): Input values.
        A (float): Amplitude of the peak.
        x0 (float): Center of the peak.
        gamma (float): Width parameter.

        Returns:
        array-like: Lorentzian values.
        """
        return A * cauchy.pdf(x, loc=x0, scale=gamma)

    @staticmethod
    def gaussian(x, A, mu, sigma):
        """
        Gaussian (normal) distribution PDF.

        Parameters:
        x (array-like): Input values.
        A (float): Amplitude of the peak.
        mu (float): Mean of the distribution.
        sigma (float): Standard deviation.

        Returns:
        array-like: Gaussian values.
        """
        return A * norm.pdf(x, loc=mu, scale=sigma)

    @staticmethod
    def pseudo_voigt(x, A, x0, gamma, eta):
        """
        Pseudo-Voigt profile (combination of Lorentzian and Gaussian).

        Parameters:
        x (array-like): Input values.
        A (float): Amplitude of the peak.
        x0 (float): Center of the peak.
        gamma (float): Width parameter for Lorentzian component.
        eta (float): Mixing ratio (0 for pure Gaussian, 1 for pure Lorentzian).

        Returns:
        array-like: Pseudo-Voigt values.
        """
        gaussian_part = HistogramFitter.gaussian(x, A, x0, gamma)
        lorentzian_part = HistogramFitter.lorentzian(x, A, x0, gamma)
        return eta * lorentzian_part + (1 - eta) * gaussian_part

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
    def compute_histogram(self):
        """
        Compute the histogram values and bin centers.
        """
        self.hist_values, self.bin_edges = np.histogram(self.data, bins=self.bins)
        self.bin_centers = (self.bin_edges[:-1] + self.bin_edges[1:]) / 2

    def fit(self, model="lorentzian", initial_guess=None):
        """
        Fit the histogram data to a specified model.

        Parameters:
        model (str): The model to fit ("lorentzian", "gaussian", or "pseudo_voigt").
        initial_guess (list or None): Initial guess for the parameters.

        Returns:
        tuple: Optimized parameters and their covariance matrix.
        """
        if self.hist_values is None or self.bin_centers is None:
            self.compute_histogram()

        if model == "lorentzian":
            func = self.lorentzian
            if initial_guess is None:
                initial_guess = [max(self.hist_values), np.mean(self.data), 100]
        elif model == "gaussian":
            func = self.gaussian
            if initial_guess is None:
                initial_guess = [max(self.hist_values), np.mean(self.data), np.std(self.data)]
        elif model == "pseudo_voigt":
            func = self.pseudo_voigt
            if initial_guess is None:
                initial_guess = [max(self.hist_values), np.mean(self.data), 100, 0.5]
        else:
            raise ValueError("Unsupported model. Choose from 'lorentzian', 'gaussian', or 'pseudo_voigt'.")

        popt, pcov = curve_fit(func, self.bin_centers, self.hist_values, p0=initial_guess)
        self.fit_params = popt
        self.fit_errors = np.sqrt(np.diag(pcov))
        return popt, pcov

    def get_figure(self, model="lorentzian"):
        """
        Plot the histogram and the specified model fit.

        Parameters:
        model (str): The model to plot ("lorentzian", "gaussian", or "pseudo_voigt").
        """
        if self.fit_params is None:
            raise ValueError("Fit the data before plotting.")

        if model == "lorentzian":
            func = self.lorentzian
            # label = f"Lorentzian Fit (A={self.fit_params[0]:.2e}, x0={self.fit_params[1]:.2f}, gamma={self.fit_params[2]:.2f})"
            label = f"Lorentzian Fit\n  x0 = {self.fit_params[1]:.1f} K\n  gamma = {self.fit_params[2]:.1f} K\n  (sigma = {round(self.fit_params[2]/self.fit_params[1], 3)*100:} %)"
        elif model == "gaussian":
            func = self.gaussian
            label = f"Gaussian Fit (A={self.fit_params[0]:.2e}, mu={self.fit_params[1]:.2f}, sigma={self.fit_params[2]:.2f})"
        elif model == "pseudo_voigt":
            func = self.pseudo_voigt
            # label = f"Pseudo-Voigt Fit (A={self.fit_params[0]:.2e}, x0={self.fit_params[1]:.2f}, gamma={self.fit_params[2]:.2f}, eta={self.fit_params[3]:.2f})"
            label = f"Pseudo-Voigt Fit\n  x0 = {self.fit_params[1]:.1f} K\n  gamma = {self.fit_params[2]:.1f} K\n  Lo. ratio= {self.fit_params[3]:.2f}\n  (sigma = {round(self.fit_params[2]/self.fit_params[1]*100, 2)} %)"
        else:
            raise ValueError("Unsupported model. Choose from 'lorentzian', 'gaussian', or 'pseudo_voigt'.")

        x = np.linspace(min(self.bin_centers), max(self.bin_centers), 1000)
        y_fit = func(x, *self.fit_params)

        fig = plt.figure(figsize=(8, 5), dpi=300)
        plt.bar(self.bin_centers, self.hist_values, width=(self.bin_edges[1] - self.bin_edges[0]), alpha=0.6, color='g', label='Temperature Histogram')
        plt.plot(x, y_fit, 'r-', label=label)
        plt.xlabel('Temperature (K)')
        plt.ylabel('Frequency')
        plt.title(f'Histogram and {model.capitalize()} Fit')
        plt.legend(fontsize='small')
        return fig

# Example usage:
# temperatures = np.random.normal(300, 50, 1000)  # Replace with actual data
# fitter = HistogramFitter(temperatures)
# fitter.compute_histogram()
# fitter.fit(model="lorentzian")
# fitter.plot_fit(model="lorentzian")
# fitter.fit(model="gaussian")
# fitter.plot_fit(model="gaussian")
# fitter.fit(model="pseudo_voigt")
# fitter.plot_fit(model="pseudo_voigt")