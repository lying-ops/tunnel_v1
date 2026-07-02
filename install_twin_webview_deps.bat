@echo off
chcp 65001 >nul
title Optional Twin WebView Dependencies

echo.
echo ============================================================
echo  隧道泵站自动控制系统 V5.7.14_TwinBindFix - 三维孪生内嵌增强
echo ============================================================
echo.
echo 说明：Tkinter 本身不能渲染 WebGL。外部 GLB 查看器为稳定方案。
echo 如果希望在程序内启动独立 WebView 窗口，可尝试安装 pywebview：
echo.
echo   python -m pip install pywebview

echo.
echo 安装后，点击“加载内嵌动态查看器”时会优先尝试 pywebview。
echo 如果安装失败，不影响主程序，仍可使用“外部GLB查看器”。
echo.
set /p DOINSTALL=是否现在安装 pywebview？输入 Y 安装，其他键退出：
if /I "%DOINSTALL%"=="Y" (
  python -m pip install pywebview
)
echo.
pause
