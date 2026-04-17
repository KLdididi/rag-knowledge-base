"""
Gradio 可视化界面
面试展示亮点：一键启动的 Web UI，支持流式输出
"""

import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
from gradio.themes import Soft

from app.api.server import (
    get_rag_engine,
    get_vectorstore,
    get_document_loader,
    get_text_splitter,
)
from app.core.config import config


# ============ 全局实例 ============

_rag_engine = None
_vectorstore = None


def get_rag():
    global _rag_engine
    if _rag_engine is None:
        from app.api.server import get_rag_engine as _get_rag
        _rag_engine = _get_rag()
    return _rag_engine


def get_vs():
    global _vectorstore
    if _vectorstore is None:
        from app.api.server import get_vectorstore as _get_vs
        _vectorstore = _get_vs()
    return _vectorstore


def chat(query, history, search_type, prompt_mode):
    """对话处理函数"""
    if not query.strip():
        return "", history, ""
    
    engine = get_rag()
    engine.search_type = search_type
    engine.prompt_mode = prompt_mode
    
    try:
        result = engine.query(query, return_sources=True)
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        
        # 构建来源信息
        source_info = ""
        if sources:
            source_info = "\n\n**参考来源:**\n"
            for i, src in enumerate(sources[:3], 1):
                filename = src.get("metadata", {}).get("filename", "未知")
                content = src.get("content", "")[:100]
                source_info += f"{i}. {filename}: {content}...\n"
        
        full_response = answer + source_info
        history.append((query, answer))
        
        return "", history, f"✅ 检索到 {len(sources)} 个相关文档"
    except Exception as e:
        history.append((query, f"❌ 错误: {str(e)}"))
        return "", history, f"❌ 错误: {str(e)}"


def chat_stream(query, history, search_type):
    """流式对话处理函数"""
    if not query.strip():
        return "", history, ""
    
    engine = get_rag()
    engine.search_type = search_type
    
    try:
        full_answer = ""
        
        # 使用 query_stream 获取流式回答
        for token in engine.query_stream(query):
            full_answer += token
            # 实时更新显示
            history.append((query, full_answer + " ▌"))
            yield "", history, f"🔄 正在生成..."
        
        # 获取来源
        docs = engine._retrieve(query)
        if engine.use_reranker:
            docs = engine._rerank(query, docs)
        
        source_info = f"\n\n📚 检索到 {len(docs)} 个相关文档"
        if engine.use_cache:
            source_info += " (已缓存)"
        
        # 移除临时标记
        history[-1] = (query, full_answer + source_info)
        
        yield "", history, source_info
    except Exception as e:
        history.append((query, f"❌ 错误: {str(e)}"))
        yield "", history, f"❌ 错误: {str(e)}"


def upload_file(file):
    """文件上传处理"""
    if file is None:
        return "❌ 请选择文件", 0
    
    try:
        loader = get_document_loader()
        splitter = get_text_splitter()
        vs = get_vs()
        
        # 加载文档
        docs = loader.load_file(file.name)
        
        # 切分文档
        chunks = splitter.split_and_preserve_metadata(docs)
        
        # 索引文档
        vs.add_documents(chunks)
        
        return f"✅ 成功索引 {len(chunks)} 个文本块", len(chunks)
    except Exception as e:
        return f"❌ 上传失败: {str(e)}", 0


def clear_history():
    """清空对话历史"""
    engine = get_rag()
    engine.reset_all_memories()
    return [], "✅ 对话历史已清空"


def get_status():
    """获取系统状态"""
    try:
        vs = get_vs()
        count = vs.document_count()
        model = config.llm.model
        provider = config.llm.provider
        return f"✅ 系统正常\n\n- LLM: {provider}/{model}\n- 索引文档: {count} 个"
    except Exception as e:
        return f"❌ 系统错误: {str(e)}"


def build_ui():
    """构建 Gradio 界面"""
    
    with gr.Blocks(title="RAG 知识库问答系统") as app:
        # 标题
        gr.Markdown("""
        # 🤖 RAG 智能知识库问答系统
        
        基于混合检索 + 大语言模型的智能问答系统，支持本地部署！
        
        ---
        """)
        
        # 状态栏
        status_display = gr.Markdown(value=get_status)
        
        with gr.Row():
            with gr.Column(scale=3):
                # 聊天界面
                chatbot = gr.Chatbot(
                    label="对话历史",
                    height=500,
                )
                
                with gr.Row():
                    query_input = gr.Textbox(
                        label="请输入问题",
                        placeholder="例如: 什么是 RAG 技术？",
                        scale=4,
                    )
                    submit_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清空对话", variant="secondary")
            
            with gr.Column(scale=1):
                # 设置面板
                gr.Markdown("### ⚙️ 设置")
                
                search_type = gr.Radio(
                    label="检索模式",
                    choices=["hybrid", "similarity", "mmr"],
                    value="hybrid",
                )
                
                prompt_mode = gr.Radio(
                    label="Prompt 模式",
                    choices=["standard", "few_shot", "structured"],
                    value="standard",
                )
                
                gr.Markdown("---")
                
                # 文件上传
                gr.Markdown("### 📤 文档上传")
                file_input = gr.File(
                    label="选择文件 (PDF/Word/TXT/Markdown/CSV)",
                    file_count="single",
                )
                upload_btn = gr.Button("上传并索引")
                upload_status = gr.Textbox(label="上传状态", interactive=False)
                
                gr.Markdown("---")
                
                # 帮助信息
                gr.Markdown("""
                ### 💡 使用提示
                
                - **混合检索 (hybrid)**: 向量 + BM25 组合，效果最好
                - **相似度检索 (similarity)**: 纯向量检索，速度快
                - **MMR 检索**: 注重结果多样性
                
                ### 🔧 技术栈
                
                - LLM: Ollama (本地) / OpenAI API
                - 向量库: Chroma
                - 框架: LangChain + Gradio
                """)
        
        # 事件绑定
        submit_btn.click(
            fn=chat,
            inputs=[query_input, chatbot, search_type, prompt_mode],
            outputs=[query_input, chatbot, status_display],
        )
        
        query_input.submit(
            fn=chat,
            inputs=[query_input, chatbot, search_type, prompt_mode],
            outputs=[query_input, chatbot, status_display],
        )
        
        clear_btn.click(
            fn=clear_history,
            inputs=[],
            outputs=[chatbot, status_display],
        )
        
        upload_btn.click(
            fn=upload_file,
            inputs=[file_input],
            outputs=[upload_status, status_display],
        )
        
        # 定期刷新状态
        app.load(fn=get_status, outputs=status_display)
    
    return app


def main():
    """启动 Gradio 应用"""
    print("Starting RAG Knowledge Base System...")
    print(f"   LLM Provider: {config.llm.provider}")
    print(f"   Model: {config.llm.model}")
    print(f"   URL: http://localhost:7860")
    
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # 面试时设为 False，避免意外分享
        show_error=True,
        theme=Soft(),
    )


if __name__ == "__main__":
    main()
