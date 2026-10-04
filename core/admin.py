from django.contrib import admin
from django.utils.safestring import mark_safe 
from django.utils.html import format_html
from .models import (
    CustomUser, PlatformSettings, Level, BankDetails, Deposit, 
    Withdrawal, Task, Roulette, RouletteSettings, UserLevel, 
    PlatformBankDetails, Post, Coupon, CouponRedemption
)

# --- USUÁRIO CUSTOMIZADO ---
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'available_balance', 'subsidy_balance', 'is_restricted', 'is_staff', 'is_active', 'date_joined', 'roulette_spins')
    search_fields = ('phone_number', 'invite_code')
    list_filter = ('is_restricted', 'is_staff', 'is_active', 'level_active')
    list_editable = ('is_restricted',)

# --- CONFIGURAÇÕES DA PLATAFORMA ---
@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'whatsapp_link', 'history_text', 'deposit_instruction', 'withdrawal_instruction')
    search_fields = ('whatsapp_link',)

# --- NÍVEIS / PLANOS ---
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_category_badge', 'deposit_value', 'daily_gain', 'monthly_gain', 'cycle_days', 'get_active_users_count')
    list_filter = ('category', 'cycle_days')
    search_fields = ('name',)
    list_editable = ('deposit_value', 'daily_gain', 'monthly_gain', 'cycle_days')
    ordering = ('category', 'deposit_value')

    @admin.display(description="Categoria")
    def get_category_badge(self, obj):
        colors = {
            'long_term': '#28a745',  
            'short_term': '#007bff', 
            'activities': '#dc3545', 
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_category_display()
        )

    @admin.display(description="Utilizadores Ativos")
    def get_active_users_count(self, obj):
        count = UserLevel.objects.filter(level=obj, is_active=True).count()
        return format_html('<strong>{}</strong>', count)

# --- BANCOS DOS USUÁRIOS ---
@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ('user', 'bank_name', 'account_holder_name')
    search_fields = ('user__phone_number', 'bank_name', 'account_holder_name')

# --- CONTAS DA PLATAFORMA ---
@admin.register(PlatformBankDetails)
class PlatformBankDetailsAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'IBAN', 'account_holder_name', 'is_crypto', 'is_active')
    list_filter = ('is_crypto', 'is_active')
    search_fields = ('bank_name', 'IBAN', 'account_holder_name')
    list_editable = ('is_crypto', 'is_active')

    def get_fieldsets(self, request, obj=None):
        if obj and obj.is_crypto:
            fieldsets = (
                ('Informações da Wallet USDT', {
                    'fields': (
                        'is_crypto',
                        'bank_name',
                        'IBAN',
                        'account_holder_name',
                        'is_active',
                    ),
                    'description': 'Preencha os dados referentes à rede e endereço da carteira USDT.',
                }),
            )
        elif obj and not obj.is_crypto:
            fieldsets = (
                ('Informações da Conta Bancária (Kwanza)', {
                    'fields': (
                        'is_crypto',
                        'bank_name',
                        'IBAN',
                        'account_holder_name',
                        'is_active',
                    ),
                    'description': 'Preencha os dados referentes ao banco nacional e IBAN.',
                }),
            )
        else:
            fieldsets = (
                ('Detalhes da Conta da Plataforma', {
                    'fields': (
                        'is_crypto',
                        'bank_name',
                        'IBAN',
                        'account_holder_name',
                        'is_active',
                    ),
                    'description': 'Selecione primeiro se é Canal USDT/Crypto para direcionar os campos corretos.',
                }),
            )
        return fieldsets

# --- TRANSAÇÕES ---
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'is_approved', 'created_at', 'proof_link') 
    search_fields = ('user__phone_number',)
    list_filter = ('is_approved',)
    
    fields = ('user', 'amount', 'proof_of_payment', 'current_proof_display', 'is_approved')
    readonly_fields = ('current_proof_display',)

    def proof_link(self, obj):
        if obj.proof_of_payment:
            return mark_safe(f'<a href="{obj.proof_of_payment.url}" target="_blank">Ver Comprovativo</a>')
        return "Nenhum"
    proof_link.short_description = 'Comprovativo'

    def current_proof_display(self, obj):
        if obj.proof_of_payment:
            return mark_safe(f'''
                <a href="{obj.proof_of_payment.url}" target="_blank">Ver Imagem em Tamanho Real</a><br/>
                <img src="{obj.proof_of_payment.url}" style="max-width:300px; height:auto; margin-top: 10px;" />
            ''')
        return "Nenhum Comprovativo Carregado"
    current_proof_display.short_description = 'Comprovativo Atual'

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = Deposit.objects.get(pk=obj.pk)
            if not old_obj.is_approved and obj.is_approved:
                obj.user.available_balance += obj.amount
                obj.user.save()
        else:
            if obj.is_approved:
                obj.user.available_balance += obj.amount
                obj.user.save()
        super().save_model(request, obj, form, change)

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'amount', 'get_amount_real', 'get_taxed_amount_kz', 
        'get_taxed_amount_real', 'get_bank_details', 'status', 'created_at'
    )
    search_fields = ('user__phone_number',)
    list_filter = ('status', 'user')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Se for administrador auxiliar, filtra com base no campo ou permissão específica
        # Caso queira atribuir um filtro personalizado por admin, ajuste aqui conforme sua regra de país.
        return qs

    @admin.display(description="Valor em Real (R$)")
    def get_amount_real(self, obj):
        # 1 Real = 200 Kz => Valor em Kz / 200
        real_value = float(obj.amount) / 200.0
        return f"R$ {real_value:,.2f}"

    @admin.display(description="Líquido Kz (-5%)")
    def get_taxed_amount_kz(self, obj):
        taxed = float(obj.amount) * 0.95
        return f"{taxed:,.2f} Kz"

    @admin.display(description="Líquido Real (-5%)")
    def get_taxed_amount_real(self, obj):
        taxed_kz = float(obj.amount) * 0.95
        real_value = taxed_kz / 200.0
        return f"R$ {real_value:,.2f}"

    @admin.display(description="Dados Bancários do Cliente")
    def get_bank_details(self, obj):
        bank = BankDetails.objects.filter(user=obj.user).first()
        if bank:
            return format_html(
                '<strong>Banco:</strong> {}<br><strong>Titular:</strong> {}<br><strong>Conta/IBAN:</strong> {}',
                bank.bank_name, bank.account_holder_name, getattr(bank, 'account_number', getattr(bank, 'IBAN', 'N/D'))
            )
        return format_html('<span style="color: red;">Sem dados bancários</span>')

# --- TAREFAS ---
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('user', 'earnings', 'completed_at')
    search_fields = ('user__phone_number',)


# --- CUPOM ---
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = (
        'code',
        'reward',
        'is_active',
        'used_count',
        'max_uses',
        'expires_at',
        'created_at',
    )

    search_fields = (
        'code',
    )

    list_filter = (
        'is_active',
        'expires_at',
        'created_at',
    )

    list_editable = (
        'reward',
        'is_active',
    )

    readonly_fields = (
        'used_count',
        'created_at',
        'updated_at',
    )

    ordering = (
        '-created_at',
    )


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):

    list_display = (
        'coupon',
        'user',
        'reward',
        'redeemed_at',
    )

    search_fields = (
        'coupon__code',
        'user__phone_number',
    )

    list_filter = (
        'redeemed_at',
    )

    readonly_fields = (
        'coupon',
        'user',
        'reward',
        'redeemed_at',
    )

    ordering = (
        '-redeemed_at',
    )

# --- NÍVEL DO USUÁRIO ---
@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'level', 'get_category_badge', 'days_progress', 
        'accumulated_credit', 'is_active', 'last_task_processed_at'
    )
    search_fields = ('user__phone_number', 'level__name')
    list_filter = ('is_active', 'level__category', 'cycle_completed')
    readonly_fields = ('purchase_date', 'activated_at')
    
    fields = (
        'user', 'level', 'is_active', 'days_processed', 
        'accumulated_credit', 'last_task_processed_at', 
        'cycle_completed', 'payout_executed', 'activated_at'
    )

    @admin.display(description="Progresso (Dias)")
    def days_progress(self, obj):
        return f"{obj.days_processed}/{obj.level.cycle_days}"

    @admin.display(description="Categoria")
    def get_category_badge(self, obj):
        colors = {
            'long_term': '#28a745',
            'short_term': '#007bff',
            'activities': '#dc3545',
        }
        color = colors.get(obj.level.category, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">{}</span>',
            color,
            obj.level.get_category_display()
        )

# --- COMUNIDADE / BLOG ---
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_snippet', 'has_image', 'created_at')
    search_fields = ('user__phone_number', 'content')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'image_preview')

    fields = ('user', 'content', 'image', 'image_preview', 'created_at')

    @admin.display(description="Conteúdo")
    def content_snippet(self, obj):
        if obj.content:
            return obj.content[:50] + ("..." if len(obj.content) > 50 else "")
        return "Sem texto"

    @admin.display(description="Tem Imagem?")
    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True

    @admin.display(description="Visualização da Imagem")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 300px; height: auto; border-radius: 6px;" />', obj.image.url)
        return "Sem imagem anexada"
        