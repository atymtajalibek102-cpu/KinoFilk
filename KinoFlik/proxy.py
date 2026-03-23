import re
import requests
from flask import Response, request, stream_with_context
from urllib.parse import urlparse, urljoin, quote
import urllib3

# Suppress insecure request warnings for proxying
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def setup_proxy(app):
    @app.route('/proxy/stream')
    def proxy_stream():
        url = request.args.get('url', '').strip()
        if not url: return 'No URL', 400

        # Список рефереров для обхода защиты
        referer_map = {
            'qazcdn.com': 'https://www.qazaqstan.tv/',
            'beetv.kz': 'https://beetv.kz/',
            'amagi.tv': 'https://www.samsung.com/',
            'wurl.tv': 'https://www.samsung.com/'
        }

        parsed = urlparse(url)
        referer = next((ref for dom, ref in referer_map.items() if dom in url), f"https://{parsed.netloc}/")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': referer,
            'Origin': referer.rstrip('/')
        }

        try:
            r = requests.get(url, headers=headers, timeout=10, stream=True, verify=False)
            
            # Если это плейлист (.m3u8), переписываем ссылки внутри него
            if 'm3u8' in url or 'mpegurl' in r.headers.get('Content-Type', '').lower():
                base_url = url.rsplit('/', 1)[0] + '/'
                lines = r.text.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith('#') and 'URI=' in line:
                        line = re.sub(r'URI="([^"]+)"', lambda m: f'URI="/proxy/stream?url={quote(urljoin(base_url, m.group(1)), safe="")}"', line)
                    elif line and not line.startswith('#'):
                        line = f'/proxy/stream?url={quote(urljoin(base_url, line), safe="")}'
                    new_lines.append(line)
                return Response('\n'.join(new_lines), content_type='application/vnd.apple.mpegurl')
            
            # Если это видео-сегмент (.ts), просто пробрасываем байты
            return Response(stream_with_context(r.iter_content(chunk_size=1024*64)), content_type=r.headers.get('Content-Type'))
        except Exception as e:
            return str(e), 502