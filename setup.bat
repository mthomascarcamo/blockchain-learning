@ECHO OFF
FOR /F "tokens=*" %%i IN ('python -c "import os;print([i for i in os.getenv('Path').split(';') if '37' in i][0])"') DO (
    virtualenv -p "%%i\python.exe" %PUBLIC%\BLOCKCHAIN_LEARNING_VENV
)
%PUBLIC%\BLOCKCHAIN_LEARNING_VENV\Scripts\activate && %PUBLIC%\BLOCKCHAIN_LEARNING_VENV\Scripts\python.exe setup.py install