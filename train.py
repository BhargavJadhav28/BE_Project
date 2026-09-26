"""
Root runner for microgrid training pipeline.
Delegates to ml_service.train.
"""

from ml_service.train import run_training

if __name__ == "__main__":
    run_training()
