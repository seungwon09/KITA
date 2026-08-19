const express = require('express');
const crypto = require('crypto');

const { plans, planById, planStatus, userFromRequest } = require('../services/plans');

const router = express.Router();

function paymentConfigured() {
    return Boolean(process.env.TOSS_CLIENT_KEY && process.env.TOSS_SECRET_KEY);
}

function devPaymentsAllowed() {
    return process.env.ALLOW_DEV_PAYMENTS === 'true' && process.env.NODE_ENV !== 'production';
}

function tossAuthHeader() {
    return `Basic ${Buffer.from(`${process.env.TOSS_SECRET_KEY}:`).toString('base64')}`;
}

function publicBaseUrl(req) {
    return process.env.PUBLIC_BASE_URL || `${req.protocol}://${req.get('host')}`;
}

function safeSubscription(subscription) {
    if (!subscription) return null;
    const value = subscription.toObject ? subscription.toObject() : { ...subscription };
    delete value.paymentKey;
    return value;
}

async function activate(user, plan, source, payment = {}) {
    const startedAt = new Date();
    const expiresAt = new Date(startedAt);
    expiresAt.setMonth(expiresAt.getMonth() + 1);

    if (user) {
        user.plan = plan.id;
        user.subscription = {
            status: 'active',
            startedAt,
            expiresAt,
            source,
            orderId: payment.orderId || '',
            paymentKey: payment.paymentKey || ''
        };
        await user.save();
    }

    return {
        id: `sub_${crypto.randomUUID()}`,
        planId: plan.id,
        planName: plan.name,
        status: 'active',
        currentPeriod: 'monthly',
        startedAt: startedAt.toISOString(),
        expiresAt: expiresAt.toISOString(),
        savedToAccount: Boolean(user)
    };
}

router.get('/plans', (req, res) => {
    res.json({ ok: true, plans });
});

router.get('/status', (req, res) => {
    res.json({
        ok: true,
        provider: process.env.PAYMENT_PROVIDER || 'toss',
        configured: paymentConfigured(),
        devMode: devPaymentsAllowed()
    });
});

router.get('/me', async (req, res) => {
    const status = await planStatus(req);
    res.json({
        ok: true,
        loggedIn: Boolean(status.user),
        plan: status.plan,
        subscription: safeSubscription(status.user?.subscription)
    });
});

router.get('/config', (req, res) => {
    res.json({
        ok: true,
        provider: process.env.PAYMENT_PROVIDER || 'toss',
        configured: paymentConfigured(),
        clientKey: process.env.TOSS_CLIENT_KEY || '',
        sdkUrl: 'https://js.tosspayments.com/v2/standard',
        baseUrl: publicBaseUrl(req),
        mode: process.env.TOSS_CLIENT_KEY?.startsWith('live_') ? 'live' : 'test-or-dev'
    });
});

router.post('/checkout', async (req, res) => {
    const plan = planById(req.body?.planId);
    if (plan.id !== req.body?.planId) return res.status(400).json({ ok: false, error: 'PLAN_NOT_FOUND' });
    const user = await userFromRequest(req);

    if (plan.id === 'free') {
        return res.json({
            ok: true,
            ready: true,
            plan,
            subscription: await activate(user, plan, 'free'),
            message: 'Free plan activated.'
        });
    }

    if (!user) return res.status(401).json({ ok: false, error: 'LOGIN_REQUIRED' });
    if (!paymentConfigured()) {
        if (!devPaymentsAllowed()) return res.status(503).json({ ok: false, error: 'PAYMENT_NOT_CONFIGURED' });
        return res.status(202).json({
            ok: false,
            ready: false,
            devMode: true,
            plan,
            orderId: `dev_${Date.now()}_${crypto.randomUUID()}`,
            message: 'Development payment mode is active.'
        });
    }

    res.json({
        ok: true,
        ready: true,
        provider: process.env.PAYMENT_PROVIDER || 'toss',
        orderId: `order_${Date.now()}_${crypto.randomUUID()}`,
        amount: plan.price,
        plan,
        message: 'Payment checkout is ready.'
    });
});

router.post('/confirm', async (req, res) => {
    try {
        const user = await userFromRequest(req);
        if (!user) return res.status(401).json({ ok: false, error: 'LOGIN_REQUIRED' });
        const { paymentKey, orderId, amount, planId } = req.body || {};
        const plan = planById(planId);
        if (plan.id !== planId || plan.id === 'free') return res.status(400).json({ ok: false, error: 'INVALID_PAID_PLAN' });
        if (!paymentKey || !orderId) return res.status(400).json({ ok: false, error: 'PAYMENT_CONFIRMATION_REQUIRED' });
        if (Number(amount) !== Number(plan.price)) return res.status(400).json({ ok: false, error: 'PAYMENT_AMOUNT_MISMATCH' });
        if (!paymentConfigured()) return res.status(503).json({ ok: false, error: 'PAYMENT_NOT_CONFIGURED' });

        const response = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
            method: 'POST',
            headers: {
                Authorization: tossAuthHeader(),
                'Content-Type': 'application/json',
                'Idempotency-Key': crypto.randomUUID()
            },
            body: JSON.stringify({ paymentKey, orderId, amount: plan.price })
        });
        const data = await response.json();
        if (!response.ok) return res.status(response.status).json({ ok: false, error: data.message || 'PAYMENT_CONFIRM_FAILED' });

        res.json({
            ok: true,
            plan,
            subscription: await activate(user, plan, 'toss', { paymentKey, orderId }),
            payment: {
                orderId: data.orderId,
                status: data.status,
                totalAmount: data.totalAmount,
                approvedAt: data.approvedAt
            }
        });
    } catch (err) {
        res.status(500).json({ ok: false, error: 'PAYMENT_CONFIRM_FAILED' });
    }
});

router.post('/dev-activate', async (req, res) => {
    if (!devPaymentsAllowed() || paymentConfigured()) return res.status(403).json({ ok: false, error: 'DEV_PAYMENTS_DISABLED' });
    const user = await userFromRequest(req);
    if (!user) return res.status(401).json({ ok: false, error: 'LOGIN_REQUIRED' });
    const plan = planById(req.body?.planId);
    if (plan.id !== req.body?.planId) return res.status(400).json({ ok: false, error: 'PLAN_NOT_FOUND' });
    res.json({
        ok: true,
        devMode: true,
        plan,
        subscription: await activate(user, plan, 'dev'),
        message: 'Development plan activated without a real payment.'
    });
});

module.exports = router;
