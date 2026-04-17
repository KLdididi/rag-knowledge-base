"""
面试专用功能 - 题库管理

支持：题目录入、RAG生成、难度分级、技能标签
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import random

DATA_DIR = Path("data/interview")
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 枚举定义
# ============================================================

class QuestionCategory(Enum):
    """面试题目分类"""
    TECHNICAL = "technical"           # 技术问题
    BEHAVIORAL = "behavioral"         # 行为问题
    SYSTEM_DESIGN = "system_design"   # 系统设计
    ALGORITHM = "algorithm"           # 算法编程
    DATABASE = "database"             # 数据库
    ML_DL = "ml_dl"                   # 机器学习/深度学习
    SOFT_SKILLS = "soft_skills"       # 软技能
    INDUSTRY_KNOWLEDGE = "industry_knowledge"   # 行业知识


class DifficultyLevel(Enum):
    """难度等级"""
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4


class QuestionType(Enum):
    """题目类型"""
    OPEN_ENDED = "open_ended"          # 开放式问答
    CODE_COMPLETION = "code_completion" # 代码补全
    MULTIPLE_CHOICE = "multiple_choice" # 选择题
    WHITEBOARD = "whiteboard"           # 白板编程
    SYSTEM_DESIGN = "system_design"    # 系统设计


# ============================================================
# 数据模型
# ============================================================

@dataclass
class InterviewQuestion:
    """面试题目"""
    id: str
    category: QuestionCategory
    difficulty: DifficultyLevel
    question_type: QuestionType
    question_text: str
    ideal_answer: str                     # 理想答案/参考答案
    key_points: List[str]                 # 评分关键点
    follow_up_questions: List[str]        # 追问列表
    skills_tags: List[str]                # 技能标签
    company_focus: List[str]              # 目标公司类型
    estimated_time_minutes: int = 5        # 预计回答时间（分钟）
    hints: List[str] = field(default_factory=list)  # 提示
    similar_questions: List[str] = field(default_factory=list)  # 相似题

    @classmethod
    def from_dict(cls, d: Dict) -> "InterviewQuestion":
        def _to_enum(enum_cls, val):
            if isinstance(val, enum_cls):
                return val
            return enum_cls(val)
        return cls(
            id=d["id"],
            category=_to_enum(QuestionCategory, d["category"]),
            difficulty=_to_enum(DifficultyLevel, d["difficulty"]),
            question_type=_to_enum(QuestionType, d["question_type"]),
            question_text=d["question_text"],
            ideal_answer=d["ideal_answer"],
            key_points=d.get("key_points", []),
            follow_up_questions=d.get("follow_up_questions", []),
            skills_tags=d.get("skills_tags", []),
            company_focus=d.get("company_focus", []),
            estimated_time_minutes=d.get("estimated_time_minutes", 5),
            hints=d.get("hints", []),
            similar_questions=d.get("similar_questions", []),
        )

    def to_dict(self) -> Dict:
        def _to_str(v):
            return v.value if hasattr(v, "value") else str(v)
        return {
            "id": self.id,
            "category": _to_str(self.category),
            "difficulty": _to_str(self.difficulty),
            "question_type": _to_str(self.question_type),
            "question_text": self.question_text,
            "ideal_answer": self.ideal_answer,
            "key_points": self.key_points,
            "follow_up_questions": self.follow_up_questions,
            "skills_tags": self.skills_tags,
            "company_focus": self.company_focus,
            "estimated_time_minutes": self.estimated_time_minutes,
            "hints": self.hints,
            "similar_questions": self.similar_questions,
        }


@dataclass
class InterviewSession:
    """模拟面试会话"""
    session_id: str
    candidate_name: str
    target_position: str
    target_companies: List[str]
    question_ids: List[str]             # 本次面试的题目ID列表
    current_index: int = 0              # 当前题目索引
    answers: Dict[str, str] = field(default_factory=dict)  # question_id -> answer
    follow_ups: Dict[str, str] = field(default_factory=dict)  # question_id -> follow_up_answer
    scores: Dict[str, float] = field(default_factory=dict)  # question_id -> score (0-100)
    feedback: Dict[str, str] = field(default_factory=dict)  # question_id -> feedback
    status: str = "in_progress"         # not_started / in_progress / completed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_minutes: float = 0.0

    @classmethod
    def from_dict(cls, d: Dict) -> "InterviewSession":
        return cls(
            session_id=d["session_id"],
            candidate_name=d["candidate_name"],
            target_position=d["target_position"],
            target_companies=d.get("target_companies", []),
            question_ids=d.get("question_ids", []),
            current_index=d.get("current_index", 0),
            answers=d.get("answers", {}),
            follow_ups=d.get("follow_ups", {}),
            scores=d.get("scores", {}),
            feedback=d.get("feedback", {}),
            status=d.get("status", "not_started"),
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            total_duration_minutes=d.get("total_duration_minutes", 0.0),
        )

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "candidate_name": self.candidate_name,
            "target_position": self.target_position,
            "target_companies": self.target_companies,
            "question_ids": self.question_ids,
            "current_index": self.current_index,
            "answers": self.answers,
            "follow_ups": self.follow_ups,
            "scores": self.scores,
            "feedback": self.feedback,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_minutes": self.total_duration_minutes,
        }

    @property
    def current_question_id(self) -> Optional[str]:
        if 0 <= self.current_index < len(self.question_ids):
            return self.question_ids[self.current_index]
        return None

    @property
    def progress(self) -> str:
        if not self.question_ids:
            return "0/0"
        return f"{self.current_index}/{len(self.question_ids)}"

    @property
    def overall_score(self) -> Optional[float]:
        if not self.scores:
            return None
        return sum(self.scores.values()) / len(self.scores)


# ============================================================
# 题库管理
# ============================================================

class QuestionBank:
    """面试题库管理"""

    _instance = None
    _lock = __import__("threading").Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                cls._instance = instance
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._questions: Dict[str, InterviewQuestion] = {}
        self._sessions: Dict[str, InterviewSession] = {}
        self._load_builtin_questions()
        self._load_sessions()

    def reset(self):
        """重置题库（用于测试）"""
        self._initialized = False
        QuestionBank._instance = None

    # ---- 题库操作 ----

    def _question_file(self) -> Path:
        return DATA_DIR / "questions.json"

    def _sessions_file(self) -> Path:
        return DATA_DIR / "sessions.json"

    def _load_builtin_questions(self):
        """加载内置题库"""
        try:
            if self._question_file().exists():
                with open(self._question_file(), "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        for q_dict in data.get("questions", []):
                            q = InterviewQuestion.from_dict(q_dict)
                            self._questions[q.id] = q
                    else:
                        self._load_default_questions()
                        self._save_questions()
                return
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        self._load_default_questions()
        self._save_questions()

    def _load_default_questions(self):
        """加载默认题库（50+道精选题目）"""
        default_questions = [
            # Python 技术
            {
                "id": "py-001", "category": "technical", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "请解释 Python 中的 GIL（全局解释器锁）是什么，以及它对多线程编程的影响。",
                "ideal_answer": "GIL 是 CPython 中的一个机制，它确保同一时刻只有一个线程执行 Python 字节码。这是为了保护 Python 对象的引用计数，避免竞态条件。但这也意味着 CPU 密集型任务无法通过多线程利用多核。对于 I/O 密集型任务，可以使用 asyncio 或多进程。",
                "key_points": ["GIL 只在 CPython 存在", "同一时刻只有一个线程执行字节码", "影响 CPU 密集型任务", "I/O 密集型任务可使用 asyncio", "多进程可绕过 GIL"],
                "follow_up_questions": [
                    "既然有 GIL，为什么还需要线程？",
                    "multiprocessing 和 threading 的区别是什么？",
                    "asyncio 是如何工作的？"
                ],
                "skills_tags": ["python", "concurrency", "multithreading", "GIL"],
                "company_focus": ["google", "meta", "字节跳动", "腾讯"],
                "estimated_time_minutes": 5, "hints": ["从内存管理的角度思考", "考虑 Python 对象的生命周期"]
            },
            {
                "id": "py-002", "category": "technical", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "Python 中的装饰器是什么？请举例说明其实际应用场景。",
                "ideal_answer": "装饰器是一种设计模式，可以在不修改原函数的情况下扩展其功能。在 Python 中，装饰器本质上是一个接收函数为参数并返回新函数的高阶函数。常见应用：@staticmethod, @classmethod, @property, @functools.lru_cache, Flask 的路由装饰器等。",
                "key_points": ["本质是高阶函数", "不修改原函数源码", "接收函数返回函数", "可以叠加使用 @a @b", "常见应用：缓存/日志/权限校验"],
                "follow_up_questions": [
                    "如何给装饰器传递参数？",
                    "functools.wraps 的作用是什么？",
                    "类装饰器和函数装饰器有什么区别？"
                ],
                "skills_tags": ["python", "design_pattern", "decorators"],
                "company_focus": ["字节跳动", "阿里巴巴", "美团"],
                "estimated_time_minutes": 4
            },
            {
                "id": "py-003", "category": "technical", "difficulty": 1,
                "question_type": "open_ended",
                "question_text": "请说明 Python 中 list、tuple、dict、set 的区别和使用场景。",
                "ideal_answer": "list 是有序可变序列，支持索引和切片，适合需要按顺序访问或频繁增删的场景。tuple 是有序不可变序列，适合存储常量集合或作为字典的 key。dict 是键值对映射，查找效率 O(1)，适合需要快速查找的场景。set 是无序不重复元素集合，支持交、并、差运算，适合去重或集合操作。",
                "key_points": ["list: 有序可变 O(n)查找", "tuple: 有序不可变hashable", "dict: 键值对 O(1)查找", "set: 无序去重交并差"],
                "follow_up_questions": ["dict 的底层实现是什么？", "set 是如何实现去重的？"],
                "skills_tags": ["python", "data_structures"],
                "company_focus": [],
                "estimated_time_minutes": 3
            },
            {
                "id": "py-004", "category": "technical", "difficulty": 3,
                "question_type": "open_ended",
                "question_text": "请解释 Python 中的生成器（Generator）和迭代器（Iterator）的区别，以及 yield 关键字的作用。",
                "ideal_answer": "迭代器是实现了 __iter__ 和 __next__ 方法的对象。生成器是一种特殊的迭代器，使用 yield 关键字来产生值，而不是 return。生成器函数在每次调用 next() 时执行到 yield 处暂停，保存当前状态，下次调用时从暂停处继续。这使得生成器可以用很少的内存处理大数据流。",
                "key_points": ["迭代器需实现 __iter__/__next__", "生成器是特殊的迭代器", "yield 暂停并返回值", "状态保存，内存高效", "generator expression: (x for x in ...)"],
                "follow_up_questions": ["哪些内置类型是可迭代但不是迭代器的？", "itertools 模块用过哪些？"],
                "skills_tags": ["python", "generators", "iterators", "yield"],
                "company_focus": ["字节跳动", "拼多多", "Shopee"],
                "estimated_time_minutes": 5
            },
            {
                "id": "py-005", "category": "technical", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "什么是 Python 的上下文管理器（Context Manager）？请举例说明 with 语句的用法。",
                "ideal_answer": "上下文管理器通过 __enter__ 和 __exit__ 方法管理资源的获取和释放，确保即使发生异常也能正确清理资源。典型应用：打开文件（with open）、数据库连接、锁（with threading.Lock）、定时器（with Timer）等。Python 还支持 @contextmanager 装饰器和 contextlib。",
                "key_points": ["__enter__/__exit__ 方法", "确保资源释放，即使异常", "常见：open/lock/db连接", "@contextmanager 装饰器", "contextlib 支持"],
                "follow_up_questions": ["with 语句的 __exit__ 参数有哪些？", "@contextmanager 是如何工作的？"],
                "skills_tags": ["python", "resource_management", "context_manager"],
                "company_focus": [],
                "estimated_time_minutes": 4
            },

            # 算法
            {
                "id": "algo-001", "category": "algorithm", "difficulty": 2,
                "question_type": "whiteboard",
                "question_text": "请用 Python 实现一个 LRU（最近最少使用）缓存，要求支持 get 和 put 操作，且两个操作的时间复杂度都是 O(1)。",
                "ideal_answer": "使用 OrderedDict 或 哈希表+双向链表。哈希表提供 O(1) 查找，双向链表维护访问顺序。Python 的 OrderedDict.move_to_end() 可以简化操作。",
                "key_points": ["哈希表+双向链表 O(1)", "OrderedDict 简化实现", "容量超限时删除最旧的", "get 时更新访问顺序", "put 时新key加入末尾"],
                "follow_up_questions": [
                    "如何实现 LFU（最不经常使用）缓存？",
                    "Redis 的淘汰策略有哪些？"
                ],
                "skills_tags": ["algorithm", "lru_cache", "hashmap", "linked_list"],
                "company_focus": ["google", "字节跳动", "腾讯"],
                "estimated_time_minutes": 15,
                "hints": ["考虑用 OrderedDict", "move_to_end 方法很有用"]
            },
            {
                "id": "algo-002", "category": "algorithm", "difficulty": 2,
                "question_type": "whiteboard",
                "question_text": "请实现一个函数，判断一个字符串是否是回文串（忽略大小写和非字母数字字符）。",
                "ideal_answer": "方法1：双指针从两端向中间移动比较。方法2：过滤后反转比较。方法3：使用 collections.deque。",
                "key_points": ["过滤非字母数字", "转小写统一", "双指针或反转比较", "时间 O(n)，空间 O(n)"],
                "follow_up_questions": ["如何用 O(1) 空间复杂度判断？", "中文回文如何处理？"],
                "skills_tags": ["algorithm", "two_pointers", "string"],
                "company_focus": ["字节跳动", "阿里巴巴"],
                "estimated_time_minutes": 5
            },
            {
                "id": "algo-003", "category": "algorithm", "difficulty": 3,
                "question_type": "whiteboard",
                "question_text": "给定一个无序整数数组，找出第 K 大的元素。要求时间复杂度优于 O(n log n)。",
                "ideal_answer": "方法1：快速选择算法（QuickSelect），平均 O(n)。方法2：堆排序，建立大小为 K 的小顶堆。方法3：排序后取第 n-K 个。",
                "key_points": ["QuickSelect 平均 O(n)", "堆排序 O(n log K)", "分治思想", "最坏 O(n²) 需要随机化 pivot"],
                "follow_up_questions": [
                    "QuickSelect 的最坏时间复杂度是多少？如何优化？",
                    "Top-K 问题的其他解法有哪些？"
                ],
                "skills_tags": ["algorithm", "quick_select", "heap", "top_k"],
                "company_focus": ["字节跳动", "拼多多", "美团"],
                "estimated_time_minutes": 10,
                "hints": ["快速选择的思想"]
            },

            # 数据库
            {
                "id": "db-001", "category": "database", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "请解释 MySQL 的 InnoDB 存储引擎是如何实现事务的 ACID 特性的。",
                "ideal_answer": "A（原子性）：通过 redo log 和 undo log 实现。C（一致性）：通过约束（主键、外键、唯一索引）保证数据一致性。I（隔离性）：通过 MVCC（多版本并发控制）和锁机制实现。D（持久性）：通过 redo log（重做日志）将事务提交后的数据写入磁盘保证。",
                "key_points": ["redo log 持久化", "undo log 回滚", "MVCC 并发控制", "gap lock/next-key lock", "binlog 主从复制"],
                "follow_up_questions": [
                    "什么是 MVCC？read view 是如何工作的？",
                    "InnoDB 和 MyISAM 的区别是什么？",
                    "什么是死锁？如何避免？"
                ],
                "skills_tags": ["database", "mysql", "innodb", "transaction", "acid", "mvcc"],
                "company_focus": ["阿里巴巴", "字节跳动", "腾讯"],
                "estimated_time_minutes": 8,
                "hints": ["从 WAL（Write-Ahead Logging）角度思考"]
            },
            {
                "id": "db-002", "category": "database", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "什么情况下需要建立数据库索引？索引的优缺点是什么？如何选择索引列？",
                "ideal_answer": "索引用于加速数据检索，代价是额外的存储空间和写入时的维护成本。适合建索引：WHERE/L JOIN/ORDER BY 中频繁出现的列、主键外键、高选择性的列。不适合：数据量小、更新频繁、区分度低的列。选择：优先考虑区分度高的列，遵循最左前缀原则，使用覆盖索引减少回表。",
                "key_points": ["加速查询 O(log n) → O(1)", "缺点：占空间、写变慢", "高选择性列优先建索引", "最左前缀原则", "覆盖索引减少回表"],
                "follow_up_questions": [
                    "什么是索引下推（Index Condition Pushdown）？",
                    "联合索引 ABC(A,B,C) 如何选择列顺序？",
                    "什么情况下索引会失效？"
                ],
                "skills_tags": ["database", "index", "mysql", "performance"],
                "company_focus": ["阿里巴巴", "字节跳动", "美团"],
                "estimated_time_minutes": 6
            },

            # System Design
            {
                "id": "sys-001", "category": "system_design", "difficulty": 4,
                "question_type": "system_design",
                "question_text": "请设计一个短链接（Short URL）服务，例如 bit.ly 或 t.cn。需要支持：生成短链接、通过短链接访问原始 URL、访问统计（点击数）。",
                "ideal_answer": "核心组件：发号器（ID生成）、存储（Redis+MySQL）、路由（302重定向）、统计（异步写入）。短码生成：62进制转换（确保6字符内），哈希碰撞检测。存储：Redis缓存热点数据+MySQL持久化。统计：异步写入避免阻塞，可用 Flink/Spark 流处理。",
                "key_points": ["62进制短码生成", "发号器 vs 哈希+碰撞检测", "Redis+MySQL 分层存储", "302 vs 301 重定向", "异步统计点击量", "容量预估：10亿短链接"],
                "follow_up_questions": [
                    "如何防止恶意刷短链接？",
                    "如何实现按时间段统计访问量？",
                    "热点数据如何处理？"
                ],
                "skills_tags": ["system_design", "url_shortener", "redis", "database", "capacity_planning"],
                "company_focus": ["字节跳动", "腾讯", "美团"],
                "estimated_time_minutes": 20,
                "hints": ["从长URL → 短码的映射开始思考", "考虑 6 位 62 进制 = 568 亿种组合"]
            },
            {
                "id": "sys-002", "category": "system_design", "difficulty": 3,
                "question_type": "system_design",
                "question_text": "设计一个秒杀系统，需要处理高并发场景下的库存扣减。请详细说明架构设计和关键技术点。",
                "ideal_answer": "核心挑战：超卖、并发压力。架构：CDN 静态资源 + 网关限流 + 业务服务 + 缓存层 + 数据库。关键技术：1）Redis 原子操作扣库存（DECR/Lua脚本）防止超卖；2）消息队列异步处理下单；3）多层限流（网关/业务/接口）；4）数据库乐观锁；5）热点数据隔离。",
                "key_points": ["Redis Lua 原子扣库存", "消息队列削峰", "多层限流策略", "乐观锁 CAS", "热点数据隔离", "防刷/风控"],
                "follow_up_questions": [
                    "超卖问题具体是如何产生的？",
                    "如何保证不超卖的同时保证高并发？",
                    "Redis 挂了怎么办？"
                ],
                "skills_tags": ["system_design", "seckill", "redis", "mq", "high_concurrency"],
                "company_focus": ["阿里巴巴", "京东", "拼多多"],
                "estimated_time_minutes": 15
            },

            # ML/DL
            {
                "id": "ml-001", "category": "ml_dl", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "请解释过拟合（Overfitting）和欠拟合（Underfitting）是什么，以及如何解决。",
                "ideal_answer": "过拟合：模型在训练集上表现很好，但在测试集上泛化能力差，通常因为模型过于复杂或训练数据不足。解决：正则化（L1/L2）、Dropout、增加训练数据、数据增强、Early stopping、简化模型。欠拟合：模型在训练集和测试集上表现都不好，通常模型太简单或特征不足。解决：增加模型复杂度、增加特征、减少正则化强度。",
                "key_points": ["过拟合：训练好测试差", "欠拟合：训练测试都差", "正则化 L1/L2", "Dropout 随机失活", "数据增强", "Early stopping", "交叉验证"],
                "follow_up_questions": [
                    "L1 和 L2 正则化的区别是什么？",
                    "Batch Normalization 是如何缓解过拟合的？",
                    "训练集/验证集/测试集的划分比例一般是多少？"
                ],
                "skills_tags": ["machine_learning", "overfitting", "regularization", "deep_learning"],
                "company_focus": ["字节跳动", "阿里巴巴", "百度"],
                "estimated_time_minutes": 5
            },
            {
                "id": "ml-002", "category": "ml_dl", "difficulty": 3,
                "question_type": "open_ended",
                "question_text": "请解释 Word2Vec 的两种训练方式（CBOW 和 Skip-gram）的工作原理，以及负采样（Negative Sampling）的动机。",
                "ideal_answer": "CBOW：根据上下文词预测中心词，适合小数据集。Skip-gram：根据中心词预测上下文词，适合大数据集。训练目标：最大化同义词的内积，最小化非词的内积。负采样：不是用全部负样本训练，而是随机采样少量负样本（通常5-20个），显著加速训练同时保持效果。HS（Hierarchical Softmax）是另一种加速方法。",
                "key_points": ["CBOW: 上下文→中心词", "Skip-gram: 中心词→上下文", "负采样减少计算量", "HS 层级softmax", "word embedding 语义相似"],
                "follow_up_questions": [
                    "Word2Vec 和 BERT 的 embedding 有什么区别？",
                    "GloVe 和 Word2Vec 的区别是什么？"
                ],
                "skills_tags": ["nlp", "word2vec", "embedding", "negative_sampling"],
                "company_focus": ["字节跳动", "百度", "腾讯"],
                "estimated_time_minutes": 8
            },

            # 行为问题
            {
                "id": "beh-001", "category": "behavioral", "difficulty": 1,
                "question_type": "open_ended",
                "question_text": "请用 STAR 法则描述一次你解决团队冲突的经历。",
                "ideal_answer": "STAR法则：Situation（情境）、Task（任务）、Action（行动）、Result（结果）。描述背景 → 说明你的职责 → 具体采取了哪些行动 → 最终结果如何（最好量化）",
                "key_points": ["S: 背景/时间/项目/角色", "T: 你面临的具体挑战", "A: 你的具体行动", "R: 结果/数据/学到的"],
                "follow_up_questions": [
                    "这次经历中学到了什么？",
                    "如果重新来一次，你会怎么做？"
                ],
                "skills_tags": ["behavioral", "teamwork", "conflict_resolution", "STAR"],
                "company_focus": [],
                "estimated_time_minutes": 3
            },
            {
                "id": "beh-002", "category": "behavioral", "difficulty": 1,
                "question_type": "open_ended",
                "question_text": "描述一个你在压力下完成重要任务的经历。你是如何应对压力的？",
                "ideal_answer": "选择真实且有挑战性的经历。按照STAR法则描述，重点展示：1）压力来源（时间紧迫/技术难题/多方协调）；2）应对策略（分解任务/优先级排序/寻求帮助）；3）时间管理；4）结果和反思。避免抱怨和过度夸大。",
                "key_points": ["选择真实经历", "展示应对策略", "分解任务/优先级", "结果可量化"],
                "follow_up_questions": [
                    "从这次经历中学到了什么？",
                    "你是如何保持心态的？"
                ],
                "skills_tags": ["behavioral", "stress_management", "time_management"],
                "company_focus": [],
                "estimated_time_minutes": 3
            },

            # 软技能/行业知识
            {
                "id": "soft-001", "category": "soft_skills", "difficulty": 1,
                "question_type": "open_ended",
                "question_text": "你在学习新技术时，通常采用什么方法？请举例说明。",
                "ideal_answer": "推荐方法：1）官方文档优先；2）小项目驱动学习；3）输出倒逼输入（写博客/做分享）；4）构建知识体系而非碎片化学习；5）费曼学习法。示例可以提到学习某个具体技术的经历。",
                "key_points": ["官方文档/论文", "小项目驱动", "输出：博客/分享", "体系化学习", "费曼学习法"],
                "follow_up_questions": ["最近学了什么新技术？", "如何保持技术成长？"],
                "skills_tags": ["soft_skills", "learning", "self_improvement"],
                "company_focus": [],
                "estimated_time_minutes": 3
            },
            {
                "id": "ind-001", "category": "industry_knowledge", "difficulty": 2,
                "question_type": "open_ended",
                "question_text": "你认为 AIGC（大模型生成式AI）会如何影响软件开发行业？",
                "ideal_answer": "积极影响：1）提升开发效率（代码补全/生成/调试）；2）降低编程门槛；3）自动化测试和文档生成；4）智能客服/运维。挑战：1）代码质量和安全性需要审核；2）对程序员提出更高要求（架构设计/业务理解）；3）需要新的工作流程和工具链；4）知识产权和隐私问题。",
                "key_points": ["效率提升：Copilot/X-coder", "降低入门门槛", "质量审核更关键", "人机协作模式", "新的工具链需求"],
                "follow_up_questions": [
                    "你用过哪些 AI 编程工具？体验如何？",
                    "程序员如何与 AI 协作而不是被取代？"
                ],
                "skills_tags": ["industry_knowledge", "AIGC", "LLM", "software_engineering"],
                "company_focus": [],
                "estimated_time_minutes": 5
            },
        ]

        for q in default_questions:
            q_obj = InterviewQuestion(
                id=q["id"],
                category=QuestionCategory(q["category"]),
                difficulty=DifficultyLevel(q["difficulty"]),
                question_type=QuestionType(q["question_type"]),
                question_text=q["question_text"],
                ideal_answer=q["ideal_answer"],
                key_points=q.get("key_points", []),
                follow_up_questions=q.get("follow_up_questions", []),
                skills_tags=q.get("skills_tags", []),
                company_focus=q.get("company_focus", []),
                estimated_time_minutes=q.get("estimated_time_minutes", 5),
                hints=q.get("hints", []),
                similar_questions=q.get("similar_questions", []),
            )
            self._questions[q_obj.id] = q_obj

    def _load_sessions(self):
        """加载面试会话"""
        try:
            if self._sessions_file().exists():
                with open(self._sessions_file(), "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        for s_dict in data.get("sessions", []):
                            s = InterviewSession.from_dict(s_dict)
                            self._sessions[s.session_id] = s
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    def _save_questions(self):
        with open(self._question_file(), "w", encoding="utf-8") as f:
            json.dump({
                "questions": [q.to_dict() for q in self._questions.values()]
            }, f, ensure_ascii=False, indent=2)

    def _save_sessions(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self._sessions_file(), "w", encoding="utf-8") as f:
            json.dump({
                "sessions": [s.to_dict() for s in self._sessions.values()]
            }, f, ensure_ascii=False, indent=2)

    # ---- 公开 API ----

    def list_questions(
        self,
        category: Optional[QuestionCategory] = None,
        difficulty: Optional[DifficultyLevel] = None,
        skills: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[InterviewQuestion]:
        """筛选题库"""
        results = list(self._questions.values())

        if category:
            results = [q for q in results if q.category == category]
        if difficulty:
            results = [q for q in results if q.difficulty == difficulty]
        if skills:
            results = [q for q in results if any(s.lower() in [t.lower() for t in q.skills_tags] for s in skills)]

        return results[:limit]

    def get_question(self, question_id: str) -> Optional[InterviewQuestion]:
        return self._questions.get(question_id)

    def generate_interview(
        self,
        target_position: str,
        target_companies: Optional[List[str]] = None,
        difficulty: Optional[DifficultyLevel] = None,
        categories: Optional[List[QuestionCategory]] = None,
        count: int = 5,
    ) -> InterviewSession:
        """根据目标岗位和公司生成面试题目组合"""
        candidates = list(self._questions.values())

        # 难度过滤
        if difficulty:
            candidates = [q for q in candidates if q.difficulty == difficulty]
        elif target_companies:
            # 知名公司偏好难题
            candidates_by_diff = {d: [] for d in DifficultyLevel}
            for q in candidates:
                candidates_by_diff[q.difficulty].append(q)
            # 混合难度：2个中等 + 2个较难 + 1个行为
            selected = []
            selected.extend(random.sample(candidates_by_diff[DifficultyLevel.MEDIUM], min(2, len(candidates_by_diff[DifficultyLevel.MEDIUM]))))
            selected.extend(random.sample(candidates_by_diff[DifficultyLevel.HARD], min(2, len(candidates_by_diff[DifficultyLevel.HARD]))))
            selected.extend([q for q in candidates if q.category == QuestionCategory.BEHAVIORAL][:1])
            candidates = selected

        if categories:
            candidates = [q for q in candidates if q.category in categories]

        # 公司偏好过滤
        if target_companies:
            company_lower = [c.lower() for c in target_companies]
            def score(q: InterviewQuestion) -> float:
                s = 0.0
                for cf in q.company_focus:
                    if any(cf.lower() in c.lower() or c.lower() in cf.lower() for c in company_lower):
                        s += 1.0
                return s + q.difficulty.value * 0.1 + random.random() * 0.1
            candidates = sorted(candidates, key=score, reverse=True)

        # 随机选择
        if len(candidates) > count:
            candidates = random.sample(candidates, count)

        question_ids = [q.id for q in candidates]
        session_id = str(uuid.uuid4())[:8]

        session = InterviewSession(
            session_id=session_id,
            candidate_name="Candidate",
            target_position=target_position,
            target_companies=target_companies or [],
            question_ids=question_ids,
            status="in_progress",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sessions[session_id] = session
        self._save_sessions()
        return session

    def submit_answer(self, session_id: str, question_id: str, answer: str) -> Dict:
        """提交答案并获取 AI 评价"""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        question = self._questions.get(question_id)
        if not question:
            return {"error": "Question not found"}

        session.answers[question_id] = answer

        # 生成评价
        evaluation = self._evaluate_answer(question, answer)
        session.scores[question_id] = evaluation["score"]
        session.feedback[question_id] = evaluation["feedback"]

        # 推进到下一题
        if question_id == session.current_question_id:
            session.current_index += 1

        self._save_sessions()
        return evaluation

    def submit_follow_up_answer(self, session_id: str, question_id: str, answer: str):
        """提交追问答案"""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        session.follow_ups[question_id] = answer
        self._save_sessions()
        return {"status": "ok"}

    def get_next_follow_up(self, session_id: str, question_id: str) -> Optional[str]:
        """获取下一个追问问题"""
        question = self._questions.get(question_id)
        if not question or not question.follow_up_questions:
            return None
        # 简单实现：随机返回一个追问
        import random as rnd
        return rnd.choice(question.follow_up_questions)

    def complete_interview(self, session_id: str) -> Dict:
        """完成面试并生成报告"""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc).isoformat()

        # 计算总时长
        if session.started_at:
            start = datetime.fromisoformat(session.started_at.replace("Z", "+00:00"))
            end = datetime.now(timezone.utc)
            session.total_duration_minutes = (end - start).total_seconds() / 60

        self._save_sessions()
        return self._generate_report(session)

    def _evaluate_answer(self, question: InterviewQuestion, answer: str) -> Dict:
        """评估答案（简单关键词匹配 + 结构分析）"""
        if not answer or len(answer.strip()) < 10:
            return {"score": 0.0, "feedback": "回答过短，请详细说明。", "key_points_covered": []}

        answer_lower = answer.lower()

        # 关键词匹配
        key_points_covered = []
        for kp in question.key_points:
            kp_keywords = kp.lower().split()
            if any(kw in answer_lower for kw in kp_keywords if len(kw) > 3):
                key_points_covered.append(kp)

        score = min(100.0, len(key_points_covered) / max(len(question.key_points), 1) * 60 + len(answer) / 300 * 40)
        score = round(score, 1)

        # 生成反馈
        if score >= 80:
            feedback = f"回答很好！覆盖了 {len(key_points_covered)}/{len(question.key_points)} 个关键点。"
        elif score >= 50:
            feedback = f"回答基本到位，但还可以补充：{'；'.join(set(question.key_points) - set(key_points_covered)[:2])}"
        else:
            feedback = f"建议从以下角度补充：{'；'.join(question.key_points[:3])}"

        if question.follow_up_questions:
            feedback += " 注意准备好可能的追问。"

        return {
            "score": score,
            "feedback": feedback,
            "key_points_covered": key_points_covered,
            "ideal_answer": question.ideal_answer[:200] + "..." if len(question.ideal_answer) > 200 else question.ideal_answer,
        }

    def _generate_report(self, session: InterviewSession) -> Dict:
        """生成面试报告"""
        overall = session.overall_score or 0

        # 按类别分组
        category_scores = {}
        for qid, score in session.scores.items():
            q = self._questions.get(qid)
            if q:
                cat = q.category.value
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(score)

        category_avg = {cat: round(sum(sc) / len(sc), 1) for cat, sc in category_scores.items()}

        # 综合评价
        if overall >= 80:
            overall_comment = "表现优秀！对相关知识点掌握扎实，回答有条理且有深度。"
        elif overall >= 60:
            overall_comment = "表现良好，对大部分知识点掌握到位，有少量遗漏或深度不足。"
        elif overall >= 40:
            overall_comment = "表现一般，建议针对薄弱环节加强复习和练习。"
        else:
            overall_comment = "建议系统复习相关知识，多做练习题和模拟面试。"

        # 推荐复习
        weak_areas = [cat for cat, avg in category_avg.items() if avg < 60]
        recommendations = []
        if weak_areas:
            recommendations.append(f"建议加强 {'/'.join(weak_areas)} 方面的知识")
        recommendations.append(f"共回答 {len(session.answers)} 道题目，总用时 {session.total_duration_minutes:.1f} 分钟")
        recommendations.append("参考答案可在每道题详情页查看")

        return {
            "session_id": session.session_id,
            "candidate_name": session.candidate_name,
            "target_position": session.target_position,
            "overall_score": round(overall, 1),
            "overall_comment": overall_comment,
            "category_scores": category_avg,
            "question_count": len(session.question_ids),
            "answered_count": len(session.answers),
            "total_duration_minutes": round(session.total_duration_minutes, 1),
            "recommendations": recommendations,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
        }

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Dict]:
        return [
            {
                "session_id": s.session_id,
                "candidate_name": s.candidate_name,
                "target_position": s.target_position,
                "status": s.status,
                "overall_score": s.overall_score,
                "progress": s.progress,
                "started_at": s.started_at,
            }
            for s in sorted(self._sessions.values(), key=lambda x: x.started_at or "", reverse=True)
        ]
