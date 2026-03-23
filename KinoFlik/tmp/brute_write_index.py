
import os

filepath = r"c:\Users\ПК\Desktop\KinoFlik — копия\KinoFlik\templates\index.html"

content = """{% extends "base.html" %}

{% block title %}KinoFlik — Кино без рекламы{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/index.css') }}">
{% endblock %}

{% block content %}
<main>
    {% if movies %}
    <div class="hero-full" id="heroWrap">
        <div class="hero-bg" id="heroBg" style="background-image:url('{% if movies[0].poster %}/static/posters/{{ movies[0].poster }}{% endif %}');"></div>
        <div class="hero-trailer" id="heroTrailer">
            {% if movies[0].trailer_url %}
            {% set tu = movies[0].trailer_url %}
            {% if 'youtube.com/watch' in tu %}
            {% set vid = tu.split('v=')[-1].split('&')[0] %}
            <iframe id="heroIframe" src="https://www.youtube.com/embed/{{ vid }}?autoplay=1&mute=1&loop=1&playlist={{ vid }}&controls=0&rel=0" allow="autoplay; fullscreen"></iframe>
            {% elif 'youtu.be/' in tu %}
            {% set vid = tu.split('youtu.be/')[-1].split('?')[0] %}
            <iframe id="heroIframe" src="https://www.youtube.com/embed/{{ vid }}?autoplay=1&mute=1&loop=1&playlist={{ vid }}&controls=0" allow="autoplay; fullscreen"></iframe>
            {% else %}
            <iframe id="heroIframe" src="{{ tu }}" allow="autoplay; fullscreen"></iframe>
            {% endif %}
            {% endif %}
        </div>
        <div class="hero-overlay-gradient"></div>
        <button class="hero-sound-btn {% if movies[0].trailer_url %}vis{% endif %}" id="heroSoundBtn" onclick="toggleSound()">
            <i class="fas fa-volume-mute" id="heroSoundIcon"></i>
        </button>
        {% if movies|length > 1 %}
        <div class="hero-dots" id="heroDots">
            {% for m in movies[:6] %}
            <div class="hero-dot {% if loop.first %}active{% endif %}" onclick="heroGo('{{ loop.index0 }}')"></div>
            {% endfor %}
        </div>
        {% endif %}
        <div class="hero-content-wrapper">
            <div class="hero-text">
                <div class="hero-pretitle"><i class="fas fa-fire"></i>РЕКОМЕНДУЕМ</div>
                <h1 class="hero-title" id="heroTitle">{{ movies[0].title }}</h1>
                {% if movies[0].description %}
                <p class="hero-description" id="heroDesc">{{ movies[0].description[:150] }}{% if movies[0].description|length > 150 %}...{% endif %}</p>
                {% endif %}
                <div class="hero-meta-row" id="heroMeta">
                    {% if movies[0].year %}
                    <div class="hero-meta-item"><span class="meta-label">Год</span><span class="meta-value">{{ movies[0].year }}</span></div>
                    {% endif %}
                    {% if movies[0].rating %}
                    <div class="hero-meta-item"><span class="meta-label">Рейтинг</span><div class="hero-rating-badge"><i class="fas fa-star"></i> {{ movies[0].rating }}</div></div>
                    {% endif %}
                </div>
                <div class="hero-cta">
                    <button class="btn-large btn-play" onclick="location.href='/movie/{{ movies[0].id }}'"><i class="fas fa-play"></i>Смотреть</button>
                    <button class="btn-large btn-info" onclick="location.href='/movie/{{ movies[0].id }}'"><i class="fas fa-info-circle"></i>Подробнее</button>
                </div>
            </div>
        </div>
    </div>
    {% endif %}

    {% if continue_movies %}
    <div class="main-pad">
        <div class="section-block">
            <div class="section-head"><h2 class="section-title-big">▶ Продолжить просмотр</h2></div>
            <div class="continue-row">
                {% for w in continue_movies %}
                <a href="/movie/{{ w.id }}" class="movie-card" style="width: 220px; flex-shrink: 0;">
                    <div class="movie-poster-wrap">
                        <img src="{% if w.poster %}/static/posters/{{ w.poster }}{% else %}/static/img/no_poster.svg{% endif %}" class="movie-img">
                        <div class="movie-badge-top" style="bottom: 8px; top: auto; right: 8px;">{{ w.progress or 0 }}%</div>
                    </div>
                    <div class="movie-meta-bottom">
                        <div class="movie-title">{{ w.title }}</div>
                        <div class="continue-progress-bar"><div class="continue-progress-fill" style="width: {{ w.progress or 0 }}%"></div></div>
                    </div>
                </a>
                {% endfor %}
            </div>
        </div>
    </div>
    {% endif %}

    <div class="main-pad">
        <div class="section-block">
            <div class="section-head"><h2 class="section-title-big">🎬 Популярные фильмы</h2><a href="/movie" class="section-link">Все <i class="fas fa-arrow-right"></i></a></div>
            <div id="tmdb-grid"></div>
        </div>
    </div>

    <div class="main-pad">
        <div class="section-block">
            <div class="section-head"><h2 class="section-title-big">📺 Популярные сериалы</h2><a href="/series" class="section-link">Все <i class="fas fa-arrow-right"></i></a></div>
            <div id="tmdb-tv-grid"></div>
        </div>
    </div>
</main>
{% endblock %}

{% block extra_js %}
<script>
    window.__HERO_DATA = [
        {% for m in movies[:6] %}
        {
            id: {{ m.id | tojson }},
            title: {{ (m.title or "")|tojson }},
            desc: {{ (m.description or "")[:150]|tojson }},
            poster: {% if m.poster %}{{ ("/static/posters/" ~ m.poster)|tojson }}{% else %}null{% endif %},
            trailer: {{ (m.trailer_url or "")|tojson }},
            year: {{ (m.year or "")|tojson }},
            rating: {{ (m.rating or "")|tojson }},
            genre: {{ (m.genre.split(",")[0].strip() if m.genre else "")|tojson }}
        }{% if not loop.last %},{% endif %}
        {% endfor %}
    ];
</script>
<script src="{{ url_for('static', filename='js/index_page.js') }}"></script>
{% endblock %}"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Successfully wrote {len(content)} bytes to {filepath}")
