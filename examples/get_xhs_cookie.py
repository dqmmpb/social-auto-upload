import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.xhs_uploader.main import xhs_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookies" / "xhs_uploader" / "account.json")
    cookie_setup = asyncio.run(xhs_setup(str(account_file), handle=True))
