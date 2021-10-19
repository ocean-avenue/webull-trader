# -*- coding: utf-8 -*-

# check scheduler job exception and send notify message

def start():
    from datetime import datetime
    from django_apscheduler.models import DjangoJobExecution
    from webull_trader.models import NotifiedErrorExecution
    from common import utils
    from scripts import clear_positions

    today = datetime.today()
    # all today's executions
    executions = DjangoJobExecution.objects.filter(
        run_time__year=today.year, run_time__month=today.month, run_time__day=today.day)

    for execution in executions:
        if execution.status == DjangoJobExecution.ERROR:
            execution_id = execution.id
            # check if notified
            notified_execution = NotifiedErrorExecution.objects.filter(
                execution_id=execution_id).first()
            if notified_execution:
                # already notified
                continue
            # notify message
            utils.notify_message(
                "Job {} execution exception, fix now!".format(execution.job.id))
            # mark already notified
            notified_execution = NotifiedErrorExecution(
                execution_id=execution_id)
            notified_execution.save()

            # clear all position if trading job exception
            if 'trading' in execution.job.id:
                # check if there is any existing trading job running
                trading_running = False
                running_executions = DjangoJobExecution.objects.filter(
                    run_time__year=today.year, run_time__month=today.month, run_time__day=today.day, status=DjangoJobExecution.SENT)
                for running_execution in running_executions:
                    if 'trading' in running_execution.job.id:
                        trading_running = True
                        break
                if not trading_running:
                    clear_positions.start()


if __name__ == "django.core.management.commands.shell":
    start()
