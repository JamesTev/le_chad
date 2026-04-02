import math
from typing import List, Dict, Tuple
import sqlite3
from dataclasses import dataclass


@dataclass
class Task:
    id: int
    title: str
    description: str
    status: str
    priority: str
    created_at: str
    updated_at: str


class BM25:
    def __init__(self, corpus: List[Tuple[int, str, str]]):
        self.corpus = corpus
        self.documents = [f"{title} {description}" for _, title, description in corpus]
        self.documents_len = [len(doc.split()) for doc in self.documents]
        self.avg_doc_len = sum(self.documents_len) / len(self.documents_len) if self.documents_len else 0
        self.k1 = 1.5
        self.b = 0.75
        self.idf = self._calculate_idf()

    def _calculate_idf(self) -> Dict[str, float]:
        """Calculate Inverse Document Frequency (IDF) for each term."""
        idf = {}
        total_docs = len(self.documents)
        
        # Count document frequency for each term
        term_doc_freq = {}
        for doc in self.documents:
            terms = set(doc.split())
            for term in terms:
                term_doc_freq[term] = term_doc_freq.get(term, 0) + 1
        
        # Calculate IDF
        for term, freq in term_doc_freq.items():
            idf[term] = math.log((total_docs - freq + 0.5) / (freq + 0.5) + 1)
        
        return idf

    def _calculate_tf(self, term: str, document: str) -> float:
        """Calculate Term Frequency (TF) for a term in a document."""
        terms = document.split()
        term_count = terms.count(term)
        return term_count / len(terms) if terms else 0

    def score(self, query: str, doc_index: int) -> float:
        """Calculate BM25 score for a document given a query."""
        score = 0.0
        doc = self.documents[doc_index]
        doc_len = self.documents_len[doc_index]
        
        for term in query.lower().split():
            tf = self._calculate_tf(term, doc)
            idf = self.idf.get(term, 0)
            
            # BM25 scoring formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
            score += idf * (numerator / denominator)
        
        return score


def search_tasks(db_path: str, query: str, limit: int = 10) -> List[Task]:
    """
    Search tasks using BM25 ranking algorithm.
    
    Args:
        db_path: Path to the SQLite database
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of Task objects sorted by BM25 score in descending order
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Fetch all tasks with their titles and descriptions
        cursor.execute("""
            SELECT id, title, description, status, priority, created_at, updated_at
            FROM tasks
        """)
        
        tasks_data = cursor.fetchall()
        
        if not tasks_data:
            return []
        
        # Prepare corpus for BM25
        corpus = [(task[0], task[1], task[2]) for task in tasks_data]
        
        # Initialize BM25 with the corpus
        bm25 = BM25(corpus)
        
        # Calculate scores for each task
        scored_tasks = []
        for i, task_data in enumerate(tasks_data):
            task_id = task_data[0]
            score = bm25.score(query, i)
            scored_tasks.append((score, task_id, task_data))
        
        # Sort by score in descending order
        scored_tasks.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N tasks as Task objects
        results = []
        for score, task_id, task_data in scored_tasks[:limit]:
            results.append(Task(
                id=task_data[0],
                title=task_data[1],
                description=task_data[2],
                status=task_data[3],
                priority=task_data[4],
                created_at=task_data[5],
                updated_at=task_data[6]
            ))
        
        return results
        
    finally:
        conn.close()