"""User Service — manages user lifecycle."""
import hashlib
from typing import List
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import UserAlreadyExistsException, UserNotFoundException
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


def _hash_password(password: str) -> str:
    """Simple SHA-256 hash placeholder. Phase 6 replaces with bcrypt."""
    return hashlib.sha256(password.encode()).hexdigest()


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def create_user(self, data: UserCreate) -> User:
        if await self._repo.get_by_email(data.email):
            raise UserAlreadyExistsException("email", data.email)
        if await self._repo.get_by_username(data.username):
            raise UserAlreadyExistsException("username", data.username)

        user = User(
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            hashed_password=_hash_password(data.password),
            phone=data.phone,
            department=data.department,
        )
        user = await self._repo.create(user)
        logger.info("User created | id={id} | username={u}", id=user.id, u=user.username)
        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return user

    async def list_users(self, skip: int = 0, limit: int = 20) -> List[User]:
        return await self._repo.get_all(skip=skip, limit=limit)

    async def update_user(
        self, user_id: uuid.UUID, data: UserUpdate
    ) -> User:
        user = await self.get_user(user_id)
        if data.email and data.email != user.email:
            if await self._repo.get_by_email(data.email):
                raise UserAlreadyExistsException("email", data.email)
        update_data = data.model_dump(exclude_none=True)
        return await self._repo.update(user, update_data)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        user = await self.get_user(user_id)
        await self._repo.delete(user)
        logger.info("User deleted | id={id}", id=user_id)

    async def count_users(self) -> int:
        return await self._repo.count()
