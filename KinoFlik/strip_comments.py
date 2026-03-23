"""Удаляет комментарии из Python файлов"""
import re, sys, tokenize, io

def strip_comments_from_py(source):
    tokens = []
    try:
        reader = io.StringIO(source).readline
        for tok in tokenize.generate_tokens(reader):
            if tok.type == tokenize.COMMENT:
                continue
            tokens.append(tok)
        return tokenize.untokenize(tokens)
    except Exception:
        return source

def strip_js_comments(code):
    result = []
    i = 0
    n = len(code)
    while i < n:
        if code[i] == '/' and i + 1 < n:
            if code[i+1] == '/':
                while i < n and code[i] != '\n':
                    i += 1
                continue
            elif code[i+1] == '*':
                i += 2
                while i < n - 1 and not (code[i] == '*' and code[i+1] == '/'):
                    i += 1
                i += 2
                continue
        if code[i] in ('"', "'", '`'):
            q = code[i]
            result.append(code[i])
            i += 1
            while i < n:
                if code[i] == '\\':
                    result.append(code[i:i+2])
                    i += 2
                    continue
                result.append(code[i])
                if code[i] == q:
                    i += 1
                    break
                i += 1
            continue
        result.append(code[i])
        i += 1
    cleaned = ''.join(result)
    import re
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned

def strip_html_comments(code):
    return re.sub(r'\n?\s*<!--(?!\[if)[\s\S]*?-->', '', code)

files_py = ['app.py', 'manage.py', 'create_db.py']
files_js = ['static/js/script.js', 'static/js/kp_features.js']
files_html = [
    'templates/base.html', 'templates/index.html',
    'templates/movie.html', 'templates/movie_detail.html',
    'templates/series.html', 'templates/404.html',
    'templates/login.html', 'templates/profile.html',
    'templates/admin.html',
]

for f in files_py:
    try:
        code = open(f, encoding='utf-8').read()
        cleaned = strip_comments_from_py(code)
        open(f, 'w', encoding='utf-8').write(cleaned)
        print(f'PY OK: {f}')
    except Exception as e:
        print(f'PY ERR {f}: {e}')

for f in files_js:
    try:
        code = open(f, encoding='utf-8').read()
        cleaned = strip_js_comments(code)
        open(f, 'w', encoding='utf-8').write(cleaned)
        print(f'JS OK: {f}')
    except Exception as e:
        print(f'JS ERR {f}: {e}')

for f in files_html:
    try:
        code = open(f, encoding='utf-8').read()
        cleaned = strip_html_comments(code)
        open(f, 'w', encoding='utf-8').write(cleaned)
        print(f'HTML OK: {f}')
    except Exception as e:
        print(f'HTML ERR {f}: {e}')
