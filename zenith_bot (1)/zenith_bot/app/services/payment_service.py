# -*- coding: utf-8 -*-
"""
Zenith Bot — Payment Service
Midtrans Snap integration
"""

import uuid
from typing import Optional
from loguru import logger
import midtransclient

from app.config import settings, TIER_PRICES
from app.database import get_supabase


def get_midtrans_snap() -> midtransclient.Snap:
    return midtransclient.Snap(
        is_production=settings.midtrans_is_production,
        server_key=settings.midtrans_server_key,
        client_key=settings.midtrans_client_key,
    )


async def create_payment(user_id: str, telegram_id: int, tier: str,
                          user_email: str = None, user_name: str = None) -> Optional[dict]:
    """Buat payment order Midtrans, return snap token + redirect URL"""
    try:
        if tier not in TIER_PRICES:
            logger.error(f"Invalid tier: {tier}")
            return None

        amount = TIER_PRICES[tier]
        order_id = f"ZENITH-{telegram_id}-{uuid.uuid4().hex[:8].upper()}"

        snap = get_midtrans_snap()
        transaction = snap.create_transaction({
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": amount,
            },
            "customer_details": {
                "first_name": user_name or "Zenith User",
                "email": user_email or f"user{telegram_id}@zenith.app",
            },
            "item_details": [{
                "id": tier,
                "price": amount,
                "quantity": 1,
                "name": f"Zenith {tier.capitalize()} - 30 Hari",
            }],
            "callbacks": {
                "finish": f"{settings.base_url}/payment/finish",
            },
        })

        # Simpan ke Supabase
        sb = get_supabase()
        sb.table("payments").insert({
            "user_id": user_id,
            "midtrans_order_id": order_id,
            "tier": tier,
            "amount": amount,
            "status": "pending",
        }).execute()

        return {
            "order_id": order_id,
            "snap_token": transaction.get("token"),
            "redirect_url": transaction.get("redirect_url"),
            "amount": amount,
            "tier": tier,
        }
    except Exception as e:
        logger.error(f"create_payment error: {e}")
        return None


async def handle_payment_notification(notification: dict) -> bool:
    """Handle Midtrans webhook notification"""
    try:
        snap = get_midtrans_snap()
        status = snap.transactions.notification(notification)

        order_id = status.get("order_id", "")
        transaction_status = status.get("transaction_status", "")
        fraud_status = status.get("fraud_status", "")

        is_paid = (
            transaction_status == "capture" and fraud_status == "accept"
        ) or transaction_status == "settlement"

        sb = get_supabase()

        if is_paid:
            # Update payment status
            result = sb.table("payments").update({"status": "paid", "paid_at": "now()"}).eq("midtrans_order_id", order_id).execute()

            if result.data:
                payment = result.data[0]
                # Aktifkan subscription
                from app.services.subscription_service import activate_subscription
                await activate_subscription(payment["user_id"], payment["tier"], days=30)
                logger.info(f"Payment confirmed: {order_id} tier={payment['tier']}")
                return True
        else:
            sb.table("payments").update({"status": transaction_status}).eq("midtrans_order_id", order_id).execute()

        return False
    except Exception as e:
        logger.error(f"handle_payment_notification error: {e}")
        return False
