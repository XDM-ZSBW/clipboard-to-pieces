#!/usr/bin/env python3
"""
Feedback System for Agentic Learning
Implements feedback loops for continuous improvement
"""

import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class FeedbackType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    USER_CORRECTION = "user_correction"
    PERFORMANCE = "performance"
    QUALITY = "quality"

@dataclass
class FeedbackEvent:
    timestamp: float
    feedback_type: FeedbackType
    content_id: str
    message: str
    metadata: Dict
    severity: int  # 1-10, higher is more severe

class FeedbackSystem:
    """Implements feedback loops for continuous improvement"""
    
    def __init__(self):
        self.feedback_handlers: Dict[FeedbackType, List[Callable]] = {}
        self.feedback_history: List[FeedbackEvent] = []
        self.performance_metrics: Dict[str, float] = {}
        self.quality_scores: Dict[str, float] = {}
    
    def register_handler(self, feedback_type: FeedbackType, handler: Callable):
        """Register a feedback handler"""
        if feedback_type not in self.feedback_handlers:
            self.feedback_handlers[feedback_type] = []
        self.feedback_handlers[feedback_type].append(handler)
    
    def provide_feedback(self, feedback_type: FeedbackType, content_id: str, message: str, metadata: Dict = None, severity: int = 5):
        """Provide feedback for processing"""
        event = FeedbackEvent(
            timestamp=time.time(),
            feedback_type=feedback_type,
            content_id=content_id,
            message=message,
            metadata=metadata or {},
            severity=severity
        )
        
        self.feedback_history.append(event)
        
        # Trigger handlers
        if feedback_type in self.feedback_handlers:
            for handler in self.feedback_handlers[feedback_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in feedback handler: {e}")
        
        # Update metrics
        self._update_metrics(event)
    
    def get_feedback_summary(self, hours: int = 24) -> Dict:
        """Get feedback summary for the last N hours"""
        cutoff_time = time.time() - (hours * 3600)
        recent_feedback = [f for f in self.feedback_history if f.timestamp > cutoff_time]
        
        if not recent_feedback:
            return {'total': 0}
        
        summary = {
            'total': len(recent_feedback),
            'by_type': {},
            'by_severity': {},
            'avg_severity': sum(f.severity for f in recent_feedback) / len(recent_feedback)
        }
        
        # Group by type
        for event in recent_feedback:
            feedback_type = event.feedback_type.value
            if feedback_type not in summary['by_type']:
                summary['by_type'][feedback_type] = 0
            summary['by_type'][feedback_type] += 1
        
        # Group by severity
        for event in recent_feedback:
            severity_range = f"{((event.severity - 1) // 3) * 3 + 1}-{((event.severity - 1) // 3) * 3 + 3}"
            if severity_range not in summary['by_severity']:
                summary['by_severity'][severity_range] = 0
            summary['by_severity'][severity_range] += 1
        
        return summary
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        return self.performance_metrics.copy()
    
    def get_quality_scores(self) -> Dict[str, float]:
        """Get current quality scores"""
        return self.quality_scores.copy()
    
    def _update_metrics(self, event: FeedbackEvent):
        """Update performance metrics based on feedback"""
        content_id = event.content_id
        
        if event.feedback_type == FeedbackType.SUCCESS:
            # Update success metrics
            if 'success_rate' not in self.performance_metrics:
                self.performance_metrics['success_rate'] = 0.0
            self.performance_metrics['success_rate'] = (self.performance_metrics['success_rate'] + 1.0) / 2.0
            
        elif event.feedback_type == FeedbackType.FAILURE:
            # Update failure metrics
            if 'failure_rate' not in self.performance_metrics:
                self.performance_metrics['failure_rate'] = 0.0
            self.performance_metrics['failure_rate'] = (self.performance_metrics['failure_rate'] + 1.0) / 2.0
            
        elif event.feedback_type == FeedbackType.PERFORMANCE:
            # Update performance metrics
            if 'processing_time' in event.metadata:
                processing_time = event.metadata['processing_time']
                if 'avg_processing_time' not in self.performance_metrics:
                    self.performance_metrics['avg_processing_time'] = processing_time
                else:
                    self.performance_metrics['avg_processing_time'] = (
                        self.performance_metrics['avg_processing_time'] + processing_time
                    ) / 2.0
            
        elif event.feedback_type == FeedbackType.QUALITY:
            # Update quality scores
            if 'quality_score' in event.metadata:
                quality_score = event.metadata['quality_score']
                self.quality_scores[content_id] = quality_score
                
                # Update overall quality average
                if self.quality_scores:
                    avg_quality = sum(self.quality_scores.values()) / len(self.quality_scores)
                    self.performance_metrics['avg_quality'] = avg_quality

class AdaptiveProcessor:
    """Adaptive processor that learns from feedback"""
    
    def __init__(self, feedback_system: FeedbackSystem):
        self.feedback_system = feedback_system
        self.adaptation_rules: Dict[str, Callable] = {}
        self.performance_thresholds = {
            'success_rate': 0.8,
            'failure_rate': 0.2,
            'avg_processing_time': 5.0,
            'avg_quality': 7.0
        }
    
    def register_adaptation_rule(self, condition: str, rule: Callable):
        """Register an adaptation rule"""
        self.adaptation_rules[condition] = rule
    
    def check_adaptations(self) -> List[str]:
        """Check if adaptations are needed"""
        adaptations = []
        metrics = self.feedback_system.get_performance_metrics()
        
        for metric, threshold in self.performance_thresholds.items():
            if metric in metrics:
                if metric == 'failure_rate' and metrics[metric] > threshold:
                    adaptations.append(f"High failure rate: {metrics[metric]:.2f} > {threshold}")
                elif metric == 'success_rate' and metrics[metric] < threshold:
                    adaptations.append(f"Low success rate: {metrics[metric]:.2f} < {threshold}")
                elif metric == 'avg_processing_time' and metrics[metric] > threshold:
                    adaptations.append(f"Slow processing: {metrics[metric]:.2f}s > {threshold}s")
                elif metric == 'avg_quality' and metrics[metric] < threshold:
                    adaptations.append(f"Low quality: {metrics[metric]:.2f} < {threshold}")
        
        return adaptations
    
    def apply_adaptations(self, adaptations: List[str]):
        """Apply necessary adaptations"""
        for adaptation in adaptations:
            print(f"Applying adaptation: {adaptation}")
            # Here you would implement specific adaptation logic
            # For example, adjusting processing parameters, changing strategies, etc.


