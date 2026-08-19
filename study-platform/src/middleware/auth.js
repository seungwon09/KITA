const { verifyAccessToken } = require('../services/tokens');

module.exports = (req, res, next) => {
    const authHeader = String(req.headers.authorization || '');
    const parts = authHeader.split(' ');

    if (parts.length !== 2 || parts[0] !== 'Bearer') {
        return res.status(401).json({ msg: 'Login required.' });
    }

    try {
        const decoded = verifyAccessToken(parts[1]);
        if (!decoded.email) return res.status(401).json({ msg: 'Invalid login token.' });
        req.user = decoded;
        next();
    } catch (err) {
        res.status(401).json({ msg: 'Login expired. Sign in again.' });
    }
};
