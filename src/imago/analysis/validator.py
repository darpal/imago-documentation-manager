"""Document structure validation for Markdown files."""

import re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IssueLevel(Enum):
    """Severity level of validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue found in a document."""
    file: str
    line: Optional[int]
    level: IssueLevel
    message: str
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.level.value}] {loc}: {self.message}"


class DocumentValidator:
    """Validates Markdown documentation structure."""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self.issues: list[ValidationIssue] = []

    def validate(self) -> list[ValidationIssue]:
        """Run all validations on the repository."""
        self.issues = []

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

            self._validate_file(md_file)

        return self.issues

    def _validate_file(self, file_path: Path) -> None:
        """Validate a single Markdown file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.issues.append(ValidationIssue(
                file=str(file_path.relative_to(self.repo_path)),
                line=None,
                level=IssueLevel.ERROR,
                message=f"Could not read file: {e}"
            ))
            return

        rel_path = str(file_path.relative_to(self.repo_path))
        lines = content.split("\n")

        self._check_title(rel_path, lines)
        self._check_headers(rel_path, lines)
        self._check_links(rel_path, lines, file_path)
        self._check_code_blocks(rel_path, lines)
        self._check_empty_sections(rel_path, lines)
        self._check_trailing_whitespace(rel_path, lines)

    def _check_title(self, file: str, lines: list[str]) -> None:
        """Check that file has a title (H1 header)."""
        has_title = False
        for line in lines:
            if line.strip().startswith("# "):
                has_title = True
                break
            # Skip empty lines and metadata
            if line.strip() and not line.startswith("---"):
                break

        if not has_title:
            self.issues.append(ValidationIssue(
                file=file,
                line=1,
                level=IssueLevel.WARNING,
                message="Document has no title (H1 header)",
                suggestion="Add a title with '# Your Title'"
            ))

    def _check_headers(self, file: str, lines: list[str]) -> None:
        """Check header hierarchy (no skipping levels)."""
        current_level = 0
        for i, line in enumerate(lines, 1):
            if line.startswith("#"):
                # Count the header level
                match = re.match(r"^(#+)\s", line)
                if match:
                    level = len(match.group(1))
                    if current_level > 0 and level > current_level + 1:
                        self.issues.append(ValidationIssue(
                            file=file,
                            line=i,
                            level=IssueLevel.WARNING,
                            message=f"Header level skipped from H{current_level} to H{level}",
                            suggestion=f"Use H{current_level + 1} instead"
                        ))
                    current_level = level

    def _check_links(self, file: str, lines: list[str], file_path: Path) -> None:
        """Check for broken internal links."""
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

        for i, line in enumerate(lines, 1):
            for match in link_pattern.finditer(line):
                link_text, link_url = match.groups()

                # Skip external links and anchors
                if link_url.startswith(("http://", "https://", "mailto:", "#")):
                    continue

                # Check internal file links
                if not link_url.startswith("#"):
                    # Handle relative paths
                    link_path = link_url.split("#")[0]  # Remove anchor
                    target_path = (file_path.parent / link_path).resolve()

                    if not target_path.exists():
                        self.issues.append(ValidationIssue(
                            file=file,
                            line=i,
                            level=IssueLevel.ERROR,
                            message=f"Broken link: '{link_url}'",
                            suggestion="Fix the link path or create the missing file"
                        ))

    def _check_code_blocks(self, file: str, lines: list[str]) -> None:
        """Check that code blocks are properly closed and have language specified."""
        in_code_block = False
        code_block_start = 0
        has_language = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = i
                    has_language = len(stripped) > 3
                    if not has_language:
                        self.issues.append(ValidationIssue(
                            file=file,
                            line=i,
                            level=IssueLevel.INFO,
                            message="Code block without language specified",
                            suggestion="Add language (e.g., ```python, ```javascript)"
                        ))
                else:
                    in_code_block = False

        if in_code_block:
            self.issues.append(ValidationIssue(
                file=file,
                line=code_block_start,
                level=IssueLevel.ERROR,
                message="Unclosed code block",
                suggestion="Add closing ``` to the code block"
            ))

    def _check_empty_sections(self, file: str, lines: list[str]) -> None:
        """Check for empty sections (headers with no content)."""
        header_line = None
        header_text = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                # If we have a previous header with no content
                if header_line is not None:
                    self.issues.append(ValidationIssue(
                        file=file,
                        line=header_line,
                        level=IssueLevel.WARNING,
                        message=f"Empty section: '{header_text}'",
                        suggestion="Add content or remove the empty section"
                    ))
                header_line = i
                header_text = stripped.lstrip("#").strip()
            elif stripped and not stripped.startswith("```"):
                # Non-empty content found
                header_line = None
                header_text = None

    def _check_trailing_whitespace(self, file: str, lines: list[str]) -> None:
        """Check for excessive trailing whitespace."""
        trailing_count = 0
        for line in lines:
            if line.endswith("  ") or line.endswith("\t"):
                trailing_count += 1

        # Only report if significant number of lines have issues
        if trailing_count > 5:
            self.issues.append(ValidationIssue(
                file=file,
                line=None,
                level=IssueLevel.INFO,
                message=f"{trailing_count} lines with trailing whitespace",
                suggestion="Consider trimming trailing whitespace"
            ))

    def get_summary(self) -> dict:
        """Get a summary of validation issues."""
        return {
            "total": len(self.issues),
            "errors": len([i for i in self.issues if i.level == IssueLevel.ERROR]),
            "warnings": len([i for i in self.issues if i.level == IssueLevel.WARNING]),
            "info": len([i for i in self.issues if i.level == IssueLevel.INFO]),
        }
