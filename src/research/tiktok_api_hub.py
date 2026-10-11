import json
import re
import requests
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://www.tiktok.com/',
    'Accept': 'application/json, text/plain, */*',
}

def query_video_full_api(video_input: str) -> dict:
    v_clean = video_input.strip()
    if 'tiktok.com' in v_clean:
        target_url = v_clean
    else:
        target_url = 'https://www.tiktok.com/@tiktok/video/' + v_clean

    try:
        api_url = 'https://www.tikwm.com/api/?url=' + target_url
        res = requests.get(api_url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            d = res.json()
            if d.get('code') == 0:
                data = d.get('data', {})
                return {
                    'status': 'success',
                    'video_id': data.get('id'),
                    'title': data.get('title'),
                    'author': data.get('author', {}),
                    'stats': {
                        'views': data.get('play_count', 0),
                        'likes': data.get('digg_count', 0),
                        'comments': data.get('comment_count', 0),
                        'shares': data.get('share_count', 0),
                    },
                    'media_download': {
                        'mp4_no_watermark': data.get('play'),
                        'music_mp3': data.get('music'),
                        'cover': data.get('cover'),
                    },
                    'raw_json': data,
                }
    except Exception as e:
        log.warning('TikWM error: %s', e)

    try:
        oembed_url = 'https://www.tiktok.com/oembed?url=' + target_url
        r = requests.get(oembed_url, timeout=8)
        if r.status_code == 200:
            od = r.json()
            return {
                'status': 'success_oembed',
                'title': od.get('title'),
                'author_unique_id': od.get('author_unique_id'),
                'author_name': od.get('author_name'),
                'thumbnail_url': od.get('thumbnail_url'),
                'raw_json': od,
            }
    except Exception as e:
        log.warning('oEmbed error: %s', e)

    return {'status': 'error', 'message': 'Không thể lấy thông tin video này'}

def query_comments_full_api(video_input: str, count: int = 50, cursor: int = 0) -> dict:
    v_clean = video_input.strip()
    match = re.search(r'/video/(\d+)', v_clean)
    vid_id = match.group(1) if match else v_clean.replace('@', '')

    # Cach 1: Goi truc tiep API comment TikTok
    try:
        api_url = f'https://www.tiktok.com/api/comment/list/?aweme_id={vid_id}&count={count}&cursor={cursor}&aid=1988'
        res = requests.get(api_url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            d = res.json()
            raw_list = d.get('comments', []) or []
            if raw_list:
                c_clean = []
                for c in raw_list:
                    c_clean.append({
                        'cid': c.get('cid'),
                        'user': c.get('user', {}).get('unique_id'),
                        'nickname': c.get('user', {}).get('nickname'),
                        'text': c.get('text'),
                        'likes': c.get('digg_count', 0),
                        'reply_count': c.get('reply_comment_total', 0),
                        'create_time': c.get('create_time', 0),
                    })
                return {
                    'status': 'success',
                    'video_id': vid_id,
                    'total_fetched': len(c_clean),
                    'cursor': d.get('cursor', 0),
                    'has_more': bool(d.get('has_more', 0)),
                    'comments': c_clean,
                    'raw_json': d,
                }
    except Exception as e:
        log.warning('TikTok comments API error: %s', e)

    # Cach 2: TikWM gateway
    try:
        target_url = v_clean if 'tiktok.com' in v_clean else f'https://www.tiktok.com/@tiktok/video/{vid_id}'
        api_url = f'https://www.tikwm.com/api/comment/list?url={target_url}&count={count}&cursor={cursor}'
        res = requests.get(api_url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            d = res.json()
            if d.get('code') == 0:
                raw_list = d.get('data', {}).get('comments', [])
                c_clean = []
                for c in raw_list:
                    c_clean.append({
                        'cid': c.get('cid') or c.get('id'),
                        'user': c.get('user', {}).get('unique_id'),
                        'nickname': c.get('user', {}).get('nickname'),
                        'text': c.get('text'),
                        'likes': c.get('digg_count', 0),
                    })
                return {
                    'status': 'success',
                    'video_id': vid_id,
                    'total_fetched': len(c_clean),
                    'comments': c_clean,
                    'raw_json': d,
                }
    except Exception as e:
        log.warning('TikWM comments error: %s', e)

    return {'status': 'error', 'message': 'Không thể tải bình luận cho video này'}

def query_comment_replies_api(video_input: str, comment_id: str = '', count: int = 20) -> dict:
    v_clean = video_input.strip()
    match = re.search(r'/video/(\d+)', v_clean)
    vid_id = match.group(1) if match else v_clean.replace('@', '')

    cid = comment_id.strip() if comment_id else ''
    if not cid:
        c_res = query_comments_full_api(vid_id, count=3)
        if c_res.get('status') == 'success' and c_res.get('comments'):
            cid = str(c_res['comments'][0].get('cid'))

    if not cid:
        return {'status': 'error', 'message': 'Cần cung cấp comment_id hoặc video hợp lệ có bình luận'}

    try:
        reply_url = f'https://www.tiktok.com/api/comment/list/reply/?item_id={vid_id}&comment_id={cid}&count={count}&cursor=0&aid=1988'
        res = requests.get(reply_url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            d = res.json()
            raw_replies = d.get('comments', []) or []
            replies = []
            for r in raw_replies:
                replies.append({
                    'reply_id': r.get('cid'),
                    'user': r.get('user', {}).get('unique_id'),
                    'nickname': r.get('user', {}).get('nickname'),
                    'text': r.get('text'),
                    'likes': r.get('digg_count', 0),
                })
            return {
                'status': 'success',
                'video_id': vid_id,
                'parent_comment_id': cid,
                'total_replies': len(replies),
                'replies': replies,
                'raw_json': d,
            }
    except Exception as e:
        log.warning('Replies error: %s', e)

    return {'status': 'error', 'message': f'Không thể lấy phản hồi cho comment {cid}'}

def query_user_profile_api(username_input: str) -> dict:
    clean_user = username_input.strip().replace('@', '').split('/')[0]
    profile_url = 'https://www.tiktok.com/@' + clean_user
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    try:
        r = requests.get(profile_url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tag = soup.find('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
            if tag and tag.string:
                d = json.loads(tag.string)
                u_info = d.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {}).get('userInfo', {})
                user = u_info.get('user', {})
                stats = u_info.get('stats', {})
                if user:
                    commerce = user.get('commerceUserInfo', {})
                    return {
                        'status': 'success',
                        'unique_id': user.get('uniqueId'),
                        'nickname': user.get('nickname'),
                        'bio': user.get('signature'),
                        'avatar': user.get('avatarLarger') or user.get('avatarMedium'),
                        'verified': user.get('verified', False),
                        'has_tiktok_shop': bool(commerce.get('commerceUser', False)),
                        'stats': {
                            'followers': stats.get('followerCount', 0),
                            'hearts': stats.get('heartCount', 0),
                            'videos': stats.get('videoCount', 0),
                            'following': stats.get('followingCount', 0),
                        },
                        'raw_json': u_info,
                    }
    except Exception as e:
        log.warning('User profile error: %s', e)
    return {'status': 'error', 'message': 'Không tìm thấy hồ sơ @' + clean_user}

def query_search_api(keyword: str, search_type: str = 'general') -> dict:
    clean_kw = keyword.strip()
    return {
        'status': 'info',
        'query': clean_kw,
        'search_type': search_type,
        'message': f'Đang truy vấn phân tích từ khoá TikTok #{clean_kw}',
        'tips': 'Sử dụng User Profile hoặc Item Detail để lấy toàn bộ dữ liệu thực thể tương ứng.',
    }

def query_live_room_api(room_id_or_user: str) -> dict:
    clean_val = room_id_or_user.strip().replace('@', '')
    return {
        'status': 'info',
        'target': clean_val,
        'message': f'Đã nhận diện phòng Live Stream {clean_val}',
        'api_endpoint': f'https://webcast.tiktok.com/webcast/room/info/?room_id={clean_val}',
    }
