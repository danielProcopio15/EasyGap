"""
Comando: generate_reports

Uso:
    # Retrospecto da semana atual
    python manage.py generate_reports --weekly

    # Retrospecto de uma semana específica (qualquer data dentro dela)
    python manage.py generate_reports --weekly --date 2026-05-05

    # Retrospecto do mês atual
    python manage.py generate_reports --monthly

    # Retrospecto de mês/ano específico
    python manage.py generate_reports --monthly --year 2026 --month 4

    # Gerar ambos de uma vez
    python manage.py generate_reports --weekly --monthly
"""

import pendulum
from django.core.management.base import BaseCommand
from estudos.analytics import generate_weekly_report, generate_monthly_report


class Command(BaseCommand):
    help = 'Gera retrospectos semanais e/ou mensais usando pandas e matplotlib.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--weekly',
            action='store_true',
            help='Gera o retrospecto semanal.',
        )
        parser.add_argument(
            '--monthly',
            action='store_true',
            help='Gera o retrospecto mensal.',
        )
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Data de referência para o relatório semanal (YYYY-MM-DD). Padrão: hoje.',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Ano do relatório mensal. Padrão: ano atual.',
        )
        parser.add_argument(
            '--month',
            type=int,
            default=None,
            help='Mês do relatório mensal (1–12). Padrão: mês atual.',
        )

    def handle(self, *args, **options):
        generated_any = False

        if options['weekly']:
            generated_any = True
            if options['date']:
                ref = pendulum.parse(options['date'], tz='America/Sao_Paulo')
            else:
                ref = pendulum.now('America/Sao_Paulo')

            self.stdout.write(f'Gerando retrospecto semanal para a semana de {ref.to_date_string()}...')
            obj = generate_weekly_report(ref)
            self.stdout.write(self.style.SUCCESS(
                f'  Semana {obj.week_start} a {obj.week_end} — '
                f'{obj.net_minutes} min líquidos | '
                f'{obj.efficiency}% eficiência | '
                f'Gráfico: {obj.chart_path}'
            ))

        if options['monthly']:
            generated_any = True
            obj = generate_monthly_report(
                year=options.get('year'),
                month=options.get('month'),
            )
            self.stdout.write(f'Gerando retrospecto mensal {obj.month:02d}/{obj.year}...')
            self.stdout.write(self.style.SUCCESS(
                f'  {obj.month:02d}/{obj.year} — '
                f'{obj.net_minutes} min líquidos | '
                f'{obj.efficiency}% eficiência | '
                f'{obj.goals_hit} meta(s) atingida(s) | '
                f'Gráfico: {obj.chart_path}'
            ))

        if not generated_any:
            self.stdout.write(self.style.WARNING(
                'Nenhuma opção fornecida. Use --weekly e/ou --monthly.'
            ))
