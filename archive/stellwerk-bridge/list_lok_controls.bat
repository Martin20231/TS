@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Lok-Regler im Spiel anzeigen (Train Simulator muss laufen, in Lok sitzen) ===
echo.
python -c "from ts_tracker import load_raildriver, establish_connection, get_controller_list; from radar_config import load_config; c=load_config(); dll=load_raildriver(c['raildriver_dll_path']); establish_connection(dll); ctrls=get_controller_list(dll); print('Regler der aktuellen Lok:'); [print(f'  {i}: {n}') for i,n in enumerate(ctrls)] if ctrls else print('  (keine - in Fahrt einsteigen!)')"
echo.
pause
