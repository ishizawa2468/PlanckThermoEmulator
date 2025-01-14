import streamlit as st

class CalibrateSpectraWriter():
    @staticmethod
    def output_to_hdf5(
            original_radiation,
            ref_spectrum,
            up_filter,
            down_filter,
            path_to_hdf5
    ):
        st.write('書き出し開始')

        st.write('書き出し完了')