"""
analytics.py
────────────
Serviço de geração de retrospectos semanais e mensais.

Uso manual:
    from estudos.analytics import generate_weekly_report, generate_monthly_report
    import pendulum

    generate_weekly_report(pendulum.now().subtract(weeks=1))
    generate_monthly_report(2026, 5)

Ou via manage.py:
    python manage.py generate_reports --weekly
    python manage.py generate_reports --monthly --year 2026 --month 5
"""

import os
import pendulum
import pandas as pd
import matplotlib
matplotlib.use('Agg')          # renderiza sem abrir janela (modo servidor)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from django.conf import settings
from django.db import connection

from .models import WeeklyMetrics, MonthlyMetrics, Subject


# ─────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────

CHARTS_DIR = os.path.join(settings.BASE_DIR, 'media', 'charts')


def _ensure_charts_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def _load_sessions_df(date_start, date_end):
    """Carrega sessões do período em um DataFrame do pandas."""
    query = """
        SELECT
            ss.id,
            ss.date,
            ss.gross_minutes,
            ss.net_minutes,
            ss.planned_minutes,
            subj.name AS subject_name,
            subj.id   AS subject_id
        FROM estudos_studysession ss
        JOIN estudos_subject subj ON subj.id = ss.subject_id
        WHERE ss.date BETWEEN %s AND %s
        AND ss.status != 'em_andamento'
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [str(date_start), str(date_end)])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(
        columns=['id', 'date', 'gross_minutes', 'net_minutes',
                 'planned_minutes', 'subject_name', 'subject_id']
    )


def _load_pauses_df(date_start, date_end):
    """Carrega pausas do período."""
    query = """
        SELECT
            p.duration_minutes,
            subj.name AS subject_name,
            subj.id   AS subject_id
        FROM estudos_pause p
        JOIN estudos_studysession ss ON ss.id = p.session_id
        JOIN estudos_subject subj    ON subj.id = p.subject_id
        WHERE ss.date BETWEEN %s AND %s
          AND p.ended_at IS NOT NULL
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [str(date_start), str(date_end)])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(
        columns=['duration_minutes', 'subject_name', 'subject_id']
    )


def _calc_base_metrics(sessions_df, pauses_df):
    """Calcula métricas base a partir dos DataFrames."""
    total_gross = int(sessions_df['gross_minutes'].sum())
    total_net = int(sessions_df['net_minutes'].sum())
    total_pause_min = int(pauses_df['duration_minutes'].sum()) if not pauses_df.empty else 0
    total_pauses = len(pauses_df)
    study_days = sessions_df['date'].nunique() if not sessions_df.empty else 0

    efficiency = round((total_net / total_gross * 100), 2) if total_gross > 0 else 0.0
    procrastination = round((total_pause_min / total_gross * 100), 2) if total_gross > 0 else 0.0

    # Matéria mais estudada
    if not sessions_df.empty:
        by_subject = sessions_df.groupby('subject_name')['net_minutes'].sum()
        most_studied_name = by_subject.idxmax()
        most_studied_id = int(
            sessions_df.loc[sessions_df['subject_name'] == most_studied_name, 'subject_id'].iloc[0]
        )
    else:
        most_studied_name = None
        most_studied_id = None

    # Matéria mais procrastinada (mais pausas)
    if not pauses_df.empty:
        by_pause = pauses_df.groupby('subject_name')['duration_minutes'].sum()
        most_procrastinated_name = by_pause.idxmax()
        most_procrastinated_id = int(
            pauses_df.loc[pauses_df['subject_name'] == most_procrastinated_name, 'subject_id'].iloc[0]
        )
    else:
        most_procrastinated_name = None
        most_procrastinated_id = None

    return {
        'total_gross': total_gross,
        'total_net': total_net,
        'total_pauses': total_pauses,
        'total_pause_min': total_pause_min,
        'efficiency': efficiency,
        'procrastination': procrastination,
        'study_days': study_days,
        'most_studied_id': most_studied_id,
        'most_studied_name': most_studied_name,
        'most_procrastinated_id': most_procrastinated_id,
        'most_procrastinated_name': most_procrastinated_name,
    }


# ─────────────────────────────────────────────────────────────────
# Geração de gráficos
# ─────────────────────────────────────────────────────────────────

def _chart_weekly(sessions_df, pauses_df, week_start, week_end):
    """Gera gráfico de barras do retrospecto semanal e retorna o caminho do arquivo."""
    _ensure_charts_dir()
    filename = f'weekly_{week_start}.png'
    filepath = os.path.join(CHARTS_DIR, filename)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        f'Retrospecto Semanal — {_fmt_date(week_start)} a {_fmt_date(week_end)}',
        fontsize=14, fontweight='bold'
    )

    # Gráfico 1: minutos líquidos por matéria
    ax1 = axes[0]
    if not sessions_df.empty:
        by_subject = sessions_df.groupby('subject_name')['net_minutes'].sum().sort_values(ascending=False)
        ax1.bar(by_subject.index, by_subject.values, color='steelblue')
        ax1.set_title('Minutos líquidos por matéria')
        ax1.set_ylabel('Minutos')
        ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        plt.setp(ax1.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    else:
        ax1.text(0.5, 0.5, 'Sem dados', ha='center', va='center')
        ax1.set_title('Minutos líquidos por matéria')

    # Gráfico 2: minutos de pausa por matéria
    ax2 = axes[1]
    if not pauses_df.empty:
        by_pause = pauses_df.groupby('subject_name')['duration_minutes'].sum().sort_values(ascending=False)
        ax2.bar(by_pause.index, by_pause.values, color='tomato')
        ax2.set_title('Minutos de pausa por matéria')
        ax2.set_ylabel('Minutos')
        ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        plt.setp(ax2.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    else:
        ax2.text(0.5, 0.5, 'Sem pausas registradas', ha='center', va='center')
        ax2.set_title('Minutos de pausa por matéria')

    plt.tight_layout()
    plt.savefig(filepath, dpi=120)
    plt.close(fig)
    return os.path.join('media', 'charts', filename)


def _chart_monthly(sessions_df, pauses_df, year, month):
    """Gera gráfico de linha do retrospecto mensal e retorna o caminho do arquivo."""
    _ensure_charts_dir()
    filename = f'monthly_{year}_{month:02d}.png'
    filepath = os.path.join(CHARTS_DIR, filename)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    month_label = pendulum.date(year, month, 1).format('MMMM [de] YYYY', locale='pt')
    fig.suptitle(f'Retrospecto Mensal — {month_label}', fontsize=14, fontweight='bold')

    # Gráfico 1: minutos líquidos por dia
    ax1 = axes[0]
    if not sessions_df.empty:
        by_day = sessions_df.groupby('date')['net_minutes'].sum().reset_index()
        by_day['date'] = pd.to_datetime(by_day['date'])
        by_day = by_day.sort_values('date')
        ax1.plot(by_day['date'], by_day['net_minutes'], marker='o', color='steelblue', linewidth=2)
        ax1.fill_between(by_day['date'], by_day['net_minutes'], alpha=0.15, color='steelblue')
        ax1.set_title('Minutos líquidos por dia')
        ax1.set_ylabel('Minutos')
        ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        plt.setp(ax1.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    else:
        ax1.text(0.5, 0.5, 'Sem dados', ha='center', va='center')
        ax1.set_title('Minutos líquidos por dia')

    # Gráfico 2: distribuição por matéria (pizza)
    ax2 = axes[1]
    if not sessions_df.empty:
        by_subject = sessions_df.groupby('subject_name')['net_minutes'].sum()
        ax2.pie(
            by_subject.values,
            labels=by_subject.index,
            autopct='%1.1f%%',
            startangle=140,
        )
        ax2.set_title('Distribuição de tempo por matéria')
    else:
        ax2.text(0.5, 0.5, 'Sem dados', ha='center', va='center')
        ax2.set_title('Distribuição de tempo por matéria')

    plt.tight_layout()
    plt.savefig(filepath, dpi=120)
    plt.close(fig)
    return os.path.join('media', 'charts', filename)


# ─────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────

def generate_weekly_report(reference_date=None):
    """
    Gera (ou atualiza) o WeeklyMetrics da semana que contém reference_date.

    Parâmetros
    ----------
    reference_date : pendulum.DateTime | None
        Qualquer data dentro da semana desejada.
        Padrão: semana atual.

    Retorna
    -------
    WeeklyMetrics
    """
    if reference_date is None:
        reference_date = pendulum.now('America/Sao_Paulo')

    week_start = reference_date.start_of('week').date()
    week_end = reference_date.end_of('week').date()

    sessions_df = _load_sessions_df(week_start, week_end)
    pauses_df = _load_pauses_df(week_start, week_end)
    m = _calc_base_metrics(sessions_df, pauses_df)

    chart_path = _chart_weekly(sessions_df, pauses_df, week_start, week_end)

    # Monta JSON completo por matéria
    subject_breakdown = {}
    if not sessions_df.empty:
        for subj, grp in sessions_df.groupby('subject_name'):
            subject_breakdown[subj] = {
                'gross_minutes': int(grp['gross_minutes'].sum()),
                'net_minutes': int(grp['net_minutes'].sum()),
                'sessions': len(grp),
            }

    report_json = {
        'week_start': str(week_start),
        'week_end': str(week_end),
        'total_gross_minutes': m['total_gross'],
        'total_net_minutes': m['total_net'],
        'efficiency_pct': m['efficiency'],
        'procrastination_pct': m['procrastination'],
        'total_pauses': m['total_pauses'],
        'pause_minutes': m['total_pause_min'],
        'study_days': m['study_days'],
        'most_studied': m['most_studied_name'],
        'most_procrastinated': m['most_procrastinated_name'],
        'by_subject': subject_breakdown,
    }

    most_studied_obj = Subject.objects.filter(pk=m['most_studied_id']).first()
    most_procrastinated_obj = Subject.objects.filter(pk=m['most_procrastinated_id']).first()

    obj, _ = WeeklyMetrics.objects.update_or_create(
        week_start=week_start,
        week_end=week_end,
        defaults=dict(
            total_minutes=m['total_gross'],
            net_minutes=m['total_net'],
            total_pauses=m['total_pauses'],
            pause_minutes=m['total_pause_min'],
            efficiency=m['efficiency'],
            procrastination_index=m['procrastination'],
            most_studied_subject=most_studied_obj,
            most_procrastinated_subject=most_procrastinated_obj,
            study_days=m['study_days'],
            report_json=report_json,
            chart_path=chart_path,
        ),
    )
    return obj


def generate_monthly_report(year=None, month=None):
    """
    Gera (ou atualiza) o MonthlyMetrics do mês especificado.

    Parâmetros
    ----------
    year  : int | None  — padrão: ano atual
    month : int | None  — padrão: mês atual

    Retorna
    -------
    MonthlyMetrics
    """
    now = pendulum.now('America/Sao_Paulo')
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    period_start = pendulum.date(year, month, 1)
    period_end = period_start.end_of('month')

    sessions_df = _load_sessions_df(period_start, period_end)
    pauses_df = _load_pauses_df(period_start, period_end)
    m = _calc_base_metrics(sessions_df, pauses_df)

    chart_path = _chart_monthly(sessions_df, pauses_df, year, month)

    # Metas atingidas: matérias onde net_minutes >= goal_hours * 60
    goals_hit = 0
    if not sessions_df.empty:
        for subj_id, grp in sessions_df.groupby('subject_id'):
            try:
                subj = Subject.objects.get(pk=subj_id)
                if subj.goal_hours and int(grp['net_minutes'].sum()) >= float(subj.goal_hours) * 60:
                    goals_hit += 1
            except Subject.DoesNotExist:
                pass

    # Breakdown semanal dentro do mês
    weekly_breakdown = {}
    if not sessions_df.empty:
        sessions_df['date'] = pd.to_datetime(sessions_df['date'])
        sessions_df['week'] = sessions_df['date'].dt.isocalendar().week.astype(int)
        for week_num, grp in sessions_df.groupby('week'):
            weekly_breakdown[f'semana_{week_num}'] = {
                'net_minutes': int(grp['net_minutes'].sum()),
                'sessions': len(grp),
                'study_days': grp['date'].nunique(),
            }

    report_json = {
        'year': year,
        'month': month,
        'total_gross_minutes': m['total_gross'],
        'total_net_minutes': m['total_net'],
        'efficiency_pct': m['efficiency'],
        'procrastination_pct': m['procrastination'],
        'total_pauses': m['total_pauses'],
        'pause_minutes': m['total_pause_min'],
        'study_days': m['study_days'],
        'goals_hit': goals_hit,
        'most_studied': m['most_studied_name'],
        'by_week': weekly_breakdown,
    }

    most_studied_obj = Subject.objects.filter(pk=m['most_studied_id']).first()

    obj, _ = MonthlyMetrics.objects.update_or_create(
        year=year,
        month=month,
        defaults=dict(
            total_minutes=m['total_gross'],
            net_minutes=m['total_net'],
            total_pauses=m['total_pauses'],
            pause_minutes=m['total_pause_min'],
            efficiency=m['efficiency'],
            procrastination_index=m['procrastination'],
            most_studied_subject=most_studied_obj,
            study_days=m['study_days'],
            goals_hit=goals_hit,
            report_json=report_json,
            chart_path=chart_path,
        ),
    )
    return obj


# ─────────────────────────────────────────────────────────────────
# Utilitário
# ─────────────────────────────────────────────────────────────────

def _fmt_date(d):
    return pendulum.instance(
        pendulum.datetime(d.year, d.month, d.day)
    ).format('DD/MM/YYYY')
