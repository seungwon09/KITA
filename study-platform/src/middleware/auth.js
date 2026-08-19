const { tokenFromRequest, verifyAccessToken } = require('../services/tokens');

module.exports = (req, res, next) => {
    const token = tokenFromRequest(req);
    if (!token) {
        return res.status(401).json({ msg: 'Login required.' });
    }

    try {
        const decoded = verifyAccessToken(token);
        if (!decoded.email) return res.status(401).json({ msg: 'Invalid login token.' });
        req.user = decoded;
        next();
    } catch (err) {
        res.status(401).json({ msg: 'Login expired. Sign in again.' });
    }
};
