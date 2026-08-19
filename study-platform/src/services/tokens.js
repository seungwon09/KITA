const jwt = require('jsonwebtoken');

const JWT_ISSUER = 'kita-web';
const JWT_AUDIENCE = 'kita-user';
const ACCESS_TOKEN_COOKIE = 'kita_token';
const ACCESS_TOKEN_MAX_AGE_MS = 14 * 24 * 60 * 60 * 1000;

function jwtSecret() {
    if (!process.env.JWT_SECRET) throw new Error('JWT_SECRET is required.');
    return process.env.JWT_SECRET;
}

function signAccessToken(user) {
    return jwt.sign(
        { email: user.email, provider: user.provider || 'local' },
        jwtSecret(),
        {
            expiresIn: '14d',
            issuer: JWT_ISSUER,
            audience: JWT_AUDIENCE,
            algorithm: 'HS256'
        }
    );
}

function verifyAccessToken(token) {
    return jwt.verify(token, jwtSecret(), {
        issuer: JWT_ISSUER,
        audience: JWT_AUDIENCE,
        algorithms: ['HS256']
    });
}

function parseCookies(header) {
    return String(header || '')
        .split(';')
        .map(item => item.trim())
        .filter(Boolean)
        .reduce((cookies, item) => {
            const index = item.indexOf('=');
            if (index === -1) return cookies;
            const key = item.slice(0, index).trim();
            const value = item.slice(index + 1);
            try {
                cookies[key] = decodeURIComponent(value);
            } catch (err) {
                cookies[key] = value;
            }
            return cookies;
        }, {});
}

function tokenFromRequest(req) {
    const authHeader = String(req.headers.authorization || '');
    const parts = authHeader.split(' ');
    if (parts.length === 2 && parts[0] === 'Bearer' && parts[1]) return parts[1];
    return parseCookies(req.headers.cookie)[ACCESS_TOKEN_COOKIE] || '';
}

function cookieOptions(req) {
    const secure = process.env.NODE_ENV === 'production' || req.secure || req.headers['x-forwarded-proto'] === 'https';
    return {
        httpOnly: true,
        sameSite: 'lax',
        secure,
        maxAge: ACCESS_TOKEN_MAX_AGE_MS,
        path: '/'
    };
}

function setAuthCookie(res, token, req) {
    res.cookie(ACCESS_TOKEN_COOKIE, token, cookieOptions(req));
}

function clearAuthCookie(res, req) {
    const options = cookieOptions(req);
    delete options.maxAge;
    res.clearCookie(ACCESS_TOKEN_COOKIE, options);
}

module.exports = {
    ACCESS_TOKEN_COOKIE,
    clearAuthCookie,
    parseCookies,
    setAuthCookie,
    signAccessToken,
    tokenFromRequest,
    verifyAccessToken
};
