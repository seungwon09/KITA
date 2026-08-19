const jwt = require('jsonwebtoken');

const JWT_ISSUER = 'kita-web';
const JWT_AUDIENCE = 'kita-user';

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

module.exports = { signAccessToken, verifyAccessToken };
