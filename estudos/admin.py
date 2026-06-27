from django.contrib import admin
from .models import (
    Subject, StudyPlan, StudyPlanItem,
    StudySession, Pause, StudyContent,
    Observation, WeeklyMetrics, MonthlyMetrics,
)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'difficulty', 'priority', 'goal_hours', 'status')
    list_filter = ('difficulty', 'priority', 'status')
    search_fields = ('name',)


class StudyPlanItemInline(admin.TabularInline):
    model = StudyPlanItem
    extra = 1


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [StudyPlanItemInline]


class PauseInline(admin.TabularInline):
    model = Pause
    extra = 0
    readonly_fields = ('duration_minutes',)


class StudyContentInline(admin.TabularInline):
    model = StudyContent
    extra = 1


class ObservationInline(admin.TabularInline):
    model = Observation
    extra = 1


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('date', 'subject', 'planned_minutes', 'gross_minutes', 'net_minutes', 'status')
    list_filter = ('status', 'subject', 'date')
    readonly_fields = ('efficiency',)
    inlines = [PauseInline, StudyContentInline, ObservationInline]


@admin.register(WeeklyMetrics)
class WeeklyMetricsAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'week_end', 'total_minutes', 'net_minutes', 'efficiency', 'study_days')
    readonly_fields = ('generated_at',)


@admin.register(MonthlyMetrics)
class MonthlyMetricsAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'total_minutes', 'net_minutes', 'efficiency', 'study_days', 'goals_hit')
    readonly_fields = ('generated_at',)
