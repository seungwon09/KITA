const express = require('express');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const auth = require('../middleware/auth');
const { verifyAccessToken } = require('../services/tokens');

const router = express.Router();
const STORE_PATH = path.join(__dirname, '../../data/rewards.json');
const REWARDS = { signupWithReferral: 500, inviteAccepted: 1000, dailyCheckin: 100, solveProblem: 10, firstAiUse: 200, shareSolution: 300, solutionLiked: 50, weeklyRank1: 3000, weeklyRank2: 2000, weeklyRank3: 1000 };

function loadStore() {
    fs.mkdirSync(path.dirname(STORE_PATH), { recursive: true });
    if (!fs.existsSync(STORE_PATH)) return { users: {}, events: [], solutions: [], weeklySettlements: {} };
    const store = JSON.parse(fs.readFileSync(STORE_PATH, 'utf8'));
    store.users ||= {}; store.events ||= []; store.solutions ||= []; store.weeklySettlements ||= {};
    return store;
}
function saveStore(store) { store.updatedAt = new Date().toISOString(); fs.writeFileSync(STORE_PATH, JSON.stringify(store, null, 2), 'utf8'); }
function clean(value, max = 3000) { return String(value || '').trim().slice(0, max); }
function optionalEmail(req) {
    const token = String(req.headers.authorization || '').replace(/^Bearer\s+/, '');
    if (!token || !process.env.JWT_SECRET) return '';
    try { return String(verifyAccessToken(token).email || '').toLowerCase(); } catch (err) { return ''; }
}
function maskEmail(email) { return String(email || '').replace(/(.{2}).+(@.*)/, '$1***$2'); }
function referralCodeFor(email) { return `${String(email).split('@')[0].replace(/[^a-zA-Z0-9]/g, '').slice(0, 5).toUpperCase() || 'KITA'}${crypto.createHash('sha1').update(email).digest('hex').slice(0, 5).toUpperCase()}`; }
function getUser(store, email) {
    if (!store.users[email]) store.users[email] = { email, referralCode: referralCodeFor(email), points: 0, invitedCount: 0, usedInviteCode: '', history: [] };
    return store.users[email];
}
function addEvent(store, user, type, points, memo) {
    const event = { id: crypto.randomUUID(), email: user.email, type, points, memo, createdAt: new Date().toISOString() };
    user.points = Number(user.points || 0) + points; user.history.unshift(event); store.events.unshift(event);
    user.history = user.history.slice(0, 120); store.events = store.events.slice(0, 1000);
    return event;
}
function weekKey() {
    const d = new Date(); const first = new Date(Date.UTC(d.getUTCFullYear(), 0, 1)); const day = Math.floor((d - first) / 86400000);
    return `${d.getUTCFullYear()}-W${String(Math.ceil((day + first.getUTCDay() + 1) / 7)).padStart(2, '0')}`;
}
function rewardForRank(rank) { return rank === 1 ? 3000 : rank === 2 ? 2000 : rank === 3 ? 1000 : 0; }
function solutionView(solution, viewer = '') { return { ...solution, likedBy: undefined, authorMasked: maskEmail(solution.authorEmail), likedByMe: (solution.likedBy || []).includes(viewer), isMine: solution.authorEmail === viewer }; }
function ranked(store, viewer = '') { return [...store.solutions].sort((a, b) => Number(b.likes || 0) - Number(a.likes || 0) || new Date(b.createdAt) - new Date(a.createdAt)).map(item => solutionView(item, viewer)); }

router.get('/me', auth, (req, res) => {
    const store = loadStore(), user = getUser(store, req.user.email); saveStore(store);
    res.json({ ok: true, user, rewardRules: REWARDS, inviteLink: `${req.protocol}://${req.get('host')}/login.html?ref=${encodeURIComponent(user.referralCode)}` });
});
router.post('/apply-code', auth, (req, res) => {
    const store = loadStore(), user = getUser(store, req.user.email), code = clean(req.body?.code, 40).toUpperCase();
    if (!code || code === user.referralCode || user.usedInviteCode) return res.status(400).json({ ok: false, error: '사용할 수 없는 초대 코드입니다.' });
    const inviter = Object.values(store.users).find(item => item.referralCode === code);
    if (!inviter) return res.status(404).json({ ok: false, error: '초대 코드를 찾지 못했습니다.' });
    inviter.invitedCount = Number(inviter.invitedCount || 0) + 1; user.usedInviteCode = code;
    addEvent(store, inviter, 'inviteAccepted', REWARDS.inviteAccepted, `${maskEmail(user.email)} 친구 가입`);
    addEvent(store, user, 'signupWithReferral', REWARDS.signupWithReferral, '친구 초대 코드 입력');
    saveStore(store); res.json({ ok: true, user });
});
router.post('/checkin', auth, (req, res) => {
    const store = loadStore(), user = getUser(store, req.user.email), today = new Date().toISOString().slice(0, 10);
    if ((user.history || []).some(event => event.type === 'dailyCheckin' && event.createdAt.startsWith(today))) return res.status(400).json({ ok: false, error: '오늘 출석 포인트는 이미 받았습니다.' });
    const event = addEvent(store, user, 'dailyCheckin', REWARDS.dailyCheckin, '오늘 출석'); saveStore(store); res.json({ ok: true, user, event });
});
router.post('/earn', auth, (req, res) => {
    const allowed = ['solveProblem', 'firstAiUse']; const type = req.body?.type;
    if (!allowed.includes(type)) return res.status(400).json({ ok: false, error: '허용되지 않은 포인트 적립입니다.' });
    const store = loadStore(), user = getUser(store, req.user.email), event = addEvent(store, user, type, REWARDS[type], clean(req.body?.memo, 120) || '학습 보상');
    saveStore(store); res.json({ ok: true, user, event });
});
router.get('/leaderboard', (req, res) => {
    const users = Object.values(loadStore().users).sort((a, b) => Number(b.points || 0) - Number(a.points || 0)).slice(0, 20).map((user, index) => ({ rank: index + 1, email: maskEmail(user.email), points: Number(user.points || 0), invitedCount: Number(user.invitedCount || 0) }));
    res.json({ ok: true, users });
});
router.get('/solutions', (req, res) => res.json({ ok: true, weekKey: weekKey(), solutions: ranked(loadStore(), optionalEmail(req)) }));
router.post('/solutions', auth, (req, res) => {
    const title = clean(req.body?.title, 80), solutionText = clean(req.body?.solutionText, 4000);
    if (!title || !solutionText) return res.status(400).json({ ok: false, error: '제목과 풀이를 입력해 주세요.' });
    const store = loadStore(), user = getUser(store, req.user.email);
    const solution = { id: crypto.randomUUID(), title, subject: clean(req.body?.subject, 30) || 'math', level: clean(req.body?.level, 30) || 'middle', style: clean(req.body?.style, 40) || '빠른 풀이', problemText: clean(req.body?.problemText, 1200), solutionText, authorEmail: req.user.email, likes: 0, likedBy: [], weekKey: weekKey(), createdAt: new Date().toISOString() };
    store.solutions.unshift(solution); addEvent(store, user, 'shareSolution', REWARDS.shareSolution, '나만의 풀이 공유'); saveStore(store); res.json({ ok: true, solution: solutionView(solution, req.user.email), user });
});
router.post('/solutions/:id/like', auth, (req, res) => {
    const store = loadStore(), solution = store.solutions.find(item => item.id === req.params.id);
    if (!solution) return res.status(404).json({ ok: false, error: '풀이를 찾지 못했습니다.' });
    solution.likedBy ||= [];
    if (solution.authorEmail === req.user.email || solution.likedBy.includes(req.user.email)) return res.status(400).json({ ok: false, error: '이미 처리된 좋아요입니다.' });
    solution.likedBy.push(req.user.email); solution.likes = Number(solution.likes || 0) + 1;
    addEvent(store, getUser(store, solution.authorEmail), 'solutionLiked', REWARDS.solutionLiked, `"${solution.title}" 좋아요`); saveStore(store); res.json({ ok: true, solution: solutionView(solution, req.user.email) });
});
router.get('/solutions/weekly', (req, res) => res.json({ ok: true, weekKey: weekKey(), ranking: ranked(loadStore(), optionalEmail(req)).filter(item => item.weekKey === weekKey()).slice(0, 10).map((item, index) => ({ ...item, rank: index + 1, weeklyReward: rewardForRank(index + 1) })) }));

module.exports = router;
