#!/usr/bin/env python3
"""
State Manager for Agentic Processing
Tracks processing state, learning, and optimization
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

class ProcessingState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class ProcessingRecord:
    id: str
    content_type: str
    strategy: str
    state: ProcessingState
    timestamp: float
    attempts: int
    success: bool
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict] = None

class StateManager:
    """Manages processing state and learning"""
    
    def __init__(self, state_file: str = "processing_state.json"):
        self.state_file = Path(state_file)
        self.records: Dict[str, ProcessingRecord] = {}
        self.learning_data: Dict[str, Any] = {}
        self.load_state()
    
    def load_state(self):
        """Load state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    records_data = {}
                    for k, v in data.get('records', {}).items():
                        # Convert state string back to enum
                        v['state'] = ProcessingState(v['state'])
                        records_data[k] = ProcessingRecord(**v)
                    self.records = records_data
                    self.learning_data = data.get('learning', {})
            except Exception as e:
                print(f"Error loading state: {e}")
                self.records = {}
                self.learning_data = {}
    
    def save_state(self):
        """Save state to file"""
        try:
            # Convert ProcessingState enum to string for JSON serialization
            records_data = {}
            for k, v in self.records.items():
                record_dict = asdict(v)
                record_dict['state'] = v.state.value  # Convert enum to string
                records_data[k] = record_dict
            
            data = {
                'records': records_data,
                'learning': self.learning_data,
                'timestamp': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def start_processing(self, content_id: str, content_type: str, strategy: str) -> ProcessingRecord:
        """Start processing a new item"""
        record = ProcessingRecord(
            id=content_id,
            content_type=content_type,
            strategy=strategy,
            state=ProcessingState.PROCESSING,
            timestamp=time.time(),
            attempts=1,
            success=False
        )
        self.records[content_id] = record
        self.save_state()
        return record
    
    def complete_processing(self, content_id: str, success: bool, processing_time: float = None, error_message: str = None):
        """Complete processing for an item"""
        if content_id in self.records:
            record = self.records[content_id]
            record.state = ProcessingState.COMPLETED if success else ProcessingState.FAILED
            record.success = success
            record.processing_time = processing_time
            record.error_message = error_message
            self.save_state()
            
            # Update learning data
            self._update_learning_data(record)
    
    def retry_processing(self, content_id: str) -> bool:
        """Retry processing for a failed item"""
        if content_id in self.records:
            record = self.records[content_id]
            if record.attempts < 3:  # Max 3 attempts
                record.attempts += 1
                record.state = ProcessingState.RETRYING
                record.timestamp = time.time()
                self.save_state()
                return True
        return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total = len(self.records)
        if total == 0:
            return {'total': 0}
        
        completed = sum(1 for r in self.records.values() if r.state == ProcessingState.COMPLETED)
        failed = sum(1 for r in self.records.values() if r.state == ProcessingState.FAILED)
        pending = sum(1 for r in self.records.values() if r.state == ProcessingState.PENDING)
        
        success_rate = (completed / total) * 100 if total > 0 else 0
        
        # Strategy performance
        strategy_stats = {}
        for record in self.records.values():
            strategy = record.strategy
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'total': 0, 'success': 0}
            strategy_stats[strategy]['total'] += 1
            if record.success:
                strategy_stats[strategy]['success'] += 1
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'success_rate': success_rate,
            'strategy_performance': strategy_stats
        }
    
    def get_optimal_strategy(self, content_type: str) -> str:
        """Get optimal strategy based on learning data"""
        if content_type in self.learning_data:
            strategies = self.learning_data[content_type].get('strategies', {})
            if strategies:
                # Return strategy with highest success rate
                best_strategy = max(strategies.items(), key=lambda x: x[1].get('success_rate', 0))
                return best_strategy[0]
        
        # Default strategies
        default_strategies = {
            'code': 'priority',
            'image': 'immediate',
            'text': 'immediate',
            'config': 'priority',
            'log': 'batch',
            'data': 'immediate'
        }
        return default_strategies.get(content_type, 'immediate')
    
    def _update_learning_data(self, record: ProcessingRecord):
        """Update learning data based on processing results"""
        content_type = record.content_type
        strategy = record.strategy
        
        if content_type not in self.learning_data:
            self.learning_data[content_type] = {'strategies': {}}
        
        if strategy not in self.learning_data[content_type]['strategies']:
            self.learning_data[content_type]['strategies'][strategy] = {
                'total': 0,
                'success': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
        
        strategy_data = self.learning_data[content_type]['strategies'][strategy]
        strategy_data['total'] += 1
        if record.success:
            strategy_data['success'] += 1
        
        strategy_data['success_rate'] = (strategy_data['success'] / strategy_data['total']) * 100
        
        if record.processing_time:
            # Update average processing time
            current_avg = strategy_data['avg_processing_time']
            total = strategy_data['total']
            strategy_data['avg_processing_time'] = ((current_avg * (total - 1)) + record.processing_time) / total
        
        self.save_state()
    
    def cleanup_old_records(self, max_age_hours: int = 24):
        """Clean up old processing records"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        old_records = [k for k, v in self.records.items() if v.timestamp < cutoff_time]
        
        for record_id in old_records:
            del self.records[record_id]
        
        if old_records:
            self.save_state()
            print(f"Cleaned up {len(old_records)} old records")
