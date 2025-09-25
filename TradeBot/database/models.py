from __future__ import annotations
from typing import List, Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, Numeric, ForeignKey, JSON, UniqueConstraint, Text

class Base(DeclarativeBase):
    pass

class Symbol(Base):
    __tablename__ = "symbols"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)  #OANDA:EUR_USD
    display_symbol: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(String(256))

    candles: Mapped[List["Candle"]] = relationship(back_populates="symbol", cascade="all, delete-orphan")

class Candle(Base):
    __tablename__ = "candles"
    # symbol_id, resolution, ts
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), primary_key=True)
    resolution: Mapped[str] = mapped_column(String(8), primary_key=True)   # 1,5,15,30,60,D,W,M
    ts: Mapped[int] = mapped_column(BigInteger, primary_key=True)          # Unix seconds (int)

    open: Mapped[Optional[float]] = mapped_column(Numeric(18, 8))
    high: Mapped[Optional[float]] = mapped_column(Numeric(18, 8))
    low:  Mapped[Optional[float]] = mapped_column(Numeric(18, 8))
    close:Mapped[Optional[float]] = mapped_column(Numeric(18, 8))
    volume:Mapped[Optional[float]] = mapped_column(Numeric(28, 8))

    symbol: Mapped["Symbol"] = relationship(back_populates="candles")


class NewsEvent(Base):
    __tablename__ = "news_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)   # forexfactory / investing / finnhub / ...
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)       # Unix seconds (UTC)
    title: Mapped[str] = mapped_column(String(256), nullable=False)

    importance: Mapped[int] = mapped_column(Integer, nullable=False)              # 1=Low, 2=Medium, 3=High
    body: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(String(32))                    # US/DE/...
    currency: Mapped[Optional[str]] = mapped_column(String(16))                   # USD/EUR/...
    category: Mapped[Optional[str]] = mapped_column(String(64))                   # NFP, CPI, PMI
    url: Mapped[Optional[str]] = mapped_column(String(512)) 
    source_event_id: Mapped[Optional[str]] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("source", "ts", "title", name="uq_news_source_ts_title"),
    )
