"""Build a portable Windows folder; all build artifacts remain in the project."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
BUILD=ROOT/'.build'

def build():
    BUILD.mkdir(exist_ok=True)
    (BUILD/'temp').mkdir(exist_ok=True)
    env=os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE']='1'
    env['TEMP']=env['TMP']=env['TMPDIR']=str(BUILD/'temp')
    env['PYINSTALLER_CONFIG_DIR']=str(BUILD/'pyinstaller-cache')
    env['PYTHONPATH']=os.pathsep.join(str(path) for path in [ROOT/'.packaging',ROOT/'vendor',ROOT])
    exclusions=['numpy','scipy','pandas','matplotlib','PIL','tkinter','IPython','pytest','PyQt5','PyQt6','PySide2','PySide6','torch','tensorflow','cv2','notebook']
    args=[sys.executable,'-B','-m','PyInstaller','--noconfirm','--onedir','--windowed',
        '--name','奶龙外卖','--distpath',str(BUILD/'dist'),'--workpath',str(BUILD/'work'),
        '--specpath',str(BUILD),'--icon',str(ROOT/'assets'/'app-icon.ico'),
        '--add-data',str(ROOT/'assets')+os.pathsep+'assets']
    for name in exclusions:
        args+=['--exclude-module',name]
    args.append(str(ROOT/'main.py'))
    subprocess.run(args,cwd=ROOT,env=env,check=True)
    print('Portable output: '+str(BUILD/'dist'/'奶龙外卖'))

if __name__=='__main__':
    build()
