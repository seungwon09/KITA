const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SECURITY_LOG = path.join(__dirname, '../../data/security_events.jsonl');

function hash(value) {
    return crypto.createHash('sha256').update(String(value || '')).digest();
}

function secureEqual(left, right) {
    const leftHash = hash(left);
    const rightHash = hash(right);
    return crypto.timingSafeEqual(leftHash, rightHash) && Boolean(left) && Boolean(right);
}

function auditSecurityEvent(req, event, detail = '') {
    try {
        fs.mkdirSync(path.dirname(SECURITY_LOG), { recursive: true });
        const ip = String(req?.ip || req?.socket?.remoteAddress || 'unknown');
        const record = {
            time: new Date().toISOString(),
            event: String(event || 'security_event').slice(0, 80),
            detail: String(detail || '').slice(0, 200),
            requestId: String(req?.requestId || '').slice(0, 80),
            method: String(req?.method || '').slice(0, 16),
            path: String(req?.originalUrl || req?.url || '').split('?')[0].slice(0, 240),
            ipHash: crypto.createHash('sha256').update(ip).digest('hex').slice(0, 20)
        };
        fs.appendFileSync(SECURITY_LOG, `${JSON.stringify(record)}\n`, 'utf8');
    } catch (err) {
        console.error(`security audit log failed: ${err.message}`);
    }
}

function hasDangerousKeys(value, depth = 0) {
    if (!value || typeof value !== 'object') return false;
    if (depth > 12) return true;
    for (const key of Object.keys(value)) {
        if (
            key.startsWith('$')
            || key.includes('.')
            || key === '__proto__'
            || key === 'prototype'
            || key === 'constructor'
        ) return true;
        if (hasDangerousKeys(value[key], depth + 1)) return true;
    }
    return false;
}

function rejectDangerousInput(req, res, next) {
    if ([req.body, req.query, req.params].some(hasDangerousKeys)) {
        auditSecurityEvent(req, 'dangerous_input_rejected');
        return res.status(400).json({ ok: false, error: 'INVALID_REQUEST_INPUT' });
    }
    next();
}

function securityRequestContext(req, res, next) {
    req.requestId = crypto.randomUUID();
    res.setHeader('X-Request-Id', req.requestId);
    next();
}

function requireHttps(req, res, next) {
    if (process.env.ENFORCE_HTTPS !== 'true') return next();
    const forwarded = String(req.headers['x-forwarded-proto'] || '').split(',')[0].trim();
    if (req.secure || forwarded === 'https') return next();
    auditSecurityEvent(req, 'https_required');
    if (req.method === 'GET' || req.method === 'HEAD') {
        return res.redirect(308, `https://${req.get('host')}${req.originalUrl}`);
    }
    return res.status(426).json({ ok: false, error: 'HTTPS_REQUIRED' });
}

function materialFileFilter(req, file, callback) {
    const extension = path.extname(file.originalname || '').toLowerCase();
    const allowed = {
        '.pdf': ['application/pdf', 'application/octet-stream'],
        '.txt': ['text/plain', 'application/octet-stream'],
        '.md': ['text/plain', 'text/markdown', 'application/octet-stream'],
        '.csv': ['text/csv', 'text/plain', 'application/vnd.ms-excel', 'application/octet-stream'],
        '.json': ['application/json', 'text/plain', 'application/octet-stream'],
        '.png': ['image/png'],
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
        '.webp': ['image/webp']
    };
    const accepted = allowed[extension]?.includes(String(file.mimetype || '').toLowerCase());
    if (accepted) return callback(null, true);
    auditSecurityEvent(req, 'admin_upload_type_rejected', extension);
    const error = new Error('UPLOAD_TYPE_NOT_ALLOWED');
    error.code = 'UPLOAD_TYPE_NOT_ALLOWED';
    callback(error);
}

function aiImageFileFilter(req, file, callback) {
    const extension = path.extname(file.originalname || '').toLowerCase();
    const allowed = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp'
    };
    if (allowed[extension] === String(file.mimetype || '').toLowerCase()) return callback(null, true);
    auditSecurityEvent(req, 'ai_upload_type_rejected', extension);
    const error = new Error('IMAGE_TYPE_NOT_ALLOWED');
    error.code = 'UPLOAD_TYPE_NOT_ALLOWED';
    callback(error);
}

function validateEnvironment() {
    const strict = process.env.STRICT_PRODUCTION_SECURITY === 'true';
    const issues = [];
    if (String(process.env.JWT_SECRET || '').length < 48) issues.push('JWT_SECRET must be at least 48 characters.');
    if (String(process.env.ADMIN_PIN || '').length < 10) issues.push('ADMIN_PIN must be at least 10 characters.');
    if (process.env.NODE_ENV === 'production' && !String(process.env.PUBLIC_BASE_URL || '').startsWith('https://')) issues.push('PUBLIC_BASE_URL must use HTTPS.');
    if (process.env.NODE_ENV === 'production' && !String(process.env.CORS_ORIGINS || '').trim()) issues.push('CORS_ORIGINS must be configured.');
    if (process.env.NODE_ENV === 'production' && process.env.ALLOW_DEV_PAYMENTS === 'true') issues.push('ALLOW_DEV_PAYMENTS must be false in production.');
    if (issues.length) {
        const message = `Security environment check: ${issues.join(' ')}`;
        if (strict) throw new Error(message);
        console.warn(message);
    }
}

module.exports = {
    aiImageFileFilter,
    auditSecurityEvent,
    materialFileFilter,
    rejectDangerousInput,
    requireHttps,
    secureEqual,
    securityRequestContext,
    validateEnvironment
};
