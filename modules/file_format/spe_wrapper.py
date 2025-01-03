from typing import Optional, Sequence

import numpy as np

from modules.file_format.read_spe import SpeReference

# 自分で欲しい形式でデータを返してもらうためのラッパー
class SpeWrapper(SpeReference):
    # ref) SpeFile in T-rax
    DATA_TYPE_DICT = {
        0: np.float32,
        1: np.int32,
        2: np.int16,
        3: np.uint16,
        8: np.uint32
    }
    INITIAL_POSITION = 4100

    def __init__(self, filepath: str):
        super().__init__(filepath)
        self._filepath = filepath

    # 指定されたframeのimgデータを返す
    def get_frame_data(self,
                       rois:Optional[Sequence[int]] = None,
                       frame:Optional[int] = None) -> np.ndarray:
        # NOTE: frameを指定しないと、shape=(1, 800, 512, 512)のように返ってくる。
        # numpy.ndarrayのlistなので四次元 (List(ndarray))
        return self.get_data(frames=[frame])[0][0] # list, ndarrayを外して、二次元の露光データを取得

    # (frame_num, pixel, pixel)の3次元のndarrayを返す
    def get_all_data_arr(self) -> np.ndarray:
        return self.get_data()[0]

    # 最大値配列を返す
    def get_max_intensity(self):
        return self.get_all_data_arr().max(axis=2).max(axis=1)

    # SpeFileからの借用
    def _read_at(self, pos, size, ntype):
        with open(self._filepath, 'rb') as fid:
            pos = int(pos)
            size = int(size)
            fid.seek(pos)
            return np.fromfile(fid, ntype, size)

    def set_datatype(self):
        self._data_type = self._read_at(108, 1, np.uint16)[0]

    def _get_xml_string(self):
        """Reads out the xml string from the file end"""
        self.xml_offset = self._read_at(678, 1, np.int_)[0]
        with open(self._filepath, 'rb') as fid:
            fid.seek(int(self.xml_offset))
            self.xml_string = fid.read()

    def get_params_from_xml(self):
        self._get_xml_string()
        xml = self.xml_string
        str_xml = str(xml)
        list_xml = str_xml.split("<")

        # 特定の文字列が入っているものから情報を抜き出す
        for i, ele in enumerate(list_xml):
            if ('FrameRate r:readOnly' in ele) and ('/' not in ele):
                # print(f"{i}: {ele = }") # デバッグ用
                self.framerate = float(ele.split('>')[-1])
            if ('BaseFileName' in ele) and ('/' not in ele):
                # print(f"{i}: {ele = }")
                self.basename = ele.split('>')[-1]
            if ('IncrementNumber' in ele) and ('/' not in ele):
                # print(f"{i}: {ele = }")
                self.filenum = int(ele.split('>')[-1])
            if ('ReferenceFileDate r:readOnly' in ele) and ('/' not in ele):
                # print(f"{i}: {ele = }")
                self.date = ele.split('>')[-1]
            if ('Date r:readOnly' in ele) and ('Reference' not in ele) and ('/' not in ele):
                # print(f"{i}: {ele = }")
                self.calibration_date = ele.split('>')[-1]
            if ('Name type' in ele) and ('/' not in ele):
                # print(f"{i}: {ele = }")
                self.OD = ele.split('>')[-1]


