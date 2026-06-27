import asyncio

from app.services.auth_service import AuthService
from app.core.security import verify_password

async def main():
    email = "saniyamihani031@gmail.com"

    user = await AuthService.get_user_by_email(email)

    print("=" * 60)
    print("User found:", user is not None)

    if user is None:
        return

    print("ID:", user.id)
    print("Email:", user.email)
    print("Hash:", user.hashed_password)
    print("=" * 60)

    password = input("Enter your password: ")

    print("Password valid:",
          verify_password(password, user.hashed_password))

asyncio.run(main())