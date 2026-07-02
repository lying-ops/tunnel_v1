@echo off
cd /d %~dp0
if exist data\pump_station.db del data\pump_station.db
echo 数据库已删除。重新启动软件会自动初始化测试数据库。
pause
