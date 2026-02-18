import sys
import os
from datetime import timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core.security import create_access_token

def generate_long_lived_token():
    email = "admin@lavete.com" # Or make it an argument
    role = "admin"
    
    # payload matches what auth endpoint uses
    access_token_expires = timedelta(days=3650) # 10 years
    access_token = create_access_token(
        data={"sub": email, "role": role},
        expires_delta=access_token_expires
    )
    print(f"Generated Token for {email} (Expires in 10 years):")
    print("-" * 20)
    print(access_token)
    print("-" * 20)

if __name__ == "__main__":
    generate_long_lived_token()
