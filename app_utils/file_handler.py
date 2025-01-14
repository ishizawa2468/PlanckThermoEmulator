import os

import pandas as pd
import streamlit as st

from modules.file_format.spe_wrapper import SpeWrapper

class FileHandler:
    @staticmethod
    def get_file_list_with_OD(path_to_files, files):
        spe_list = []
        spe_display_data = []
        for file in files:
            if not file.endswith('.spe'):
                raise Exception(".spe以外のファイルが含まれています。")
            spe_list.append(SpeWrapper(os.path.join(path_to_files, file)))
        for spe in spe_list:
            try:
                spe.get_params_from_xml()
                OD = spe.OD
            except Exception as e:
                OD = None
            spe_display_data.append({"File Name": spe.file_name, "OD": OD})
        return pd.DataFrame(spe_display_data)

    @staticmethod
    def build_tree_structure(path_to_calib, walked):
        """os.walk の結果からツリー構造を辞書形式で構築"""
        tree = {}
        for dirpath, dirnames, filenames in walked:
            # 現在のディレクトリを基点としたパス
            relative_path = os.path.relpath(dirpath, start=path_to_calib)
            parts = relative_path.split(os.sep)
            current = tree
            for part in parts:
                current = current.setdefault(part, {})
            current.update({name: {} for name in dirnames})
            current.update({name: None for name in filenames})
        return tree

    @classmethod
    def display_tree(cls, tree, level=0):
        """再帰的にツリー構造を Streamlit 上に表示"""
        for key, value in tree.items():
            indent = "  " * level
            if value is None:
                st.write(f"{indent}- 📄 {key}")
            else:
                st.write(f"{indent}- 📂 {key}")
                cls.display_tree(value, level + 1)