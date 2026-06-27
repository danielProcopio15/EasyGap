from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Matérias
    path('materias/', views.materia_lista, name='materia_lista'),
    path('materias/nova/', views.materia_nova, name='materia_nova'),
    path('materias/<int:pk>/editar/', views.materia_editar, name='materia_editar'),
    path('materias/<int:pk>/remover/', views.materia_remover, name='materia_remover'),
    path('materias/<int:pk>/notas/', views.materia_notas_update, name='materia_notas_update'),

    # Cronogramas
    path('cronogramas/', views.cronograma_lista, name='cronograma_lista'),
    path('cronogramas/novo/', views.cronograma_novo, name='cronograma_novo'),
    path('cronogramas/<int:pk>/editar/', views.cronograma_editar, name='cronograma_editar'),
    path('cronogramas/<int:pk>/remover/', views.cronograma_remover, name='cronograma_remover'),
    path('cronogramas/<int:pk>/ativar/', views.cronograma_ativar, name='cronograma_ativar'),

    # Agenda diária
    path('agenda/', views.agenda_diaria, name='agenda_diaria'),
    path('agenda/iniciar/subject/<int:subject_pk>/', views.iniciar_sessao_subject, name='iniciar_sessao_subject'),

    # Runner de sessão
    path('sessao/<int:pk>/', views.sessao_runner, name='sessao_runner'),
    path('sessao/<int:pk>/pausar/', views.sessao_pausar, name='sessao_pausar'),
    path('sessao/<int:pk>/retomar/', views.sessao_retomar, name='sessao_retomar'),
    path('sessao/<int:pk>/encerrar/', views.sessao_encerrar, name='sessao_encerrar'),
    path('sessao/<int:pk>/pular/', views.sessao_pular, name='sessao_pular'),
    path('sessao/<int:pk>/conteudo/', views.sessao_add_conteudo, name='sessao_add_conteudo'),
    path('sessao/<int:pk>/observacao/', views.sessao_add_observacao, name='sessao_add_observacao'),

    # Produtividade
    path('produtividade/', views.produtividade, name='produtividade'),

    # Rendimentos
    path('rendimentos/', views.rendimentos, name='rendimentos'),

    # Anotações
    path('anotacoes/', views.anotacoes, name='anotacoes'),
]
