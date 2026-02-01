import json

from sqlalchemy import ForeignKey, Text, delete, func, insert, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from . import AsyncSession, Base


# Users duh
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hash: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()


# Track data
class TrackMeta(Base):
    __tablename__ = "track_meta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column()
    artist: Mapped[str] = mapped_column()

    sources: Mapped[list["TrackSource"]] = relationship(
        back_populates="track_meta", cascade="all, delete-orphan"
    )

    @classmethod
    async def batch_get_or_create(cls, session: AsyncSession, artist_title_pairs):
        conditions = []
        for artist, title in artist_title_pairs:
            conditions.append((TrackMeta.artist == artist) & (TrackMeta.title == title))

        or_conditions = or_(*conditions)

        result = await session.execute(
            select(TrackMeta)
            .where(or_conditions)
            .options(selectinload(TrackMeta.sources))
        )
        existing_metas = result.scalars().all()

        metas_by_key = {(meta.artist, meta.title): meta for meta in existing_metas}

        new_metas = []
        for artist, title in artist_title_pairs:
            if (artist, title) not in metas_by_key:
                new_meta = TrackMeta(artist=artist, title=title)
                new_metas.append(new_meta)
                metas_by_key[(artist, title)] = new_meta

        if new_metas:
            session.add_all(new_metas)
            await session.flush()

        return metas_by_key


# Links a track from a specific source to our canonical metadata
class TrackSource(Base):
    __tablename__ = "track_source"

    source: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    track_meta_id: Mapped[int] = mapped_column(ForeignKey("track_meta.id"))

    track_meta: Mapped["TrackMeta"] = relationship(back_populates="sources")


# CACHE! cuz the spotify gotta be cached due to the long request times
class Cache(Base):
    __tablename__ = "cache"

    key: Mapped[str] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    updated_at: Mapped[int] = mapped_column(
        server_default=func.strftime("%s", "now"),
        onupdate=func.strftime("%s", "now"),
    )

    @classmethod
    async def get_content(cls, session: AsyncSession, type: str, id: str):
        cache = await session.get(Cache, f"{type}:{id}")
        if not cache:
            return None
        return json.loads(cache.content)

    @classmethod
    async def set_content(cls, session: AsyncSession, type: str, id: str, new_item):
        key = f"{type}:{id}"
        existing = await session.get(Cache, key)

        if existing:
            existing.type = type
            existing.content = json.dumps(new_item)
        else:
            session.add(
                Cache(
                    key=key,
                    content=json.dumps(new_item),
                )
            )

        await session.commit()

    @classmethod
    async def prune(cls, session: AsyncSession, max_age: int):
        await session.execute(
            delete(Cache).where(Cache.updated_at < func.strftime("%s", "now") - max_age)
        )
