from django.db import models


# ─────────────────────────────────────────────
# 1. MATÉRIA
# ─────────────────────────────────────────────

class Subject(models.Model):
    DIFFICULTY_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
    ]
    PRIORITY_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
    ]
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('pausada', 'Pausada'),
        ('concluida', 'Concluída'),
    ]

    PRIORITY_WEIGHT = {
        'baixa': 1,
        'media': 2,
        'alta':  3,
    }

    name = models.CharField(max_length=150, verbose_name='Nome')
    certames = models.TextField(blank=True, verbose_name='Certames')
    description = models.TextField(blank=True, verbose_name='Descrição')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='media', verbose_name='Dificuldade')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='media', verbose_name='Prioridade')
    weight = models.PositiveIntegerField(default=2, editable=False, verbose_name='Peso')
    goal_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Meta de horas')
    default_minutes = models.PositiveIntegerField(default=60, verbose_name='Tempo padrão de sessão (min)')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ativa', verbose_name='Status')
    notes = models.TextField(blank=True, verbose_name='Observações gerais')
    has_discursiva = models.BooleanField(default=False, verbose_name='Discursiva')
    has_oral = models.BooleanField(default=False, verbose_name='Oral')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Matéria'
        verbose_name_plural = 'Matérias'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.weight = self.PRIORITY_WEIGHT.get(self.priority, 1)
        super().save(*args, **kwargs)

    @property
    def certames_list(self):
        """Returns non-empty lines from the certames field."""
        return [c.strip() for c in self.certames.splitlines() if c.strip()]


# ─────────────────────────────────────────────
# 2. CRONOGRAMA SEMANAL
# ─────────────────────────────────────────────

class StudyPlan(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('arquivado', 'Arquivado'),
    ]

    name = models.CharField(max_length=150, verbose_name='Nome do cronograma')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inativo', verbose_name='Status')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cronograma'
        verbose_name_plural = 'Cronogramas'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.status})'


class StudyPlanItem(models.Model):
    DAY_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='items', verbose_name='Cronograma')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='plan_items', verbose_name='Matéria')
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name='Dia da semana')
    order = models.PositiveIntegerField(default=1, verbose_name='Ordem')
    planned_minutes = models.PositiveIntegerField(default=60, verbose_name='Tempo planejado (min)')
    scheduled_time = models.TimeField(null=True, blank=True, verbose_name='Horário previsto')

    class Meta:
        verbose_name = 'Item do cronograma'
        verbose_name_plural = 'Itens do cronograma'
        ordering = ['day_of_week', 'order']

    def __str__(self):
        return f'{self.get_day_of_week_display()} — {self.subject.name}'


# ─────────────────────────────────────────────
# 3. SESSÃO DE ESTUDO
# ─────────────────────────────────────────────

class StudySession(models.Model):
    STATUS_CHOICES = [
        ('em_andamento', 'Em andamento'),
        ('concluida', 'Concluída'),
        ('encerrada', 'Encerrada pelo usuário'),
        ('pulada', 'Pulada'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sessions', verbose_name='Matéria')
    plan_item = models.ForeignKey(StudyPlanItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='sessions', verbose_name='Item do cronograma')
    date = models.DateField(verbose_name='Data')
    started_at = models.DateTimeField(verbose_name='Início')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='Término')
    planned_minutes = models.PositiveIntegerField(default=0, verbose_name='Tempo planejado (min)')
    gross_minutes = models.PositiveIntegerField(default=0, verbose_name='Tempo bruto (min)')
    net_minutes = models.PositiveIntegerField(default=0, verbose_name='Tempo líquido (min)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='em_andamento', verbose_name='Status')

    class Meta:
        verbose_name = 'Sessão de estudo'
        verbose_name_plural = 'Sessões de estudo'
        ordering = ['-date', '-started_at']

    def __str__(self):
        return f'{self.date} — {self.subject.name} ({self.net_minutes} min líquidos)'

    @property
    def efficiency(self):
        """Retorna eficiência em % (tempo líquido / tempo bruto)."""
        if self.gross_minutes > 0:
            return round((self.net_minutes / self.gross_minutes) * 100, 1)
        return 0.0


# ─────────────────────────────────────────────
# 4. PAUSA
# ─────────────────────────────────────────────

class Pause(models.Model):
    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='pauses', verbose_name='Sessão')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='pauses', verbose_name='Matéria ativa')
    started_at = models.DateTimeField(verbose_name='Início da pausa')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='Fim da pausa')
    duration_minutes = models.PositiveIntegerField(default=0, verbose_name='Duração (min)')

    class Meta:
        verbose_name = 'Pausa'
        verbose_name_plural = 'Pausas'
        ordering = ['started_at']

    def __str__(self):
        return f'Pausa em {self.session} — {self.duration_minutes} min'


# ─────────────────────────────────────────────
# 5. CONTEÚDO ESTUDADO
# ─────────────────────────────────────────────

class StudyContent(models.Model):
    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='contents', verbose_name='Sessão')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='contents', verbose_name='Matéria')
    description = models.CharField(max_length=255, verbose_name='Conteúdo estudado')
    date = models.DateField(verbose_name='Data')
    minutes_spent = models.PositiveIntegerField(default=0, verbose_name='Tempo dedicado (min)')

    class Meta:
        verbose_name = 'Conteúdo estudado'
        verbose_name_plural = 'Conteúdos estudados'
        ordering = ['-date']

    def __str__(self):
        return f'{self.subject.name} — {self.description}'


# ─────────────────────────────────────────────
# 6. OBSERVAÇÃO
# ─────────────────────────────────────────────

class Observation(models.Model):
    TYPE_CHOICES = [
        ('duvida', 'Dúvida'),
        ('observacao', 'Observação'),
        ('pesquisa', 'Pesquisa'),
        ('resposta', 'Resposta de questionário'),
    ]

    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='observations', verbose_name='Sessão')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='observations', verbose_name='Matéria')
    type = models.CharField(max_length=15, choices=TYPE_CHOICES, verbose_name='Tipo')
    text = models.TextField(verbose_name='Texto')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data/hora')

    class Meta:
        verbose_name = 'Observação'
        verbose_name_plural = 'Observações'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_type_display()}] {self.subject.name} — {self.created_at.strftime("%d/%m/%Y %H:%M")}'


# ─────────────────────────────────────────────
# 7. MÉTRICAS SEMANAIS E MENSAIS
# ─────────────────────────────────────────────

class WeeklyMetrics(models.Model):
    """Snapshot calculado ao final de cada semana via pandas/matplotlib."""
    week_start = models.DateField(verbose_name='Início da semana')
    week_end = models.DateField(verbose_name='Fim da semana')
    total_minutes = models.PositiveIntegerField(default=0, verbose_name='Total de minutos estudados')
    net_minutes = models.PositiveIntegerField(default=0, verbose_name='Minutos líquidos')
    total_pauses = models.PositiveIntegerField(default=0, verbose_name='Total de pausas')
    pause_minutes = models.PositiveIntegerField(default=0, verbose_name='Minutos de pausas')
    efficiency = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Eficiência (%)')
    procrastination_index = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Índice de procrastinação (%)')
    most_studied_subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.SET_NULL, related_name='weekly_top', verbose_name='Matéria mais estudada')
    most_procrastinated_subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.SET_NULL, related_name='weekly_procrastinated', verbose_name='Matéria mais procrastinada')
    study_days = models.PositiveIntegerField(default=0, verbose_name='Dias com estudo')
    report_json = models.JSONField(default=dict, blank=True, verbose_name='Dados completos (JSON)')
    chart_path = models.CharField(max_length=255, blank=True, verbose_name='Caminho do gráfico gerado')
    generated_at = models.DateTimeField(auto_now=True, verbose_name='Gerado em')

    class Meta:
        verbose_name = 'Métrica semanal'
        verbose_name_plural = 'Métricas semanais'
        ordering = ['-week_start']
        unique_together = [['week_start', 'week_end']]

    def __str__(self):
        return f'Semana {self.week_start} a {self.week_end} — {self.efficiency}% eficiência'


class MonthlyMetrics(models.Model):
    """Snapshot calculado ao final de cada mês via pandas/matplotlib."""
    year = models.PositiveIntegerField(verbose_name='Ano')
    month = models.PositiveIntegerField(verbose_name='Mês')
    total_minutes = models.PositiveIntegerField(default=0, verbose_name='Total de minutos estudados')
    net_minutes = models.PositiveIntegerField(default=0, verbose_name='Minutos líquidos')
    total_pauses = models.PositiveIntegerField(default=0, verbose_name='Total de pausas')
    pause_minutes = models.PositiveIntegerField(default=0, verbose_name='Minutos de pausas')
    efficiency = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Eficiência (%)')
    procrastination_index = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Índice de procrastinação (%)')
    most_studied_subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.SET_NULL, related_name='monthly_top', verbose_name='Matéria mais estudada')
    study_days = models.PositiveIntegerField(default=0, verbose_name='Dias com estudo')
    goals_hit = models.PositiveIntegerField(default=0, verbose_name='Metas de matérias atingidas')
    report_json = models.JSONField(default=dict, blank=True, verbose_name='Dados completos (JSON)')
    chart_path = models.CharField(max_length=255, blank=True, verbose_name='Caminho do gráfico gerado')
    generated_at = models.DateTimeField(auto_now=True, verbose_name='Gerado em')

    class Meta:
        verbose_name = 'Métrica mensal'
        verbose_name_plural = 'Métricas mensais'
        ordering = ['-year', '-month']
        unique_together = [['year', 'month']]

    def __str__(self):
        return f'{self.month:02d}/{self.year} — {self.efficiency}% eficiência'
