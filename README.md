# README #

### How do I get set up? ###

* Clone repository
* Install Python 3.12
* Install dependencies: `pip install -r requirements.txt`
* (Might be required) Install [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)

### Running from source

* `python main.py`

### Running from executable

* `pip install pyinstaller==6.12.0`
* `python -m PyInstaller main.spec`
* Copy data folder to dist folder
* Run fightbattle.exe
