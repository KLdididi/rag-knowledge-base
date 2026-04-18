@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   RAG 知识库问答系统 - Tauri 构建脚本
echo ============================================
echo.

cd /d "%~dp0.."

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: 检查 Rust
rustc --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Rust，请先安装 Rust
    echo    访问: https://rustup.rs
    pause
    exit /b 1
)

:: 安装依赖
echo 📦 安装前端依赖...
cd desktop
call npm install
if errorlevel 1 (
    echo ❌ npm install 失败
    pause
    exit /b 1
)

:: 构建前端
echo.
echo 🔨 构建前端...
call npm run build
if errorlevel 1 (
    echo ❌ 前端构建失败
    pause
    exit /b 1
)

:: 构建 Tauri 应用
echo.
echo 🔨 构建 Tauri 应用（这可能需要几分钟）...
call npm run tauri build
if errorlevel 1 (
    echo ❌ Tauri 构建失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   ✅ 构建完成！
echo ============================================
echo.
echo 输出目录: desktop\src-tauri\target\release\bundle\
echo.

pause
