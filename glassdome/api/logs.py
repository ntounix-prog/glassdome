"""
Log Query API Endpoints

Provides fast access to Elasticsearch logs from Glassdome and infrastructure.

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# ELK Configuration
ELASTICSEARCH_URL = "http://192.168.3.26:9200"


class LogEntry(BaseModel):
    timestamp: str
    level: Optional[str] = None
    logger: Optional[str] = None
    message: str
    host: Optional[str] = None
    service: Optional[str] = None


class LogQueryResponse(BaseModel):
    total: int
    took_ms: int
    logs: List[dict]


@router.get("/search", response_model=LogQueryResponse)
async def search_logs(
    q: str = Query(default="*", description="Search query (Lucene syntax)"),
    level: Optional[str] = Query(default=None, description="Log level filter: ERROR, WARN, INFO, DEBUG"),
    hours: int = Query(default=1, description="Hours to look back"),
    limit: int = Query(default=50, le=500, description="Max results"),
    index: str = Query(default="glassdome-*", description="Index pattern")
):
    """
    Search logs in Elasticsearch.
    
    Examples:
    - /api/logs/search?q=error
    - /api/logs/search?q=uvicorn&level=ERROR&hours=24
    - /api/logs/search?q=lab_id:test-123
    """
    
    # Build query
    must = []
    
    if q and q != "*":
        must.append({"query_string": {"query": q}})
    
    if level:
        must.append({"match": {"level": level.upper()}})
    
    # Time range
    time_from = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    must.append({"range": {"@timestamp": {"gte": time_from}}})
    
    query = {
        "size": limit,
        "sort": [{"@timestamp": "desc"}],
        "query": {
            "bool": {
                "must": must if must else [{"match_all": {}}]
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ELASTICSEARCH_URL}/{index}/_search",
                json=query,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Elasticsearch error: {response.text}"
                )
            
            data = response.json()
            
            logs = []
            for hit in data.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                logs.append({
                    "timestamp": source.get("@timestamp"),
                    "level": source.get("level") or source.get("log", {}).get("level"),
                    "logger": source.get("logger"),
                    "message": source.get("message", ""),
                    "host": source.get("hostname") or source.get("beat_host", {}).get("name"),
                    "service": source.get("service"),
                    "index": hit.get("_index")
                })
            
            return LogQueryResponse(
                total=data.get("hits", {}).get("total", {}).get("value", 0),
                took_ms=data.get("took", 0),
                logs=logs
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Elasticsearch timeout")
    except Exception as e:
        logger.error(f"Log search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", response_model=LogQueryResponse)
async def recent_logs(
    limit: int = Query(default=20, le=100),
    level: Optional[str] = Query(default=None)
):
    """Get most recent logs (last hour)"""
    return await search_logs(q="*", level=level, hours=1, limit=limit)


@router.get("/errors", response_model=LogQueryResponse)
async def error_logs(
    hours: int = Query(default=24),
    limit: int = Query(default=50, le=200)
):
    """Get recent error logs"""
    return await search_logs(q="*", level="ERROR", hours=hours, limit=limit)


@router.get("/stats")
async def log_stats():
    """Get log statistics from Elasticsearch"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get index stats
            response = await client.get(f"{ELASTICSEARCH_URL}/_cat/indices/glassdome-*?format=json")
            indices = response.json() if response.status_code == 200 else []
            
            total_docs = sum(int(idx.get("docs.count", 0) or 0) for idx in indices)
            
            # Parse size (e.g., "66.6mb", "1.2gb")
            total_size = 0
            for idx in indices:
                size_str = idx.get("store.size", "0b")
                try:
                    if "gb" in size_str:
                        total_size += float(size_str.replace("gb", "")) * 1024
                    elif "mb" in size_str:
                        total_size += float(size_str.replace("mb", ""))
                    elif "kb" in size_str:
                        total_size += float(size_str.replace("kb", "")) / 1024
                except:
                    pass
            
            # Get cluster health
            health_resp = await client.get(f"{ELASTICSEARCH_URL}/_cluster/health")
            health = health_resp.json() if health_resp.status_code == 200 else {}
            
            return {
                "status": "connected",
                "cluster_status": health.get("status", "unknown"),
                "indices": len(indices),
                "total_documents": total_docs,
                "total_size_mb": round(total_size, 2),
                "elasticsearch_url": ELASTICSEARCH_URL
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "elasticsearch_url": ELASTICSEARCH_URL
        }

