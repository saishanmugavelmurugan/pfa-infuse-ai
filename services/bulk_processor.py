"""
Scalable Bulk Processing Service
Handles millions of identifiers with async processing
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator
from uuid import uuid4
import json

class BulkProcessorService:
    """
    High-performance bulk identifier processor
    - Chunked processing to prevent timeouts
    - Async job queue
    - Progress tracking
    - Error handling with retry
    """
    
    # Configuration
    CHUNK_SIZE = 1000  # Process in chunks
    MAX_CONCURRENT = 50  # Max concurrent processing
    RETRY_ATTEMPTS = 3
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.results_cache: Dict[str, List] = {}
        
    async def create_bulk_job(
        self,
        user_id: str,
        segment: str,
        identifiers: List[Dict[str, Any]],
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Create a new bulk processing job
        Returns job ID for tracking
        """
        job_id = f"bulk_{uuid4().hex[:12]}"
        
        job = {
            "id": job_id,
            "user_id": user_id,
            "segment": segment,
            "status": "pending",
            "priority": priority,
            "total_records": len(identifiers),
            "processed_records": 0,
            "successful_records": 0,
            "failed_records": 0,
            "error_log": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "completed_at": None,
            "identifiers": identifiers,
            "results": []
        }
        
        self.jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._process_job(job_id))
        
        return {
            "job_id": job_id,
            "status": "pending",
            "total_records": len(identifiers),
            "message": "Bulk job created and queued for processing"
        }
    
    async def _process_job(self, job_id: str):
        """Background job processor"""
        job = self.jobs.get(job_id)
        if not job:
            return
        
        job["status"] = "processing"
        job["started_at"] = datetime.now(timezone.utc).isoformat()
        
        identifiers = job["identifiers"]
        segment = job["segment"]
        
        # Process in chunks
        for i in range(0, len(identifiers), self.CHUNK_SIZE):
            chunk = identifiers[i:i + self.CHUNK_SIZE]
            
            # Process chunk with concurrency limit
            results = await self._process_chunk(chunk, segment, job_id)
            
            # Update job progress
            job["processed_records"] += len(chunk)
            job["successful_records"] += len([r for r in results if r.get("success")])
            job["failed_records"] += len([r for r in results if not r.get("success")])
            job["results"].extend(results)
            
            # Small delay between chunks to prevent overload
            await asyncio.sleep(0.1)
        
        job["status"] = "completed"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Clean up large data
        del job["identifiers"]
    
    async def _process_chunk(
        self, 
        chunk: List[Dict], 
        segment: str,
        job_id: str
    ) -> List[Dict]:
        """Process a chunk of identifiers with concurrency control"""
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        
        async def process_with_semaphore(identifier: Dict) -> Dict:
            async with semaphore:
                return await self._process_single_identifier(identifier, segment)
        
        tasks = [process_with_semaphore(ident) for ident in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "identifier": chunk[i],
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_identifier(
        self, 
        identifier: Dict, 
        segment: str
    ) -> Dict:
        """Process a single identifier with retry logic"""
        from services.vran_connector import vran_connector
        from services.threat_engine import threat_engine
        
        # Extract identifier value based on segment
        id_value = self._extract_identifier_value(identifier, segment)
        conn_type = identifier.get("connection_type", "mobile_number")
        
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                # Connect to vRAN
                if conn_type == "apn":
                    connection = await vran_connector.connect_apn(
                        apn=id_value,
                        user_id=identifier.get("user_id", "bulk"),
                        segment=segment
                    )
                else:
                    connection = await vran_connector.connect_mobile_number(
                        mobile_number=id_value,
                        user_id=identifier.get("user_id", "bulk"),
                        segment=segment
                    )
                
                if not connection.get("success"):
                    raise Exception(connection.get("error", "Connection failed"))
                
                # Analyze for threats
                analysis = await threat_engine.analyze_identifier(
                    identifier=id_value,
                    segment=segment,
                    connection_type=conn_type,
                    additional_data=identifier
                )
                
                return {
                    "success": True,
                    "identifier": id_value,
                    "session_id": connection.get("session_id"),
                    "threat_score": analysis.get("threat_score", 0),
                    "severity": analysis.get("severity", "minimal"),
                    "action": analysis.get("recommended_action", "detect"),
                    "threats_found": len(analysis.get("threats_found", []))
                }
                
            except Exception as e:
                if attempt == self.RETRY_ATTEMPTS - 1:
                    return {
                        "success": False,
                        "identifier": id_value,
                        "error": str(e)
                    }
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
        
        return {"success": False, "identifier": id_value, "error": "Max retries exceeded"}
    
    def _extract_identifier_value(self, identifier: Dict, segment: str) -> str:
        """Extract the primary identifier value based on segment"""
        if segment == "telco":
            return identifier.get("msisdn") or identifier.get("imsi") or identifier.get("apn", "")
        elif segment == "mobile":
            return identifier.get("phone_number") or identifier.get("imei", "")
        elif segment == "enterprise":
            return identifier.get("ip_address") or identifier.get("domain") or identifier.get("apn", "")
        elif segment == "automotive":
            return identifier.get("vin") or identifier.get("esim_iccid", "")
        return identifier.get("identifier", "")
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get current job status and progress"""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        
        progress = 0
        if job["total_records"] > 0:
            progress = (job["processed_records"] / job["total_records"]) * 100
        
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress_percent": round(progress, 2),
            "total_records": job["total_records"],
            "processed_records": job["processed_records"],
            "successful_records": job["successful_records"],
            "failed_records": job["failed_records"],
            "created_at": job["created_at"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "error_count": len(job["error_log"])
        }
    
    async def get_job_results(
        self, 
        job_id: str,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """Get paginated job results"""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        
        results = job.get("results", [])
        total = len(results)
        
        start = (page - 1) * page_size
        end = start + page_size
        
        return {
            "job_id": job_id,
            "total_results": total,
            "page": page,
            "page_size": page_size,
            "results": results[start:end]
        }
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job"""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        
        if job["status"] == "completed":
            return {"error": "Job already completed"}
        
        job["status"] = "cancelled"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        return {"success": True, "message": "Job cancelled"}
    
    async def get_all_jobs(
        self, 
        user_id: str, 
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get all jobs for a user"""
        user_jobs = [
            {
                "job_id": j["id"],
                "status": j["status"],
                "segment": j["segment"],
                "total_records": j["total_records"],
                "processed_records": j["processed_records"],
                "created_at": j["created_at"]
            }
            for j in self.jobs.values()
            if j["user_id"] == user_id and (status is None or j["status"] == status)
        ]
        return user_jobs


# Singleton instance
bulk_processor = BulkProcessorService()
