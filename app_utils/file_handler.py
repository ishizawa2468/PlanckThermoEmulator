import os

import pandas as pd

from modules.file_format.spe_wrapper import SpeWrapper

class FileHander:
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
