# -*- coding: utf-8 -*-

# check scheduler job exception and send notify message

def start():
    from datetime import datetime
    from django_apscheduler.models import DjangoJobExecution
    from webull_trader.models import NotifiedErrorExecution
    from scripts import utils

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


if __name__ == "django.core.management.commands.shell":
    start()