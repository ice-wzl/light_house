from fastapi import APIRouter, Depends, HTTPException, Security
from typing import List
from datetime import datetime, timezone

# CORRECT imports when you're inside the 'server' package
from server_helper.user_helper import Users, UserRead, UserCreate, UserDelete
from server_helper.auth_helper import oauth2_scheme, verify_token
from server_helper.db import get_db, SessionLocal

router = APIRouter(prefix="/users", tags=["users"])

# PROTECTED endpoint to view all information about all users
@router.get("/", response_model=List[UserRead])
def read_users(
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    """
    Provide all the users that exist in the users table
    :param db: The active db connection
    :param token: The jwt authentication token provided during authentication
    :return users: The users from the user table in json format
    """
    verify_token(token)
    users = db.query(Users).all()
    return users


# PROTECTED endpoint to view all information about a user
@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    """
    Provide specific user by id that may or may not exist in the users table
    :param db: The active db connection
    :param token: The jwt authentication token provided during authentication
    :return user: The requested user or a 404 code
    """
    verify_token(token)
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# PROTECTED endpoint to delete a user
@router.delete("/delete/{user_id}", response_model=UserDelete)
def delete_user(
    user_id: int,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    """
    The user to delete from the users table by ID
    :param user_id: The user id to attempt to remove from the users table
    :param db: The active db connection
    :param token: The jwt authentication token provided during authentication
    :return UserDelete: The user to delete from the users table, or 404 status code
    """
    verify_token(token)
    db_user = db.query(Users).filter(Users.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return UserDelete(id=user_id)


# PROTECTED endpoint to create a new user
@router.post("/create", response_model=UserCreate)
def create_user(
    user: UserCreate,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    """
    Create a user in the users table via username and password
    :param user: The user to create via username and password
    :param db: The active db connection
    :param token: The jwt authentication token provided during authentication
    :return db_user: The users information that was added to the users table or a 400 status code
    """
    verify_token(token)
    existing_user = db.query(Users).filter(Users.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    if len(user.username) == 0:
        raise HTTPException(status_code=400, detail="Username cannot be blank")
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password cannot be less than 8 characters")
    user_data = user.model_dump(exclude={"created_at"})
    db_user = Users(**user_data, created_at=datetime.now(timezone.utc).isoformat())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
