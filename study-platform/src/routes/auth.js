const express = require('express');
const bcrypt = require('bcrypt');
const crypto = require('crypto');

const User = require('../models/user');
const { firebaseAdminStatus, firebaseClientConfig, verifyFirebaseIdToken } = require('../services/firebase');
const { signAccessToken, verifyAccessToken } = require('../services/tokens');

const router = express.Router();
const MAX_LOGIN_ATTEMPTS = 5;
const LOGIN_LOCK_MS = 15 * 60 * 1000;

function createReferralCode(email) {
    const prefix = String(email || 'KITA').split('@')[0].replace(/[^a-zA-Z0-9]/g, '').slice(0, 4).toUpperCase() || 'KITA';
    return `${prefix}${crypto.randomBytes(3).toString('hex').toUpperCase()}`;
}

function safeUser(user) {
    if (!user) return null;
    const obj = user.toObject ? user.toObject() : { ...user };
    delete obj.password;
    delete obj.failedLoginAttempts;
    delete obj.lockedUntil;
    if (obj.subscription) delete obj.subscription.paymentKey;
    return obj;
}

function kakaoRedirectUri(req) {
    return process.env.KAKAO_REDIRECT_URI || `${req.protocol}://${req.get('host')}/api/auth/kakao/callback`;
}

router.post('/register', async (req, res) => {
    try {
        const email = String(req.body?.email || '').trim().toLowerCase();
        const password = String(req.body?.password || '');
        const referralCode = String(req.body?.referralCode || req.body?.ref || '').trim().toUpperCase();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) return res.status(400).json({ msg: 'Enter a valid email address.' });
        if (password.length < 8 || password.length > 128) return res.status(400).json({ msg: 'Password must be between 8 and 128 characters.' });
        if (await User.findOne({ email })) return res.status(400).json({ msg: 'This email is already registered.' });

        const user = new User({
            email,
            password: await bcrypt.hash(password, 10),
            provider: 'local',
            referralCode: createReferralCode(email),
            referredBy: referralCode,
            points: referralCode ? 500 : 0,
            plan: 'free',
            lastLoginAt: new Date()
        });
        await user.save();
        res.json({ ok: true, msg: 'Registration complete.', token: signAccessToken(user), user: safeUser(user) });
    } catch (err) {
        if (err.code === 11000) return res.status(400).json({ msg: 'This account or referral code is already in use.' });
        res.status(500).json({ msg: 'Registration failed.' });
    }
});

router.post('/login', async (req, res) => {
    try {
        const email = String(req.body?.email || '').trim().toLowerCase();
        const password = String(req.body?.password || '');
        if (!email || !password) return res.status(400).json({ msg: 'Enter your email and password.' });
        const user = await User.findOne({ email });
        if (user?.lockedUntil && user.lockedUntil > new Date()) return res.status(429).json({ msg: 'Login is temporarily locked. Try again later.' });
        if (!user || !await bcrypt.compare(password, user.password)) {
            if (user) {
                user.failedLoginAttempts = Number(user.failedLoginAttempts || 0) + 1;
                if (user.failedLoginAttempts >= MAX_LOGIN_ATTEMPTS) user.lockedUntil = new Date(Date.now() + LOGIN_LOCK_MS);
                await user.save();
            }
            return res.status(400).json({ msg: 'Email or password is incorrect.' });
        }
        if (!user.referralCode) user.referralCode = createReferralCode(email);
        user.failedLoginAttempts = 0;
        user.lockedUntil = undefined;
        user.lastLoginAt = new Date();
        await user.save();
        res.json({ ok: true, token: signAccessToken(user), user: safeUser(user) });
    } catch (err) {
        res.status(500).json({ msg: 'Login failed.' });
    }
});

router.get('/me', async (req, res) => {
    try {
        const token = String(req.headers.authorization || '').replace(/^Bearer\s+/, '');
        if (!token) return res.status(401).json({ ok: false, msg: 'Login required.' });
        const decoded = verifyAccessToken(token);
        const user = await User.findOne({ email: decoded.email });
        if (!user) return res.status(404).json({ ok: false, msg: 'User not found.' });
        res.json({ ok: true, user: safeUser(user) });
    } catch (err) {
        res.status(401).json({ ok: false, msg: 'Login expired. Sign in again.' });
    }
});

router.get('/kakao/status', (req, res) => {
    res.json({ ok: true, configured: Boolean(process.env.KAKAO_REST_API_KEY), redirectUri: kakaoRedirectUri(req) });
});

router.get('/firebase/status', (req, res) => {
    res.json({ ok: true, admin: firebaseAdminStatus(), client: firebaseClientConfig() });
});

router.get('/firebase/config', (req, res) => {
    const client = firebaseClientConfig();
    res.json({ ok: true, ...client });
});

router.post('/firebase/login', async (req, res) => {
    try {
        const idToken = String(req.body?.idToken || '').trim();
        const referralCode = String(req.body?.referralCode || req.body?.ref || '').trim().toUpperCase();
        if (!idToken) return res.status(400).json({ ok: false, msg: 'Firebase ID token is required.' });

        const decoded = await verifyFirebaseIdToken(idToken);
        const firebaseUid = String(decoded.uid || '');
        const email = String(decoded.email || `firebase_${firebaseUid}@firebase.local`).toLowerCase();
        if (!firebaseUid) return res.status(400).json({ ok: false, msg: 'Invalid Firebase token.' });

        let user = await User.findOne({ firebaseUid }) || await User.findOne({ email });
        if (!user) {
            user = new User({
                email,
                password: await bcrypt.hash(`firebase:${firebaseUid}:${crypto.randomUUID()}`, 10),
                provider: 'firebase',
                firebaseUid,
                name: decoded.name || '',
                referralCode: createReferralCode(email),
                referredBy: referralCode,
                points: referralCode ? 500 : 0,
                plan: 'free'
            });
        }
        user.provider = user.provider === 'local' ? 'firebase' : user.provider || 'firebase';
        user.firebaseUid = firebaseUid;
        user.name = user.name || decoded.name || '';
        user.failedLoginAttempts = 0;
        user.lockedUntil = undefined;
        user.lastLoginAt = new Date();
        await user.save();
        res.json({ ok: true, token: signAccessToken(user), user: safeUser(user) });
    } catch (err) {
        const status = err.code === 'FIREBASE_NOT_CONFIGURED' ? 503 : 401;
        res.status(status).json({ ok: false, msg: status === 503 ? 'Firebase is not configured yet.' : 'Firebase login failed.' });
    }
});

router.get('/kakao/start', (req, res) => {
    if (!process.env.KAKAO_REST_API_KEY) return res.redirect('/login.html?kakao=not-configured');
    const params = new URLSearchParams({ response_type: 'code', client_id: process.env.KAKAO_REST_API_KEY, redirect_uri: kakaoRedirectUri(req) });
    res.redirect(`https://kauth.kakao.com/oauth/authorize?${params.toString()}`);
});

router.get('/kakao/callback', async (req, res) => {
    try {
        if (!req.query.code) return res.redirect('/login.html');
        const tokenParams = new URLSearchParams({
            grant_type: 'authorization_code',
            client_id: process.env.KAKAO_REST_API_KEY,
            redirect_uri: kakaoRedirectUri(req),
            code: req.query.code
        });
        const tokenResponse = await fetch('https://kauth.kakao.com/oauth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
            body: tokenParams
        });
        const tokenData = await tokenResponse.json();
        if (!tokenResponse.ok) throw new Error('Kakao authentication failed.');
        const userResponse = await fetch('https://kapi.kakao.com/v2/user/me', { headers: { Authorization: `Bearer ${tokenData.access_token}` } });
        const kakaoUser = await userResponse.json();
        if (!userResponse.ok) throw new Error('Failed to load Kakao profile.');
        const kakaoId = String(kakaoUser.id);
        const account = kakaoUser.kakao_account || {};
        const email = String(account.email || `kakao_${kakaoId}@kakao.local`).toLowerCase();
        let user = await User.findOne({ email });
        if (!user) {
            user = new User({
                email,
                password: await bcrypt.hash(`kakao:${kakaoId}:${crypto.randomUUID()}`, 10),
                provider: 'kakao',
                kakaoId,
                name: account.profile?.nickname || '',
                referralCode: createReferralCode(email),
                plan: 'free'
            });
        }
        user.provider = 'kakao';
        user.kakaoId = kakaoId;
        user.failedLoginAttempts = 0;
        user.lockedUntil = undefined;
        user.lastLoginAt = new Date();
        await user.save();
        const token = signAccessToken(user);
        res.send(`<meta charset="UTF-8"><script>localStorage.setItem('token',${JSON.stringify(token)});location.href='/';</script>`);
    } catch (err) {
        res.redirect('/login.html?kakao=failed');
    }
});

module.exports = router;
