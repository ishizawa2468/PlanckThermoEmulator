import os
import h5py
import numpy as np
import pandas as pd

class HDF5():
    SUPPORTED_FILE_TYPES = ['.hdf5', '.hdf', '.h5', '.nxs'] # 有効な拡張子を示すクラス変数

    def __init__(self, file_path):
        if any(file_path.endswith(ext) for ext in self.SUPPORTED_FILE_TYPES):
            self.file_path = file_path
            # ファイルが存在すれば、ファイル内のpath構造を設定する。
            if os.path.exists(file_path):
                with h5py.File(self.file_path, 'r') as f:
                    self.path_list = self._get_all_dataset_paths(f)
            else:
                print('ファイルが見つかりません。: ' + self.file_path)
        else:
            raise ValueError(
                f"ファイルパスが無効です。対応するHDFファイルでない可能性があります。\n\t有効なもの: {self.SUPPORTED_FILE_TYPES}"
            )

    def _get_all_dataset_paths(self, file):
        dataset_paths = []
        def collect_datasets(name, obj):
            if isinstance(obj, h5py.Dataset):
                dataset_paths.append(name)
        file.visititems(collect_datasets)
        return dataset_paths

class HDF5Writer(HDF5):

    def __init__(self, file_path):
        super().__init__(file_path)
        if not os.path.exists(file_path):
            self._create_file()
        else:
            print(f"HDF5ファイルが見つかりました: {self.file_path}")

    def _create_file(self):
        with h5py.File(self.file_path, 'w') as f:
            f.create_group('entry')
        print(f"HDF5ファイルが作成されました: {self.file_path}")

    def write(self, *, data_path, data, compression=None, overwrite=False):
        if overwrite:
            self._delete_if_exists(data_path)
        else:
            if self._data_exists(data_path):
                print(f"{data_path}にはすでにデータが存在します。上書きしたい場合は overwrite オプションをTrueにしてください。")
                return

        self._write_data(data_path, data, compression)
        print(f"書き込みに成功しました: '{data_path}' in {self.file_path}")

    def _delete_if_exists(self, data_path):
        with h5py.File(self.file_path, 'a') as f:
            if data_path in f:
                del f[data_path]

    def _data_exists(self, data_path):
        with h5py.File(self.file_path, 'r') as f:
            return data_path in f

    def _write_data(self, data_path, data, compression):
        # 単一のnumpyのデータの扱いがめんどくさいので、一括で浮動小数点に変換する。
        if isinstance(data, (np.integer, np.floating)):
            data = float(data)
        if isinstance(data, (int, float, str, np.ndarray)):
            with h5py.File(self.file_path, 'a') as f:
                f.create_dataset(data_path, data=data, compression=compression)
        elif isinstance(data, pd.DataFrame):
            data.to_hdf(self.file_path, key=data_path, mode='a')
        else:
            raise TypeError(
                f"データの種類: {type(data)} は書き込めません。\n可能なもの: int, float, str, numpyの整数・小数系, np.ndarray, pd.DataFrame"
            )

    def delete(self, data_path):
        with h5py.File(self.file_path, 'a') as f:
            if data_path in f:
                del f[data_path]
                print(f"{data_path} を削除しました。")
            else:
                raise KeyError(f"{data_path} が見つかりません。")

class HDF5Reader(HDF5):
    def __init__(self, file_path):
        super().__init__(file_path)
        print(f"HDF5ファイルが見つかりました: {self.file_path}")

    def find_by(self, query, shape: list = None):
        with h5py.File(self.file_path, 'r') as f_read:
            self.path_list = self._get_all_dataset_paths(f_read)  # 最新のデータパスリストを取得する
            to_data = self.search_data_path(query=query)

            if type(to_data) is str:
                return self.return_data(data_path=to_data, shape=shape)
            elif type(to_data) is list:
                raise Exception("複数のlayer pathが見つかりました。一括で返して欲しい場合は実装してください。")
            else:
                raise Exception("layer pathが見つかりませんでした。")

    def search_data_path(self, query: str):
        result_list = []

        print(f"「{query}」で検索します。")
        for path in self.path_list:
            if query in path:
                if path.startswith('/'): # 最初のスラッシュを削除する
                    path = path[1:]
                result_list.append(path)

        if len(result_list) >= 2: # 2個以上見つかった場合
            print(f"\t-> {len(result_list)} 個のpathが見つかりました。リストで返しました。\n")
            for i, path in enumerate(result_list):
                print(f"{i: >2}: {path}")
            return result_list
        elif len(result_list) == 1: # 1個だけに絞られた場合
            result = result_list[0]
            print(f"\t-> {result} を返しました。")
            return result
        else: # 0個の場合
            print(f"\t-> 「{query}」を含むpathは見つかりませんでした。")
            return None

    def return_data(self, data_path: str, shape: list = None):
        with h5py.File(self.file_path, 'r') as f:
            dataset = f[data_path]
            if dataset.shape == ():  # スカラー(単一値)の場合
                value = dataset[()]  # スカラーの場合の読み取り
                try:
                    # 文字列への変換を試みる
                    value = value.decode('utf-8')
                except:
                    # できなかったら処理をそのまま流す
                    pass
            else:
                if shape is None:  # スライス指定がない場合
                    value = f.get(data_path)[:]
                else:  # スライス指定がある場合
                    value = f.get(data_path)[tuple(shape)]  # 部分的に返す
        return value

    def print_contents(self, preview_elements=2):
        print(f"  -- {self.file_path} の内容を表示します --")
        print(f"(データのPreviewは{preview_elements+1}つまで)")
        with h5py.File(self.file_path, 'r') as f:
            def print_structure(name, obj):
                if isinstance(obj, h5py.Dataset):
                    # データセットの場合、shapeとdtypeを表示
                    if obj.shape == ():
                        # スカラーの場合、直接値を取得
                        preview = obj[()]
                    else:
                        # スカラーでない場合は通常のスライス処理
                        preview = obj[:preview_elements] if obj.size >= preview_elements else obj[:]
                    print(f"\t -> Dataset: {name}, Shape: {obj.shape}, Type: {obj.dtype}, Preview: {preview}")
                elif isinstance(obj, h5py.Group):
                    # グループの場合、グループ名のみを表示
                    print(f"Group: {name}")

            # HDF5ファイルの中身を再帰的に探索
            f.visititems(print_structure)

    def create_fetcher(self, query: str):
        """
        queryを使ってHDFDataFetcherオブジェクトを作成し、検索したデータパスに基づいて返す
        """
        fetcher = HDFDataFetcher(file_path=self.file_path)
        fetcher.set_data_path(query=query)
        return fetcher


class HDFDataFetcher:
    def __init__(self, file_path: str, data_path: str = None):
        """
        file_path: HDF5ファイルのパス
        data_path: 初期化時に指定するHDF5ファイル内のデータセットのパス
        """
        self.file_path = file_path
        self.data_path = data_path
        self.dataset_shape = None
        self.path_list = self._get_all_dataset_paths()

        if data_path:
            self._initialize_dataset_shape()

    def _get_all_dataset_paths(self):
        """ファイル内の全データセットパスを取得"""
        with h5py.File(self.file_path, 'r') as f:
            dataset_paths = []
            def collect_datasets(name, obj):
                if isinstance(obj, h5py.Dataset):
                    dataset_paths.append(name)
            f.visititems(collect_datasets)
        return dataset_paths

    def _initialize_dataset_shape(self):
        """指定されたdata_pathのデータセットの形状を初期化"""
        with h5py.File(self.file_path, 'r') as f:
            if self.data_path in f:
                self.dataset_shape = f[self.data_path].shape
            else:
                raise KeyError(f"指定されたデータパス '{self.data_path}' が見つかりません。")

    def fetch_by_frame(self, frame: int):
        """
        指定されたframeに基づいて、データの一部を取得する
        frame: 取得したいデータのframe（インデックス）
        """
        if self.dataset_shape is None:
            raise RuntimeError("データセットのshapeが初期化されていません。")

        if frame >= self.dataset_shape[0]:
            raise IndexError(f"指定されたframe {frame} は範囲外です (最大: {self.dataset_shape[0] - 1})。")

        # 指定されたframeのデータを取得
        with h5py.File(self.file_path, 'r') as f:
            dataset = f[self.data_path]
            return dataset[frame]  # frameの部分だけを返す

    def get_shape(self):
        """データセットの形状を返す"""
        return self.dataset_shape

    def search_data_path(self, query: str):
        """queryに基づいてデータパスを検索し、1つに絞られた場合のみ返す"""
        result_list = []
        print(f"「{query}」で検索します。")
        for path in self.path_list:
            if query in path:
                result_list.append(path)

        if len(result_list) == 1:
            result = result_list[0]
            print(f"\t-> {result} を返しました。")
            return result
        elif len(result_list) > 1:
            raise Exception(f"複数のデータパスが見つかりました: {result_list}")
        else:
            raise Exception(f"「{query}」に一致するデータパスは見つかりませんでした。")

    def set_data_path(self, query: str):
        """
        queryに基づいて検索したデータパスをdata_pathに設定し、データセットの形状を初期化する
        """
        self.data_path = self.search_data_path(query)
        self._initialize_dataset_shape()
