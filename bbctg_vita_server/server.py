import uvicorn

from core.config import get_settings
from main import create_app

app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
