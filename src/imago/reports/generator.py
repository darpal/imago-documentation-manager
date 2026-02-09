"""Documentation health report generation."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from imago.analysis.stats import DocumentStats
from imago.analysis.validator import DocumentValidator
from imago.analysis.indexer import DocumentIndexer
from imago.config import Config


class ReportGenerator:
    """Generates documentation health reports."""

    def __init__(self, repo_path: Path, config: Config):
        self.repo_path = Path(repo_path)
        self.config = config
        self.stats = DocumentStats(repo_path)
        self.validator = DocumentValidator(repo_path)

    def generate(self, format: str = "md") -> str:
        """Generate a report in the specified format."""
        if format == "html":
            return self._generate_html()
        return self._generate_markdown()

    def _gather_data(self) -> dict:
        """Gather all data needed for the report."""
        structure = self.stats.get_structure()
        validation_issues = self.validator.validate()
        validation_summary = self.validator.get_summary()
        stale_docs = self.stats.find_stale_documents(days=90)
        short_docs = self.stats.find_short_documents(min_words=100)
        long_docs = self.stats.find_long_documents(max_words=3000)

        return {
            "repo_name": self.repo_path.name,
            "generated_at": datetime.now().isoformat(),
            "structure": structure,
            "validation_issues": validation_issues,
            "validation_summary": validation_summary,
            "stale_docs": stale_docs,
            "short_docs": short_docs,
            "long_docs": long_docs,
        }

    def _generate_markdown(self) -> str:
        """Generate a Markdown report."""
        data = self._gather_data()
        structure = data["structure"]

        lines = [
            f"# Documentation Health Report",
            f"",
            f"**Repository:** {data['repo_name']}",
            f"**Generated:** {data['generated_at']}",
            f"",
            f"---",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Documents | {structure['total_documents']} |",
            f"| Total Words | {structure['total_words']:,} |",
            f"| Avg Words/Doc | {structure['total_words'] / max(structure['total_documents'], 1):.0f} |",
            f"| Validation Errors | {data['validation_summary']['errors']} |",
            f"| Validation Warnings | {data['validation_summary']['warnings']} |",
            f"| Stale Documents (90+ days) | {len(data['stale_docs'])} |",
            f"",
        ]

        # Health Score
        score = self._calculate_health_score(data)
        lines.extend([
            f"## Health Score: {score}/100",
            f"",
            self._get_score_badge(score),
            f"",
        ])

        # Validation Issues
        if data["validation_issues"]:
            lines.extend([
                f"## Validation Issues",
                f"",
            ])

            # Group by level
            errors = [i for i in data["validation_issues"] if i.level.value == "error"]
            warnings = [i for i in data["validation_issues"] if i.level.value == "warning"]

            if errors:
                lines.append("### Errors")
                lines.append("")
                for issue in errors[:10]:
                    lines.append(f"- **{issue.file}**: {issue.message}")
                if len(errors) > 10:
                    lines.append(f"- ... and {len(errors) - 10} more errors")
                lines.append("")

            if warnings:
                lines.append("### Warnings")
                lines.append("")
                for issue in warnings[:10]:
                    lines.append(f"- **{issue.file}**: {issue.message}")
                if len(warnings) > 10:
                    lines.append(f"- ... and {len(warnings) - 10} more warnings")
                lines.append("")

        # Stale Documents
        if data["stale_docs"]:
            lines.extend([
                f"## Stale Documents",
                f"",
                f"Documents not updated in 90+ days:",
                f"",
                f"| Document | Last Modified | Author |",
                f"|----------|---------------|--------|",
            ])
            for doc in data["stale_docs"][:10]:
                date = doc.last_modified.strftime("%Y-%m-%d") if doc.last_modified else "Unknown"
                author = doc.last_author or "Unknown"
                lines.append(f"| {doc.path} | {date} | {author} |")
            lines.append("")

        # Document Length Issues
        if data["short_docs"] or data["long_docs"]:
            lines.extend([
                f"## Document Length Issues",
                f"",
            ])

            if data["short_docs"]:
                lines.append("### Potentially Too Short (<100 words)")
                lines.append("")
                for doc in data["short_docs"][:5]:
                    lines.append(f"- **{doc.path}**: {doc.word_count} words")
                lines.append("")

            if data["long_docs"]:
                lines.append("### Potentially Too Long (>3000 words)")
                lines.append("")
                for doc in data["long_docs"][:5]:
                    lines.append(f"- **{doc.path}**: {doc.word_count} words")
                lines.append("")

        # Document Structure
        lines.extend([
            f"## Documentation Structure",
            f"",
        ])

        for directory, docs in structure.get("directories", {}).items():
            lines.append(f"### {directory}/")
            lines.append("")
            for doc in docs:
                lines.append(f"- **{doc['file']}**: {doc['title']} ({doc['words']} words)")
            lines.append("")

        # Recommendations
        recommendations = self._generate_recommendations(data)
        if recommendations:
            lines.extend([
                f"## Recommendations",
                f"",
            ])
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)

    def _generate_html(self) -> str:
        """Generate an HTML report."""
        data = self._gather_data()
        structure = data["structure"]
        score = self._calculate_health_score(data)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Health Report - {data['repo_name']}</title>
    <style>
        :root {{
            --bg: #f8f9fa;
            --card-bg: #ffffff;
            --text: #212529;
            --muted: #6c757d;
            --border: #dee2e6;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --info: #17a2b8;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background: var(--bg);
            margin: 0;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ border-bottom: 2px solid var(--border); padding-bottom: 1rem; }}
        h2 {{ color: var(--muted); margin-top: 2rem; }}
        .card {{
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .score {{
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            padding: 2rem;
        }}
        .score.good {{ color: var(--success); }}
        .score.warning {{ color: var(--warning); }}
        .score.danger {{ color: var(--danger); }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
        .stat {{
            background: var(--bg);
            padding: 1rem;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--info); }}
        .stat-label {{ color: var(--muted); font-size: 0.9rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: var(--bg); font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        .badge.error {{ background: var(--danger); color: white; }}
        .badge.warning {{ background: var(--warning); color: black; }}
        .badge.info {{ background: var(--info); color: white; }}
        .issue-list {{ list-style: none; padding: 0; }}
        .issue-list li {{ padding: 0.5rem 0; border-bottom: 1px solid var(--border); }}
        .recommendations {{ background: #e8f4f8; padding: 1.5rem; border-radius: 8px; }}
        .recommendations li {{ margin-bottom: 0.5rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Documentation Health Report</h1>
        <p><strong>Repository:</strong> {data['repo_name']}<br>
        <strong>Generated:</strong> {data['generated_at']}</p>

        <div class="card">
            <div class="score {'good' if score >= 70 else 'warning' if score >= 40 else 'danger'}">
                {score}/100
            </div>
            <p style="text-align: center; color: var(--muted);">Health Score</p>
        </div>

        <div class="card">
            <h2 style="margin-top: 0;">Summary</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{structure['total_documents']}</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{structure['total_words']:,}</div>
                    <div class="stat-label">Total Words</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{data['validation_summary']['errors']}</div>
                    <div class="stat-label">Errors</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{data['validation_summary']['warnings']}</div>
                    <div class="stat-label">Warnings</div>
                </div>
            </div>
        </div>
"""

        # Validation Issues
        if data["validation_issues"]:
            html += """
        <div class="card">
            <h2 style="margin-top: 0;">Validation Issues</h2>
            <ul class="issue-list">
"""
            for issue in data["validation_issues"][:15]:
                badge_class = issue.level.value
                html += f'                <li><span class="badge {badge_class}">{issue.level.value}</span> <strong>{issue.file}</strong>: {issue.message}</li>\n'
            if len(data["validation_issues"]) > 15:
                html += f'                <li><em>... and {len(data["validation_issues"]) - 15} more issues</em></li>\n'
            html += """            </ul>
        </div>
"""

        # Recommendations
        recommendations = self._generate_recommendations(data)
        if recommendations:
            html += """
        <div class="recommendations">
            <h2 style="margin-top: 0;">Recommendations</h2>
            <ol>
"""
            for rec in recommendations:
                html += f"                <li>{rec}</li>\n"
            html += """            </ol>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""
        return html

    def _calculate_health_score(self, data: dict) -> int:
        """Calculate a health score from 0-100."""
        score = 100

        # Deduct for validation errors (5 points each, max 30)
        score -= min(data["validation_summary"]["errors"] * 5, 30)

        # Deduct for validation warnings (2 points each, max 20)
        score -= min(data["validation_summary"]["warnings"] * 2, 20)

        # Deduct for stale documents (2 points each, max 20)
        score -= min(len(data["stale_docs"]) * 2, 20)

        # Deduct for very short documents (3 points each, max 15)
        score -= min(len(data["short_docs"]) * 3, 15)

        # Deduct for very long documents (2 points each, max 10)
        score -= min(len(data["long_docs"]) * 2, 10)

        return max(0, score)

    def _get_score_badge(self, score: int) -> str:
        """Get a text badge for the health score."""
        if score >= 80:
            return "**Excellent** - Documentation is in great shape!"
        elif score >= 60:
            return "**Good** - Documentation is healthy with minor issues"
        elif score >= 40:
            return "**Fair** - Documentation needs attention"
        else:
            return "**Poor** - Documentation requires significant work"

    def _generate_recommendations(self, data: dict) -> list[str]:
        """Generate prioritized recommendations."""
        recommendations = []

        # Critical issues first
        if data["validation_summary"]["errors"] > 0:
            recommendations.append(
                f"Fix {data['validation_summary']['errors']} validation errors "
                "(broken links, unclosed code blocks, etc.)"
            )

        # Stale content
        if len(data["stale_docs"]) > 3:
            recommendations.append(
                f"Review and update {len(data['stale_docs'])} stale documents "
                "that haven't been modified in 90+ days"
            )

        # Short documents
        if len(data["short_docs"]) > 0:
            recommendations.append(
                f"Expand {len(data['short_docs'])} short documents that may lack sufficient detail"
            )

        # Long documents
        if len(data["long_docs"]) > 0:
            recommendations.append(
                f"Consider splitting {len(data['long_docs'])} very long documents "
                "into smaller, focused pieces"
            )

        # Warnings
        if data["validation_summary"]["warnings"] > 5:
            recommendations.append(
                f"Address {data['validation_summary']['warnings']} validation warnings "
                "to improve documentation quality"
            )

        # General recommendations if score is low
        score = self._calculate_health_score(data)
        if score < 60 and not recommendations:
            recommendations.append("Conduct a documentation audit to identify coverage gaps")
            recommendations.append("Establish documentation standards and templates")

        return recommendations[:5]  # Top 5 recommendations
