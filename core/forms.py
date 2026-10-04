from django import forms
from .models import CustomUser, Deposit, BankDetails

class RegisterForm(forms.ModelForm):
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirme a Senha", widget=forms.PasswordInput)
    
    # Campo para o código de convite de quem convidou o usuário
    invited_by_code = forms.CharField(max_length=8, required=False, label="Código de Convite")

    class Meta:
        model = CustomUser
        # Altera o campo do formulário para o novo nome
        fields = ['phone_number', 'password', 'confirm_password', 'invited_by_code']
    
    # Método clean() para validar o formulário como um todo
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        # Validação para verificar se as senhas coincidem
        if password and confirm_password and password != confirm_password:
            # Adiciona o erro ao campo confirm_password para que seja exibido corretamente
            self.add_error('confirm_password', "As senhas não coincidem.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # A lógica para definir o `invited_by` deve estar na view,
        # e o `invite_code` do novo usuário é gerado no `models.py`.
        
        if commit:
            user.save()
        return user

class DepositForm(forms.ModelForm):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, label="Valor do Depósito")
    proof_of_payment = forms.ImageField(label="Comprovativo de Pagamento")

    class Meta:
        model = Deposit
        fields = ['amount', 'proof_of_payment']

class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, label="Valor a Sacar")

class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = BankDetails
        fields = ['account_holder_name', 'bank_name', 'IBAN']
        labels = {
            'account_holder_name': 'Nome Completo',
            'bank_name': 'Nome do Banco',
            'IBAN': 'IBAN',
        }
        