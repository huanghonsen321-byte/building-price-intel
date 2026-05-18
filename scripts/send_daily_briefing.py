from app.core.database import SessionLocal
from app.services.notification_service import send_daily_briefing


def main() -> None:
    with SessionLocal() as db:
        result = send_daily_briefing(db, channel="mock", target="mock://cli")
        print(result.status)
        print(result.message)
        if result.error_message:
            print(result.error_message)


if __name__ == "__main__":
    main()
