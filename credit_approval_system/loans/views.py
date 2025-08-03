from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from .models import Customer, Loan
from .serializers import (
    CustomerSerializer,
    RegisterCustomerSerializer,
    CheckEligibilitySerializer,
    CreateLoanSerializer,
    LoanDetailSerializer
)
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
import math
from datetime import date
from django.db.models import Sum

class RegisterCustomerView(APIView):
    def post(self, request):
        serializer = RegisterCustomerSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            response_data = {
                'customer_id': customer.customer_id,
                'name': customer.name,
                'age': customer.age,
                'monthly_income': customer.monthly_salary,
                'approved_limit': customer.approved_limit,
                'phone_number': customer.phone_number
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckEligibilityView(APIView):
    def post(self, request):
        serializer = CheckEligibilitySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        # Calculate credit score
        credit_score = self.calculate_credit_score(customer)

        # Check eligibility based on credit score
        approval, corrected_interest_rate = self.check_loan_approval(
            credit_score, 
            interest_rate, 
            customer, 
            loan_amount, 
            tenure
        )

        # Calculate monthly installment
        if approval:
            monthly_installment = self.calculate_monthly_installment(
                loan_amount, 
                corrected_interest_rate, 
                tenure
            )
        else:
            monthly_installment = 0

        response_data = {
            'customer_id': customer_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate,
            'tenure': tenure,
            'monthly_installment': monthly_installment
        }

        return Response(response_data)

    def calculate_credit_score(self, customer):
        # Rule 1: If sum of current loans > approved limit, credit score = 0
        total_current_loans = Loan.objects.filter(
            customer=customer, 
            is_active=True
        ).aggregate(total=Sum('loan_amount'))['total'] or 0

        if total_current_loans > customer.approved_limit:
            return 0

        # Get all loans for the customer
        loans = Loan.objects.filter(customer=customer)

        if not loans.exists():
            return 100  # No loans means perfect credit (for this simple implementation)

        # Calculate components
        total_loans = loans.count()
        loans_paid_on_time = sum(loan.emis_paid_on_time for loan in loans)
        current_year_loans = loans.filter(start_date__year=date.today().year).count()
        total_loan_volume = sum(loan.loan_amount for loan in loans)

        # Simple credit score calculation (this can be enhanced)
        credit_score = min(
            100,
            (loans_paid_on_time * 10) +  # Weight for on-time payments
            (total_loans * 5) +          # Weight for number of loans
            (current_year_loans * 15) +   # Weight for recent activity
            (total_loan_volume / 10000)   # Weight for loan volume
        )

        return max(0, min(100, credit_score))

    def check_loan_approval(self, credit_score, interest_rate, customer, loan_amount, tenure):
        # Check if sum of all current EMIs > 50% of monthly salary
        current_monthly_emis = Loan.objects.filter(
            customer=customer, 
            is_active=True
        ).aggregate(total=Sum('monthly_repayment'))['total'] or 0

        if current_monthly_emis > (customer.monthly_salary * 0.5):
            return False, interest_rate

        # Check credit score conditions
        if credit_score > 50:
            return True, interest_rate
        elif 30 < credit_score <= 50:
            if interest_rate >= 12:
                return True, interest_rate
            else:
                return False, 12
        elif 10 < credit_score <= 30:
            if interest_rate >= 16:
                return True, interest_rate
            else:
                return False, 16
        else:
            return False, interest_rate

    def calculate_monthly_installment(self, principal, annual_rate, tenure_months):
        monthly_rate = annual_rate / 12 / 100
        emi = principal * monthly_rate * (1 + monthly_rate)**tenure_months
        emi /= ((1 + monthly_rate)**tenure_months - 1)
        return round(emi, 2)


class CreateLoanView(APIView):
    def post(self, request):
        serializer = CreateLoanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check eligibility
        credit_score = CheckEligibilityView().calculate_credit_score(customer)
        approval, corrected_interest_rate = CheckEligibilityView().check_loan_approval(
            credit_score, interest_rate, customer, loan_amount, tenure
        )

        if not approval:
            return Response({
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': 'Loan not approved based on eligibility criteria',
                'monthly_installment': 0
            })

        # Calculate monthly installment with corrected interest rate
        monthly_installment = CheckEligibilityView().calculate_monthly_installment(
            loan_amount, corrected_interest_rate, tenure
        )

        # Create loan
        with transaction.atomic():
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=loan_amount,
                tenure=tenure,
                interest_rate=corrected_interest_rate,
                monthly_repayment=monthly_installment,
                emis_paid_on_time=0,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30*tenure),
                is_active=True
            )

            # Update customer's current debt
            customer.current_debt += loan_amount
            customer.save()

        return Response({
            'loan_id': loan.loan_id,
            'customer_id': customer_id,
            'loan_approved': True,
            'message': 'Loan approved successfully',
            'monthly_installment': monthly_installment
        })


class ViewLoanView(APIView):
    def get(self, request, loan_id):
        loan = get_object_or_404(Loan, loan_id=loan_id)
        serializer = LoanDetailSerializer(loan)
        return Response(serializer.data)


class ViewCustomerLoansView(APIView):
    def get(self, request, customer_id):
        loans = Loan.objects.filter(customer_id=customer_id, is_active=True)
        serializer = LoanDetailSerializer(loans, many=True)
        return Response(serializer.data)

        