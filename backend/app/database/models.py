from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database.database import Base


# --------------------------------------------------
# Meeting Request Model
# --------------------------------------------------

class MeetingRequest(Base):

    __tablename__ = "meeting_requests"

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # --------------------------------------------------
    # Unique Request ID
    # --------------------------------------------------

    request_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    # --------------------------------------------------
    # Original User Request
    # --------------------------------------------------

    user_input = Column(
        Text,
        nullable=False
    )

    # --------------------------------------------------
    # Request Status
    # --------------------------------------------------

    status = Column(
        String,
        nullable=False,
        default="processing"
    )

    # --------------------------------------------------
    # Request Creation Time
    # --------------------------------------------------

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # --------------------------------------------------
    # Request Completion Time
    # --------------------------------------------------

    completed_at = Column(
        DateTime,
        nullable=True
    )

    # --------------------------------------------------
    # Error Message
    # --------------------------------------------------

    error_message = Column(
        Text,
        nullable=True
    )