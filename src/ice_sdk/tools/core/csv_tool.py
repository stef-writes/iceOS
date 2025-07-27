"""Unified CSV tool for all CSV operations."""
from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field
from ice_sdk.decorators import tool
from ice_sdk.tools.base import ToolBase
from ice_sdk.utils.errors import ToolExecutionError


@tool(name="csv")
class CSVTool(ToolBase):
    """Unified CSV operations - read, write, append, update, and delete.
    
    This tool combines all CSV operations in a single interface while
    maintaining clear separation of concerns internally.
    """
    
    name: str = "csv"
    description: str = "Comprehensive CSV file operations"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute CSV operation based on action parameter."""
        action = kwargs.get("action", "read")
        file_path = kwargs.get("file_path")
        
        if not file_path:
            raise ToolExecutionError("csv", "file_path is required")
        
        path = Path(file_path)
        
        # Dispatch to appropriate operation
        if action == "read":
            return await self._read_csv(path, kwargs)
        elif action == "write":
            return await self._write_csv(path, kwargs, mode="write")
        elif action == "append":
            return await self._write_csv(path, kwargs, mode="append")
        elif action == "update":
            return await self._update_csv(path, kwargs)
        elif action == "delete":
            return await self._delete_csv(path, kwargs)
        elif action == "query":
            return await self._query_csv(path, kwargs)
        else:
            raise ToolExecutionError("csv", f"Unknown action: {action}")
    
    async def _read_csv(self, path: Path, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Read CSV file and return data."""
        if not path.exists():
            raise ToolExecutionError("csv", f"File not found: {path}")
        
        delimiter = kwargs.get("delimiter", ",")
        encoding = kwargs.get("encoding", "utf-8")
        
        def _read():
            with path.open(newline="", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = list(reader)
                headers = reader.fieldnames or []
                return headers, rows
        
        headers, rows = await asyncio.to_thread(_read)
        
        return {
            "action": "read",
            "file_path": str(path),
            "headers": headers,
            "rows": rows,
            "total_rows": len(rows),
            "rows_json": json.dumps(rows, ensure_ascii=False)
        }
    
    async def _write_csv(self, path: Path, kwargs: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """Write or append data to CSV file."""
        rows = kwargs.get("rows", [])
        headers = kwargs.get("headers")
        delimiter = kwargs.get("delimiter", ",")
        encoding = kwargs.get("encoding", "utf-8")
        
        if not rows:
            raise ToolExecutionError("csv", "rows parameter is required for write operations")
        
        # Ensure rows is a list of dicts
        if isinstance(rows, str):
            try:
                rows = json.loads(rows)
            except json.JSONDecodeError as e:
                raise ToolExecutionError("csv", f"Invalid JSON in rows: {e}")
        
        def _write():
            # If headers not provided, extract from first row
            if not headers and rows:
                headers = list(rows[0].keys())
            
            # Determine file mode
            file_mode = "w" if mode == "write" or not path.exists() else "a"
            write_header = file_mode == "w" or not path.exists()
            
            with path.open(file_mode, newline="", encoding=encoding) as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)
                if write_header:
                    writer.writeheader()
                writer.writerows(rows)
                
            # Read back the file to return current state
            with path.open(newline="", encoding=encoding) as f:
                reader = list(csv.DictReader(f, delimiter=delimiter))
                return reader
        
        all_rows = await asyncio.to_thread(_write)
        
        return {
            "action": mode,
            "file_path": str(path),
            "rows_written": len(rows),
            "total_rows": len(all_rows),
            "rows_json": json.dumps(all_rows, ensure_ascii=False)
        }
    
    async def _update_csv(self, path: Path, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Update specific rows in CSV file."""
        if not path.exists():
            raise ToolExecutionError("csv", f"File not found: {path}")
        
        updates = kwargs.get("updates", {})
        key_column = kwargs.get("key_column", "id")
        delimiter = kwargs.get("delimiter", ",")
        encoding = kwargs.get("encoding", "utf-8")
        
        if not updates:
            raise ToolExecutionError("csv", "updates parameter is required")
        
        def _update():
            # Read existing data
            with path.open(newline="", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = list(reader)
                headers = reader.fieldnames or []
            
            # Apply updates
            updated_count = 0
            for i, row in enumerate(rows):
                key_value = row.get(key_column)
                if key_value in updates:
                    rows[i].update(updates[key_value])
                    updated_count += 1
            
            # Write back
            with path.open("w", newline="", encoding=encoding) as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(rows)
            
            return rows, updated_count
        
        rows, updated_count = await asyncio.to_thread(_update)
        
        return {
            "action": "update",
            "file_path": str(path),
            "rows_updated": updated_count,
            "total_rows": len(rows),
            "rows_json": json.dumps(rows, ensure_ascii=False)
        }
    
    async def _delete_csv(self, path: Path, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Delete specific rows from CSV file."""
        if not path.exists():
            raise ToolExecutionError("csv", f"File not found: {path}")
        
        delete_keys = kwargs.get("delete_keys", [])
        key_column = kwargs.get("key_column", "id")
        delimiter = kwargs.get("delimiter", ",")
        encoding = kwargs.get("encoding", "utf-8")
        
        if not delete_keys:
            raise ToolExecutionError("csv", "delete_keys parameter is required")
        
        def _delete():
            # Read existing data
            with path.open(newline="", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = list(reader)
                headers = reader.fieldnames or []
            
            # Filter out rows to delete
            original_count = len(rows)
            rows = [r for r in rows if r.get(key_column) not in delete_keys]
            deleted_count = original_count - len(rows)
            
            # Write back
            with path.open("w", newline="", encoding=encoding) as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(rows)
            
            return rows, deleted_count
        
        rows, deleted_count = await asyncio.to_thread(_delete)
        
        return {
            "action": "delete",
            "file_path": str(path),
            "rows_deleted": deleted_count,
            "total_rows": len(rows),
            "rows_json": json.dumps(rows, ensure_ascii=False)
        }
    
    async def _query_csv(self, path: Path, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Query CSV with simple filters."""
        if not path.exists():
            raise ToolExecutionError("csv", f"File not found: {path}")
        
        filters = kwargs.get("filters", {})
        columns = kwargs.get("columns", [])
        limit = kwargs.get("limit", None)
        delimiter = kwargs.get("delimiter", ",")
        encoding = kwargs.get("encoding", "utf-8")
        
        def _query():
            with path.open(newline="", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                headers = reader.fieldnames or []
                
                # Filter rows
                results = []
                for row in reader:
                    # Check all filters
                    match = True
                    for col, value in filters.items():
                        if row.get(col) != str(value):
                            match = False
                            break
                    
                    if match:
                        # Select only requested columns
                        if columns:
                            row = {k: v for k, v in row.items() if k in columns}
                        results.append(row)
                        
                        # Apply limit
                        if limit and len(results) >= limit:
                            break
                
                return results, headers
        
        results, headers = await asyncio.to_thread(_query)
        
        return {
            "action": "query",
            "file_path": str(path),
            "filters": filters,
            "matched_rows": len(results),
            "headers": headers,
            "rows": results,
            "rows_json": json.dumps(results, ensure_ascii=False)
        }
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Define comprehensive input schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "append", "update", "delete", "query"],
                    "description": "Operation to perform",
                    "default": "read"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to CSV file"
                },
                "rows": {
                    "type": "array",
                    "description": "Rows to write/append (for write operations)"
                },
                "headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column headers (optional for write)"
                },
                "updates": {
                    "type": "object",
                    "description": "Key-value pairs for updates {key: {field: value}}"
                },
                "delete_keys": {
                    "type": "array",
                    "description": "Values to match for deletion"
                },
                "key_column": {
                    "type": "string",
                    "description": "Column to use as key for update/delete",
                    "default": "id"
                },
                "filters": {
                    "type": "object",
                    "description": "Column-value pairs for filtering"
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Columns to return in query"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return"
                },
                "delimiter": {
                    "type": "string",
                    "description": "CSV delimiter",
                    "default": ","
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["file_path"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Define output schema."""
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "file_path": {"type": "string"},
                "headers": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "rows": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "rows_json": {"type": "string"},
                "total_rows": {"type": "integer"},
                "rows_written": {"type": "integer"},
                "rows_updated": {"type": "integer"},
                "rows_deleted": {"type": "integer"},
                "matched_rows": {"type": "integer"}
            }
        } 