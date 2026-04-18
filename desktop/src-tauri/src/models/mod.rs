use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// 查询请求
#[derive(Debug, Deserialize)]
pub struct QueryRequest {
    pub question: String,
    pub model: Option<String>,
    #[serde(default = "default_use_rag")]
    pub use_rag: bool,
}

fn default_use_rag() -> bool {
    true
}

/// 查询响应
#[derive(Debug, Serialize)]
pub struct QueryResponse {
    pub answer: String,
    pub sources: Option<Vec<String>>,
    pub confidence: Option<f32>,
}

/// 文档信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub filename: String,
    pub doc_type: String,
    pub chunks: i32,
    pub size: i64,
    pub uploaded_at: String,
}

/// 面试配置
#[derive(Debug, Deserialize)]
pub struct InterviewConfig {
    pub position: String,
    pub companies: Option<Vec<String>>,
    pub difficulty: Option<i32>,
    pub count: Option<i32>,
}

/// 面试会话
#[derive(Debug, Serialize)]
pub struct InterviewSession {
    pub id: String,
    pub position: String,
    pub progress: String,
    pub current_question: Option<Question>,
    pub questions: Vec<Question>,
    pub current_index: usize,
}

/// 面试题目
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Question {
    pub id: String,
    pub category: String,
    pub question: String,
    pub difficulty: i32,
    pub estimated_time: i32,
}

/// 答案评估
#[derive(Debug, Serialize)]
pub struct AnswerEvaluation {
    pub score: f32,
    pub feedback: String,
    pub key_points: Vec<String>,
}

/// 面试报告
#[derive(Debug, Serialize)]
pub struct InterviewReport {
    pub score: f32,
    pub comment: String,
    pub category_scores: HashMap<String, f32>,
    pub recommendations: Vec<String>,
}

/// 系统设置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Settings {
    pub ollama_host: String,
    pub default_model: String,
    pub embedding_model: String,
    pub top_k: i32,
    pub temperature: f32,
    pub chunk_size: i32,
    pub chunk_overlap: i32,
    pub enable_cache: bool,
    pub cache_ttl: i32,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            ollama_host: "http://localhost:11434".to_string(),
            default_model: "qwen2.5:3b".to_string(),
            embedding_model: "nomic-embed-text".to_string(),
            top_k: 5,
            temperature: 0.7,
            chunk_size: 1000,
            chunk_overlap: 200,
            enable_cache: true,
            cache_ttl: 3600,
        }
    }
}
