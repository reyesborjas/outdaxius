# backend/app/api/payment_stripe.py
import stripe
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

router = APIRouter(prefix="/payments/stripe", tags=["payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ============================================================================
# ONBOARDING DE AGENCIAS
# ============================================================================

@router.post("/companies/{company_id}/connect-account")
async def create_connect_account(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una cuenta Stripe Connect para la agencia.
    La agencia manejará sus propios pagos.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    
    # Verificar que el usuario es admin de la empresa
    is_admin = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id,
        CompanyMember.userid == current_user.id,
        CompanyMember.is_admin == True
    ).first()
    
    if not is_admin:
        raise HTTPException(403, "Only company admins can setup payments")
    
    try:
        # Crear cuenta Connect tipo "standard" (la agencia maneja todo)
        account = stripe.Account.create(
            type="standard",  # ✅ Ellos manejan sus propios pagos
            country="CL",
            email=current_user.email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            business_type="company",
            company={
                "name": company.legal_name,
                "tax_id": company.tax_id or company.fiscal_data.get("tax_identification", {}).get("primary_identification_number"),
            },
            metadata={
                "outdaxius_company_id": str(company_id),
                "platform": "outdaxius"
            }
        )
        
        # Guardar el Stripe Account ID
        company.stripe_account_id = account.id
        db.commit()
        
        # Crear link de onboarding para que completen su perfil
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"https://outdaxius.com/company/{company_id}/payments/refresh",
            return_url=f"https://outdaxius.com/company/{company_id}/payments/success",
            type="account_onboarding",
        )
        
        return {
            "stripe_account_id": account.id,
            "onboarding_url": account_link.url,
            "message": "Complete el proceso de verificación en Stripe"
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


# ============================================================================
# PROCESO DE PAGO (Traveler → Agencia directamente)
# ============================================================================

@router.post("/bookings/{booking_id}/create-payment-intent")
async def create_payment_intent(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un PaymentIntent donde el dinero va DIRECTO a la agencia.
    Outdaxius cobra comisión aparte (subscription).
    """
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    # Obtener el schedule y la empresa dueña
    if booking.activity_schedule_id:
        schedule = db.query(ActivitySchedule).filter(
            ActivitySchedule.id == booking.activity_schedule_id
        ).first()
        activity = db.query(Activity).filter(Activity.id == schedule.activity_id).first()
        guide = db.query(User).filter(User.id == activity.created_by).first()
    else:
        schedule = db.query(ProgramSchedule).filter(
            ProgramSchedule.id == booking.program_schedule_id
        ).first()
        program = db.query(Program).filter(Program.id == schedule.program_id).first()
        guide = db.query(User).filter(User.id == program.created_by).first()
    
    # Obtener la empresa del guide
    company_member = db.query(CompanyMember).filter(
        CompanyMember.userid == guide.id,
        CompanyMember.is_active == True
    ).first()
    
    if not company_member:
        raise HTTPException(400, "Guide must belong to a company to accept payments")
    
    company = db.query(Company).filter(Company.id == company_member.companyid).first()
    
    if not company.stripe_account_id:
        raise HTTPException(400, "Company has not setup payment account yet")
    
    # Calcular precio
    amount_cents = int(schedule.price * 100)  # Convertir a centavos
    
    try:
        # ✅ PAGO DIRECTO: application_fee_amount = 0
        # El dinero va 100% a la agencia
        # Tú cobras subscripción mensual aparte
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="clp",  # Peso chileno
            application_fee_amount=0,  # ✅ NO cobras fee aquí
            transfer_data={
                "destination": company.stripe_account_id,  # ✅ Directo a la agencia
            },
            metadata={
                "booking_id": str(booking_id),
                "company_id": str(company.id),
                "user_email": current_user.email,
            }
        )
        
        # Guardar referencia
        payment = Payment(
            booking_id=booking_id,
            amount=schedule.price,
            currency="CLP",
            status="pending",
            reference=payment_intent.id,
            method_id=None,
        )
        db.add(payment)
        db.commit()
        
        return {
            "client_secret": payment_intent.client_secret,
            "payment_id": payment.id,
            "amount": schedule.price,
            "currency": "CLP"
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


# ============================================================================
# WEBHOOK: Confirmación automática
# ============================================================================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stripe notifica cuando el pago se completa.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    # Manejar eventos
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        booking_id = payment_intent["metadata"]["booking_id"]
        
        # Actualizar booking y payment
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if booking:
            booking.status = "confirmed"
            
            payment = db.query(Payment).filter(
                Payment.booking_id == booking_id,
                Payment.reference == payment_intent.id
            ).first()
            if payment:
                payment.status = "confirmed"
            
            db.commit()
            
            # TODO: Enviar email de confirmación
            
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        booking_id = payment_intent["metadata"]["booking_id"]
        
        payment = db.query(Payment).filter(
            Payment.booking_id == booking_id,
            Payment.reference == payment_intent.id
        ).first()
        if payment:
            payment.status = "failed"
            db.commit()
    
    return {"status": "success"}


# ============================================================================
# REEMBOLSOS (si la agencia cancela)
# ============================================================================

@router.post("/bookings/{booking_id}/refund")
async def process_refund(
    booking_id: UUID,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    La agencia puede procesar reembolsos desde su panel.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    # Verificar que el usuario es de la empresa dueña
    # (código de verificación similar al anterior)
    
    payment = db.query(Payment).filter(
        Payment.booking_id == booking_id,
        Payment.status == "confirmed"
    ).first()
    
    if not payment:
        raise HTTPException(400, "No confirmed payment to refund")
    
    try:
        refund = stripe.Refund.create(
            payment_intent=payment.reference,
            reason="requested_by_customer" if reason else None,
            metadata={
                "booking_id": str(booking_id),
                "refund_reason": reason or "cancellation"
            }
        )
        
        # Actualizar estado
        booking.status = "cancelled"
        payment.status = "refunded"
        db.commit()
        
        return {
            "refund_id": refund.id,
            "status": refund.status,
            "amount": refund.amount / 100
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))