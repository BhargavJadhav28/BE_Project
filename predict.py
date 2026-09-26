"""
Root runner for microgrid predict CLI.
Delegates to ml_service.predict.
"""

from ml_service.predict import main

if __name__ == "__main__":
    main()
