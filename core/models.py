from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

# --- GESTOR DE USUÁRIOS ---
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('O número de telefone deve ser fornecido')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(phone_number, password, **extra_fields)


# --- MODELO DE USUÁRIO ---
class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Número de Telefone")
    full_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome Completo")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name="Foto de Perfil")
    is_restricted = models.BooleanField(default=False, verbose_name="Usuário Restrito (Apenas Leitura no Blog)")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    invite_code = models.CharField(max_length=8, unique=True, blank=True, null=True)
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Convidado por")
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Disponível")
    subsidy_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo de Subsídios")
    level_active = models.BooleanField(default=False, verbose_name="Nível Ativo")
    roulette_spins = models.IntegerField(default=0, verbose_name="Giros da Roleta")

    # --- CAMPOS ADICIONADOS PARA RESOLVER O ERRO DO USDT NO PERFIL ---
    usdt_channel = models.CharField(max_length=50, blank=True, null=True, verbose_name="Canal USDT (Ex: TRC20)")
    usdt_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Endereço da Wallet USDT")

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number

    def save(self, *args, **kwargs):
        if not self.invite_code:
            while True:
                new_invite_code = uuid.uuid4().hex[:8]
                if not CustomUser.objects.filter(invite_code=new_invite_code).exists():
                    self.invite_code = new_invite_code
                    break
        super().save(*args, **kwargs)


# --- CONFIGURAÇÕES DA PLATAFORMA ---
class PlatformSettings(models.Model):
    whatsapp_link = models.URLField(verbose_name="Link do grupo de apoio do WhatsApp")
    history_text = models.TextField(verbose_name="Texto da página 'Sobre'")
    deposit_instruction = models.TextField(verbose_name="Texto de instrução para depósito")
    withdrawal_instruction = models.TextField(verbose_name="Texto de instrução para saque")
    
    class Meta:
        verbose_name = "Configuração da Plataforma"
        verbose_name_plural = "Configurações da Plataforma"

    def __str__(self):
        return "Configurações da Plataforma"


class PlatformBankDetails(models.Model):
    bank_name = models.CharField(max_length=100, verbose_name="Nome do Banco / Rede USDT")
    IBAN = models.CharField(max_length=150, verbose_name="IBAN / Endereço da Wallet")
    account_holder_name = models.CharField(max_length=100, verbose_name="Nome do Titular / Descrição do Canal", blank=True, null=True)
    is_crypto = models.BooleanField(default=False, verbose_name="É Canal USDT/Crypto?")
    is_active = models.BooleanField(default=True, verbose_name="Ativo para Depósito")

    class Meta:
        verbose_name = "Detalhe Bancário da Plataforma"
        verbose_name_plural = "Detalhes Bancários da Plataforma"
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_holder_name or self.IBAN}"


class BankDetails(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, verbose_name="Usuário")
    bank_name = models.CharField(max_length=100, verbose_name="Nome do Banco", blank=True, null=True)
    IBAN = models.CharField(max_length=50, verbose_name="IBAN", blank=True, null=True)
    account_holder_name = models.CharField(max_length=100, verbose_name="Nome do Titular", blank=True, null=True)
    
    class Meta:
        verbose_name = "Detalhe Bancário do Usuário"
        verbose_name_plural = "Detalhes Bancários do Usuário"

    def __str__(self):
        return f"Detalhes Bancários de {self.user.phone_number}"


# --- TRANSAÇÕES FINANCEIRAS ---
class Deposit(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Usuário")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor")
    proof_of_payment = models.ImageField(upload_to='deposit_proofs/', verbose_name="Comprovativo")
    is_approved = models.BooleanField(default=False, verbose_name="Aprovado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"

    def __str__(self):
        return f"Depósito de {self.amount} por {self.user.phone_number}"


class Withdrawal(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Usuário")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor")
    status = models.CharField(max_length=20, default='Pending', verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    class Meta:
        verbose_name = "Saque"
        verbose_name_plural = "Saques"

    def __str__(self):
        return f"Saque de {self.amount} por {self.user.phone_number} ({self.status})"


# --- ESTRUTURA DOS PLANOS (NÍVEIS) ---
class Level(models.Model):
    CATEGORY_CHOICES = [
        ('long_term', 'Longo Prazo'),
        ('short_term', 'Curto Prazo'),
        ('activities', 'Actividades'),
    ]

    name = models.CharField(max_length=50, verbose_name="Nome do Nível (Ex: 1, 2, 3)")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='long_term', verbose_name="Categoria do Plano")
    deposit_value = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor de Depósito")
    daily_gain = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Ganho Diário")
    monthly_gain = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Ganho Mensal")
    cycle_days = models.IntegerField(verbose_name="Ciclo (dias)")
    image = models.ImageField(upload_to='level_images/', verbose_name="Imagem")

    class Meta:
        verbose_name = "Nível"
        verbose_name_plural = "Níveis"
        unique_together = ('name', 'category')

    def __str__(self):
        return f"{self.get_category_display()} {self.name} - (Investimento: {self.deposit_value})"

    @property
    def annual_gain(self):
        return self.daily_gain * 365

    @property
    def total_expected_gain(self):
        return self.daily_gain * self.cycle_days


# --- CONTROLE REAL DE COMPRA E EXECUÇÃO DE PLANOS ---
class UserLevel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Usuário")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, verbose_name="Nível")
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name="Data da Compra")
    activated_at = models.DateTimeField(default=timezone.now, verbose_name="Data de Ativação")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    cycle_completed = models.BooleanField(default=False, verbose_name="Ciclo Concluído")
    payout_executed = models.BooleanField(default=False, verbose_name="Pago ao Saldo")
    
    days_processed = models.IntegerField(default=0, verbose_name="Dias Processados")
    last_task_processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Último Processamento de Tarefa")
    accumulated_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Crédito Acumulado Retido")

    class Meta:
        verbose_name = "Nível do Usuário"
        verbose_name_plural = "Níveis dos Usuários"

    def clean(self):
        if self.pk:
            return

        existing_count = UserLevel.objects.filter(
            user=self.user,
            level=self.level
        ).count()

        if existing_count >= 3:
            raise ValidationError(
                f"Você já atingiu o limite máximo de 3 aquisições para o plano "
                f"{self.level.get_category_display()} {self.level.name}."
            )

        # Curto Prazo permanece no sistema para não quebrar dados
        # ou funcionalidades antigas, mas não é exigido para Actividades.
        if self.level.category == 'short_term':
            has_long_term = UserLevel.objects.filter(
                user=self.user,
                level__category='long_term',
                level__name=self.level.name,
                is_active=True
            ).exists()

            if not has_long_term:
                raise ValidationError(
                    f"Operação bloqueada. Para ativar o Curto Prazo "
                    f"{self.level.name}, você precisa obrigatoriamente ter "
                    f"o Longo Prazo {self.level.name} Ativo."
                )

        # Actividades exigem apenas o Diário/Longo Prazo
        # correspondente ao mesmo nível.
        if self.level.category == 'activities':
            has_long_term = UserLevel.objects.filter(
                user=self.user,
                level__category='long_term',
                level__name=self.level.name,
                is_active=True
            ).exists()

            if not has_long_term:
                raise ValidationError(
                    f"Operação bloqueada. Para ativar a Actividade "
                    f"{self.level.name}, você precisa ter o plano "
                    f"Diário {self.level.name} ativo."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.user.phone_number} - "
            f"{self.level.get_category_display()} {self.level.name} "
            f"[{self.days_processed}/{self.level.cycle_days}]"
        )


# --- MODELO DE TAREFAS / HISTÓRICO DE CAPTAÇÃO REAL ---
class Task(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Usuário")
    user_level = models.ForeignKey(UserLevel, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Nível Vinculado")
    earnings = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Ganhos")
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Conclusão")

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"

    def __str__(self):
        return f"Rendimento de {self.earnings} gerado para {self.user.phone_number}"

# --- CUPOM ---

class Coupon(models.Model):
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Código do Cupom"
    )

    reward = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Valor da Recompensa"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Cupom Ativo"
    )

    max_uses = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Limite de Utilizações",
        help_text=(
            "Número máximo de vezes que este cupom pode ser utilizado. "
            "Deixe vazio para permitir utilizações ilimitadas."
        )
    )

    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Utilizações"
    )

    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Data de Expiração"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    class Meta:
        verbose_name = "Cupom"
        verbose_name_plural = "Cupons"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.reward}"


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="redemptions",
        verbose_name="Cupom"
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="coupon_redemptions",
        verbose_name="Usuário"
    )

    reward = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Recompensa Recebida"
    )

    redeemed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data do Resgate"
    )

    class Meta:
        verbose_name = "Resgate de Cupom"
        verbose_name_plural = "Resgates de Cupons"
        ordering = ["-redeemed_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["coupon", "user"],
                name="unique_coupon_user"
            )
        ]

    def __str__(self):
        return (
            f"{self.user.phone_number} - "
            f"{self.coupon.code} - "
            f"{self.reward}"
        )

# --- SISTEMA DE COMUNIDADE / BLOG ---
class Post(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Autor")
    content = models.TextField(blank=True, null=True, verbose_name="Mensagem")
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True, verbose_name="Imagem da Publicação")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Envio")

    class Meta:
        verbose_name = "Publicação da Comunidade"
        verbose_name_plural = "Publicações da Comunidade"
        ordering = ['created_at']

    def __str__(self):
        return f"Mensagem de {self.user.phone_number} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

# --- SISTEMA DE ROLETA ---
class Roulette(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Usuário")
    prize_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Prêmio Ganho")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data do Giro")

    class Meta:
        verbose_name = "Roleta"
        verbose_name_plural = "Roletas"

    def __str__(self):
        return f"Giro de {self.user.phone_number} - Prêmio: {self.prize_amount}"

# --- CONFIGURAÇÕES DA ROLETA ---
class RouletteSettings(models.Model):
    spin_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Custo por Giro")
    is_active = models.BooleanField(default=True, verbose_name="Roleta Ativa")

    class Meta:
        verbose_name = "Configuração da Roleta"
        verbose_name_plural = "Configurações da Roleta"

    def __str__(self):
        return "Configurações da Roleta"
            