"""AI-powered documentation coach using Claude."""

import json
from typing import Optional

from anthropic import Anthropic

from imago.ai.prompts import (
    DOCUMENTATION_COACH_SYSTEM,
    DOCUMENT_REVIEW_PROMPT,
    GAP_ANALYSIS_PROMPT,
    QUALITY_ASSESSMENT_PROMPT,
    CHAT_CONTEXT_PROMPT,
)


class DocumentationCoach:
    """AI documentation coach powered by Claude."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self._client: Optional[Anthropic] = None
        self._conversation: list[dict] = []
        self._context: Optional[dict] = None

    @property
    def client(self) -> Anthropic:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _call_api(self, messages: list[dict], system: str) -> str:
        """Make an API call to Claude."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def review_document(self, content: str, filename: str) -> str:
        """Review a single document and provide feedback."""
        prompt = DOCUMENT_REVIEW_PROMPT.format(
            filename=filename,
            content=content,
        )

        return self._call_api(
            messages=[{"role": "user", "content": prompt}],
            system=DOCUMENTATION_COACH_SYSTEM,
        )

    def analyze_gaps(self, structure: dict) -> str:
        """Analyze documentation structure for gaps."""
        # Format structure for the prompt
        structure_text = json.dumps(structure.get("directories", {}), indent=2)

        prompt = GAP_ANALYSIS_PROMPT.format(
            repo_name=structure.get("repo_name", "Unknown"),
            total_documents=structure.get("total_documents", 0),
            total_words=structure.get("total_words", 0),
            structure=structure_text,
        )

        return self._call_api(
            messages=[{"role": "user", "content": prompt}],
            system=DOCUMENTATION_COACH_SYSTEM,
        )

    def assess_quality(
        self,
        structure: dict,
        validation_summary: dict,
    ) -> str:
        """Provide overall quality assessment."""
        # Format documents list
        docs_text = ""
        for directory, docs in structure.get("directories", {}).items():
            docs_text += f"\n{directory}/\n"
            for doc in docs:
                docs_text += f"  - {doc['file']}: {doc['title']} ({doc['words']} words)\n"

        prompt = QUALITY_ASSESSMENT_PROMPT.format(
            repo_name=structure.get("repo_name", "Unknown"),
            total_documents=structure.get("total_documents", 0),
            total_words=structure.get("total_words", 0),
            avg_words_per_doc=structure.get("total_words", 0) / max(structure.get("total_documents", 1), 1),
            validation_summary=json.dumps(validation_summary, indent=2),
            documents=docs_text,
        )

        return self._call_api(
            messages=[{"role": "user", "content": prompt}],
            system=DOCUMENTATION_COACH_SYSTEM,
        )

    def start_session(self, context: Optional[dict] = None) -> None:
        """Start an interactive coaching session."""
        self._conversation = []
        self._context = context

    def chat(self, user_message: str) -> str:
        """Send a message in the interactive session."""
        # Build system prompt with context if available
        system = DOCUMENTATION_COACH_SYSTEM
        if self._context:
            # Format structure for context
            structure_text = json.dumps(self._context.get("directories", {}), indent=2)
            context_info = CHAT_CONTEXT_PROMPT.format(
                repo_name=self._context.get("repo_name", "Unknown"),
                total_documents=self._context.get("total_documents", 0),
                total_words=self._context.get("total_words", 0),
                structure=structure_text,
            )
            system = f"{DOCUMENTATION_COACH_SYSTEM}\n\n{context_info}"

        # Add user message to conversation
        self._conversation.append({
            "role": "user",
            "content": user_message,
        })

        # Get response
        response = self._call_api(
            messages=self._conversation,
            system=system,
        )

        # Add assistant response to conversation
        self._conversation.append({
            "role": "assistant",
            "content": response,
        })

        return response

    def suggest_improvements(self, content: str, doc_type: str = "general") -> str:
        """Suggest specific improvements for a document."""
        prompt = f"""Review this {doc_type} documentation and suggest specific improvements.

For each suggestion:
1. Quote the original text
2. Explain the issue
3. Provide the improved version

Focus on:
- Clarity and readability
- Technical accuracy
- Completeness
- Structure and organization

Document content:
---
{content}
---"""

        return self._call_api(
            messages=[{"role": "user", "content": prompt}],
            system=DOCUMENTATION_COACH_SYSTEM,
        )

    def generate_outline(self, topic: str, doc_type: str = "guide") -> str:
        """Generate a documentation outline for a topic."""
        prompt = f"""Generate a detailed documentation outline for: {topic}

Document type: {doc_type}

Provide:
1. Suggested title
2. Document structure with headers
3. Key points to cover in each section
4. Code examples to include (describe what they should demonstrate)
5. Related documentation to link to

The outline should be comprehensive enough to guide writing the actual documentation."""

        return self._call_api(
            messages=[{"role": "user", "content": prompt}],
            system=DOCUMENTATION_COACH_SYSTEM,
        )

    def check_consistency(self, documents: list[dict]) -> str:
        """Check consistency across multiple documents."""
        docs_text = ""
        for doc in documents:
            docs_text += f"\n## {doc['filename']}\n{doc['content'][:1000]}...\n"

        prompt = f"""Review these documentation excerpts for consistency:

{docs_text}

Check for:
1. Terminology consistency - Are the same terms used throughout?
2. Style consistency - Similar tone, formatting, structure?
3. Technical consistency - Consistent API patterns, code style?
4. Cross-references - Do documents properly reference each other?

Identify specific inconsistencies and suggest how to resolve them."""

        return self._call_api(
            messages=[{"role": "user", "content": prompt}],
            system=DOCUMENTATION_COACH_SYSTEM,
        )
