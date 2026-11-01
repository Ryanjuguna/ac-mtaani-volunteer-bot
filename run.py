import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 65)
    print("  AMERICAN CORNER MTAANI - VOLUNTEER TASK MANAGEMENT BOT")
    print(f"  Target Demo: Monday Showcase")
    print(f"  Trigger Tag: {settings.TASK_TRIGGER_TAG}")
    print(f"  Interactive Simulator: http://localhost:{settings.PORT}")
    print("=" * 65)
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
