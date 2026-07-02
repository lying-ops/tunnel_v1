@echo off
chcp 65001 >nul
cd /d %~dp0
if exist data\pump_station.db (
  ren data\pump_station.db pump_station_backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.db
  echo 已备份并重置数据库，重新启动软件会自动创建新数据库。
) else (
  echo 当前没有数据库文件。
)
pause
