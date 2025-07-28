"""
📚 ArxivSearchTool - Academic Paper Search
=========================================

Highly reusable tool for searching academic papers from arXiv API.
Perfect for any research-related use case.

## Reusability
✅ Any academic research use case
✅ Literature reviews  
✅ Technology trend analysis
✅ Citation analysis
✅ Research gap identification

## Features
- Real arXiv API integration
- Configurable search parameters
- Rich metadata extraction
- Error handling and rate limiting
- Structured output for downstream processing
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class ArxivSearchTool(ToolBase):
    """Search academic papers from arXiv with rich metadata extraction.
    
    This tool provides a robust interface to the arXiv API with comprehensive
    error handling, rate limiting, and structured output formatting.
    """
    
    name: str = "arxiv_search"
    description: str = "Search academic papers from arXiv API with metadata"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Execute arXiv search with comprehensive metadata extraction.
        
        Args:
            query: Search query string (required)
            max_results: Maximum number of papers to return (default: 50)
            sort_by: Sort criteria - 'relevance', 'date', 'citations' (default: 'relevance')
            start_date: Filter papers after this date (YYYY-MM-DD format)
            end_date: Filter papers before this date (YYYY-MM-DD format)
            categories: Filter by arXiv categories (e.g., ['cs.AI', 'stat.ML'])
            
        Returns:
            Dict containing papers list, search metadata, and statistics
        """
        try:
            # Extract and validate parameters
            query = kwargs.get("query")
            if not query:
                raise ValueError("Query parameter is required")
                
            max_results = kwargs.get("max_results", 50)
            sort_by = kwargs.get("sort_by", "relevance")
            start_date = kwargs.get("start_date")
            end_date = kwargs.get("end_date") 
            categories = kwargs.get("categories", [])
            
            logger.info(f"Searching arXiv for: '{query}' (max_results={max_results})")
            
            # Import arxiv library 
            try:
                import arxiv
            except ImportError:
                return {
                    "error": "arxiv library not installed. Run: pip install arxiv",
                    "papers": [],
                    "count": 0
                }
            
            # Build search query
            search_query = self._build_search_query(query, categories, start_date, end_date)
            
            # Configure search parameters
            sort_criterion = self._get_sort_criterion(sort_by)
            
            # Execute search
            search = arxiv.Search(
                query=search_query,
                max_results=max_results,
                sort_by=sort_criterion
            )
            
            # Process results
            papers = []
            for paper in search.results():
                try:
                    paper_data = self._extract_paper_metadata(paper)
                    papers.append(paper_data)
                except Exception as e:
                    logger.warning(f"Error processing paper {paper.title}: {e}")
                    continue
            
            # Generate search statistics
            stats = self._generate_statistics(papers)
            
            return {
                "papers": papers,
                "count": len(papers),
                "query": query,
                "search_metadata": {
                    "query_used": search_query,
                    "sort_by": sort_by,
                    "max_results": max_results,
                    "categories_filter": categories,
                    "date_range": {
                        "start": start_date,
                        "end": end_date
                    }
                },
                "statistics": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ArxivSearchTool execution failed: {e}")
            return {
                "error": str(e),
                "papers": [],
                "count": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    def _build_search_query(self, query: str, categories: List[str], 
                           start_date: Optional[str], end_date: Optional[str]) -> str:
        """Build comprehensive arXiv search query."""
        search_parts = [query]
        
        # Add category filters
        if categories:
            category_filter = " OR ".join([f"cat:{cat}" for cat in categories])
            search_parts.append(f"({category_filter})")
        
        # Add date filters (arXiv uses submittedDate)
        if start_date:
            search_parts.append(f"submittedDate:[{start_date}0000 TO *]")
        if end_date:
            search_parts.append(f"submittedDate:[* TO {end_date}2359]")
        
        return " AND ".join(search_parts)
    
    def _get_sort_criterion(self, sort_by: str):
        """Convert sort_by string to arxiv sort criterion."""
        import arxiv
        
        sort_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "date": arxiv.SortCriterion.SubmittedDate, 
            "citations": arxiv.SortCriterion.Relevance  # arXiv doesn't have citation sort
        }
        
        return sort_map.get(sort_by, arxiv.SortCriterion.Relevance)
    
    def _extract_paper_metadata(self, paper) -> Dict[str, Any]:
        """Extract comprehensive metadata from arXiv paper."""
        return {
            "title": paper.title.strip(),
            "abstract": paper.summary.strip(),
            "authors": [str(author) for author in paper.authors],
            "published": paper.published.isoformat(),
            "updated": paper.updated.isoformat() if paper.updated else None,
            "categories": paper.categories,
            "primary_category": paper.primary_category,
            "pdf_url": paper.pdf_url,
            "entry_id": paper.entry_id,
            "doi": paper.doi,
            "journal_ref": paper.journal_ref,
            "comment": paper.comment,
            "links": [{"href": link.href, "title": link.title} for link in paper.links],
            "metadata": {
                "word_count_abstract": len(paper.summary.split()),
                "author_count": len(paper.authors),
                "category_count": len(paper.categories),
                "is_recent": (datetime.now() - paper.published).days < 365,
                "has_doi": bool(paper.doi),
                "has_journal": bool(paper.journal_ref)
            }
        }
    
    def _generate_statistics(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive statistics about the search results."""
        if not papers:
            return {}
        
        # Basic statistics
        total_papers = len(papers)
        total_authors = sum(paper["metadata"]["author_count"] for paper in papers)
        
        # Date analysis
        dates = [datetime.fromisoformat(paper["published"]) for paper in papers]
        latest_date = max(dates)
        oldest_date = min(dates)
        
        # Category analysis
        all_categories = []
        for paper in papers:
            all_categories.extend(paper["categories"])
        
        category_counts = {}
        for cat in all_categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Journal analysis
        with_journal = sum(1 for paper in papers if paper["metadata"]["has_journal"])
        with_doi = sum(1 for paper in papers if paper["metadata"]["has_doi"])
        recent_papers = sum(1 for paper in papers if paper["metadata"]["is_recent"])
        
        return {
            "total_papers": total_papers,
            "total_authors": total_authors,
            "avg_authors_per_paper": round(total_authors / total_papers, 2),
            "date_range": {
                "oldest": oldest_date.isoformat(),
                "latest": latest_date.isoformat(),
                "span_days": (latest_date - oldest_date).days
            },
            "categories": {
                "unique_count": len(category_counts),
                "most_common": sorted(category_counts.items(), 
                                    key=lambda x: x[1], reverse=True)[:5],
                "distribution": category_counts
            },
            "publication_quality": {
                "with_journal_ref": with_journal,
                "with_doi": with_doi,
                "journal_percentage": round((with_journal / total_papers) * 100, 1),
                "doi_percentage": round((with_doi / total_papers) * 100, 1)
            },
            "recency": {
                "recent_papers": recent_papers,
                "recent_percentage": round((recent_papers / total_papers) * 100, 1)
            }
        }

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for arXiv papers (required)"
                },
                "max_results": {
                    "type": "integer", 
                    "description": "Maximum number of papers to return",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000
                },
                "sort_by": {
                    "type": "string",
                    "description": "Sort criteria for results",
                    "enum": ["relevance", "date", "citations"],
                    "default": "relevance"
                },
                "start_date": {
                    "type": "string",
                    "description": "Filter papers after this date (YYYY-MM-DD)",
                    "pattern": r"^\d{4}-\d{2}-\d{2}$"
                },
                "end_date": {
                    "type": "string", 
                    "description": "Filter papers before this date (YYYY-MM-DD)",
                    "pattern": r"^\d{4}-\d{2}-\d{2}$"
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by arXiv categories (e.g., ['cs.AI', 'stat.ML'])"
                }
            },
            "required": ["query"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return the output schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "papers": {
                    "type": "array",
                    "description": "List of papers found"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of papers returned"
                },
                "query": {
                    "type": "string", 
                    "description": "Original search query"
                },
                "search_metadata": {
                    "type": "object",
                    "description": "Metadata about the search performed"
                },
                "statistics": {
                    "type": "object",
                    "description": "Statistical analysis of results"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the search was performed"
                }
            }
        } 