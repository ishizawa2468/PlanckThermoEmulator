import subprocess

if __name__ == '__main__':
    print("ブラウザでアプリを起動します。")
    command: list = ["streamlit", "run", "home.py"]
    subprocess.Popen(command)
