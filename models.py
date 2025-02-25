from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)

    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Roles", back_populates="users")


class UserSessions(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)

    user = relationship("Users", backref="sessions")


class Roles(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, nullable=False, index=True)
    role_name = Column(String, nullable=False, unique=True, index=True)
    color_code = Column(String, index=True)

    users = relationship("Users", back_populates="role")

    permissions = relationship("RolePermission", back_populates="role")


class Pages(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, nullable=False, index=True)
    page_name = Column(String, nullable=False, index=True)
    page_url = Column(String, nullable=False, index=True)

    permissions = relationship("RolePermission", back_populates="page")


class RolePermission(Base):
    __tablename__ = "role_permission"
    id = Column(Integer, primary_key=True, nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)

    role = relationship("Roles", back_populates="permissions")
    page = relationship("Pages", back_populates="permissions")