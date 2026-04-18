use crate::models::*;
use anyhow::Result;
use serde::de::Error;
use std::collections::HashMap;
use std::sync::Mutex;
use tauri::State;

/// 应用状态
pub struct AppState {
    pub settings: Mutex<Settings>,
    pub db: Mutex<Option<rusqlite::Connection>>,
}

/// RAG 查询
#[tauri::command]
pub async fn query_rag(
    request: QueryRequest,
    state: State<'_, AppState>,
) -> Result<QueryResponse, String> {
    let settings = state.settings.lock().map_err(|e| e.to_string())?.clone();
    
    // 调用 Ollama API
    let client = reqwest::Client::new();
    
    let model = request.model.unwrap_or(settings.default_model);
    
    // 构建提示词
    let prompt = if request.use_rag {
        format!(
            "你是一个智能问答助手。请基于以下上下文回答用户问题。\n\n上下文：\n[知识库内容]\n\n问题：{}\n\n请提供详细、准确的回答：",
            request.question
        )
    } else {
        request.question.clone()
    };
    
    let response = client
        .post(format!("{}/api/generate", settings.ollama_host))
        .json(&serde_json::json!({
            "model": model,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": settings.temperature
            }
        }))
        .send()
        .await
        .map_err(|e| format!("请求 Ollama 失败: {}", e))?;
    
    let json: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;
    let answer = json["response"]
        .as_str()
        .unwrap_or("无法获取回答")
        .to_string();
    
    Ok(QueryResponse {
        answer,
        sources: if request.use_rag {
            Some(vec!["文档1.pdf".to_string(), "文档2.docx".to_string()])
        } else {
            None
        },
        confidence: Some(0.85),
    })
}

/// 上传文档
#[tauri::command]
pub async fn upload_documents(files: Vec<serde_json::Value>) -> Result<String, String> {
    // TODO: 实现文档上传和向量化
    Ok(format!("已上传 {} 个文件", files.len()))
}

/// 获取文档列表
#[tauri::command]
pub async fn get_documents(state: State<'_, AppState>) -> Result<DocumentsResponse, String> {
    // TODO: 从数据库获取文档列表
    Ok(DocumentsResponse {
        documents: vec![
            Document {
                id: "1".to_string(),
                filename: "技术文档.pdf".to_string(),
                doc_type: "PDF".to_string(),
                chunks: 42,
                size: 1024000,
                uploaded_at: "2024-01-15 10:30".to_string(),
            },
        ],
        stats: DocumentStats {
            total_docs: 1,
            total_vectors: 42,
            storage_size: 1.0,
            last_update: "2024-01-15".to_string(),
        },
    })
}

#[derive(Serialize)]
pub struct DocumentsResponse {
    pub documents: Vec<Document>,
    pub stats: DocumentStats,
}

#[derive(Serialize)]
pub struct DocumentStats {
    pub total_docs: i32,
    pub total_vectors: i32,
    pub storage_size: f32,
    pub last_update: String,
}

/// 删除文档
#[tauri::command]
pub async fn delete_document(id: String) -> Result<String, String> {
    // TODO: 从数据库删除文档
    Ok(format!("已删除文档 {}", id))
}

/// 获取文档内容
#[tauri::command]
pub async fn get_document_content(id: String) -> Result<String, String> {
    // TODO: 从数据库获取文档内容
    Ok(format!("文档 {} 的内容...", id))
}

/// 开始面试
#[tauri::command]
pub async fn start_interview(config: InterviewConfig) -> Result<InterviewSession, String> {
    let session_id = uuid::Uuid::new_v4().to_string();
    
    // 生成面试题目
    let questions = vec![
        Question {
            id: "q1".to_string(),
            category: "技术".to_string(),
            question: "请介绍一下你对微服务架构的理解？".to_string(),
            difficulty: 2,
            estimated_time: 5,
        },
        Question {
            id: "q2".to_string(),
            category: "技术".to_string(),
            question: "如何处理高并发场景下的数据一致性问题？".to_string(),
            difficulty: 3,
            estimated_time: 8,
        },
    ];
    
    Ok(InterviewSession {
        id: session_id,
        position: config.position,
        progress: "0/2".to_string(),
        current_question: Some(questions[0].clone()),
        questions,
        current_index: 0,
    })
}

/// 提交面试答案
#[tauri::command]
pub async fn submit_interview_answer(
    session_id: String,
    question_id: String,
    answer: String,
) -> Result<SubmitAnswerResponse, String> {
    // 简单的评分逻辑
    let score = if answer.len() > 100 { 75.0 } else { 45.0 };
    
    let feedback = if score >= 70.0 {
        "回答完整，条理清晰。"
    } else {
        "回答较为简单，建议展开更多细节。"
    }.to_string();
    
    Ok(SubmitAnswerResponse {
        evaluation: AnswerEvaluation {
            score,
            feedback,
            key_points: vec!["关键点1".to_string(), "关键点2".to_string()],
        },
        next_question: None,
        progress: "1/2".to_string(),
    })
}

#[derive(Serialize)]
pub struct SubmitAnswerResponse {
    pub evaluation: AnswerEvaluation,
    pub next_question: Option<Question>,
    pub progress: String,
}

/// 完成面试
#[tauri::command]
pub async fn complete_interview(session_id: String) -> Result<InterviewReport, String> {
    let mut category_scores = HashMap::new();
    category_scores.insert("技术".to_string(), 75.0);
    category_scores.insert("系统设计".to_string(), 68.0);
    
    Ok(InterviewReport {
        score: 72.0,
        comment: "整体表现良好，技术基础扎实，建议加强系统设计能力。".to_string(),
        category_scores,
        recommendations: vec![
            "建议深入学习分布式系统设计".to_string(),
            "加强对数据库优化的理解".to_string(),
        ],
    })
}

/// 获取面试历史
#[tauri::command]
pub async fn get_interview_history() -> Result<Vec<InterviewHistory>, String> {
    Ok(vec![
        InterviewHistory {
            id: "1".to_string(),
            position: "后端工程师".to_string(),
            score: 75.0,
            date: "2024-01-14".to_string(),
        },
    ])
}

#[derive(Serialize)]
pub struct InterviewHistory {
    pub id: String,
    pub position: String,
    pub score: f32,
    pub date: String,
}

/// 获取设置
#[tauri::command]
pub async fn get_settings(state: State<'_, AppState>) -> Result<Settings, String> {
    let settings = state.settings.lock().map_err(|e| e.to_string())?;
    Ok(settings.clone())
}

/// 保存设置
#[tauri::command]
pub async fn save_settings(
    settings: Settings,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let mut current = state.settings.lock().map_err(|e| e.to_string())?;
    *current = settings;
    Ok("设置已保存".to_string())
}

/// 检查 Ollama 连接
#[tauri::command]
pub async fn check_ollama(host: String) -> Result<OllamaStatus, String> {
    let client = reqwest::Client::new();
    
    let response = client
        .get(format!("{}/api/tags", host))
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            let json: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
            let models: Vec<String> = json["models"]
                .as_array()
                .map(|arr| {
                    arr.iter()
                        .filter_map(|m| m["name"].as_str().map(|s| s.to_string()))
                        .collect()
                })
                .unwrap_or_default();
            
            Ok(OllamaStatus {
                connected: true,
                models,
            })
        }
        Err(_) => Ok(OllamaStatus {
            connected: false,
            models: vec![],
        }),
    }
}

#[derive(Serialize)]
pub struct OllamaStatus {
    pub connected: bool,
    pub models: Vec<String>,
}

/// 清空缓存
#[tauri::command]
pub async fn clear_cache() -> Result<String, String> {
    // TODO: 清空缓存
    Ok("缓存已清空".to_string())
}
