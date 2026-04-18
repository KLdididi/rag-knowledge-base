pub mod database;

use anyhow::Result;
use rusqlite::Connection;
use std::path::Path;

/// 初始化数据库
pub fn init(db_path: &Path) -> Result<()> {
    let conn = Connection::open(db_path)?;
    
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            doc_type TEXT,
            chunks INTEGER DEFAULT 0,
            size INTEGER DEFAULT 0,
            content_hash TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            content TEXT NOT NULL,
            chunk_index INTEGER,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id TEXT PRIMARY KEY,
            position TEXT,
            companies TEXT,
            difficulty INTEGER,
            status TEXT DEFAULT 'in_progress',
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            overall_score REAL
        );
        
        CREATE TABLE IF NOT EXISTS interview_answers (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            answer TEXT,
            score REAL,
            feedback TEXT,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_answers_session ON interview_answers(session_id);
        "#,
    )?;
    
    Ok(())
}
