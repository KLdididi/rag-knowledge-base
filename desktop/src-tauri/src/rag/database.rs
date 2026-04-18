use anyhow::Result;
use rusqlite::Connection;

/// 数据库连接管理
pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(conn: Connection) -> Self {
        Self { conn }
    }
    
    /// 添加文档
    pub fn add_document(&self, id: &str, filename: &str, doc_type: &str, size: i64) -> Result<()> {
        self.conn.execute(
            "INSERT INTO documents (id, filename, doc_type, size) VALUES (?1, ?2, ?3, ?4)",
            (id, filename, doc_type, size),
        )?;
        Ok(())
    }
    
    /// 获取所有文档
    pub fn get_documents(&self) -> Result<Vec<crate::models::Document>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, filename, doc_type, chunks, size, uploaded_at FROM documents ORDER BY uploaded_at DESC"
        )?;
        
        let docs = stmt.query_map([], |row| {
            Ok(crate::models::Document {
                id: row.get(0)?,
                filename: row.get(1)?,
                doc_type: row.get(2)?,
                chunks: row.get(3)?,
                size: row.get(4)?,
                uploaded_at: row.get(5)?,
            })
        })?.collect::<Result<Vec<_>, _>>()?;
        
        Ok(docs)
    }
    
    /// 删除文档
    pub fn delete_document(&self, id: &str) -> Result<()> {
        self.conn.execute("DELETE FROM documents WHERE id = ?1", [id])?;
        self.conn.execute("DELETE FROM chunks WHERE document_id = ?1", [id])?;
        Ok(())
    }
    
    /// 添加缓存
    pub fn set_cache(&self, key: &str, value: &str, ttl_seconds: i64) -> Result<()> {
        let expires_at = chrono::Utc::now() + chrono::Duration::seconds(ttl_seconds);
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?1, ?2, ?3)",
            (key, value, expires_at.to_rfc3339()),
        )?;
        Ok(())
    }
    
    /// 获取缓存
    pub fn get_cache(&self, key: &str) -> Result<Option<String>> {
        let now = chrono::Utc::now().to_rfc3339();
        let result: Option<String> = self.conn.query_row(
            "SELECT value FROM cache WHERE key = ?1 AND expires_at > ?2",
            (key, now),
            |row| row.get(0),
        ).ok();
        
        Ok(result)
    }
    
    /// 清空缓存
    pub fn clear_cache(&self) -> Result<()> {
        self.conn.execute("DELETE FROM cache", [])?;
        Ok(())
    }
}
