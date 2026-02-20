import asyncio
from datetime import datetime
from app.core.timezone import get_cr_time
from pydantic import BaseModel

class TestM(BaseModel):
    dt: datetime

def main():
    now_cr = get_cr_time()
    print(f"Generated CR time: {now_cr} (tzinfo: {now_cr.tzinfo})")
    print("Pydantic JSON:", TestM(dt=now_cr).model_dump_json())

if __name__ == "__main__":
    main()
