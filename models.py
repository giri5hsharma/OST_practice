#DATABASE MODELS --> TABLES

from __future__ import annotations
from datetime import UTC, datetime # timestamps
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

class User(Base):
    __tablename__ = "users"

    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True) #typeend for ide, mapped_column defines actual column
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False) #nullable makes it a required field
    image_file: Mapped[str | None ] =mapped_column(
        String(20), 
        nullable=True, 
        default=None
    )

    #USING POST BEFORE CREATING --> FORWARD REFERENCE

    posts:Mapped[list[Post]] =relationship(
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin",
    ) #creates a 1 to many relationship. 
    #back populates allows us to access the user from the post and vice versa. 
    #relationship is a function that takes the name of the class we are relating to. 
    # in this case, we are relating to the Post class. we can access the posts of a user by calling user.posts. we can access the author of a post by calling post.author.

    @property
    def image_path(self) ->str:
        profile_image = (
            Path(__file__).resolve().parent
            / "media"
            / "profile_pics"
            / self.image_file
            if self.image_file
            else None
        )
        if profile_image and profile_image.is_file():
            return f"/media/profile_pics/{self.image_file}"
        return "/static/profile_pics/default.jpg" # makes deployments easier since we don't have to worry about the path to the image file
    
class Post(Base):
    __tablename__="posts"

    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title:Mapped[str] = mapped_column(String(30), nullable=False)
    content:Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int]= mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC)
    ) #default is the current time in UTC

    author:Mapped[User] = relationship(
        back_populates="posts",
        lazy="selectin",
    ) #creates a many to 1 relationship. we can access the author of a post by calling post.author. we can access the posts of a user by calling user.posts.