import streamlit as st

def display_title_with_link(
        title, # ヘッダー
        link_title, # サイドバーに表示するタイトル
        tag # リンク要素を見分けるためのタグ。ページ内で他と異なれば(一意であれば)大丈夫なはず
):
    st.markdown(f"### {title} <a name='{tag}'></a>", unsafe_allow_html=True)
    st.sidebar.markdown(f"[{link_title}](#{tag})")