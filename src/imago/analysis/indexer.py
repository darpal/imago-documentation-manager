"""Document indexing and full-text search using SQLite FTS5."""

import sqlite3
from pathlib import Path
from typing import Optional


class DocumentIndexer:
    """Indexes Markdown documents for full-text search."""

    def __init__(self, index_path: Path):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database with FTS5."""
        with sqlite3.connect(self.index_path) as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
                    repo,
                    file_path,
                    title,
                    content,
                    tokenize='porter unicode61'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_meta (
                    id INTEGER PRIMARY KEY,
                    repo TEXT,
                    file_path TEXT UNIQUE,
                    last_modified REAL,
                    word_count INTEGER,
                    line_count INTEGER
                )
            """)
            conn.commit()

    def _extract_title(self, content: str) -> str:
        """Extract title from Markdown content."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def _count_words(self, content: str) -> int:
        """Count words in content."""
        return len(content.split())

    def index_file(self, repo_name: str, file_path: Path) -> bool:
        """Index a single Markdown file."""
        if not file_path.exists() or file_path.suffix.lower() not in (".md", ".markdown"):
            return False

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return False

        title = self._extract_title(content)
        rel_path = str(file_path)
        last_modified = file_path.stat().st_mtime
        word_count = self._count_words(content)
        line_count = len(content.split("\n"))

        with sqlite3.connect(self.index_path) as conn:
            # Check if file needs reindexing
            cursor = conn.execute(
                "SELECT last_modified FROM document_meta WHERE file_path = ?",
                (rel_path,)
            )
            row = cursor.fetchone()

            if row and row[0] >= last_modified:
                return False  # Already indexed and up to date

            # Remove old entry if exists
            conn.execute("DELETE FROM documents WHERE file_path = ?", (rel_path,))
            conn.execute("DELETE FROM document_meta WHERE file_path = ?", (rel_path,))

            # Insert new entry
            conn.execute(
                "INSERT INTO documents (repo, file_path, title, content) VALUES (?, ?, ?, ?)",
                (repo_name, rel_path, title, content)
            )
            conn.execute(
                """INSERT INTO document_meta
                   (repo, file_path, last_modified, word_count, line_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (repo_name, rel_path, last_modified, word_count, line_count)
            )
            conn.commit()

        return True

    def index_repository(self, repo_path: Path, repo_name: Optional[str] = None) -> int:
        """Index all Markdown files in a repository."""
        repo_path = Path(repo_path)
        repo_name = repo_name or repo_path.name
        indexed_count = 0

        for md_file in repo_path.rglob("*.md"):
            # Get path relative to repo for checking hidden dirs
            try:
                rel_path = md_file.relative_to(repo_path)
            except ValueError:
                continue

            # Skip hidden directories and common non-doc paths (only within repo)
            if any(part.startswith(".") for part in rel_path.parts):
                continue
            if "node_modules" in rel_path.parts:
                continue

            if self.index_file(repo_name, md_file):
                indexed_count += 1

        # Also index .markdown files
        for md_file in repo_path.rglob("*.markdown"):
            try:
                rel_path = md_file.relative_to(repo_path)
            except ValueError:
                continue

            if any(part.startswith(".") for part in rel_path.parts):
                continue
            if self.index_file(repo_name, md_file):
                indexed_count += 1

        return indexed_count

    def search(self, query: str, repo: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Search for documents matching the query."""
        with sqlite3.connect(self.index_path) as conn:
            if repo:
                cursor = conn.execute(
                    """SELECT file_path, title, snippet(documents, 3, '>>>', '<<<', '...', 32)
                       FROM documents
                       WHERE documents MATCH ? AND repo = ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, repo, limit)
                )
            else:
                cursor = conn.execute(
                    """SELECT file_path, title, snippet(documents, 3, '>>>', '<<<', '...', 32)
                       FROM documents
                       WHERE documents MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, limit)
                )

            results = []
            for row in cursor:
                results.append({
                    "file": row[0],
                    "title": row[1],
                    "snippet": row[2],
                })

            return results

    def get_all_documents(self, repo: Optional[str] = None) -> list[dict]:
        """Get all indexed documents."""
        with sqlite3.connect(self.index_path) as conn:
            if repo:
                cursor = conn.execute(
                    """SELECT m.file_path, m.word_count, m.line_count
                       FROM document_meta m
                       WHERE m.repo = ?""",
                    (repo,)
                )
            else:
                cursor = conn.execute(
                    "SELECT file_path, word_count, line_count FROM document_meta"
                )

            return [
                {"file": row[0], "word_count": row[1], "line_count": row[2]}
                for row in cursor
            ]

    def clear(self, repo: Optional[str] = None) -> None:
        """Clear indexed documents."""
        with sqlite3.connect(self.index_path) as conn:
            if repo:
                conn.execute("DELETE FROM documents WHERE repo = ?", (repo,))
                conn.execute("DELETE FROM document_meta WHERE repo = ?", (repo,))
            else:
                conn.execute("DELETE FROM documents")
                conn.execute("DELETE FROM document_meta")
            conn.commit()
