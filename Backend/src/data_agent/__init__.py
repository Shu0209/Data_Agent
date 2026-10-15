"""Data Agent package."""

def get_app():
    """Lazy load FastAPI app."""
    from data_agent.main import app
    return app

def main():
    """Main CLI entrypoint."""
    from data_agent.main import main as _main
    _main()

__all__ = ["get_app", "main"]
