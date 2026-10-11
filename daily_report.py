"""Generate and email a JobPilot report; schedule this script using cron or Task Scheduler."""
from dotenv import load_dotenv
from jobpilot import create_daily_report, mark_latest_report_sent, send_email


def main() -> None:
    load_dotenv()
    report = create_daily_report()
    print(report["content"])
    try:
        send_email(f"JobPilot AI Daily Report — {report['date']}", report["content"])
        mark_latest_report_sent()
        print("\nEmail report sent successfully.")
    except Exception as exc:
        print(f"\nEmail not sent: {exc}")
        print("The report was still saved to the local database.")


if __name__ == "__main__":
    main()
