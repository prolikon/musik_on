from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import AsyncSession, Base


class TrackMeta(Base):
    __tablename__ = "track_meta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column()
    artist: Mapped[str] = mapped_column()

    sources: Mapped[list["TrackSource"]] = relationship(
        back_populates="track_meta", cascade="all, delete-orphan"
    )

    @classmethod
    async def get_or_create(
        cls, session: AsyncSession, artist: str, title: str
    ) -> "TrackMeta":
        # Select
        stmt = select(cls).where(cls.artist == artist, cls.title == title)
        result = await session.scalar(stmt)
        # Return existing TrackMeta
        if result:
            return result
        # Create and return new TrackMeta
        obj = cls(artist=artist, title=title)
        session.add(obj)
        return obj


# Links a track from a specific source to our canonical metadata
class TrackSource(Base):
    __tablename__ = "track_source"

    source: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    track_meta_id: Mapped[int] = mapped_column(ForeignKey("track_meta.id"))

    track_meta: Mapped["TrackMeta"] = relationship(back_populates="sources")
