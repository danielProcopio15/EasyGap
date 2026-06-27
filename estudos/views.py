from django.shortcuts import render, get_object_or_404, redirect
from django.forms import inlineformset_factory
from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour
from django.http import JsonResponse
from django.urls import reverse
from datetime import date as dt_date, timedelta
from collections import defaultdict
import json
from .models import (
    Subject, StudyPlan, StudyPlanItem, StudySession,
    Pause, StudyContent, Observation, WeeklyMetrics, MonthlyMetrics,
)
from .forms import SubjectForm, StudyPlanForm, StudyPlanItemForm
import pendulum


# ─────────────────────────────────────────────
# HOME / DASHBOARD
# ─────────────────────────────────────────────

def home(request):
    hoje = pendulum.now('America/Sao_Paulo').date()
    materias = Subject.objects.filter(status='ativa')
    sessoes_hoje = StudySession.objects.filter(date=hoje).select_related('subject')
    ultima_semana = WeeklyMetrics.objects.first()
    ultimo_mes = MonthlyMetrics.objects.first()

    context = {
        'hoje': hoje,
        'materias': materias,
        'sessoes_hoje': sessoes_hoje,
        'ultima_semana': ultima_semana,
        'ultimo_mes': ultimo_mes,
    }
    return render(request, 'estudos/home.html', context)


# ─────────────────────────────────────────────
# MATÉRIAS
# ─────────────────────────────────────────────

def materia_lista(request):
    materias = Subject.objects.all().order_by('name')

    # Última sessão concluída/encerrada por matéria
    ultima_sessao = {}
    for s in (StudySession.objects
              .filter(status__in=['concluida', 'encerrada'])
              .order_by('subject_id', '-date')
              .values('subject_id', 'date')):
        if s['subject_id'] not in ultima_sessao:
            ultima_sessao[s['subject_id']] = s['date']

    materias_info = []
    hoje = pendulum.now('America/Sao_Paulo').date()
    for m in materias:
        last = ultima_sessao.get(m.pk)
        days = (hoje - last).days if last else None
        materias_info.append({'materia': m, 'last_studied': last, 'days_since': days})

    return render(request, 'estudos/materias/lista.html', {'materias_info': materias_info})


def materia_nova(request):
    form = SubjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('materia_lista')
    return render(request, 'estudos/materias/form.html', {'form': form, 'titulo': 'Nova matéria'})


def materia_editar(request, pk):
    materia = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST or None, instance=materia)
    if form.is_valid():
        form.save()
        return redirect('materia_lista')
    return render(request, 'estudos/materias/form.html', {'form': form, 'titulo': f'Editar — {materia.name}'})


def materia_remover(request, pk):
    materia = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        materia.delete()
        return redirect('materia_lista')
    return render(request, 'estudos/materias/confirmar_remocao.html', {'objeto': materia, 'tipo': 'a matéria'})


# ─────────────────────────────────────────────
# CRONOGRAMAS
# ─────────────────────────────────────────────

DAYS = [
    (0, 'Segunda-feira'),
    (1, 'Terça-feira'),
    (2, 'Quarta-feira'),
    (3, 'Quinta-feira'),
    (4, 'Sexta-feira'),
    (5, 'Sábado'),
    (6, 'Domingo'),
]

PlanItemFormSet = inlineformset_factory(
    StudyPlan, StudyPlanItem,
    form=StudyPlanItemForm,
    extra=0,
    can_delete=True,
)


def _days_with_forms(formset):
    """Agrupa os formulários do formset por dia da semana."""
    by_day = {day: [] for day, _ in DAYS}
    for f in formset.forms:
        val = f['day_of_week'].value()
        if val not in (None, ''):
            try:
                by_day[int(val)].append(f)
            except (ValueError, KeyError):
                pass
    return [(day, name, by_day[day]) for day, name in DAYS]


def cronograma_lista(request):
    planos = StudyPlan.objects.all().order_by('-created_at')
    return render(request, 'estudos/cronograma/lista.html', {'planos': planos})


def cronograma_novo(request):
    form = StudyPlanForm(request.POST or None)
    formset = PlanItemFormSet(request.POST or None, prefix='items')
    if form.is_valid() and formset.is_valid():
        plano = form.save()
        formset.instance = plano
        formset.save()
        return redirect('cronograma_lista')
    return render(request, 'estudos/cronograma/form.html', {
        'form': form,
        'formset': formset,
        'titulo': 'Novo cronograma',
        'days_with_forms': _days_with_forms(formset),
    })


def cronograma_editar(request, pk):
    plano = get_object_or_404(StudyPlan, pk=pk)
    form = StudyPlanForm(request.POST or None, instance=plano)
    formset = PlanItemFormSet(request.POST or None, instance=plano, prefix='items')
    if form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        return redirect('cronograma_lista')
    return render(request, 'estudos/cronograma/form.html', {
        'form': form,
        'formset': formset,
        'titulo': f'Editar — {plano.name}',
        'days_with_forms': _days_with_forms(formset),
    })


def cronograma_remover(request, pk):
    plano = get_object_or_404(StudyPlan, pk=pk)
    if request.method == 'POST':
        plano.delete()
        return redirect('cronograma_lista')
    return render(request, 'estudos/materias/confirmar_remocao.html', {'objeto': plano, 'tipo': 'o cronograma'})


def cronograma_ativar(request, pk):
    """Ativa o cronograma escolhido e desativa todos os outros."""
    if request.method == 'POST':
        StudyPlan.objects.update(status='inativo')
        plano = get_object_or_404(StudyPlan, pk=pk)
        plano.status = 'ativo'
        plano.save()
    return redirect('cronograma_lista')


# ─────────────────────────────────────────────
# RENDIMENTOS
# ─────────────────────────────────────────────

def rendimentos(request):
    semanas = WeeklyMetrics.objects.all()[:8]
    meses = MonthlyMetrics.objects.all()[:6]

    # Pausas por matéria (todas as pausas registradas)
    pausas_por_materia = (
        Pause.objects
        .select_related('subject')
        .values('subject__name')
        .annotate(
            total_pausas=Count('id'),
            total_minutos=Sum('duration_minutes'),
        )
        .order_by('-total_minutos')
    )

    # Sessões recentes
    sessoes = StudySession.objects.select_related('subject').order_by('-date', '-started_at')[:20]

    context = {
        'semanas': semanas,
        'meses': meses,
        'pausas_por_materia': pausas_por_materia,
        'sessoes': sessoes,
    }
    return render(request, 'estudos/rendimentos/dashboard.html', context)


# ─────────────────────────────────────────────
# AGENDA DIÁRIA
# ─────────────────────────────────────────────

_BASELINE_DATE  = dt_date(2000, 1, 1)
_STALE_DAYS     = 4
_PRIORITY_ORDER = {'alta': 0, 'media': 1, 'baixa': 2}


def _calcular_fila(materias, hoje, sessoes_hoje=None):
    """
    Fila por stride scheduler: virtual_due = total_sessoes / peso

    Garante rotação proporcional entre todas as prioridades:
      - alta  (w=3): virtual_due cresce 1/3 por sessão → aparece ~3× mais que baixa
      - media (w=2): virtual_due cresce 1/2 por sessão → aparece ~2× mais que baixa
      - baixa (w=1): virtual_due cresce 1/1 por sessão → aparece 1×

    Quem tem menor virtual_due vai primeiro.
    Empate → maior peso primeiro → mesma data de acesso → estável (ordem alfabética).

    O badge 'Negligenciada' é apenas visual — não altera a posição na fila.
    """
    ids    = [m.pk for m in materias]
    cutoff = hoje - timedelta(days=_STALE_DAYS)

    # Contagem total de sessões por subject (qualquer status)
    session_counts = {
        row['subject_id']: row['n']
        for row in StudySession.objects
            .filter(subject_id__in=ids)
            .values('subject_id')
            .annotate(n=Count('id'))
    }

    last_any        = {}
    last_studied    = {}
    recent_statuses = {}

    for row in (StudySession.objects
                .filter(subject_id__in=ids)
                .order_by('subject_id', '-date', '-started_at')
                .values('subject_id', 'date', 'status')):
        sid = row['subject_id']
        if sid not in last_any:
            last_any[sid] = row['date']
        if row['status'] in ('concluida', 'encerrada') and sid not in last_studied:
            last_studied[sid] = row['date']
        if row['date'] >= cutoff:
            recent_statuses.setdefault(sid, []).append(row['status'])

    # Badge visual apenas
    stale = {}
    for m in materias:
        last    = last_any.get(m.pk)
        recents = recent_statuses.get(m.pk, [])
        all_skipped = bool(recents) and all(s == 'pulada' for s in recents)
        no_access   = last is None or (hoje - last).days >= _STALE_DAYS
        stale[m.pk] = all_skipped or no_access

    fila = []
    for m in materias:
        count       = session_counts.get(m.pk, 0)
        virtual_due = count / m.weight          # menor = mais urgente
        last_s = last_studied.get(m.pk)
        last   = last_any.get(m.pk)

        entry = {
            'subject':      m,
            'last_studied': last_s,
            'days_since':   (hoje - last_s).days if last_s else None,
            'is_stale':     stale[m.pk],
            '_last_any':    last,
        }
        if sessoes_hoje is not None:
            entry['sessao_hoje'] = sessoes_hoje.get(m.pk)

        # (virtual_due ASC, -weight ASC, last_any ASC)
        fila.append((virtual_due, -m.weight, last or _BASELINE_DATE, entry))

    fila.sort(key=lambda x: (x[0], x[1], x[2]))
    return [e for _, _, _, e in fila]


def agenda_diaria(request):
    tz = pendulum.timezone('America/Sao_Paulo')
    hoje = pendulum.now(tz).date()

    materias = list(Subject.objects.filter(status='ativa'))

    # Sessões de hoje mapeadas por subject_id (única query)
    sessoes_hoje = {}
    for s in StudySession.objects.filter(date=hoje).select_related('subject'):
        existing = sessoes_hoje.get(s.subject_id)
        if existing is None or s.started_at > existing.started_at:
            sessoes_hoje[s.subject_id] = s

    fila = _calcular_fila(materias, hoje, sessoes_hoje)

    for i, entry in enumerate(fila, 1):
        entry['order'] = i

    sessao_em_andamento = (
        StudySession.objects
        .filter(date=hoje, status='em_andamento')
        .select_related('subject')
        .first()
    )

    context = {
        'hoje': hoje,
        'fila': fila,
        'sessao_em_andamento': sessao_em_andamento,
    }
    return render(request, 'estudos/agenda/diaria.html', context)


def _proximo_por_prioridade(sessao_atual):
    """
    Retorna o próximo Subject da fila rotativa após encerrar/pular a sessão atual.

    IMPORTANTE: calcula a fila com TODOS os subjects ativos (incluindo o atual)
    e retorna o primeiro que não é o atual.

    Por que incluir o atual? Porque as frações de interleaving são calculadas
    com base no tamanho de cada grupo. Se excluirmos o atual antes de calcular,
    o grupo dele encolhe e os índices fracionários se rebalanceiam — o que
    quebra o interleaving e faz o mesmo grupo dominar sempre.

    A sessão recém-encerrada/pulada já foi salva no banco antes desta chamada,
    então last_any do subject atual = hoje → ele cai para o fim do seu grupo
    na rotação, e o primeiro item diferente do atual é o correto próximo.
    """
    hoje = pendulum.now('America/Sao_Paulo').date()
    todos = list(Subject.objects.filter(status='ativa'))
    if len(todos) <= 1:
        return None

    fila = _calcular_fila(todos, hoje)
    for entry in fila:
        if entry['subject'].pk != sessao_atual.subject_id:
            return entry['subject']
    return None


def iniciar_sessao_subject(request, subject_pk):
    """Cria (ou retoma) uma sessão para uma matéria diretamente, sem plan_item."""
    subject = get_object_or_404(Subject, pk=subject_pk)
    tz = pendulum.timezone('America/Sao_Paulo')
    agora = pendulum.now(tz)
    hoje = agora.date()

    sessao = StudySession.objects.filter(
        subject=subject, date=hoje, status='em_andamento'
    ).first()

    if not sessao:
        sessao = StudySession.objects.create(
            subject=subject,
            plan_item=None,
            date=hoje,
            started_at=agora,
            planned_minutes=subject.default_minutes,
            status='em_andamento',
        )

    return redirect('sessao_runner', pk=sessao.pk)



# ─────────────────────────────────────────────
# RUNNER DE SESSÃO
# ─────────────────────────────────────────────

def sessao_runner(request, pk):
    sessao = get_object_or_404(StudySession, pk=pk)
    tz = pendulum.timezone('America/Sao_Paulo')
    agora = pendulum.now(tz)

    pausas = list(sessao.pauses.all().order_by('started_at'))
    pause_seconds_closed = sum(
        p.duration_minutes * 60 for p in pausas if p.ended_at is not None
    )
    pausa_aberta = next((p for p in pausas if p.ended_at is None), None)
    is_paused = pausa_aberta is not None

    started = pendulum.instance(sessao.started_at)
    elapsed_total = (agora - started).total_seconds()

    if is_paused and pausa_aberta:
        pause_atual_secs = (agora - pendulum.instance(pausa_aberta.started_at)).total_seconds()
        elapsed_study = max(0, elapsed_total - pause_seconds_closed - pause_atual_secs)
    else:
        elapsed_study = max(0, elapsed_total - pause_seconds_closed)

    remaining_seconds = max(0, sessao.planned_minutes * 60 - int(elapsed_study))

    proximo_subject = _proximo_por_prioridade(sessao)
    proximo_subject_url = (
        reverse('iniciar_sessao_subject', kwargs={'subject_pk': proximo_subject.pk})
        if proximo_subject else None
    )

    conteudos = sessao.contents.select_related('subject').order_by('-date', 'description')
    observacoes = sessao.observations.select_related('subject').order_by('-created_at')

    hoje = agora.date()
    todos_subjects = list(Subject.objects.filter(status='ativa'))
    fila_geral = _calcular_fila(todos_subjects, hoje)
    for i, entry in enumerate(fila_geral, 1):
        entry['order'] = i

    context = {
        'sessao': sessao,
        'pausas': pausas,
        'is_paused': is_paused,
        'remaining_seconds': remaining_seconds,
        'elapsed_study_seconds': int(elapsed_study),
        'pause_seconds': int(pause_seconds_closed),
        'proximo_subject': proximo_subject,
        'proximo_subject_url': proximo_subject_url,
        'conteudos': conteudos,
        'observacoes': observacoes,
        'tipos_obs': Observation.TYPE_CHOICES,
        'fila_geral': fila_geral,
    }
    return render(request, 'estudos/sessao/runner.html', context)


# ─────────────────────────────────────────────
# AJAX — CONTROLE DE SESSÃO
# ─────────────────────────────────────────────

def _fechar_sessao(sessao, agora, status):
    """Encerra uma sessão calculando gross/net minutes."""
    pausa_aberta = sessao.pauses.filter(ended_at__isnull=True).first()
    if pausa_aberta:
        pausa_aberta.ended_at = agora
        dur = (agora - pendulum.instance(pausa_aberta.started_at)).total_seconds() / 60
        pausa_aberta.duration_minutes = max(0, int(dur))
        pausa_aberta.save()

    started = pendulum.instance(sessao.started_at)
    gross_seconds = (agora - started).total_seconds()
    gross_minutes = max(0, int(gross_seconds / 60))
    total_pause_min = sum(
        p.duration_minutes for p in sessao.pauses.all() if p.ended_at is not None
    )
    net_minutes = max(0, gross_minutes - total_pause_min)

    sessao.ended_at = agora
    sessao.gross_minutes = gross_minutes
    sessao.net_minutes = net_minutes
    sessao.status = status
    sessao.save()

    return {
        'status': status,
        'gross_minutes': gross_minutes,
        'net_minutes': net_minutes,
        'total_pause_minutes': total_pause_min,
        'efficiency': sessao.efficiency,
    }


def sessao_pausar(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    sessao = get_object_or_404(StudySession, pk=pk)
    if sessao.status != 'em_andamento':
        return JsonResponse({'error': 'sessão não está em andamento'}, status=400)
    tz = pendulum.timezone('America/Sao_Paulo')
    agora = pendulum.now(tz)
    if sessao.pauses.filter(ended_at__isnull=True).exists():
        return JsonResponse({'status': 'already_paused'})
    Pause.objects.create(session=sessao, subject=sessao.subject, started_at=agora)
    return JsonResponse({'status': 'paused', 'paused_at': agora.isoformat()})


def sessao_retomar(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    sessao = get_object_or_404(StudySession, pk=pk)
    tz = pendulum.timezone('America/Sao_Paulo')
    agora = pendulum.now(tz)
    pausa = sessao.pauses.filter(ended_at__isnull=True).first()
    if not pausa:
        return JsonResponse({'status': 'not_paused'})
    pausa.ended_at = agora
    dur = (agora - pendulum.instance(pausa.started_at)).total_seconds() / 60
    pausa.duration_minutes = max(0, int(dur))
    pausa.save()
    return JsonResponse({'status': 'resumed', 'pause_duration_minutes': pausa.duration_minutes})


def sessao_encerrar(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    sessao = get_object_or_404(StudySession, pk=pk)
    if sessao.status != 'em_andamento':
        return JsonResponse({'error': 'sessão já encerrada'}, status=400)
    tz = pendulum.timezone('America/Sao_Paulo')
    agora = pendulum.now(tz)
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    status_code = data.get('status', 'encerrada')
    if status_code not in ('concluida', 'encerrada', 'pulada'):
        status_code = 'encerrada'
    result = _fechar_sessao(sessao, agora, status_code)
    proximo = _proximo_por_prioridade(sessao)
    result['next_subject_url'] = (
        reverse('iniciar_sessao_subject', kwargs={'subject_pk': proximo.pk})
        if proximo else None
    )
    result['next_subject_name'] = proximo.name if proximo else None
    result['agenda_url'] = reverse('agenda_diaria')
    return JsonResponse(result)


def sessao_pular(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    sessao = get_object_or_404(StudySession, pk=pk)
    tz = pendulum.timezone('America/Sao_Paulo')
    agora = pendulum.now(tz)
    if sessao.status == 'em_andamento':
        _fechar_sessao(sessao, agora, 'pulada')
    proximo = _proximo_por_prioridade(sessao)
    next_subject_url = (
        reverse('iniciar_sessao_subject', kwargs={'subject_pk': proximo.pk})
        if proximo else None
    )
    return JsonResponse({
        'status': 'pulada',
        'next_subject_url': next_subject_url,
        'next_subject_name': proximo.name if proximo else None,
        'agenda_url': reverse('agenda_diaria'),
    })


def sessao_add_conteudo(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    sessao = get_object_or_404(StudySession, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    description = data.get('description', '').strip()
    if not description:
        return JsonResponse({'error': 'Descrição não pode ser vazia.'}, status=400)
    minutes_spent = max(0, int(data.get('minutes_spent', 0) or 0))
    conteudo = StudyContent.objects.create(
        session=sessao,
        subject=sessao.subject,
        description=description,
        date=sessao.date,
        minutes_spent=minutes_spent,
    )
    return JsonResponse({
        'id': conteudo.pk,
        'description': conteudo.description,
        'minutes_spent': conteudo.minutes_spent,
        'subject': sessao.subject.name,
    })


def sessao_add_observacao(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    sessao = get_object_or_404(StudySession, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'O texto da observação não pode ser vazio.'}, status=400)
    obs_type = data.get('type', 'observacao')
    valid_types = [t[0] for t in Observation.TYPE_CHOICES]
    if obs_type not in valid_types:
        obs_type = 'observacao'
    obs = Observation.objects.create(
        session=sessao, subject=sessao.subject, type=obs_type, text=text,
    )
    return JsonResponse({
        'id': obs.pk,
        'type': obs.type,
        'type_display': obs.get_type_display(),
        'text': obs.text,
        'subject': sessao.subject.name,
        'created_at': obs.created_at.strftime('%d/%m/%Y %H:%M'),
    })


def materia_notas_update(request, pk):
    """Atualiza as notas gerais de uma matéria via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'método não permitido'}, status=405)
    materia = get_object_or_404(Subject, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    materia.notes = data.get('notes', '').strip()
    materia.save(update_fields=['notes'])
    return JsonResponse({'status': 'ok', 'notes': materia.notes})


# ─────────────────────────────────────────────
# ANOTAÇÕES
# ─────────────────────────────────────────────

def anotacoes(request):
    tipo_filtro = request.GET.get('tipo', '')

    obs_qs = (
        Observation.objects
        .select_related('subject', 'session')
        .order_by('subject__name', '-created_at')
    )
    if tipo_filtro:
        obs_qs = obs_qs.filter(type=tipo_filtro)

    groups = defaultdict(list)
    for obs in obs_qs:
        groups[obs.subject].append(obs)

    subjects_obs = sorted(groups.items(), key=lambda x: x[0].name)

    return render(request, 'estudos/anotacoes/lista.html', {
        'subjects_obs': subjects_obs,
        'tipo_choices': Observation.TYPE_CHOICES,
        'tipo_filtro': tipo_filtro,
    })


# ─────────────────────────────────────────────
# PRODUTIVIDADE
# ─────────────────────────────────────────────

def produtividade(request):
    tz = pendulum.timezone('America/Sao_Paulo')
    hoje_pend = pendulum.now(tz).date()
    hoje = dt_date(hoje_pend.year, hoje_pend.month, hoje_pend.day)

    sessoes_enc = (
        StudySession.objects
        .filter(status__in=['concluida', 'encerrada'])
        .select_related('subject')
    )

    totals = sessoes_enc.aggregate(total_gross=Sum('gross_minutes'), total_net=Sum('net_minutes'))
    total_gross = totals['total_gross'] or 0
    total_net = totals['total_net'] or 0
    eficiencia_geral = round(total_net / total_gross * 100, 1) if total_gross > 0 else 0.0

    tempo_por_materia = (
        sessoes_enc
        .values('subject__id', 'subject__name')
        .annotate(
            minutos_gross=Sum('gross_minutes'),
            minutos_net=Sum('net_minutes'),
            sessoes_count=Count('id'),
        )
        .order_by('-minutos_net')
    )

    pausas_agg = Pause.objects.aggregate(
        total_pausas=Count('id'),
        total_pause_min=Sum('duration_minutes'),
    )
    total_pausas = pausas_agg['total_pausas'] or 0
    total_pause_min = pausas_agg['total_pause_min'] or 0
    media_pausas_min = round(total_pause_min / total_pausas, 1) if total_pausas > 0 else 0.0

    pausas_por_materia = (
        Pause.objects
        .values('subject__name')
        .annotate(total=Count('id'), total_min=Sum('duration_minutes'))
        .order_by('-total')
    )

    materia_mais_estudada = (
        sessoes_enc.values('subject__name')
        .annotate(total=Sum('net_minutes'))
        .order_by('-total')
        .first()
    )
    materia_mais_procrastinada = pausas_por_materia.first()

    horarios = (
        sessoes_enc
        .annotate(hora=ExtractHour('started_at'))
        .values('hora')
        .annotate(total_net=Sum('net_minutes'), contagem=Count('id'))
        .order_by('-total_net')[:6]
    )

    # Streak de dias consecutivos
    datas = set(sessoes_enc.values_list('date', flat=True))
    streak = 0
    dia = hoje
    while dia in datas:
        streak += 1
        dia -= timedelta(days=1)

    # Progresso de metas diárias por matéria
    materias_ativas = Subject.objects.filter(status='ativa')
    progresso_metas = []
    for m in materias_ativas:
        minutos_hoje = (
            StudySession.objects
            .filter(subject=m, date=hoje, status__in=['concluida', 'encerrada'])
            .aggregate(total=Sum('net_minutes'))['total'] or 0
        )
        meta_min = float(m.goal_hours) * 60
        progresso = min(100, round(minutos_hoje / meta_min * 100, 1)) if meta_min > 0 else 0
        progresso_metas.append({
            'materia': m,
            'minutos_hoje': minutos_hoje,
            'meta_minutos': int(meta_min),
            'progresso': progresso,
        })

    conteudos_recentes = (
        StudyContent.objects
        .select_related('subject', 'session')
        .order_by('-date', '-session__started_at')[:20]
    )

    proc_index = round(total_pause_min / total_gross * 100, 1) if total_gross > 0 else 0.0
    ultima_semana = WeeklyMetrics.objects.first()
    ultimo_mes = MonthlyMetrics.objects.first()

    context = {
        'total_gross': total_gross,
        'total_net': total_net,
        'eficiencia_geral': eficiencia_geral,
        'proc_index': proc_index,
        'total_pausas': total_pausas,
        'total_pause_min': total_pause_min,
        'media_pausas_min': media_pausas_min,
        'tempo_por_materia': tempo_por_materia,
        'pausas_por_materia': pausas_por_materia,
        'materia_mais_estudada': materia_mais_estudada,
        'materia_mais_procrastinada': materia_mais_procrastinada,
        'conteudos_recentes': conteudos_recentes,
        'horarios': horarios,
        'streak': streak,
        'progresso_metas': progresso_metas,
        'ultima_semana': ultima_semana,
        'ultimo_mes': ultimo_mes,
    }
    return render(request, 'estudos/produtividade/dashboard.html', context)
