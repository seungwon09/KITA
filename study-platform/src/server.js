require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });
require('dotenv').config();

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const mongoose = require('mongoose');
const path = require('path');

const connectDB = require('./config/db');
const authRoutes = require('./routes/auth');
const questionRoutes = require('./routes/question');
const aiRoutes = require('./routes/ai');
const adminRoutes = require('./routes/admin');
const paymentRoutes = require('./routes/payment');
const rewardRoutes = require('./routes/reward');
const qualityRoutes = require('./routes/quality');
const auth = require('./middleware/auth');
const {
    auditSecurityEvent,
    publicBaseUrl,
    rejectDangerousInput,
    requireHttps,
    securityRequestContext,
    validateEnvironment
} = require('./middleware/security');

const app = express();
const allowedOrigins = String(process.env.CORS_ORIGINS || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean);

function isPrivateDevelopmentOrigin(origin) {
    if (process.env.NODE_ENV === 'production') return false;
    try {
        const hostname = new URL(origin).hostname;
        return hostname === 'localhost'
            || hostname === '127.0.0.1'
            || hostname === '::1'
            || hostname.startsWith('10.')
            || hostname.startsWith('192.168.')
            || /^172\.(1[6-9]|2\d|3[01])\./.test(hostname);
    } catch (err) {
        return false;
    }
}

function isTemporaryTunnelOrigin(origin) {
    if (process.env.ALLOW_TUNNEL_ORIGINS === 'false') return false;
    if (process.env.NODE_ENV === 'production') return false;
    try {
        const hostname = new URL(origin).hostname;
        return hostname === 'trycloudflare.com' || hostname.endsWith('.trycloudflare.com');
    } catch (err) {
        return false;
    }
}

validateEnvironment();
connectDB();

app.set('trust proxy', process.env.TRUST_PROXY === 'true' ? 1 : false);
app.disable('x-powered-by');
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            baseUri: ["'self'"],
            connectSrc: ["'self'"],
            fontSrc: ["'self'", 'data:'],
            formAction: ["'self'"],
            frameAncestors: ["'none'"],
            imgSrc: ["'self'", 'data:', 'blob:'],
            objectSrc: ["'none'"],
            scriptSrc: ["'self'", "'unsafe-inline'"],
            scriptSrcAttr: ["'unsafe-inline'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            upgradeInsecureRequests: process.env.NODE_ENV === 'production' ? [] : null
        }
    },
    crossOriginEmbedderPolicy: false,
    frameguard: { action: 'deny' },
    hsts: process.env.NODE_ENV === 'production'
        ? { maxAge: 15552000, includeSubDomains: true, preload: true }
        : false
}));
app.use(securityRequestContext);
app.use(requireHttps);
app.use(cors({
    origin(origin, callback) {
        if (!origin) return callback(null, true);
        if (allowedOrigins.includes(origin)) return callback(null, true);
        if (origin === publicBaseUrl()) return callback(null, true);
        if (isTemporaryTunnelOrigin(origin)) return callback(null, true);
        if (isPrivateDevelopmentOrigin(origin)) return callback(null, true);
        const error = new Error('CORS_ORIGIN_DENIED');
        error.code = 'CORS_ORIGIN_DENIED';
        callback(error);
    },
    credentials: true
}));
app.use(express.json({ limit: '4mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb', parameterLimit: 100 }));
app.use(express.static(path.join(__dirname, '../public'), { maxAge: process.env.NODE_ENV === 'production' ? '1h' : 0 }));

const apiLimiter = rateLimit({
    windowMs: 60 * 1000,
    limit: 180,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { ok: false, error: 'API_RATE_LIMITED' }
});
const authLimiter = rateLimit({
    windowMs: 10 * 60 * 1000,
    limit: 15,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { ok: false, error: 'AUTH_RATE_LIMITED' }
});
const adminLimiter = rateLimit({
    windowMs: 10 * 60 * 1000,
    limit: 80,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { ok: false, error: 'ADMIN_RATE_LIMITED' }
});
const aiLimiter = rateLimit({
    windowMs: 60 * 1000,
    limit: 50,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { ok: false, error: 'AI_RATE_LIMITED' }
});

app.use('/api', apiLimiter, rejectDangerousInput);
app.use('/api/auth', authLimiter, authRoutes);
app.use('/api/question', questionRoutes);
app.use('/api/ai', aiLimiter, aiRoutes);
app.use('/api/admin', adminLimiter, adminRoutes);
app.use('/api/payment', paymentRoutes);
app.use('/api/rewards', rewardRoutes);
app.use('/api/quality', qualityRoutes);

app.get('/api/live', (req, res) => {
    res.json({
        ok: true,
        app: 'KITA',
        service: 'web',
        time: new Date().toISOString()
    });
});

app.get('/api/protected', auth, (req, res) => {
    res.json({ ok: true, msg: 'Authenticated.', user: req.user });
});

app.get('/api/health', async (req, res) => {
    let studyAi = false;
    try {
        const base = String(process.env.STUDY_AI_BASE_URL || 'http://127.0.0.1:8002').replace(/\/$/, '');
        const response = await fetch(`${base}/health`, { signal: AbortSignal.timeout(2500) });
        studyAi = response.ok;
    } catch (err) {
        studyAi = false;
    }
    const database = mongoose.connection.readyState === 1;
    const ok = database && studyAi;
    res.status(ok ? 200 : 503).json({
        ok,
        app: 'KITA',
        services: { web: true, database, studyAi },
        time: new Date().toISOString()
    });
});

app.use('/api', (req, res) => {
    res.status(404).json({ ok: false, error: 'API_NOT_FOUND' });
});

app.use((err, req, res, next) => {
    console.error(err.message);
    if (err.code === 'CORS_ORIGIN_DENIED') {
        auditSecurityEvent(req, 'cors_origin_denied');
        return res.status(403).json({ ok: false, error: 'CORS_ORIGIN_DENIED' });
    }
    if (err.code === 'UPLOAD_TYPE_NOT_ALLOWED') {
        return res.status(400).json({ ok: false, error: err.message });
    }
    if (err.code === 'LIMIT_FILE_SIZE') {
        auditSecurityEvent(req, 'upload_too_large');
        return res.status(413).json({ ok: false, error: 'UPLOAD_TOO_LARGE' });
    }
    auditSecurityEvent(req, 'server_error', err.message);
    res.status(500).json({ ok: false, error: 'SERVER_ERROR' });
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, '0.0.0.0', () => {
    console.log(`KITA server running on port ${PORT}`);
});
