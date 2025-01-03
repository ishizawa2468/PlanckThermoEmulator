import matplotlib.pyplot as plt

"""plot用の設定"""
plt.rcParams['mathtext.fontset'] = 'cm'     #数式用のフォントejavuserif" or "cm"
plt.rcParams['xtick.direction'] = 'in'      #x軸の目盛線 #内in')か外向き('out')か双方向か('inout')
plt.rcParams['ytick.direction'] = 'in'      #y軸の目盛線 #内in')か外向き('out')か双方向か('inout')
plt.rcParams['xtick.major.width'] = 1.0     #x軸主目盛り線の線幅
plt.rcParams['ytick.major.width'] = 1.0     #y軸主目盛り線の線幅
plt.rcParams['font.size'] = 14               #フォントの大きさ
plt.rcParams['axes.linewidth'] = 0.8        #軸の線幅edge linewidth。囲みの太さ
plt.rcParams['figure.dpi'] = 300
plt.rcParams['figure.figsize'] = (8, 6)
# Arialフォントを設定
plt.rcParams.update({
    "font.family": "Arial",           # フォントをArialに設定
    "mathtext.fontset": "custom",     # カスタムフォントを指定
    "mathtext.rm": "Arial",           # 数式の通常テキスト部分
    "mathtext.it": "Arial",    # 数式のイタリック部分
    "mathtext.bf": "Arial"       # 数式の太字部分
})

class FigureMaker:

    @staticmethod
    def get_max_I_figure(file_name, all_max_I, up_max_I, down_max_I):
        fig, ax = plt.subplots()
        ax.plot(all_max_I, color='red', label='All')
        ax.plot(up_max_I, color='blue', linestyle="--", label='Up')
        ax.plot(down_max_I, color='green', linestyle="--", label='Down')
        ax.set_xlabel("Frame")
        ax.set_ylabel("Intensity")
        ax.set_title(f"Max radiation intensity / {file_name}")
        ax.legend()
        return fig, ax

    @staticmethod
    def get_exposure_image_figure(file_name, frame, image):
        fig, ax = plt.subplots()
        im = ax.imshow(image, origin='upper', cmap='gist_gray', aspect='auto')
        # カラーバーを表示
        cbar = fig.colorbar(im, ax=ax)
        # ラベル付け
        ax.set_xlabel("Wavelength (pixel)")
        ax.set_ylabel("Position (pixel)")
        ax.set_title(f"Exposure / {file_name} / frame = {frame}")
        cbar.set_label("Intensity")
        return fig, ax

    @staticmethod
    def get_histogram_fit_figure(file_name, histgram_fitter):
        plt.hist(histgram_fitter.data, bins=histgram_fitter.bins, density=True, alpha=0.6, color="g", label="Histogram")
        plt.plot(histgram_fitter.x_fit, histgram_fitter.y_fit, color="red", label="Fitted Gaussian")
        plt.xlabel("Intensity without heating")
        plt.ylabel("Density")
        plt.title(f"Noise of exposure / {file_name}")
        plt.legend()

    @staticmethod
    def overlap_max_intensity_by_threshold(histogram_fitter, threshold):
        result = histogram_fitter.result
        mean = result['mean']['value']
        upper_lim = mean*10

        plt.ylim(0, upper_lim)
        plt.axhline(
            mean,
            label='mean',
            linewidth=3,
            color='gray',
            linestyle='--'
        )
        plt.axhline(
            threshold,
            label='threshold',
            linewidth=3,
            color='red',
            linestyle='--'
        )
        plt.legend()

    @staticmethod
    def overlap_by_center_positions(ax, center_pixels, wavelength_pixels, color="red"):
        ax.scatter(
            center_pixels,
            wavelength_pixels,
            color=color,
            s=5
        )
        return ax
