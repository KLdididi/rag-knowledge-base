# RAG 知识库问答系统 - 主入口
"""
独立可执行文件入口点
启动 Gradio UI 或 FastAPI 服务
"""

import os
import sys
import argparse
import webbrowser
import threading
import time

# 确保工作目录正确
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = os.path.dirname(sys.executable)
    os.chdir(BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 添加项目路径
sys.path.insert(0, BASE_DIR)


def main():
    parser = argparse.ArgumentParser(
        description='RAG 知识库问答系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --ui          启动 Gradio Web UI
  %(prog)s --api         启动 FastAPI 服务
  %(prog)s --ui --api    同时启动 UI 和 API
  %(prog)s --port 8080   指定端口
        """
    )
    parser.add_argument('--ui', action='store_true', help='启动 Gradio Web UI')
    parser.add_argument('--api', action='store_true', help='启动 FastAPI 服务')
    parser.add_argument('--port', type=int, default=7860, help='端口号 (默认: 7860)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='主机地址')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--ollama-host', type=str, default='http://localhost:11434', help='Ollama 服务地址')
    
    args = parser.parse_args()
    
    # 默认启动 UI
    if not args.ui and not args.api:
        args.ui = True
    
    print("=" * 60)
    print("  RAG 知识库问答系统 v1.0.0")
    print("=" * 60)
    print(f"  工作目录: {BASE_DIR}")
    print(f"  Ollama: {args.ollama_host}")
    print("=" * 60)
    
    # 检查 Ollama 连接
    try:
        import requests
        resp = requests.get(f"{args.ollama_host}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            print(f"  ✅ Ollama 已连接 ({len(models)} 个模型)")
        else:
            print("  ⚠️ Ollama 未响应，请确保服务已启动")
    except Exception as e:
        print(f"  ⚠️ 无法连接 Ollama: {e}")
        print("  提示: 请先启动 Ollama 服务")
    
    print("=" * 60)
    
    # 设置环境变量
    os.environ['OLLAMA_BASE_URL'] = args.ollama_host
    
    def open_browser(url, delay=2):
        """延迟打开浏览器"""
        time.sleep(delay)
        print(f"  🌐 打开浏览器: {url}")
        webbrowser.open(url)
    
    # 启动服务
    if args.api:
        print(f"\n🚀 启动 FastAPI 服务: http://{args.host}:{args.port}")
        import uvicorn
        from app.api.server import app
        
        # 如果同时启动 UI，使用不同端口
        api_port = args.port + 1 if args.ui else args.port
        
        if not args.no_browser:
            threading.Thread(
                target=open_browser,
                args=(f"http://{args.host}:{api_port}/docs",),
                daemon=True
            ).start()
        
        uvicorn.run(
            app,
            host=args.host,
            port=api_port,
            log_level="info"
        )
    
    elif args.ui:
        print(f"\n🚀 启动 Gradio UI: http://{args.host}:{args.port}")
        from app.ui.gradio_app import create_ui
        
        ui = create_ui()
        
        if not args.no_browser:
            threading.Thread(
                target=open_browser,
                args=(f"http://{args.host}:{args.port}",),
                daemon=True
            ).start()
        
        ui.launch(
            server_name=args.host,
            server_port=args.port,
            share=False,
            show_error=True,
        )


if __name__ == '__main__':
    main()
