"""Documentation statistics and metrics."""

import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from git import Repo
from git.exc import InvalidGitRepositoryError


@dataclass
class DocumentMetrics:
    """Metrics for a single document."""
    path: str
    title: str
    word_count: int
    line_count: int
    header_count: int
    link_count: int
    code_block_count: int
    last_modified: Optional[datetime] = None
    last_author: Optional[str] = None


@dataclass
class RepositoryStats:
    """Aggregate statistics for a repository."""
    total_documents: int = 0
    total_words: int = 0
    total_lines: int = 0
    avg_words_per_doc: float = 0.0
    documents: list[DocumentMetrics] = field(default_factory=list)


class DocumentStats:
    """Gathers statistics about documentation."""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self._repo: Optional[Repo] = None
        try:
            self._repo = Repo(self.repo_path)
        except InvalidGitRepositoryError:
            pass

    def _extract_title(self, content: str) -> str:
        """Extract title from Markdown content."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"

    def _count_headers(self, content: str) -> int:
        """Count headers in content."""
        return len(re.findall(r"^#+\s", content, re.MULTILINE))

    def _count_links(self, content: str) -> int:
        """Count links in content."""
        return len(re.findall(r"\[([^\]]+)\]\([^)]+\)", content))

    def _count_code_blocks(self, content: str) -> int:
        """Count code blocks in content."""
        return content.count("```") // 2

    def _get_file_git_info(self, file_path: Path) -> tuple[Optional[datetime], Optional[str]]:
        """Get last modified date and author from Git."""
        if not self._repo:
            return None, None

        try:
            rel_path = str(file_path.relative_to(self.repo_path))
            commits = list(self._repo.iter_commits(paths=rel_path, max_count=1))
            if commits:
                commit = commits[0]
                return commit.committed_datetime, str(commit.author)
        except Exception:
            pass

        return None, None

    def analyze_file(self, file_path: Path) -> Optional[DocumentMetrics]:
        """Analyze a single Markdown file."""
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        last_modified, last_author = self._get_file_git_info(file_path)

        return DocumentMetrics(
            path=str(file_path.relative_to(self.repo_path)),
            title=self._extract_title(content),
            word_count=len(content.split()),
            line_count=len(content.split("\n")),
            header_count=self._count_headers(content),
            link_count=self._count_links(content),
            code_block_count=self._count_code_blocks(content),
            last_modified=last_modified,
            last_author=last_author,
        )

    def analyze_repository(self) -> RepositoryStats:
        """Analyze all Markdown files in the repository."""
        stats = RepositoryStats()

        for md_file in self.repo_path.rglob("*.md"):
            # Get path relative to repo for checking hidden dirs
            try:
                rel_path = md_file.relative_to(self.repo_path)
            except ValueError:
                continue

            # Skip hidden directories (only within repo)
            if any(part.startswith(".") for part in rel_path.parts):
                continue
            if "node_modules" in rel_path.parts:
                continue

            metrics = self.analyze_file(md_file)
            if metrics:
                stats.documents.append(metrics)
                stats.total_documents += 1
                stats.total_words += metrics.word_count
                stats.total_lines += metrics.line_count

        if stats.total_documents > 0:
            stats.avg_words_per_doc = stats.total_words / stats.total_documents

        return stats

    def summary(self) -> dict:
        """Get a summary of repository statistics."""
        stats = self.analyze_repository()
        return {
            "total_documents": stats.total_documents,
            "total_words": stats.total_words,
            "total_lines": stats.total_lines,
            "avg_words_per_doc": stats.avg_words_per_doc,
        }

    def get_structure(self) -> dict:
        """Get the documentation structure for AI analysis."""
        stats = self.analyze_repository()

        # Organize by directory
        structure = {}
        for doc in stats.documents:
            path = Path(doc.path)
            directory = str(path.parent) if path.parent != Path(".") else "root"

            if directory not in structure:
                structure[directory] = []

            structure[directory].append({
                "file": path.name,
                "title": doc.title,
                "words": doc.word_count,
                "headers": doc.header_count,
                "links": doc.link_count,
                "code_blocks": doc.code_block_count,
                "last_modified": doc.last_modified.isoformat() if doc.last_modified else None,
                "last_author": doc.last_author,
            })

        return {
            "repo_name": self.repo_path.name,
            "total_documents": stats.total_documents,
            "total_words": stats.total_words,
            "directories": structure,
        }

    def find_stale_documents(self, days: int = 90) -> list[DocumentMetrics]:
        """Find documents not updated in the specified number of days."""
        from datetime import timezone

        stats = self.analyze_repository()
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
        stale = []

        for doc in stats.documents:
            if doc.last_modified:
                # Make both naive for comparison
                last_mod = doc.last_modified.replace(tzinfo=None)
                age = (cutoff - last_mod).days
                if age > days:
                    stale.append(doc)

        return sorted(stale, key=lambda d: d.last_modified or datetime.min)

    def find_short_documents(self, min_words: int = 100) -> list[DocumentMetrics]:
        """Find documents that might be too short."""
        stats = self.analyze_repository()
        return [doc for doc in stats.documents if doc.word_count < min_words]

    def find_long_documents(self, max_words: int = 3000) -> list[DocumentMetrics]:
        """Find documents that might be too long."""
        stats = self.analyze_repository()
        return [doc for doc in stats.documents if doc.word_count > max_words]
