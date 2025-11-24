"""
Standalone metrics server for fine-tuning jobs.

Can be run as a sidecar or standalone service.
"""

import argparse
import logging
import time
from pathlib import Path

from monitoring.metrics import FineTuningMetricsExporter, TrainingMetrics, get_gpu_metrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for metrics server."""
    parser = argparse.ArgumentParser(description="Fine-tuning metrics server")
    parser.add_argument("--port", type=int, default=8000, help="Metrics server port")
    parser.add_argument("--job-name", type=str, help="Job name for metrics")
    parser.add_argument("--model-id", type=str, help="Model ID")
    parser.add_argument("--method", type=str, help="Fine-tuning method")
    parser.add_argument("--training-info", type=str, help="Path to training_info.json")
    
    args = parser.parse_args()
    
    # Initialize exporter
    exporter = FineTuningMetricsExporter(port=args.port)
    exporter.start_server()
    
    logger.info(f"Metrics server started on port {args.port}")
    logger.info(f"Access metrics at http://localhost:{args.port}/metrics")
    
    # If training info is provided, update metrics
    if args.training_info and args.job_name and args.model_id:
        training_info_path = Path(args.training_info)
        if training_info_path.exists():
            import json
            with open(training_info_path, 'r') as f:
                training_info = json.load(f)
            
            # Update job status
            exporter.update_job_status(
                job_name=args.job_name,
                model_id=args.model_id,
                method=args.method or "unknown",
                status="Running"
            )
            
            # Update training metrics if available
            if "results" in training_info:
                results = training_info["results"]
                gpu_metrics = get_gpu_metrics()
                
                metrics = TrainingMetrics(
                    job_name=args.job_name,
                    model_id=args.model_id,
                    method=args.method or "unknown",
                    current_epoch=training_info.get("training_config", {}).get("epochs", 0),
                    total_epochs=training_info.get("training_config", {}).get("epochs", 0),
                    current_step=0,
                    total_steps=0,
                    train_loss=results.get("train_loss", 0.0),
                    learning_rate=training_info.get("training_config", {}).get("learning_rate", 0.0),
                    gpu_utilization=gpu_metrics.get("gpu_utilization"),
                    gpu_memory_used=gpu_metrics.get("gpu_memory_used"),
                    gpu_memory_total=gpu_metrics.get("gpu_memory_total"),
                    samples_per_second=results.get("train_samples_per_second"),
                    tokens_per_second=None
                )
                
                exporter.update_training_metrics(metrics)
    
    # Keep server running
    try:
        while True:
            time.sleep(60)  # Update every minute
            # Could periodically update metrics here
    except KeyboardInterrupt:
        logger.info("Metrics server stopped")


if __name__ == "__main__":
    main()

