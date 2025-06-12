import fcntl
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .formatter import ContextFormatter
from .store_base import BaseContextStore

logger = logging.getLogger(__name__)


class ContextStoreError(Exception):
    """Custom exception for context store errors."""

    pass


class ContextStore(BaseContextStore):
    """Handles persistent and in-memory storage of node context data, with hooks and optional schema validation."""

    def __init__(
        self,
        context_store_path: Optional[str] = None,
        formatter: Optional[ContextFormatter] = None,
    ):
        if context_store_path:
            self.context_store_path = context_store_path
        elif os.getenv("SCRIPTCHAIN_CONTEXT_STORE_PATH"):
            self.context_store_path = os.environ["SCRIPTCHAIN_CONTEXT_STORE_PATH"]
        else:
            default_workspace_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
            self.context_store_path = os.path.join(
                default_workspace_root, "data", "context_store.json"
            )
        os.makedirs(os.path.dirname(self.context_store_path), exist_ok=True)
        if not os.path.exists(self.context_store_path):
            with open(self.context_store_path, "w") as f:
                json.dump({}, f)
        self.context_cache = {}
        self._load_context()
        self.hooks: List[Callable[[str, str, Any], None]] = (
            []
        )  # hooks for observability
        self.formatter = formatter or ContextFormatter()

    def register_hook(self, hook: Callable[[str, str, Any], None]):
        """Register a hook to be called on every context operation."""
        self.hooks.append(hook)

    def _run_hooks(self, op: str, node_id: str, content: Any):
        for hook in self.hooks:
            hook(op, node_id, content)

    def _load_context(self) -> None:
        try:
            if os.path.exists(self.context_store_path):
                with open(self.context_store_path, "r") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        self.context_cache = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding context store: {str(e)}")
            self.context_cache = {}
        except Exception as e:
            logger.error(f"Error loading context store: {str(e)}")
            self.context_cache = {}

    def _save_context(self) -> None:
        try:
            with open(self.context_store_path, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(self.context_cache, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error saving context store: {str(e)}")
            raise ContextStoreError(str(e))

    def get(self, node_id: str) -> Any:
        self._run_hooks("get", node_id, None)
        return self.context_cache.get(node_id, {}).get("data", {})

    def set(
        self,
        node_id: str,
        context: Dict[str, Any],
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        if schema and not self.formatter.validate_schema(context, schema):
            raise ContextStoreError(
                f"Context for node {node_id} does not match schema."
            )
        self.context_cache[node_id] = {
            "data": context,
            "version": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._save_context()
        self._run_hooks("set", node_id, context)

    def update(
        self,
        node_id: str,
        content: Any,
        execution_id: Optional[str] = None,
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        if schema and not self.formatter.validate_schema(content, schema):
            raise ContextStoreError(
                f"Context for node {node_id} does not match schema."
            )
        context_entry = {
            "data": content,
            "version": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
        }
        if execution_id:
            context_entry["execution_id"] = execution_id
        self.context_cache[node_id] = context_entry
        # Load current data from file
        current_data = {}
        if os.path.exists(self.context_store_path):
            try:
                with open(self.context_store_path, "r") as f_read:
                    fcntl.flock(f_read.fileno(), fcntl.LOCK_SH)
                    try:
                        current_data = json.load(f_read)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Context store file {self.context_store_path} is malformed. Will overwrite with new context."
                        )
                        current_data = {}
                    finally:
                        fcntl.flock(f_read.fileno(), fcntl.LOCK_UN)
            except FileNotFoundError:
                logger.info(
                    f"Context store file {self.context_store_path} not found during update. Creating new one."
                )
                pass
            except Exception as e_read:
                logger.error(
                    f"Error reading context store for update: {str(e_read)}. Proceeding to overwrite."
                )
                current_data = {}
        current_data[node_id] = self.context_cache[node_id]
        with open(self.context_store_path, "w") as f_write:
            fcntl.flock(f_write.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(current_data, f_write, indent=2)
            finally:
                fcntl.flock(f_write.fileno(), fcntl.LOCK_UN)
        self._run_hooks("update", node_id, content)

    def clear(self, node_id: Optional[str] = None) -> None:
        if node_id:
            self.context_cache.pop(node_id, None)
            if os.path.exists(self.context_store_path):
                with open(self.context_store_path, "r+") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = {}
                        data.pop(node_id, None)
                        f.seek(0)
                        json.dump(data, f, indent=2)
                        f.truncate()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        else:
            self.context_cache.clear()
            if os.path.exists(self.context_store_path):
                with open(self.context_store_path, "w") as f:
                    json.dump({}, f)
        self._run_hooks("clear", node_id or "ALL", None)
