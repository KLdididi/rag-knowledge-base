// Prevents additional console window on Windows in release
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;
mod models;
mod rag;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // 初始化数据目录
            let app_dir = app.path_resolver().app_data_dir().expect("无法获取应用数据目录");
            std::fs::create_dir_all(&app_dir).expect("无法创建数据目录");
            
            // 初始化数据库
            let db_path = app_dir.join("rag_kb.db");
            rag::database::init(&db_path).expect("数据库初始化失败");
            
            println!("数据目录: {:?}", app_dir);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // RAG 查询
            commands::query_rag,
            commands::upload_documents,
            commands::get_documents,
            commands::delete_document,
            commands::get_document_content,
            
            // 面试功能
            commands::start_interview,
            commands::submit_interview_answer,
            commands::complete_interview,
            commands::get_interview_history,
            
            // 设置
            commands::get_settings,
            commands::save_settings,
            commands::check_ollama,
            commands::clear_cache,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
