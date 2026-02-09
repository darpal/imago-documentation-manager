"""Git repository management for documentation repos."""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError


class RepoManager:
    """Manages documentation Git repositories.

    Auto-discovers Git repositories in the repos directory.
    No tracking file needed - scans the folder to find repos.
    """

    def __init__(self, repos_dir: Path):
        self.repos_dir = Path(repos_dir)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def _extract_name(self, url: str) -> str:
        """Extract repository name from URL."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return path.split("/")[-1]

    def _get_origin_url(self, repo: Repo) -> str:
        """Get the origin URL from a Git repository."""
        try:
            return repo.remotes.origin.url
        except Exception:
            return ""

    def _discover_repos(self) -> dict[str, dict]:
        """Discover all Git repositories in the repos directory."""
        repos = {}

        if not self.repos_dir.exists():
            return repos

        for item in self.repos_dir.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith("."):
                continue

            # Check if it's a Git repository
            try:
                repo = Repo(item)
                repos[item.name] = {
                    "url": self._get_origin_url(repo),
                    "path": str(item),
                }
            except InvalidGitRepositoryError:
                # Not a Git repo, skip it
                continue
            except Exception:
                # Some other error, skip
                continue

        return repos

    def add(self, url: str, name: Optional[str] = None) -> str:
        """Clone a repository into the repos directory."""
        repo_name = name or self._extract_name(url)
        repo_path = self.repos_dir / repo_name

        if repo_path.exists():
            # Check if it's already a valid repo
            try:
                Repo(repo_path)
                raise ValueError(f"Repository '{repo_name}' already exists")
            except InvalidGitRepositoryError:
                raise ValueError(f"Directory '{repo_name}' exists but is not a Git repository")

        try:
            Repo.clone_from(url, repo_path)
        except GitCommandError as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

        return repo_name

    def remove(self, name: str, delete_files: bool = False) -> bool:
        """Remove a repository from tracking.

        If delete_files is True, also deletes the repository files.
        Otherwise, just stops tracking (repo stays in folder).
        """
        repo_path = self.repos_dir / name

        if not repo_path.exists():
            return False

        if delete_files:
            import shutil
            shutil.rmtree(repo_path)

        return True

    def list_repos(self) -> list[dict]:
        """List all discovered repositories with their status."""
        repos = []
        discovered = self._discover_repos()

        for name, info in discovered.items():
            repo_path = Path(info["path"])
            status = "unknown"
            branch = "?"

            try:
                repo = Repo(repo_path)
                branch = repo.active_branch.name
                if repo.is_dirty():
                    status = "modified"
                else:
                    try:
                        if repo.remotes.origin.refs[branch].commit != repo.head.commit:
                            status = "behind"
                        else:
                            status = "clean"
                    except (IndexError, KeyError):
                        status = "clean"
            except (InvalidGitRepositoryError, Exception) as e:
                status = "error"

            repos.append({
                "name": name,
                "url": info["url"],
                "path": str(repo_path),
                "branch": branch,
                "status": status,
            })

        return sorted(repos, key=lambda r: r["name"])

    def get_repo_path(self, name: Optional[str] = None) -> Optional[Path]:
        """Get the path to a repository."""
        discovered = self._discover_repos()

        if name:
            if name in discovered:
                return Path(discovered[name]["path"])
            # Also check if it's a direct path match
            direct_path = self.repos_dir / name
            if direct_path.exists():
                try:
                    Repo(direct_path)
                    return direct_path
                except InvalidGitRepositoryError:
                    pass
            return None

        # Return first repo if no name specified
        if discovered:
            first_name = sorted(discovered.keys())[0]
            return Path(discovered[first_name]["path"])
        return None

    def get_repo(self, name: str) -> Optional[Repo]:
        """Get a Git repository object."""
        repo_path = self.get_repo_path(name)
        if repo_path and repo_path.exists():
            try:
                return Repo(repo_path)
            except InvalidGitRepositoryError:
                return None
        return None

    def pull(self, name: str) -> str:
        """Pull latest changes for a repository."""
        repo = self.get_repo(name)
        if not repo:
            raise ValueError(f"Repository '{name}' not found")

        try:
            origin = repo.remotes.origin
            info = origin.pull()
            if info:
                return f"Updated to {info[0].commit.hexsha[:7]}"
            return "Already up to date"
        except GitCommandError as e:
            raise RuntimeError(f"Pull failed: {e}")

    def pull_all(self) -> dict[str, str]:
        """Pull all discovered repositories."""
        results = {}
        for repo_info in self.list_repos():
            name = repo_info["name"]
            try:
                results[name] = self.pull(name)
            except Exception as e:
                results[name] = f"Error: {e}"
        return results

    def push(self, name: str, message: str) -> str:
        """Commit all changes and push to remote."""
        repo = self.get_repo(name)
        if not repo:
            raise ValueError(f"Repository '{name}' not found")

        try:
            # Stage all changes
            repo.git.add(A=True)

            # Check if there are changes to commit
            if not repo.is_dirty(untracked_files=True):
                return "No changes to push"

            # Commit
            repo.index.commit(message)

            # Push
            origin = repo.remotes.origin
            origin.push()

            return f"Pushed: {message}"
        except GitCommandError as e:
            raise RuntimeError(f"Push failed: {e}")

    def status(self, name: str) -> dict:
        """Get detailed status of a repository."""
        repo = self.get_repo(name)
        if not repo:
            raise ValueError(f"Repository '{name}' not found")

        return {
            "branch": repo.active_branch.name,
            "is_dirty": repo.is_dirty(),
            "untracked_files": repo.untracked_files,
            "modified_files": [item.a_path for item in repo.index.diff(None)],
            "staged_files": [item.a_path for item in repo.index.diff("HEAD")],
            "last_commit": {
                "sha": repo.head.commit.hexsha[:7],
                "message": repo.head.commit.message.strip(),
                "author": str(repo.head.commit.author),
                "date": repo.head.commit.committed_datetime.isoformat(),
            },
        }
