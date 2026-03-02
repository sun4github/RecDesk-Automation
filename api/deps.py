# app/api/deps.py
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
from dotenv import load_dotenv

load_dotenv(override=True)

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    # In production, these should be loaded from environment variables
    correct_username = secrets.compare_digest(credentials.username, os.getenv("POSTMARK_USERNAME"))
    correct_password = secrets.compare_digest(credentials.password, os.getenv("POSTMARK_PASSWORD"))
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username