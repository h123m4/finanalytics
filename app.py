import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
from datetime import datetime

# ==================== НОРМАЛИЗАЦИЯ ДАННЫХ ====================
COLUMN_ALIASES = {
    'Период': ['Период', 'Месяц', 'Дата', 'Период.1'],
    'Выручка': ['Выручка', 'Выручка, руб', 'Выручка, руб.', 'Сумма продаж', 'Доходы'],
    'Себестоимость': ['Себестоимость', 'Себестоимость продаж', 'Себестоимость, руб', 'Расходы на производство'],
    'Оборотные активы': ['Оборотные активы', 'Текущие активы'],
    'Краткосрочные обязательства': ['Краткосрочные обязательства', 'Краткосрочные пассивы', 'Текущие обязательства'],
    'Запасы': ['Запасы', 'Товарные запасы'],
    'Дебиторская задолженность': ['Дебиторская задолженность', 'Дебиторка'],
    'Кредиторская задолженность': ['Кредиторская задолженность', 'Кредиторка'],
    'Денежные средства': ['Денежные средства', 'Деньги', 'Остаток ДС'],
    'Коммерческие расходы': ['Коммерческие расходы', 'Расходы на продажу'],
    'Управленческие расходы': ['Управленческие расходы', 'Административные расходы']
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for candidate in aliases:
            if candidate in df.columns and canonical not in df.columns:
                renamed[candidate] = canonical
                break
    return df.rename(columns=renamed)


def add_calculated_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if 'Выручка' in df.columns and 'Себестоимость' in df.columns:
        df['Валовая прибыль'] = df['Выручка'] - df['Себестоимость']
        df['Рентабельность (%)'] = ((df['Выручка'] - df['Себестоимость']) / df['Выручка']) * 100
        df['Доля затрат (%)'] = (df['Себестоимость'] / df['Выручка']) * 100

    if 'Оборотные активы' in df.columns and 'Краткосрочные обязательства' in df.columns:
        df['Ликвидность'] = df['Оборотные активы'] / df['Краткосрочные обязательства']

    if 'Дебиторская задолженность' in df.columns and 'Выручка' in df.columns:
        df['Дней дебиторки'] = (df['Дебиторская задолженность'] / df['Выручка']) * 365

    if 'Кредиторская задолженность' in df.columns and 'Себестоимость' in df.columns:
        df['Дней кредиторки'] = (df['Кредиторская задолженность'] / df['Себестоимость']) * 365

    if 'Запасы' in df.columns and 'Себестоимость' in df.columns:
        df['Дней запасов'] = (df['Запасы'] / df['Себестоимость']) * 365

    if 'Коммерческие расходы' in df.columns and 'Управленческие расходы' in df.columns and 'Выручка' in df.columns:
        df['Операционная маржа (%)'] = (
            (df['Выручка'] - df['Себестоимость'] - df['Коммерческие расходы'] - df['Управленческие расходы'])
            / df['Выручка']
        ) * 100
    return df

# ==================== НАСТРОЙКА СТРАНИЦЫ ====================
st.set_page_config(
    page_title="Финансовый анализ ФХД", 
    layout="wide", 
    page_icon="📈",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# ==================== СКРЫВАЕМ КНОПКИ STREAMLIT ====================
st.markdown("""
<style>
    /* Скрываем кнопку Deploy */
    .stAppDeployButton {
        display: none;
    }
    
    /* Скрываем меню с тремя точками */
    header[data-testid="stHeader"] {
        display: none;
    }
    
    /* Скрываем стандартный footer */
    footer {
        display: none;
    }
    
    /* Скрываем кнопку "Manage app" */
    .stActionButton {
        display: none;
    }
    
    /* Скрываем иконки в шапке */
    [data-testid="stToolbar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CSS СТИЛИ ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Marck+Script&family=Montserrat:ital,wght@0,400;0,600;0,700;1,500;1,700&display=swap');

    :root {
        --itf-blue-900: #0a2d5c;
        --itf-blue-800: #1b5ea8;
        --itf-blue-700: #2a87c8;
        --itf-cyan: #6fe2f5;
        --itf-accent: #f4bf64;
        --itf-bg: #e9f4ff;
        --itf-surface: #ffffff;
        --itf-border: #c8dff3;
        --itf-text: #173052;
        --itf-muted: #4f6f93;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 14%, rgba(111, 226, 245, 0.45) 0%, rgba(111, 226, 245, 0) 28%),
            radial-gradient(circle at 88% 6%, rgba(74, 146, 223, 0.3) 0%, rgba(74, 146, 223, 0) 35%),
            linear-gradient(180deg, #dff1ff 0%, #edf8ff 45%, #f4fbff 100%);
        color: var(--itf-text);
    }

    .main .block-container {
        max-width: 1180px;
        padding-top: 0;
        padding-bottom: 2rem;
    }

    .custom-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        width: 100vw;
        z-index: 999;
        padding: 0.72rem 1.15rem;
        box-sizing: border-box;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        color: white;
        border-bottom: 1px solid rgba(182, 225, 255, 0.45);
        box-shadow: 0 14px 28px rgba(17, 56, 98, 0.24), inset 0 1px 0 rgba(255,255,255,0.36);
        backdrop-filter: blur(8px) saturate(120%);
        background:
            radial-gradient(circle at 88% 12%, rgba(178, 233, 255, 0.42) 0%, rgba(178, 233, 255, 0) 18%),
            radial-gradient(circle at 80% 56%, rgba(120, 205, 247, 0.36) 0%, rgba(120, 205, 247, 0) 34%),
            linear-gradient(120deg, rgba(5, 35, 78, 0.95) 0%, rgba(15, 85, 146, 0.92) 58%, rgba(21, 134, 194, 0.84) 100%);
        overflow: hidden;
    }

    .custom-header::after {
        content: "";
        position: absolute;
        right: -8%;
        bottom: -16px;
        width: 58%;
        height: 120px;
        pointer-events: none;
        opacity: 0.72;
        background:
            radial-gradient(95% 72% at 62% 48%, rgba(214, 246, 255, 0.42) 0%, rgba(214, 246, 255, 0) 68%),
            linear-gradient(160deg, rgba(187, 240, 255, 0) 0%, rgba(187, 240, 255, 0.62) 42%, rgba(255,255,255,0) 84%);
        transform: rotate(-6deg);
    }

    .content-wrapper {
        margin-top: 66px;
        flex: 1;
        padding: 0 6px;
    }

    .logo-area {
        display: flex;
        align-items: center;
        gap: 14px;
        width: min(1180px, 100%);
        margin: 0 auto;
    }

    .logo-text h1 {
        margin: 0;
        font-family: 'Marck Script', cursive;
        font-size: clamp(1.9rem, 3vw, 2.8rem);
        font-weight: 400;
        line-height: 0.95;
        letter-spacing: 0.3px;
        color: white;
        text-shadow: 0 2px 12px rgba(9, 39, 76, 0.45);
    }

    .logo-text p {
        margin: 0.26rem 0 0;
        font-family: 'Montserrat', sans-serif;
        font-size: clamp(0.78rem, 1.15vw, 1rem);
        font-style: italic;
        font-weight: 500;
        line-height: 1.25;
        color: #eef8ff;
        opacity: 0.98;
        max-width: 620px;
    }

    .hero-aero {
        background:
            linear-gradient(155deg, rgba(255,255,255,0.66) 0%, rgba(255,255,255,0.34) 100%);
        border: 1px solid rgba(171, 214, 241, 0.75);
        border-radius: 14px;
        padding: 0.95rem;
        margin-top: -6px;
        margin-bottom: 0.75rem;
        box-shadow: 0 10px 24px rgba(34, 95, 150, 0.12), inset 0 1px 0 rgba(255,255,255,0.8);
    }

    .hero-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 10px;
    }

    .hero-tile {
        background: rgba(255,255,255,0.75);
        border: 1px solid rgba(177, 217, 244, 0.92);
        border-radius: 12px;
        overflow: hidden;
    }

    .hero-tile img {
        width: 100%;
        height: 120px;
        object-fit: cover;
        display: block;
    }

    .hero-tile p {
        margin: 0;
        padding: 0.45rem 0.6rem 0.55rem;
        color: var(--itf-blue-900);
        font-size: 0.76rem;
        font-weight: 600;
    }

    .upload-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(245,252,255,0.86) 100%);
        border: 1px solid var(--itf-border);
        border-top: 3px solid var(--itf-blue-700);
        border-radius: 12px;
        padding: 1rem 1rem;
        text-align: left;
        margin-bottom: 0.8rem;
        box-shadow: 0 8px 20px rgba(29, 56, 91, 0.09), inset 0 1px 0 rgba(255,255,255,0.8);
    }

    .upload-card h3 {
        color: var(--itf-blue-900);
        margin-bottom: 0.35rem;
        font-weight: bold;
        font-size: 1.1rem;
    }

    .upload-card p {
        color: var(--itf-muted);
        margin-bottom: 0.2rem;
        font-size: 0.88rem;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(241,249,255,0.9) 100%);
        border: 1px solid var(--itf-border);
        border-radius: 9px;
        padding: 0.42rem 0.56rem;
        box-shadow: 0 5px 14px rgba(21, 46, 78, 0.07);
    }

    [data-testid="stMetricLabel"] {
        color: var(--itf-muted);
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--itf-blue-900);
        font-weight: 700;
    }

    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--itf-blue-900);
        margin: 0.55rem 0 0.35rem;
        padding: 0.35rem 0.62rem;
        border-left: 3px solid var(--itf-accent);
        background: rgba(255, 255, 255, 0.72);
        border-radius: 0 8px 8px 0;
    }

    .stAlert {
        border-radius: 8px;
        border: 1px solid var(--itf-border);
    }

    .stDownloadButton > button,
    a[download] {
        border-radius: 8px !important;
    }

    [data-testid="stFileUploader"] {
        max-width: 320px;
        margin: 0.45rem 0 0.1rem;
    }

    [data-testid="stFileUploaderDropzone"] {
        min-height: auto;
        padding: 0;
        border-radius: 0;
        border: none;
        background: transparent;
        box-shadow: none;
    }

    [data-testid="stFileUploader"] button {
        border: 1px solid #9cd0f3 !important;
        border-radius: 10px !important;
        background: linear-gradient(180deg, #ffffff 0%, #dff4ff 100%) !important;
        color: #0d3f71 !important;
        font-weight: 700 !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        animation: uploadGlow 2.5s ease-in-out infinite;
    }

    [data-testid="stFileUploader"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(42, 134, 199, 0.24);
    }

    @keyframes uploadGlow {
        0% { box-shadow: 0 0 0 0 rgba(97, 189, 238, 0.45); }
        70% { box-shadow: 0 0 0 8px rgba(97, 189, 238, 0); }
        100% { box-shadow: 0 0 0 0 rgba(97, 189, 238, 0); }
    }

    .data-guide {
        max-width: 860px;
        margin: 0.35rem 0 0.45rem;
        padding: 0.8rem 1rem;
        border-radius: 12px;
        border: 1px solid rgba(154, 206, 241, 0.85);
        background:
            radial-gradient(circle at 95% 12%, rgba(192, 240, 255, 0.4) 0%, rgba(192, 240, 255, 0) 28%),
            linear-gradient(145deg, rgba(255,255,255,0.9) 0%, rgba(231,246,255,0.86) 100%);
        box-shadow: 0 8px 20px rgba(30, 93, 151, 0.1), inset 0 1px 0 rgba(255,255,255,0.7);
    }

    .data-guide h4 {
        margin: 0 0 0.35rem;
        color: #0d3a68;
        font-size: 1rem;
    }

    .data-guide p {
        margin: 0.18rem 0;
        color: #32597f;
        font-size: 0.86rem;
    }

    .rec-card {
        border-radius: 10px;
        margin: 0.2rem 0;
        padding: 0.48rem 0.58rem;
        border: 1px solid rgba(201, 217, 233, 0.9);
        box-shadow: 0 6px 14px rgba(19, 55, 92, 0.08);
        background-size: cover;
        background-position: center;
        position: relative;
        overflow: hidden;
        min-height: 255px;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .rec-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background: rgba(255, 255, 255, 0.55);
        z-index: 0;
    }
    .rec-card > * {
        position: relative;
        z-index: 1;
    }
    .rec-title {
        font-weight: 700;
        font-size: 1.11rem;
        margin-bottom: 0.16rem;
        color: #12385f;
    }
    .rec-text {
        font-size: 1rem;
        color: #234e77;
        line-height: 1.22;
        margin: 0.06rem 0;
        overflow-wrap: anywhere;
    }
    .rec-critical {
        border-left: 4px solid #b72828;
        background-image:
            linear-gradient(125deg, rgba(255, 244, 244, 0.88) 0%, rgba(255, 235, 235, 0.84) 100%),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 700'%3E%3Crect width='1200' height='700' fill='%23fff5f5'/%3E%3Cg stroke='%23ef9a9a' stroke-width='1'%3E%3Cpath d='M0 100h1200M0 200h1200M0 300h1200M0 400h1200M0 500h1200M0 600h1200'/%3E%3Cpath d='M100 0v700M250 0v700M400 0v700M550 0v700M700 0v700M850 0v700M1000 0v700M1150 0v700'/%3E%3C/g%3E%3Cpolyline points='60,130 180,170 300,210 420,260 540,320 660,390 780,460 900,520 1040,600 1140,650' fill='none' stroke='%23c62828' stroke-width='10' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    }
    .rec-high {
        border-left: 4px solid #d8582e;
        background-image:
            linear-gradient(125deg, rgba(255, 247, 240, 0.88) 0%, rgba(255, 239, 226, 0.84) 100%),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 700'%3E%3Crect width='1200' height='700' fill='%23fff8f2'/%3E%3Cg stroke='%23f7b58e' stroke-width='1'%3E%3Cpath d='M0 100h1200M0 200h1200M0 300h1200M0 400h1200M0 500h1200M0 600h1200'/%3E%3Cpath d='M100 0v700M250 0v700M400 0v700M550 0v700M700 0v700M850 0v700M1000 0v700M1150 0v700'/%3E%3C/g%3E%3Cpolyline points='60,340 180,320 300,360 420,350 540,390 660,370 780,420 900,410 1040,445 1140,430' fill='none' stroke='%23ef6c00' stroke-width='10' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    }
    .rec-medium {
        border-left: 4px solid #d39a2a;
        background-image:
            linear-gradient(125deg, rgba(255, 250, 240, 0.9) 0%, rgba(255, 245, 224, 0.85) 100%),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 700'%3E%3Crect width='1200' height='700' fill='%23fffbf2'/%3E%3Cg stroke='%23efd798' stroke-width='1'%3E%3Cpath d='M0 100h1200M0 200h1200M0 300h1200M0 400h1200M0 500h1200M0 600h1200'/%3E%3Cpath d='M100 0v700M250 0v700M400 0v700M550 0v700M700 0v700M850 0v700M1000 0v700M1150 0v700'/%3E%3C/g%3E%3Cpolyline points='60,360 180,345 300,365 420,350 540,355 660,345 780,360 900,350 1040,358 1140,348' fill='none' stroke='%23f9a825' stroke-width='10' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    }
    .rec-low {
        border-left: 4px solid #2f7f4f;
        background-image:
            linear-gradient(125deg, rgba(240, 252, 244, 0.88) 0%, rgba(227, 248, 235, 0.84) 100%),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 700'%3E%3Crect width='1200' height='700' fill='%23f4fff7'/%3E%3Cg stroke='%2398e0b3' stroke-width='1'%3E%3Cpath d='M0 100h1200M0 200h1200M0 300h1200M0 400h1200M0 500h1200M0 600h1200'/%3E%3Cpath d='M100 0v700M250 0v700M400 0v700M550 0v700M700 0v700M850 0v700M1000 0v700M1150 0v700'/%3E%3C/g%3E%3Cpolyline points='60,620 180,570 300,520 420,470 540,430 660,370 780,320 900,260 1040,190 1140,140' fill='none' stroke='%232e7d32' stroke-width='10' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    }
</style>
""", unsafe_allow_html=True)

# ==================== ХЕДЕР (закрепленный) ====================
st.markdown("""
<div class="custom-header">
    <div class="logo-area">
        <div class="logo-text">
            <h1>FinAnalytics</h1>
            <p>Экспресс-диагностика финансовых показателей</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== ОСНОВНОЙ КОНТЕНТ (с отступом под хедер) ====================
st.markdown('<div class="content-wrapper">', unsafe_allow_html=True)

st.markdown("""
<div class="hero-aero">
    <div class="hero-grid">
        <div class="hero-tile">
            <img src="https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=1200&q=80" alt="Аналитика" />
            <p>Финансовая аналитика и стратегические решения</p>
        </div>
        <div class="hero-tile">
            <img src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80" alt="Бизнес-отчеты" />
            <p>Прозрачные отчёты для контроля рентабельности</p>
        </div>
        <div class="hero-tile">
            <img src="https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1200&q=80" alt="Рост компании" />
            <p>Компактный мониторинг ключевых метрик</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== ФУНКЦИИ ====================
def generate_recommendations(df):
    recommendations = []
    signals = []
    rent_last = df['Рентабельность (%)'].iloc[-1]
    rent_prev = df['Рентабельность (%)'].iloc[-2] if len(df) > 1 else rent_last
    
    if rent_last < 10:
        signals.append("КРИТИЧЕСКИЙ")
        recommendations.append({"priority": "Высокий","signal": "Низкая рентабельность","detail": f"Рентабельность составляет {rent_last:.1f}% (норма >10%)","action": "Срочно провести анализ себестоимости\nПересмотреть ценообразование\nОптимизировать расходы","expected_effect": "Повышение рентабельности до 10-15%"})
    elif rent_last < 15:
        signals.append("НИЖЕ СРЕДНЕГО")
        recommendations.append({"priority": "Средний","signal": "Рентабельность ниже целевого уровня","detail": f"Рентабельность {rent_last:.1f}% при целевых 15%","action": "Проанализировать затраты\nИскать новых поставщиков\nАвтоматизировать процессы","expected_effect": "Рост рентабельности на 2-3%"})
    else:
        signals.append("ХОРОШО")
        recommendations.append({"priority": "Низкий","signal": "Рентабельность в норме","detail": f"Рентабельность {rent_last:.1f}% - хороший показатель","action": "Поддерживать текущий уровень\nИскать точки роста","expected_effect": "Стабильная прибыль"})
    
    if len(df) > 1:
        rent_change = rent_last - rent_prev
        if rent_change < -2:
            recommendations.append({"priority": "Высокий","signal": "Падение рентабельности","detail": f"Снижение на {abs(rent_change):.1f}%","action": "Выявить причины роста затрат\nПроверить закупки\nПересмотреть цены","expected_effect": "Остановка падения"})
        elif rent_change > 2:
            recommendations.append({"priority": "Низкий","signal": "Положительная динамика","detail": f"Рост на {rent_change:.1f}%","action": "Закрепить успех\nМасштабировать практики","expected_effect": "Дальнейший рост"})
    
    if 'Ликвидность' in df.columns:
        liq_last = df['Ликвидность'].iloc[-1]
        if liq_last < 1.0:
            recommendations.append({"priority": "Критический","signal": "Риск банкротства","detail": f"Ликвидность {liq_last:.2f}","action": "Реструктуризация долгов\nУскорение дебиторки\nПродажа активов","expected_effect": "Восстановление платежеспособности"})
        elif liq_last < 1.5:
            recommendations.append({"priority": "Высокий","signal": "Недостаточная ликвидность","detail": f"Ликвидность {liq_last:.2f}","action": "Увеличить оборотные активы\nСнизить долги\nОптимизировать запасы","expected_effect": "Повышение ликвидности"})
        elif liq_last > 3.0:
            recommendations.append({"priority": "Средний","signal": "Избыточная ликвидность","detail": f"Ликвидность {liq_last:.2f}","action": "Направить средства на развитие\nИнвестировать\nПогасить кредиты","expected_effect": "Повышение доходности"})
    
    cost_share = df['Доля затрат (%)'].iloc[-1]
    if cost_share > 80:
        recommendations.append({"priority": "Высокий","signal": "Критическая доля затрат","detail": f"Себестоимость {cost_share:.1f}% от выручки","action": "Аудит затрат\nПереговоры с поставщиками\nОптимизация","expected_effect": "Снижение доли затрат"})
    elif cost_share > 70:
        recommendations.append({"priority": "Средний","signal": "Высокая доля затрат","detail": f"Себестоимость {cost_share:.1f}%","action": "Анализ затрат\nНормативный учет\nАвтоматизация","expected_effect": "Экономия 5-10%"})
    return recommendations, signals

def export_to_html(df, recommendations):
    html_content = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Отчет ФХД</title>
    <style>body{{font-family:Arial,sans-serif;margin:40px;background:#f0f2f6}}h1{{color:#0a2351}}.card{{background:white;border-radius:12px;padding:20px;margin:10px 0}}</style>
    </head><body><h1>📊 Отчет по финансово-хозяйственной деятельности</h1><p>Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
    <div class="card"><h3>Ключевые показатели</h3><p>Рентабельность: {df['Рентабельность (%)'].iloc[-1]:.1f}%</p>
    <p>Доля себестоимости: {df['Доля затрат (%)'].iloc[-1]:.1f}%</p>
    {f"<p>Ликвидность: {df['Ликвидность'].iloc[-1]:.2f}</p>" if 'Ликвидность' in df.columns else ""}</div>
    <h2>Рекомендации</h2>"""
    for rec in recommendations:
        html_content += f"<div class='card'><b>{rec['signal']}</b><br>{rec['detail']}<br><b>Действия:</b> {rec['action'].replace(chr(10),'<br>')}<br><b>Эффект:</b> {rec['expected_effect']}</div>"
    html_content += f"<h2>Данные по периодам</h2>{df[['Период','Выручка','Себестоимость','Рентабельность (%)','Доля затрат (%)'] + (['Ликвидность'] if 'Ликвидность' in df.columns else [])].to_html(index=False)}<p style='text-align:center'>Сгенерировано системой финансового анализа</p></body></html>"
    return html_content

# ==================== ЗАГРУЗКА ФАЙЛА ====================
uploaded_file = st.session_state.get("main_uploader")
if uploaded_file is None:
    st.markdown("""
    <div class="data-guide">
        <h4>Какие данные загружать (Excel / 1С / CRM)</h4>
        <p><b>Обязательные:</b> Период, Выручка, Себестоимость</p>
        <p><b>Желательные:</b> Оборотные активы, Краткосрочные обязательства, Запасы, Дебиторская задолженность, Кредиторская задолженность, Коммерческие и Управленческие расходы</p>
        <p>Система автоматически распознаёт типовые синонимы из выгрузок 1С (например: «Выручка, руб.», «Текущие обязательства», «Дебиторка»).</p>
    </div>
    """, unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Загрузить файл",
    type=["xlsx", "xls", "csv"],
    help="Выгрузка из 1С, CRM или бухгалтерии",
    label_visibility="collapsed",
    key="main_uploader"
)

# ==================== АНАЛИЗ ДАННЫХ ====================
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        df = normalize_columns(df)
        df = add_calculated_metrics(df)

        if 'Выручка' in df.columns and 'Себестоимость' in df.columns:
            
            # Ключевые показатели
            st.markdown('<div class="section-title">Ключевые показатели</div>', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                last_rent = df['Рентабельность (%)'].iloc[-1]
                rent_change = df['Рентабельность (%)'].iloc[-1] - df['Рентабельность (%)'].iloc[-2] if len(df) > 1 else 0
                st.metric("Рентабельность продаж", f"{last_rent:.1f}%", f"{rent_change:.1f}%")
            with col2:
                if 'Ликвидность' in df.columns:
                    last_liq = df['Ликвидность'].iloc[-1]
                    liq_change = df['Ликвидность'].iloc[-1] - df['Ликвидность'].iloc[-2] if len(df) > 1 else 0
                    st.metric("Коэффициент ликвидности", f"{last_liq:.2f}", f"{liq_change:.2f}")
                else:
                    st.metric("Коэффициент ликвидности", "Нет данных", "—")
            with col3:
                last_cost = df['Доля затрат (%)'].iloc[-1]
                cost_change = df['Доля затрат (%)'].iloc[-1] - df['Доля затрат (%)'].iloc[-2] if len(df) > 1 else 0
                st.metric("Доля себестоимости", f"{last_cost:.1f}%", f"{cost_change:.1f}%")
            with col4:
                gross_profit = df['Валовая прибыль'].iloc[-1] if 'Валовая прибыль' in df.columns else 0
                gross_prev = df['Валовая прибыль'].iloc[-2] if 'Валовая прибыль' in df.columns and len(df) > 1 else gross_profit
                st.metric("Валовая прибыль", f"{gross_profit:,.0f}", f"{(gross_profit-gross_prev):,.0f}")

            extra_metrics = []
            if 'Дней дебиторки' in df.columns:
                extra_metrics.append(f"Дней дебиторки: **{df['Дней дебиторки'].iloc[-1]:.1f}**")
            if 'Дней кредиторки' in df.columns:
                extra_metrics.append(f"Дней кредиторки: **{df['Дней кредиторки'].iloc[-1]:.1f}**")
            if 'Дней запасов' in df.columns:
                extra_metrics.append(f"Дней запасов: **{df['Дней запасов'].iloc[-1]:.1f}**")
            if 'Операционная маржа (%)' in df.columns:
                extra_metrics.append(f"Операционная маржа: **{df['Операционная маржа (%)'].iloc[-1]:.1f}%**")
            if extra_metrics:
                st.caption(" | ".join(extra_metrics))
            
            st.markdown("---")
            
            # Рекомендации
            st.markdown('<div class="section-title">Аналитические сигналы и рекомендации</div>', unsafe_allow_html=True)
            recommendations, signals = generate_recommendations(df)
            
            if "КРИТИЧЕСКИЙ" in signals:
                st.error("Критическое состояние. Требуются немедленные действия.")
            elif "НИЖЕ СРЕДНЕГО" in signals:
                st.warning("Требуется внимание руководства. Есть потенциал для улучшения.")
            else:
                st.success("Стабильное состояние. Рекомендуется поддерживать текущий курс.")
            
            # Экспорт
            html_report = export_to_html(df, recommendations)
            b64 = base64.b64encode(html_report.encode()).decode()
            st.markdown(f'<a href="data:text/html;base64,{b64}" download="report_{datetime.now().strftime("%Y%m%d_%H%M")}.html" style="background:#ffaa00; color:#0a2351; padding:8px 20px; border-radius:30px; text-decoration:none; font-weight:bold; display:inline-block; margin-bottom:20px;">Экспорт отчета (HTML/PDF)</a>', unsafe_allow_html=True)
            st.caption("Сохраните HTML, откройте в браузере и распечатайте в PDF.")
            
            # Вывод рекомендаций
            cols_per_row = 3
            for i in range(0, len(recommendations), cols_per_row):
                row = st.columns(cols_per_row)
                for j, rec in enumerate(recommendations[i:i + cols_per_row]):
                    rec_class = "rec-low"
                    if rec['priority'] == 'Критический':
                        rec_class = "rec-critical"
                    elif rec['priority'] == 'Высокий':
                        rec_class = "rec-high"
                    elif rec['priority'] == 'Средний':
                        rec_class = "rec-medium"

                    with row[j]:
                        st.markdown(
                            f"<div class='rec-card {rec_class}'>"
                            f"<div class='rec-title'>{rec['signal']}</div>"
                            f"<div class='rec-text'>{rec['detail']}</div>"
                            f"<div class='rec-text'><b>Действия:</b> {rec['action'].replace(chr(10),'<br>')}</div>"
                            f"<div class='rec-text'><b>Ожидаемый эффект:</b> {rec['expected_effect']}</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
            
            # Графики
            with st.expander("Развернуть детальные графики и таблицы"):
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Bar(x=df['Период'], y=df['Выручка'], name="Выручка", marker_color='#1e3a6f'), secondary_y=False)
                fig.add_trace(go.Scatter(x=df['Период'], y=df['Рентабельность (%)'], name="Рентабельность", mode='lines+markers', marker_color='#ffaa00', line=dict(width=2)), secondary_y=True)
                fig.update_layout(title="Динамика выручки и рентабельности", height=400, plot_bgcolor='white', paper_bgcolor='white', font_color='#0a2351')
                st.plotly_chart(fig, use_container_width=True)
                
                if 'Ликвидность' in df.columns:
                    fig_liq = go.Figure()
                    fig_liq.add_trace(go.Scatter(x=df['Период'], y=df['Ликвидность'], mode='lines+markers', name='Ликвидность', line=dict(color='#1e3a6f', width=2)))
                    fig_liq.add_hline(y=1.5, line_dash="dash", line_color="#ffaa00", annotation_text="Норма (1.5)")
                    fig_liq.update_layout(title="Коэффициент ликвидности", height=400, plot_bgcolor='white', paper_bgcolor='white')
                    st.plotly_chart(fig_liq, use_container_width=True)
                
                display_cols = ['Период', 'Выручка', 'Себестоимость', 'Валовая прибыль', 'Рентабельность (%)', 'Доля затрат (%)']
                if 'Ликвидность' in df.columns:
                    display_cols.append('Ликвидность')
                for optional_col in ['Дней дебиторки', 'Дней кредиторки', 'Дней запасов', 'Операционная маржа (%)']:
                    if optional_col in df.columns:
                        display_cols.append(optional_col)
                formatters = {}
                for col in ['Выручка', 'Себестоимость', 'Валовая прибыль']:
                    if col in display_cols:
                        formatters[col] = '{:,.0f}'
                for col, fmt in {
                    'Рентабельность (%)': '{:.1f}%',
                    'Доля затрат (%)': '{:.1f}%',
                    'Ликвидность': '{:.2f}',
                    'Дней дебиторки': '{:.1f}',
                    'Дней кредиторки': '{:.1f}',
                    'Дней запасов': '{:.1f}',
                    'Операционная маржа (%)': '{:.1f}%'
                }.items():
                    if col in display_cols:
                        formatters[col] = fmt

                st.dataframe(df[display_cols].style.format(formatters), use_container_width=True)
        else:
            st.warning("В файле не найдены обязательные столбцы: 'Выручка' и 'Себестоимость'")
    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
        st.info("Убедитесь, что файл имеет правильный формат и содержит нужные колонки")

else:
    pass

# Закрываем content-wrapper
st.markdown('</div>', unsafe_allow_html=True)


