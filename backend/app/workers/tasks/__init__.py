"""Tasks package."""
from app.workers.tasks import training, inference, evaluation

__all__ = ["training", "inference", "evaluation"]