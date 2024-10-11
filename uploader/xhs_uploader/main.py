# -*- coding: utf-8 -*-
import json
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from xhs import XhsClient

from uploader.xhs_uploader.util import sign_local
from utils.base_social_media import set_init_script
from utils.log import xhs_logger


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/publish/publish")
        try:
            await page.wait_for_selector("div.footer div.links a:text('关于小红书')", timeout=5000)  # 等待5秒

            xhs_logger.info("[+] 等待5秒 cookie 失效")
            return False
        except:
            xhs_logger.success("[+] cookie 有效")
            return True


async def xhs_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        xhs_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await xhs_cookie_gen(account_file)
    return True


async def xhs_cookie_gen(account_file):
    async with async_playwright() as playwright:
        options = {
            'headless': False
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://www.xiaohongshu.com/")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)

        await page.goto("https://creator.xiaohongshu.com/publish/publish?source=official")
        # await page.pause()
        await page.wait_for_selector("div.publish-video a.btn:text('发布笔记')", timeout=5000)  # 等待5秒
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
    except json.JSONDecodeError:
        print(f"文件 {file_path} 不是有效的 JSON 格式。")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")


class XhsVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.thumbnail_path = thumbnail_path

    async def upload(self, playwright: Playwright) -> None:
        config = read_json_file(self.account_file)
        print(config)
        # 提取 cookies 并构建 cookie 字符串
        cookies = ";".join([f"{cookie['name']}={cookie['value']}" for cookie in config['cookies'] if cookie['domain'] in ['creator.xiaohongshu.com', 'www.xiaohongshu.com', '.xiaohongshu.com']])
        print(cookies)
        xhs_client = XhsClient(cookies, sign=sign_local, timeout=60)
        # auth cookie
        # 注意：该校验cookie方式可能并没那么准确
        try:
            xhs_client.get_video_first_frame_image_id("3214")
        except:
            print("cookie 失效")
            exit()

        # 加入到标题 补充标题（xhs 可以填1000字不写白不写）
        tags_str = ' '.join(['#' + tag for tag in self.tags])
        hash_tags = []

        topics = []
        # 获取hashtag
        loop = asyncio.get_event_loop()
        for i in self.tags[:3]:
            topic_official = await loop.run_in_executor(None, xhs_client.get_suggest_topic, i)
            if topic_official:
                topic_official[0]['type'] = 'topic'
                topic_one = topic_official[0]
                hash_tag_name = topic_one['name']
                hash_tags.append(hash_tag_name)
                topics.append(topic_one)

        hash_tags_str = ' ' + ' '.join(['#' + tag + '[话题]#' for tag in hash_tags])

        print(f"hash_tags_str：{hash_tags_str}")

        publish_date = datetime.now()

        if self.publish_date != 0:
            publish_date = self.publish_date

        note = await loop.run_in_executor(None, xhs_client.create_video_note,
                                          self.title[:20],
                                          str(self.file_path),
                                          self.title + tags_str + hash_tags_str,
                                          None,
                                          None,
                                          publish_date.strftime("%Y-%m-%d %H:%M:%S"),
                                          topics,
                                          False,
                                          3)

        print(f"note：{note}")

        # beauty_print(note)
        # 强制休眠30s，避免风控（必要）
        # await asyncio.sleep(30)

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

