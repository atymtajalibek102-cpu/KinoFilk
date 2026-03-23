import os

def build_series_template():
    with open('templates/movie_detail.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Основные замены
    content = content.replace('movie.', 'serial.')
    content = content.replace('movie_id', 'series_id')
    content = content.replace('MOVIE_ID', 'SERIES_ID')
    content = content.replace('rateFilm', 'rateSeries')
    content = content.replace('/rate/', '/rate_series/')
    content = content.replace('О фильме', 'О сериале')
    content = content.replace('Похожие фильмы', 'Похожие сериалы')
    content = content.replace('movie-detail', 'series-detail')

    # Блок с эпизодами
    eps_html = """
                <h2 class="md-section-title" style="margin-top:40px;"><span></span>Сезоны и Серии</h2>
                <div class="seasons-container">
                    {% for season, eps in seasons_data.items() %}
                    <div style="margin-bottom:24px;">
                        <h3 style="color:#fff;font-size:18px;margin-bottom:12px;">Сезон {{ season }}</h3>
                        <div style="display:flex;flex-wrap:wrap;gap:10px;">
                            {% for ep in eps %}
                            <a href="/watch/series/{{ serial.id }}/{{ ep.id }}" style="padding:10px 16px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:8px;color:#fff;text-decoration:none;font-size:14px;transition:.2s;">
                                {{ ep.ep_num }}. {{ ep.title }}
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                    {% if not seasons_data %}
                    <p style="color:var(--text-muted)">Серии пока не добавлены.</p>
                    {% endif %}
                </div>
"""
    content = content.replace('<div class="md-details-col">', '<div class="md-details-col">\n' + eps_html)

    with open('templates/series_detail.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print("series_detail.html created successfully.")

if __name__ == '__main__':
    build_series_template()
