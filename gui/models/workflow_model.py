# gui/models/workflow_model.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data model for workflow status and job management.

This module provides classes for representing and managing workflow status
and job information in the GUI. It includes:
- WorkflowModel: A data model for overall workflow status
- JobModel: A data model for individual job information
- WorkflowStatus: Enum for workflow status values
- JobStatus: Enum for job status values

These models provide a layer of abstraction between the GUI components and
the backend workflow systems, allowing for more maintainable and testable code.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime
from pathlib import Path
import json

from PySide6.QtCore import QObject, Signal, Slot, Qt, QAbstractListModel, QModelIndex


class WorkflowStatus(Enum):
    """Enum for overall workflow status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    
    def __str__(self):
        return self.value


class JobStatus(Enum):
    """Enum for job status values"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    
    def __str__(self):
        return self.value
    
    @classmethod
    def from_string(cls, status_str: str) -> 'JobStatus':
        """Convert a string to a JobStatus enum value"""
        try:
            return cls(status_str.lower())
        except ValueError:
            # If not found, try some common mappings
            mapping = {
                "in_queue": cls.QUEUED,
                "in progress": cls.PROCESSING,
                "not_started": cls.PENDING,
                "validation_failed": cls.FAILED,
                "validated": cls.COMPLETED,
                "partially_completed": cls.COMPLETED
            }
            return mapping.get(status_str.lower(), cls.PENDING)
    
    def is_terminal(self) -> bool:
        """Check if the status is terminal (no more state changes expected)"""
        return self in [self.COMPLETED, self.FAILED, self.CANCELLED]


@dataclass
class JobModel:
    """Data model for an individual job"""
    job_id: str
    product_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    file_path: Optional[Path] = None
    result_path: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def __post_init__(self):
        """Ensure proper types after initialization"""
        if isinstance(self.status, str):
            self.status = JobStatus.from_string(self.status)
        
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        
        if isinstance(self.result_path, str):
            self.result_path = Path(self.result_path)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get the job duration in seconds"""
        if self.started_at is None:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def is_active(self) -> bool:
        """Check if the job is currently active"""
        return self.status in [JobStatus.QUEUED, JobStatus.PROCESSING]
    
    @property
    def is_complete(self) -> bool:
        """Check if the job is completed"""
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if the job failed"""
        return self.status == JobStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "job_id": self.job_id,
            "product_id": self.product_id,
            "status": self.status.value,
            "progress": self.progress,
            "file_path": str(self.file_path) if self.file_path else None,
            "result_path": str(self.result_path) if self.result_path else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobModel':
        """Create a JobModel from a dictionary"""
        job = cls(
            job_id=data.get("job_id", ""),
            product_id=data.get("product_id", ""),
            status=JobStatus.from_string(data.get("status", "pending")),
            progress=data.get("progress", 0),
            file_path=data.get("file_path"),
            result_path=data.get("result_path"),
            error=data.get("error")
        )
        
        # Parse datetime values
        for attr in ["created_at", "started_at", "completed_at"]:
            if data.get(attr):
                try:
                    setattr(job, attr, datetime.fromisoformat(data[attr]))
                except (ValueError, TypeError):
                    pass
        
        # Set metadata
        job.metadata = data.get("metadata", {})
        
        return job


class JobListModel(QAbstractListModel):
    """Qt list model for jobs"""
    
    # Define roles
    IdRole = Qt.UserRole + 1
    ProductIdRole = Qt.UserRole + 2
    StatusRole = Qt.UserRole + 3
    ProgressRole = Qt.UserRole + 4
    CreatedAtRole = Qt.UserRole + 5
    CompletedAtRole = Qt.UserRole + 6
    ErrorRole = Qt.UserRole + 7
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs = []
    
    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows in the model"""
        return len(self.jobs)
    
    def data(self, index, role=Qt.DisplayRole):
        """Return data for the given role"""
        if not index.isValid() or index.row() >= len(self.jobs):
            return None
        
        job = self.jobs[index.row()]
        
        if role == Qt.DisplayRole:
            return f"{job.product_id} ({job.status.value})"
        elif role == self.IdRole:
            return job.job_id
        elif role == self.ProductIdRole:
            return job.product_id
        elif role == self.StatusRole:
            return job.status.value
        elif role == self.ProgressRole:
            return job.progress
        elif role == self.CreatedAtRole:
            return job.created_at
        elif role == self.CompletedAtRole:
            return job.completed_at
        elif role == self.ErrorRole:
            return job.error
        
        return None
    
    def roleNames(self):
        """Return the role names for QML"""
        return {
            self.IdRole: b"jobId",
            self.ProductIdRole: b"productId",
            self.StatusRole: b"status",
            self.ProgressRole: b"progress",
            self.CreatedAtRole: b"createdAt",
            self.CompletedAtRole: b"completedAt",
            self.ErrorRole: b"error"
        }
    
    def addJob(self, job):
        """Add a job to the model"""
        self.beginInsertRows(QModelIndex(), len(self.jobs), len(self.jobs))
        self.jobs.append(job)
        self.endInsertRows()
    
    def updateJob(self, job_id, status=None, progress=None, result_path=None, 
                 completed_at=None, error=None):
        """Update a job in the model"""
        for i, job in enumerate(self.jobs):
            if job.job_id == job_id:
                # Update the job
                if status is not None:
                    if isinstance(status, str):
                        job.status = JobStatus.from_string(status)
                    else:
                        job.status = status
                
                if progress is not None:
                    job.progress = progress
                
                if result_path is not None:
                    job.result_path = result_path
                
                if completed_at is not None:
                    job.completed_at = completed_at
                
                if error is not None:
                    job.error = error
                
                # Emit data changed signal
                self.dataChanged.emit(
                    self.index(i, 0),
                    self.index(i, 0),
                    [self.StatusRole, self.ProgressRole, self.CompletedAtRole, self.ErrorRole]
                )
                return True
        
        return False
    
    def removeJob(self, job_id):
        """Remove a job from the model"""
        for i, job in enumerate(self.jobs):
            if job.job_id == job_id:
                self.beginRemoveRows(QModelIndex(), i, i)
                self.jobs.pop(i)
                self.endRemoveRows()
                return True
        
        return False
    
    def getJob(self, job_id):
        """Get a job by ID"""
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        
        return None
    
    def clear(self):
        """Clear all jobs"""
        self.beginResetModel()
        self.jobs = []
        self.endResetModel()


class WorkflowModel(QObject):
    """Data model for workflow status"""
    
    # Signals
    statusChanged = Signal(str)  # Status value
    progressChanged = Signal(int, int)  # current, total
    jobAdded = Signal(str)  # job_id
    jobUpdated = Signal(str, str, int)  # job_id, status, progress
    jobRemoved = Signal(str)  # job_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Current workflow status
        self._status = WorkflowStatus.IDLE
        
        # Job tracking
        self.jobs = {}  # job_id: JobModel
        self.active_jobs = set()
        self.completed_jobs = set()
        self.failed_jobs = set()
        
        # Progress tracking
        self.total_jobs = 0
        self.total_products = 0
        self.processed_jobs = 0
        self.processed_products = 0
        
        # Statistics
        self.start_time = None
        self.end_time = None
    
    @property
    def status(self) -> WorkflowStatus:
        """Get the current workflow status"""
        return self._status
    
    @status.setter
    def status(self, value: Union[WorkflowStatus, str]):
        """Set the workflow status"""
        if isinstance(value, str):
            try:
                value = WorkflowStatus(value)
            except ValueError:
                # Handle invalid status values
                return
        
        if value != self._status:
            self._status = value
            self.statusChanged.emit(str(value))
            
            # Update start/end time
            if value == WorkflowStatus.RUNNING and not self.start_time:
                self.start_time = datetime.now()
            elif value in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED] and not self.end_time:
                self.end_time = datetime.now()
    
    def add_job(self, job: JobModel) -> bool:
        """Add a job to the workflow"""
        if job.job_id in self.jobs:
            return False
        
        # Add to jobs dict
        self.jobs[job.job_id] = job
        
        # Update sets based on status
        if job.status == JobStatus.PROCESSING:
            self.active_jobs.add(job.job_id)
        elif job.status == JobStatus.COMPLETED:
            self.completed_jobs.add(job.job_id)
        elif job.status == JobStatus.FAILED:
            self.failed_jobs.add(job.job_id)
        
        # Update counts
        self.total_jobs += 1
        
        # Emit signal
        self.jobAdded.emit(job.job_id)
        
        return True
    
    def update_job(self, job_id: str, status: Optional[JobStatus] = None, 
                  progress: Optional[int] = None, result_path: Optional[Path] = None,
                  error: Optional[str] = None) -> bool:
        """Update a job status"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        old_status = job.status
        
        # Update status
        if status is not None:
            job.status = status
            
            # Update sets based on status change
            if old_status != status:
                # Remove from old status set
                if old_status == JobStatus.PROCESSING:
                    self.active_jobs.discard(job_id)
                elif old_status == JobStatus.COMPLETED:
                    self.completed_jobs.discard(job_id)
                elif old_status == JobStatus.FAILED:
                    self.failed_jobs.discard(job_id)
                
                # Add to new status set
                if status == JobStatus.PROCESSING:
                    job.started_at = datetime.now()
                    self.active_jobs.add(job_id)
                elif status == JobStatus.COMPLETED:
                    job.completed_at = datetime.now()
                    self.completed_jobs.add(job_id)
                    self.processed_jobs += 1
                elif status == JobStatus.FAILED:
                    job.completed_at = datetime.now()
                    self.failed_jobs.add(job_id)
                    self.processed_jobs += 1
        
        # Update progress
        if progress is not None:
            job.progress = progress
        
        # Update result path
        if result_path is not None:
            job.result_path = result_path
        
        # Update error
        if error is not None:
            job.error = error
        
        # Emit signal
        self.jobUpdated.emit(job_id, str(job.status), job.progress)
        
        # Update overall progress
        if self.total_jobs > 0:
            progress_value = int((self.processed_jobs / self.total_jobs) * 100)
            self.progressChanged.emit(self.processed_jobs, self.total_jobs)
        
        return True
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the workflow"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        # Remove from tracking sets
        if job.status == JobStatus.PROCESSING:
            self.active_jobs.discard(job_id)
        elif job.status == JobStatus.COMPLETED:
            self.completed_jobs.discard(job_id)
        elif job.status == JobStatus.FAILED:
            self.failed_jobs.discard(job_id)
        
        # Remove from jobs dict
        del self.jobs[job_id]
        
        # Emit signal
        self.jobRemoved.emit(job_id)
        
        return True
    
    def get_job(self, job_id: str) -> Optional[JobModel]:
        """Get a job by ID"""
        return self.jobs.get(job_id)
    
    def get_active_jobs(self) -> List[JobModel]:
        """Get all active jobs"""
        return [self.jobs[job_id] for job_id in self.active_jobs if job_id in self.jobs]
    
    def get_completed_jobs(self) -> List[JobModel]:
        """Get all completed jobs"""
        return [self.jobs[job_id] for job_id in self.completed_jobs if job_id in self.jobs]
    
    def get_failed_jobs(self) -> List[JobModel]:
        """Get all failed jobs"""
        return [self.jobs[job_id] for job_id in self.failed_jobs if job_id in self.jobs]
    
    def get_all_jobs(self) -> List[JobModel]:
        """Get all jobs"""
        return list(self.jobs.values())
    
    def clear(self) -> None:
        """Clear all jobs and reset the workflow"""
        self.jobs = {}
        self.active_jobs = set()
        self.completed_jobs = set()
        self.failed_jobs = set()
        
        self.total_jobs = 0
        self.total_products = 0
        self.processed_jobs = 0
        self.processed_products = 0
        
        self.start_time = None
        self.end_time = None
        
        self.status = WorkflowStatus.IDLE
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the current workflow status"""
        elapsed_time = None
        
        if self.start_time:
            end = self.end_time or datetime.now()
            elapsed_time = (end - self.start_time).total_seconds()
        
        return {
            "status": str(self.status),
            "total_jobs": self.total_jobs,
            "processed_jobs": self.processed_jobs,
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "failed_jobs": len(self.failed_jobs),
            "progress_percentage": int((self.processed_jobs / max(1, self.total_jobs)) * 100),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": elapsed_time
        }
    
    def save_to_file(self, file_path: Union[str, Path]) -> bool:
        """Save workflow state to a file"""
        try:
            file_path = Path(file_path)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert all jobs to dictionaries
            jobs_dict = {job_id: job.to_dict() for job_id, job in self.jobs.items()}
            
            # Create state dictionary
            state = {
                "status": str(self.status),
                "total_jobs": self.total_jobs,
                "total_products": self.total_products,
                "processed_jobs": self.processed_jobs,
                "processed_products": self.processed_products,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "active_jobs": list(self.active_jobs),
                "completed_jobs": list(self.completed_jobs),
                "failed_jobs": list(self.failed_jobs),
                "jobs": jobs_dict
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving workflow state: {str(e)}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> Optional['WorkflowModel']:
        """Load workflow state from a file"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return None
            
            # Read from file
            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Create workflow model
            workflow = cls()
            
            # Set basic properties
            workflow.status = state.get("status", "idle")
            workflow.total_jobs = state.get("total_jobs", 0)
            workflow.total_products = state.get("total_products", 0)
            workflow.processed_jobs = state.get("processed_jobs", 0)
            workflow.processed_products = state.get("processed_products", 0)
            
            # Parse datetime values
            if state.get("start_time"):
                workflow.start_time = datetime.fromisoformat(state["start_time"])
            
            if state.get("end_time"):
                workflow.end_time = datetime.fromisoformat(state["end_time"])
            
            # Recreate jobs
            jobs_dict = state.get("jobs", {})
            for job_id, job_data in jobs_dict.items():
                job = JobModel.from_dict(job_data)
                workflow.jobs[job_id] = job
            
            # Recreate tracking sets
            workflow.active_jobs = set(state.get("active_jobs", []))
            workflow.completed_jobs = set(state.get("completed_jobs", []))
            workflow.failed_jobs = set(state.get("failed_jobs", []))
            
            return workflow
        except Exception as e:
            print(f"Error loading workflow state: {str(e)}")
            return None


class BatchModel:
    """Model for a batch of jobs"""
    
    def __init__(self, batch_id: str, batch_name: str):
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.job_ids = []
        self.created_at = datetime.now()
        self.total_products = 0
        self.enqueued_products = 0
        self.tags = []
        self.metadata = {}
    
    def add_job(self, job_id: str) -> None:
        """Add a job to the batch"""
        if job_id not in self.job_ids:
            self.job_ids.append(job_id)
            self.enqueued_products += 1
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the batch"""
        if job_id in self.job_ids:
            self.job_ids.remove(job_id)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "batch_id": self.batch_id,
            "batch_name": self.batch_name,
            "job_ids": self.job_ids,
            "created_at": self.created_at.isoformat(),
            "total_products": self.total_products,
            "enqueued_products": self.enqueued_products,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchModel':
        """Create a BatchModel from a dictionary"""
        batch = cls(
            batch_id=data.get("batch_id", ""),
            batch_name=data.get("batch_name", "")
        )
        
        batch.job_ids = data.get("job_ids", [])
        batch.total_products = data.get("total_products", 0)
        batch.enqueued_products = data.get("enqueued_products", 0)
        batch.tags = data.get("tags", [])
        batch.metadata = data.get("metadata", {})
        
        # Parse created_at
        if data.get("created_at"):
            try:
                batch.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        
        return batch