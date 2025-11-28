from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, Numeric, Boolean, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum
import uuid


class Base(DeclarativeBase):
    pass


class SessionStatus(enum.Enum):
    CREATING = "creating"  # Creator is setting up
    SELECTING = "selecting"  # Participants are choosing meals
    COMPLETED = "completed"  # Everyone confirmed


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"


class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_user_id: Mapped[int] = mapped_column(BigInteger)
    creator_username: Mapped[str] = mapped_column(String(255), nullable=True)
    creator_first_name: Mapped[str] = mapped_column(String(255))
    
    restaurant_name: Mapped[str] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    receipt_image_id: Mapped[str] = mapped_column(String(255))
    receipt_text: Mapped[str] = mapped_column(Text)
    
    card_number: Mapped[str] = mapped_column(String(20), nullable=True)
    participant_count: Mapped[int] = mapped_column(Integer, nullable=True)
    has_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # NEW: Calculated totals
    shared_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)  # Total of shared meals
    individual_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)  # Total of individual meals
    
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.CREATING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meals: Mapped[list["Meal"]] = relationship("Meal", back_populates="session", cascade="all, delete-orphan")
    participants: Mapped[list["SessionParticipant"]] = relationship("SessionParticipant", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session {self.id} - {self.restaurant_name}>"


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255))
    
    is_creator: Mapped[bool] = mapped_column(Boolean, default=False)
    is_delivery_person: Mapped[bool] = mapped_column(Boolean, default=False)
    has_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # NEW: Payment tracking
    payment_status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # NEW: Calculated amounts
    individual_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)  # User's individual meals
    shared_portion: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)  # User's share of shared meals
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)  # individual_total + shared_portion
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="participants")
    selections: Mapped[list["UserMealSelection"]] = relationship("UserMealSelection", back_populates="participant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Participant {self.first_name} - Session {self.session_id}>"


class Meal(Base):
    __tablename__ = "meals"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    quantity_available: Mapped[int] = mapped_column(Integer, default=1)
    
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    is_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="meals")
    selections: Mapped[list["UserMealSelection"]] = relationship("UserMealSelection", back_populates="meal", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Meal {self.name} - {self.price}>"


class UserMealSelection(Base):
    __tablename__ = "user_meal_selections"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey("meals.id", ondelete="CASCADE"))
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("session_participants.id", ondelete="CASCADE"))
    
    quantity_selected: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meal: Mapped["Meal"] = relationship("Meal", back_populates="selections")
    participant: Mapped["SessionParticipant"] = relationship("SessionParticipant", back_populates="selections")
    
    def __repr__(self):
        return f"<Selection Meal:{self.meal_id} Qty:{self.quantity_selected}>"