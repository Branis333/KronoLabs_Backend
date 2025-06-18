from fastapi import Depends, HTTPException, status
from typing import Annotated
from Endpoints.auth import get_current_user, get_front_current_user
from db.connection import get_db
from models.users_models import User
from sqlalchemy.orm import Session


user_dependency = Annotated[dict, Depends(get_current_user)]
user_Front_dependency = Annotated[dict, Depends(get_front_current_user)]

async def verify_token(
    current_user: user_dependency,
    db: Session = Depends(get_db)
) -> User:
    """
    Verify token and return the User object from database
    """
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
