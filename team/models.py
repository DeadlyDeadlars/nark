from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class AdminLevel(enum.Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class StashType(enum.Enum):
    MAGNET = "magnet"
    STASH = "stash"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    is_admin = Column(Boolean, default=False)
    admin_level = Column(Enum(AdminLevel), nullable=True)
    is_worker = Column(Boolean, default=False)
    referred_by = Column(Integer, ForeignKey('users.telegram_id'), nullable=True)
    join_date = Column(DateTime, default=datetime.utcnow)
    city = Column(String, nullable=True)
    joined_from_info_bot = Column(Boolean, default=False)
    balance = Column(Float, default=0.0)
    is_banned = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    referrals = relationship('User', backref='referrer', remote_side=[telegram_id])
    payments = relationship('Payment', back_populates='user')
    actions = relationship('UserAction', back_populates='user')
    addresses = relationship('UserAddress', backref='user')

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    amount = Column(Float)
    status = Column(String)  # 'pending', 'completed', 'failed'
    payment_date = Column(DateTime, default=datetime.utcnow)
    payment_type = Column(String)  # card, crypto, balance
    commission = Column(Float)  # Commission amount
    
    user = relationship('User', back_populates='payments')

class UserAction(Base):
    __tablename__ = 'user_actions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    action_type = Column(String)  # 'button_click', 'command', etc.
    action_data = Column(String)  # JSON string with action details
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='actions')

class BotSettings(Base):
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String)  # Ключ настройки
    value = Column(String)  # Значение настройки
    description = Column(String)  # Описание настройки
    support = Column(String, nullable=True)  # Контакт поддержки
    operator = Column(String, nullable=True)  # Контакт оператора
    card_details = Column(String, nullable=True)  # Реквизиты для оплаты картой
    crypto_details = Column(String, nullable=True)  # Реквизиты для оплаты криптовалютой
    chat = Column(String, nullable=True)  # Ссылка на чат
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey('users.telegram_id'), nullable=True)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    percent = Column(Float)  # процент скидки
    max_activations = Column(Integer)
    activations = Column(Integer, default=0)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    product_name = Column(String)
    product_weight = Column(String)
    price = Column(Float)
    commission = Column(Float)
    total_price = Column(Float)
    district = Column(String)
    stash_type = Column(Enum(StashType))
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_method = Column(String)  # card, btc, usdt
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String, nullable=True)  # For admin notes 

class UserAddress(Base):
    __tablename__ = 'user_addresses'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    address = Column(String)
    description = Column(String, nullable=True)  # Описание адреса (например, "Дом", "Работа")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    weight = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    city = Column(String, nullable=False)
    district = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>" 

class PaymentMethod(Base):
    __tablename__ = 'payment_methods'
    
    id = Column(Integer, primary_key=True)
    type = Column(String)  # card, btc, usdt
    details = Column(String)  # card number or wallet address
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey('users.telegram_id'), nullable=True) 