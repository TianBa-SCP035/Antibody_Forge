import logging

from db.session import SessionLocal
from modules.immunology.serum.service import auto_update_status


def auto_update_status_job() -> None:
    db = SessionLocal()
    try:
        result = auto_update_status(db, {})
        logging.info("serum_auto_update_status result=%s", result)
    except Exception:
        db.rollback()
        logging.exception("serum_auto_update_status failed")
    finally:
        db.close()
