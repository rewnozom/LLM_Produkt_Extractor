#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/utils/thread_worker.py

import time
import traceback
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerStatus(Enum):
    """Enum for worker status"""
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkerSignals(QObject):
    """
    Defines signals available for a Worker.
    
    Signals:
        started: Signal emitted when the worker starts
        finished: Signal emitted when the worker has completed
        error: Signal emitted if an error occurs during execution
        result: Signal to return the result of the worker
        progress: Signal to report the worker's progress
        status: Signal to report worker status changes
        cancelled: Signal emitted when the worker is cancelled
    """
    started = Signal(str)  # worker_id
    finished = Signal(str)  # worker_id
    error = Signal(str, str, str)  # worker_id, error_msg, traceback
    result = Signal(str, object)  # worker_id, result
    progress = Signal(str, int, str)  # worker_id, percent, message
    status = Signal(str, object)  # worker_id, WorkerStatus
    cancelled = Signal(str)  # worker_id


class Worker(QRunnable):
    """
    Worker thread for executing tasks in the background.
    
    Provides signals for progress updates, results, and error handling.
    Can be cancelled and supports progress reporting.
    
    Usage:
        worker = Worker(my_function, *args, **kwargs)
        worker.signals.result.connect(handle_result)
        worker.signals.error.connect(handle_error)
        QThreadPool.globalInstance().start(worker)
    """
    
    def __init__(self, 
                fn: Callable, 
                *args, 
                worker_id: str = None, 
                progress_callback: Callable[[int, str], None] = None, 
                **kwargs):
        """
        Initialize the worker thread.
        
        Args:
            fn: The function to execute in the thread
            *args: Arguments to pass to the function
            worker_id: Optional ID for the worker (auto-generated if not provided)
            progress_callback: Optional callback for progress updates
            **kwargs: Keyword arguments to pass to the function
        """
        super().__init__()
        
        # Store constructor arguments
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.worker_id = worker_id or str(uuid.uuid4())
        self.progress_callback = progress_callback
        
        # Create signals object
        self.signals = WorkerSignals()
        
        # Status tracking
        self._status = WorkerStatus.IDLE
        self._cancel_requested = False
        self._pause_requested = False
        self._progress = 0
        
        # Auto-cleanup flag - if True, worker will be auto-deleted when finished
        self.setAutoDelete(True)
    
    @property
    def status(self) -> WorkerStatus:
        """Get current worker status"""
        return self._status
    
    @status.setter
    def status(self, value: WorkerStatus) -> None:
        """Set worker status and emit status signal"""
        if self._status != value:
            self._status = value
            self.signals.status.emit(self.worker_id, value)
    
    def report_progress(self, progress: int, message: str = "") -> None:
        """
        Report progress during task execution
        
        Args:
            progress: Percentage complete (0-100)
            message: Optional status message
        """
        progress = max(0, min(100, progress))  # Clamp between 0-100
        self._progress = progress
        self.signals.progress.emit(self.worker_id, progress, message)
        
        # Call the progress callback if provided
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    def cancel(self) -> None:
        """Request cancellation of the worker"""
        self._cancel_requested = True
        self.status = WorkerStatus.CANCELLED
        self.signals.cancelled.emit(self.worker_id)
    
    def pause(self) -> None:
        """Request pausing of the worker"""
        self._pause_requested = True
        self.status = WorkerStatus.PAUSED
    
    def resume(self) -> None:
        """Resume a paused worker"""
        self._pause_requested = False
        self.status = WorkerStatus.RUNNING
    
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested"""
        return self._cancel_requested
    
    def is_paused(self) -> bool:
        """Check if pausing has been requested"""
        return self._pause_requested
    
    @Slot()
    def run(self) -> None:
        """
        Execute the function with the provided arguments.
        
        This method is automatically called by QThreadPool when the worker is started.
        """
        # Update status
        self.status = WorkerStatus.RUNNING
        self.signals.started.emit(self.worker_id)
        
        try:
            # Execute the function
            result = self.fn(
                *self.args, 
                worker_id=self.worker_id,
                progress_callback=self.report_progress,
                worker=self,  # Pass self to allow checking cancel status
                **self.kwargs
            )
            
            # Check if cancelled
            if self._cancel_requested:
                self.status = WorkerStatus.CANCELLED
                return
            
            # Emit result
            self.signals.result.emit(self.worker_id, result)
            self.status = WorkerStatus.COMPLETED
            
        except Exception as e:
            # Get traceback info
            tb = traceback.format_exc()
            
            # Emit error
            self.signals.error.emit(self.worker_id, str(e), tb)
            self.status = WorkerStatus.FAILED
            
        finally:
            # Always emit finished signal
            self.signals.finished.emit(self.worker_id)


class WorkerManager(QObject):
    """
    Manager class for handling multiple worker threads.
    
    Provides:
    - Centralized worker creation and tracking
    - Global progress reporting
    - Worker cancellation and cleanup
    - Thread pool management
    """
    
    # Signals for the manager
    all_workers_finished = Signal()
    global_progress = Signal(int, int)  # completed_tasks, total_tasks
    
    def __init__(self, max_threads: int = None):
        """
        Initialize the worker manager.
        
        Args:
            max_threads: Maximum number of concurrent threads (None = use system default)
        """
        super().__init__()
        
        # Create a thread pool
        self.thread_pool = QThreadPool.globalInstance()
        
        # Set maximum thread count if specified
        if max_threads is not None:
            self.thread_pool.setMaxThreadCount(max_threads)
        
        # Store active workers
        self._workers = {}  # worker_id -> Worker
        
        # Progress tracking
        self._completed_tasks = 0
        self._total_tasks = 0
    
    def create_worker(self, 
                     fn: Callable, 
                     *args, 
                     worker_id: str = None, 
                     autostart: bool = False, 
                     **kwargs) -> Worker:
        """
        Create a new worker.
        
        Args:
            fn: The function to execute in the thread
            *args: Arguments to pass to the function
            worker_id: Optional ID for the worker
            autostart: Whether to automatically start the worker
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The created worker
        """
        # Create worker
        worker = Worker(fn, *args, worker_id=worker_id, **kwargs)
        
        # Connect signals
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.cancelled.connect(self._on_worker_cancelled)
        
        # Store worker
        self._workers[worker.worker_id] = worker
        self._total_tasks += 1
        
        # Update global progress
        self._update_global_progress()
        
        # Start worker if requested
        if autostart:
            self.start_worker(worker.worker_id)
        
        return worker
    
    def start_worker(self, worker_id: str) -> bool:
        """
        Start a worker by ID.
        
        Args:
            worker_id: ID of the worker to start
            
        Returns:
            True if worker was started, False if not found
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return False
        
        worker.status = WorkerStatus.QUEUED
        self.thread_pool.start(worker)
        return True
    
    def cancel_worker(self, worker_id: str) -> bool:
        """
        Cancel a worker by ID.
        
        Args:
            worker_id: ID of the worker to cancel
            
        Returns:
            True if worker was cancelled, False if not found
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return False
        
        worker.cancel()
        return True
    
    def cancel_all_workers(self) -> None:
        """Cancel all active workers"""
        for worker_id in list(self._workers.keys()):
            self.cancel_worker(worker_id)
    
    def pause_worker(self, worker_id: str) -> bool:
        """
        Pause a worker by ID.
        
        Args:
            worker_id: ID of the worker to pause
            
        Returns:
            True if worker was paused, False if not found
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return False
        
        worker.pause()
        return True
    
    def resume_worker(self, worker_id: str) -> bool:
        """
        Resume a paused worker by ID.
        
        Args:
            worker_id: ID of the worker to resume
            
        Returns:
            True if worker was resumed, False if not found
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return False
        
        worker.resume()
        return True
    
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """
        Get a worker by ID.
        
        Args:
            worker_id: ID of the worker to get
            
        Returns:
            The worker if found, None otherwise
        """
        return self._workers.get(worker_id)
    
    def get_all_workers(self) -> Dict[str, Worker]:
        """
        Get all active workers.
        
        Returns:
            Dictionary of worker_id -> Worker
        """
        return self._workers.copy()
    
    def get_worker_status(self, worker_id: str) -> Optional[WorkerStatus]:
        """
        Get a worker's status by ID.
        
        Args:
            worker_id: ID of the worker
            
        Returns:
            The worker's status if found, None otherwise
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return None
        
        return worker.status
    
    def get_active_worker_count(self) -> int:
        """
        Get number of active workers.
        
        Returns:
            Number of active workers
        """
        return sum(1 for worker in self._workers.values() 
                  if worker.status in [WorkerStatus.RUNNING, WorkerStatus.QUEUED])
    
    def get_max_thread_count(self) -> int:
        """
        Get maximum thread count.
        
        Returns:
            Maximum number of concurrent threads
        """
        return self.thread_pool.maxThreadCount()
    
    def set_max_thread_count(self, count: int) -> None:
        """
        Set maximum thread count.
        
        Args:
            count: Maximum number of concurrent threads
        """
        self.thread_pool.setMaxThreadCount(count)
    
    def wait_for_all(self, timeout: int = None) -> bool:
        """
        Wait for all workers to finish.
        
        Args:
            timeout: Timeout in milliseconds (None = wait indefinitely)
            
        Returns:
            True if all workers finished, False if timed out
        """
        return self.thread_pool.waitForDone(timeout)
    
    def _on_worker_finished(self, worker_id: str) -> None:
        """Handle worker finished signal"""
        # Update completed count
        self._completed_tasks += 1
        
        # Update global progress
        self._update_global_progress()
        
        # Check if all workers are done
        if self._completed_tasks >= self._total_tasks:
            self.all_workers_finished.emit()
        
        # Remove worker from tracking
        if worker_id in self._workers:
            del self._workers[worker_id]
    
    def _on_worker_cancelled(self, worker_id: str) -> None:
        """Handle worker cancelled signal"""
        # Count as completed
        self._completed_tasks += 1
        
        # Update global progress
        self._update_global_progress()
    
    def _update_global_progress(self) -> None:
        """Update and emit global progress"""
        self.global_progress.emit(self._completed_tasks, self._total_tasks)