import json
import os
import re
from collections import Counter

class ChronosAnalytics:
    def __init__(self, failure_log, metrics_log):
        self.failure_log = failure_log
        self.metrics_log = metrics_log

    def _parse_indented_logs(self, file_path, log_type="json"):
        """Handles multi-line indented JSON blocks within a log file."""
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, "r") as f:
            content = f.read()

        # Find all JSON blocks (anything between { and })
        # This regex handles nested braces slightly but is mostly designed 
        # to find the indented blocks produced by indent=4.
        json_blocks = re.findall(r'\{.*?\}', content, re.DOTALL)
        
        parsed_data = []
        for block in json_blocks:
            try:
                parsed_data.append(json.loads(block))
            except json.JSONDecodeError:
                continue
        return parsed_data

    def get_system_kpis(self):
        stats = {
            "reliability_score": 100,
            "avg_latency_ms": 0,
            "total_interventions": 0,
            "failure_distribution": {},
            "grounding_accuracy": 0
        }

        # 1. Parse Failures (Indented blocks)
        failures = self._parse_indented_logs(self.failure_log)
        if failures:
            types = [f.get('error', 'UNKNOWN_ERROR') for f in failures]
            stats['failure_distribution'] = dict(Counter(types))
            # Reliability: Deduct 2% per error found in the log
            stats['reliability_score'] = max(0, 100 - (len(failures) * 2))

        # 2. Parse Metrics (Indented blocks)
        metrics = self._parse_indented_logs(self.metrics_log)
        if metrics:
            latencies = [m.get('latency_ms', 0) for m in metrics]
            grounding_hits = sum(1 for m in metrics if m.get("context_found", False))
            
            stats['avg_latency_ms'] = round(sum(latencies) / len(latencies), 2) if latencies else 0
            stats['grounding_accuracy'] = round((grounding_hits / len(metrics)) * 100, 2)
            stats['total_interventions'] = sum(1 for m in metrics if m.get('intervention_required', False))

        return stats

    def export_kpi_summary(self, output_path):
        """Dumps the current stats into a formatted JSON for the frontend to cache."""
        stats = self.get_system_kpis()
        with open(output_path, "w") as f:
            json.dump(stats, f, indent=4) # Maintaining your preferred format
        return stats

# Initializing with your specific local paths
analytics_engine = ChronosAnalytics(
    "D:\\full stack projects\\local LLM\\backend\\failure.log", 
    "D:\\full stack projects\\local LLM\\backend\\retrieval_metrics.log"
)
