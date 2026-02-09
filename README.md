# Imago Documentation Manager

An AI-powered documentation coach for managing and improving technical documentation.

## Features

- **Repository Management**: Clone, pull, and push Git repositories
- **AI-Powered Reviews**: Get quality assessments using Claude AI
- **Structure Validation**: Check for broken links, header issues, formatting problems
- **Full-Text Search**: Search across all indexed documentation
- **Gap Analysis**: Identify missing documentation and coverage issues
- **Health Reports**: Generate team reports in Markdown or HTML

## Installation

```bash
pip install -e .
```

## Quick Start

1. Configure your Anthropic API key:
```bash
imago config set anthropic_api_key YOUR_KEY
# Or set the ANTHROPIC_API_KEY environment variable
```

2. Add a documentation repository:
```bash
imago repo add https://github.com/your-org/docs.git
```

3. Analyze the documentation:
```bash
imago analyze
```

4. Start an interactive coaching session:
```bash
imago chat
```

## Commands

### Repository Management
```bash
imago repo add <url> [--name <alias>]  # Clone and track a repo
imago repo list                         # List tracked repos
imago repo pull [<name>]                # Pull latest changes
imago repo push [<name>] -m "message"   # Push changes
```

### Analysis
```bash
imago analyze [<name>]    # Full analysis of a repo
imago review <file>       # Review specific document
imago gaps [<name>]       # Find documentation gaps
imago search <query>      # Search across all docs
```

### Interactive
```bash
imago chat [<name>]       # Start interactive coach session
```

### Reports
```bash
imago report [<name>] [--format md|html] [--output file]
```

### Configuration
```bash
imago config set <key> <value>  # Set a config value
imago config show               # Show current config
```

## License

MIT
