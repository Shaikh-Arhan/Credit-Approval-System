from django.core.management.base import BaseCommand
from loans.tasks import ingest_customer_data, ingest_loan_data
import os

class Command(BaseCommand):
    help = 'Ingest initial data from Excel files'

    def handle(self, *args, **options):
        # Assuming files are placed in a data directory at project root
        customer_file = os.path.join('data', 'customer_data.xlsx')
        loan_file = os.path.join('data', 'loan_data.xlsx')

        if not os.path.exists(customer_file) or not os.path.exists(loan_file):
            self.stdout.write(self.style.ERROR('Data files not found in data/ directory'))
            return

        # Trigger async tasks
        customer_task = ingest_customer_data.delay(customer_file)
        loan_task = ingest_loan_data.delay(loan_file)

        self.stdout.write(self.style.SUCCESS(
            f'Started data ingestion tasks. Customer Task ID: {customer_task.id}, Loan Task ID: {loan_task.id}'
        ))