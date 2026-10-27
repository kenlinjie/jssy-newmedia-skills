# -*- coding: utf-8 -*-
# 聚合分析：account_full_raw.json → report_data.json。缺失值保持 null，不转成 0。
import json
import os
import statistics
import sys
from collections import defaultdict

DIR = sys.argv[1] if len(sys.argv) > 1 else '.'
RAW = os.path.join(DIR, 'account_full_raw.json')
OUT = os.path.join(DIR, 'report_data.json')

with open(RAW, encoding='utf-8') as handle:
    data = json.load(handle)

works_all = [item for item in (data.get('works') or []) if isinstance(item, dict)]
works = [item for item in works_all if item.get('digg_count') is not None]
if not works:
    status = (data.get('capture') or {}).get('status', 'unknown')
    print(f'无可分析作品数据（capture.status={status}）；先解决采集阻塞，不生成误导报告。', file=sys.stderr)
    sys.exit(3)

profile = data.get('profile') or {}
capture = data.get('capture') or {}


def cnstr(value):
    if value is None:
        return '—'
    value = int(value)
    if value >= 100000000:
        return f'{value / 100000000:.1f}亿'
    if value >= 10000:
        return f'{value / 10000:.1f}万'
    return f'{value:,}'


def slim(item):
    keys = [
        'aweme_id', 'title', 'create_date', 'duration_s', 'digg_count',
        'comment_count', 'share_count', 'collect_count', 'cover',
        'mix_name', 'video_page',
    ]
    return {key: item.get(key) for key in keys}


def max_known(key):
    values = [item.get(key) for item in works_all if item.get(key) is not None]
    return max(values) if values else None


dates = sorted(item['create_date'] for item in works_all if item.get('create_date'))
if dates:
    span_lo, span_hi = dates[0], dates[-1]
    y0, m0 = int(span_lo[:4]), int(span_lo[5:7])
    y1, m1 = int(span_hi[:4]), int(span_hi[5:7])
    months = max(1, (y1 - y0) * 12 + (m1 - m0) + 1)
    span = f'{span_lo} ~ {span_hi}'
else:
    months, span = None, '—'

mix = defaultdict(lambda: [0, 0])
for item in works:
    key = item.get('mix_name') or '散篇'
    mix[key][0] += 1
    mix[key][1] += item['digg_count']
mix_groups = sorted(
    [
        {'name': key, 'count': values[0], 'sum': values[1], 'avg': round(values[1] / values[0])}
        for key, values in mix.items()
    ],
    key=lambda row: -row['avg'],
)

monthly = defaultdict(lambda: [0, 0, 0])
for item in works_all:
    if item.get('create_date'):
        month = item['create_date'][:7]
        monthly[month][0] += 1
        if item.get('digg_count') is not None:
            monthly[month][1] += item['digg_count']
            monthly[month][2] += 1
trend = [
    {
        'month': month,
        'count': monthly[month][0],
        'likes': monthly[month][1] if monthly[month][2] else None,
    }
    for month in sorted(monthly)
]

diggs = [item['digg_count'] for item in works]
expected = capture.get('expected_works')
if expected is None:
    expected = profile.get('aweme_count')
captured = len(works_all)
coverage = capture.get('coverage_ratio')
if coverage is None and expected:
    coverage = round(captured / expected, 4)
capture_status = capture.get('status') or ('complete' if captured == expected and expected else 'legacy_unknown')
complete = capture_status == 'complete'

if complete:
    caveat = f'采集状态：完整（接口 has_more=0）；采集 {captured} 条。单作品播放量网页端不公开。'
else:
    expected_text = f'，主页展示 {expected} 条' if expected is not None else ''
    caveat = f'采集状态：{capture_status}；当前仅采集 {captured} 条{expected_text}，结论只代表已采集样本。单作品播放量网页端不公开。'

output = {
    'account': {
        'nickname': profile.get('nickname') or '(未知)',
        'douyin_id': profile.get('douyin_id') or '',
        'sec_uid': data.get('sec_uid'),
        'homepage': f"https://www.douyin.com/user/{data.get('sec_uid')}",
        'followers_raw': profile.get('follower_count'),
        'followers': cnstr(profile.get('follower_count')),
        'total_likes_raw': profile.get('total_favorited'),
        'total_likes': cnstr(profile.get('total_favorited')),
        'profile_works_total': profile.get('aweme_count'),
        'captured_works': captured,
        'ip': profile.get('ip_location') or '—',
        'city': profile.get('city') or '—',
        'bio': profile.get('signature') or '',
    },
    'meta': {
        'captured_at': (data.get('captured_at') or '')[:10],
        'sample': captured,
        'analyzable_sample': len(works),
        'span': span,
        'caveat': caveat,
    },
    'quality': {
        'capture_status': capture_status,
        'capture_complete': complete,
        'profile_works_total': expected,
        'captured_works': captured,
        'analyzable_works': len(works),
        'coverage_ratio': coverage,
        'has_more': capture.get('has_more'),
        'warnings': ((capture.get('diagnostics') or {}).get('warnings') or []),
    },
    'stats': {
        'works': len(works),
        'months': months,
        'per_month': round(len(works) / months) if months else None,
        'likes_sum': sum(diggs),
        'likes_avg': round(statistics.mean(diggs)),
        'likes_median': round(statistics.median(diggs)),
        'likes_max': max(diggs),
        'comment_max': max_known('comment_count'),
        'share_max': max_known('share_count'),
        'collect_max': max_known('collect_count'),
        'v100': sum(1 for value in diggs if value >= 1000000),
        'v10': sum(1 for value in diggs if 100000 <= value < 1000000),
        'v1': sum(1 for value in diggs if 10000 <= value < 100000),
        'vlow': sum(1 for value in diggs if value < 10000),
    },
    'top_viral': [slim(item) for item in sorted(works, key=lambda value: -value['digg_count'])[:12]],
    'latest': [slim(item) for item in sorted(works_all, key=lambda value: value.get('create_time') or 0, reverse=True)[:12]],
    'collections': data.get('collections') or [],
    'mix_groups': mix_groups,
    'trend': trend,
}

temp = f'{OUT}.{os.getpid()}.tmp'
with open(temp, 'w', encoding='utf-8') as handle:
    json.dump(output, handle, ensure_ascii=False, indent=2)
os.replace(temp, OUT)

print(f"analyze: 样本{captured} 可分析{len(works)} 合集{len(output['collections'])} capture={capture_status} → report_data.json")
print(f"账号: {output['account']['nickname']} | 粉{output['account']['followers']} 赞{output['account']['total_likes']} | 最高赞{cnstr(output['stats']['likes_max'])}")
