from django import forms
from .models import Subject, StudyPlan, StudyPlanItem


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'certames', 'description', 'difficulty', 'priority', 'default_minutes', 'goal_hours', 'status', 'notes', 'has_discursiva', 'has_oral']
        widgets = {
            'name':            forms.TextInput(attrs={'class': 'input'}),
            'description':     forms.Textarea(attrs={'class': 'input', 'rows': 3}),
            'difficulty':      forms.Select(attrs={'class': 'input'}),
            'priority':        forms.Select(attrs={'class': 'input'}),
            'default_minutes': forms.NumberInput(attrs={'class': 'input', 'min': '5'}),
            'goal_hours':      forms.NumberInput(attrs={'class': 'input', 'step': '0.5', 'min': '0'}),
            'status':          forms.Select(attrs={'class': 'input'}),
            'notes':           forms.Textarea(attrs={'class': 'input', 'rows': 3}),
            'certames':        forms.Textarea(attrs={'class': 'input', 'rows': 3, 'placeholder': 'Um concurso por linha\nEx: TJSP 2026\nPCDF 2026'}),
            'has_discursiva':  forms.CheckboxInput(attrs={'class': 'toggle-bool', 'id': 'id_has_discursiva'}),
            'has_oral':        forms.CheckboxInput(attrs={'class': 'toggle-bool', 'id': 'id_has_oral'}),
        }
        labels = {
            'name':            'Nome',
            'description':     'Descrição',
            'difficulty':      'Dificuldade',
            'priority':        'Prioridade',
            'default_minutes': 'Tempo padrão de sessão (min)',
            'goal_hours':      'Meta de horas diárias',
            'status':          'Status',
            'notes':           'Observações gerais',
            'certames':        'Certames (um por linha)',
            'has_discursiva':  'Discursiva',
            'has_oral':        'Oral',
        }
        help_texts = {
            'priority': 'Alta = peso 3 · Média = 2 · Baixa = 1',
        }


class StudyPlanForm(forms.ModelForm):
    class Meta:
        model = StudyPlan
        fields = ['name', 'status']
        widgets = {
            'name':   forms.TextInput(attrs={'class': 'input'}),
            'status': forms.Select(attrs={'class': 'input'}),
        }
        labels = {
            'name':   'Nome do cronograma',
            'status': 'Status',
        }


class StudyPlanItemForm(forms.ModelForm):
    class Meta:
        model = StudyPlanItem
        fields = ['subject', 'day_of_week', 'order', 'planned_minutes', 'scheduled_time']
        widgets = {
            'subject':         forms.Select(attrs={'class': 'input'}),
            'day_of_week':     forms.HiddenInput(),   # definido por JavaScript
            'order':           forms.HiddenInput(),   # definido por JavaScript
            'planned_minutes': forms.NumberInput(attrs={'class': 'input', 'min': '5'}),
            'scheduled_time':  forms.TimeInput(attrs={'class': 'input', 'type': 'time'}),
        }
        labels = {
            'subject':         'Matéria',
            'planned_minutes': 'Tempo (min)',
            'scheduled_time':  'Horário previsto',
        }
