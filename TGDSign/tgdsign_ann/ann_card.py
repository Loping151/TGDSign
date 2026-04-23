"""公告卡片渲染"""
import json
import re
import time
import asyncio
from typing import List, Union
from datetime import datetime
from pathlib import Path

from PIL import Image

from gsuid_core.logger import logger
from gsuid_core.utils.image.convert import convert_img

from ..utils.api.requests import tgd_api
from ..utils.path import ANN_CACHE_PATH, ANN_RENDER_CACHE_PATH
from ..utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    get_image_b64_with_cache,
)
from ..utils.image import pic_download_from_url

from jinja2 import Environment, FileSystemLoader

TEMPLATE_PATH = Path(__file__).parent.parent / "templates"
tgd_templates = Environment(loader=FileSystemLoader(str(TEMPLATE_PATH)))

VIDEO_EXTS = (".mp4", ".webm", ".mov", ".avi", ".mkv", ".flv")


def format_date(ts) -> str:
    if not ts:
        return "未知"
    try:
        ts = int(ts)
        if ts <= 0:
            return "未知"
        if ts > 10000000000:
            ts = ts // 1000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "未知"


def format_date_short(ts) -> str:
    if not ts:
        return "未知"
    try:
        ts = int(ts)
        if ts <= 0:
            return "未知"
        if ts > 10000000000:
            ts = ts // 1000
        return datetime.fromtimestamp(ts).strftime("%m-%d")
    except Exception:
        return "未知"


def _build_vod_cover_map(vods: list) -> dict:
    vod_cover_map: dict[str, str] = {}
    for vod in vods or []:
        if not isinstance(vod, dict):
            continue
        cover_url = vod.get("cover", "")
        if isinstance(cover_url, dict):
            cover_url = cover_url.get("url", "")
        vod_url = vod.get("url", "")
        if vod_url and cover_url:
            vod_cover_map[vod_url] = cover_url
        for item in vod.get("items") or []:
            if isinstance(item, dict) and item.get("url") and cover_url:
                vod_cover_map[item["url"]] = cover_url
    return vod_cover_map


async def _bake_html_images(
    html: str,
    vods: list = None,
    long_image_urls: set = None,
) -> str:
    """把 HTML 里远程 <img src> 预下载并替换为 base64。
    - 视频 URL 替换为封面图
    - long_image_urls 中的超长图从 HTML 中移除（会单独发送）
    """
    vod_cover_map = _build_vod_cover_map(vods)

    img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html)
    if not img_tags:
        return html

    urls_to_fetch: list[str] = []
    for u in dict.fromkeys(img_tags):
        if long_image_urls and u in long_image_urls:
            html = re.sub(r'<img[^>]+src=["\']' + re.escape(u) + r'["\'][^>]*/?>', '', html)
            continue
        if u.lower().endswith(VIDEO_EXTS):
            cover = vod_cover_map.get(u, "")
            if cover:
                urls_to_fetch.append(cover)
                html = html.replace(u, cover)
            else:
                html = re.sub(r'<img[^>]+src=["\']' + re.escape(u) + r'["\'][^>]*/?>', '', html)
            continue
        urls_to_fetch.append(u)

    unique_fetch = list(dict.fromkeys(urls_to_fetch))

    async def _fetch(url):
        b64 = await get_image_b64_with_cache(url, ANN_CACHE_PATH)
        return url, b64

    results = await asyncio.gather(*[_fetch(u) for u in unique_fetch])
    for url, b64 in results:
        if b64:
            html = html.replace(url, b64)
    return html


async def ann_list_card() -> Union[bytes, str]:
    try:
        cache_file = ANN_RENDER_CACHE_PATH / "list.jpg"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < tgd_api.ANN_LIST_CACHE_DURATION:
                return cache_file.read_bytes()

        ann_list = await tgd_api.get_ann_list()
        if not ann_list:
            return "获取公告列表失败"

        ann_list = ann_list[:18]

        logger.info(f"[TGD][Ann] 并行下载 {len(ann_list)} 张封面")
        covers = await asyncio.gather(
            *[get_image_b64_with_cache(
                ann.get("cover", ""), ANN_CACHE_PATH,
                quality=60, cover_size=(400, 200),
            ) for ann in ann_list]
        )

        items = []
        for i, ann in enumerate(ann_list):
            items.append({
                "short_id": str(i + 1),
                "title": ann.get("subject") or "(无标题)",
                "date_str": format_date_short(ann.get("sendTime") or ann.get("createTime")),
                "coverB64": covers[i],
                "likeNum": ann.get("likeNum", 0),
                "commentNum": ann.get("commentNum", 0),
            })

        context = {
            "title": "异环公告",
            "subtitle": "使用 yh公告#序号 查看详情",
            "is_list": True,
            "items": items,
        }

        img_bytes = await render_html(tgd_templates, "tgd_ann_card.html", context)

        if img_bytes:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(img_bytes)
            return img_bytes
        return "公告列表渲染失败"

    except Exception as e:
        logger.exception(f"[TGD] 公告列表生成失败: {e}")
        return f"公告列表生成失败: {e}"


async def ann_detail_card(
    ann_id: Union[int, str],
    is_check_time: bool = False,
) -> Union[bytes, str, List[bytes]]:
    try:
        actual_id = str(ann_id)
        if isinstance(ann_id, int) or (isinstance(ann_id, str) and ann_id.isdigit()):
            idx = int(ann_id)
            if 1 <= idx <= 20:
                ann_list = await tgd_api.get_ann_list(is_cache=True)
                if ann_list and idx <= len(ann_list):
                    actual_id = str(ann_list[idx - 1].get("id", ann_id))

        cache_file = ANN_RENDER_CACHE_PATH / f"detail_{actual_id}.jpg"
        if not is_check_time and cache_file.exists():
            long_cache = ANN_RENDER_CACHE_PATH / f"detail_{actual_id}_long.json"
            if long_cache.exists():
                cached_bytes = cache_file.read_bytes()
                long_paths = json.loads(long_cache.read_text())
                result_images = [cached_bytes]
                for lp in long_paths:
                    p = Path(lp)
                    if p.exists():
                        result_images.append(await convert_img(Image.open(p)))
                return result_images
            return cache_file.read_bytes()

        detail = await tgd_api.get_ann_detail(actual_id)
        if not detail:
            return "未找到该公告"

        if is_check_time:
            ts = detail.get("sendTime") or detail.get("createTime") or 0
            if ts > 10000000000:
                ts = ts // 1000
            if ts < int(time.time()) - 86400:
                return "该公告已过期"

        vods = detail.get("vods") or []
        vod_cover_map = _build_vod_cover_map(vods)

        # 区分正常图和超长图
        images = detail.get("images") or []
        long_image_urls: set[str] = set()
        for img in images:
            w = img.get("width", 0)
            h = img.get("height", 0)
            url = img.get("url", "")
            if url.lower().endswith(VIDEO_EXTS):
                continue
            if w > 0 and h / w > 5:
                long_image_urls.add(url)

        raw_html = detail.get("content", "")
        baked_html = await _bake_html_images(raw_html, vods=vods, long_image_urls=long_image_urls)

        context = {
            "title": detail.get("subject") or "(无标题)",
            "post_time": format_date(detail.get("sendTime") or detail.get("createTime")),
            "like_num": detail.get("likeNum", 0),
            "comment_num": detail.get("commentNum", 0),
            "is_list": False,
            "content_html": baked_html,
        }

        img_bytes = await render_html(tgd_templates, "tgd_ann_card.html", context)

        result_images = []
        long_local_paths = []

        if long_image_urls:
            logger.info(f"[TGD] 检测到 {len(long_image_urls)} 张超长图片，将单独发送")
            for img_url in long_image_urls:
                try:
                    img = await pic_download_from_url(ANN_CACHE_PATH, img_url)
                    local_path = ANN_CACHE_PATH / img_url.split("/")[-1]
                    webp_path = local_path.with_suffix(".webp")
                    if webp_path.exists():
                        long_local_paths.append(str(webp_path))
                    elif local_path.exists():
                        long_local_paths.append(str(local_path))
                    img_bytes_long = await convert_img(img)
                    result_images.append(img_bytes_long)
                except Exception as e:
                    logger.warning(f"[TGD] 下载超长图片失败: {img_url}, {e}")

        if img_bytes:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(img_bytes)
            if long_local_paths:
                long_cache = ANN_RENDER_CACHE_PATH / f"detail_{actual_id}_long.json"
                long_cache.write_text(json.dumps(long_local_paths))

            if result_images:
                return [img_bytes] + result_images
            return img_bytes
        return "公告详情渲染失败"

    except Exception as e:
        logger.exception(f"[TGD] 公告详情生成失败: {e}")
        return f"公告详情生成失败: {e}"
