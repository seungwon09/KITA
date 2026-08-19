const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const User = require('../models/user');
const { verifyAccessToken } = require('./tokens');

const DATA_DIR = path.join(__dirname, '../../data');
const USAGE_PATH = path.join(DATA_DIR, 'usage_limits.json');

const plans = [
    {
        id: 'free',
        name: '기본',
        price: 0,
        label: '0원 / 월',
        description: '가볍게 시작하는 무료 요금제',
        features: ['기본 문제 풀이', '단계별 해설', '일반 AI 질문', '하루 AI 요청 10회'],
        limits: { aiPerDay: 10, ocrPerMonth: 3, eliteSolution: false }
    },
    {
        id: 'middle',
        name: '중간 풀이',
        price: 5000,
        label: '5,000원 / 월',
        description: '반에서 공부 잘하는 친구처럼 쉽게 설명하는 풀이',
        features: ['기본 풀이 전체', '빠른 풀이', '약점 분석', '사진 OCR 월 100회', '하루 AI 요청 80회'],
        limits: { aiPerDay: 80, ocrPerMonth: 100, eliteSolution: false }
    },
    {
        id: 'advanced',
        name: '상급 풀이',
        price: 10000,
        label: '10,000원 / 월',
        description: '친한 친구가 시험 직전에 알려주는 실전 풀이',
        features: ['중간 풀이 전체', '상위권 풀이 비교', '시험 시간 단축 전략', '사진 OCR 월 300회', '하루 AI 요청 200회'],
        limits: { aiPerDay: 200, ocrPerMonth: 300, eliteSolution: true }
    },
    {
        id: 'ultimate',
        name: '최상급 풀이',
        price: 15000,
        label: '15,000원 / 월',
        description: '기억에 남도록 강하게 짚어 주는 최상급 실전 코칭',
        features: ['상급 풀이 전체', '최상급 압축 풀이', '맞춤 학습 루트', '사진 OCR 월 1,000회', '하루 AI 요청 500회'],
        limits: { aiPerDay: 500, ocrPerMonth: 1000, eliteSolution: true }
    }
];

function loadUsage() {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    if (!fs.existsSync(USAGE_PATH)) return {};
    try {
        return JSON.parse(fs.readFileSync(USAGE_PATH, 'utf8'));
    } catch (err) {
        return {};
    }
}

function saveUsage(store) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.writeFileSync(USAGE_PATH, JSON.stringify(store, null, 2), 'utf8');
}

function bearer(req) {
    const value = String(req.headers.authorization || '');
    return value.startsWith('Bearer ') ? value.slice(7) : '';
}

async function userFromRequest(req) {
    const token = bearer(req);
    if (!token || !process.env.JWT_SECRET) return null;
    try {
        const decoded = verifyAccessToken(token);
        return decoded.email ? await User.findOne({ email: decoded.email }) : null;
    } catch (err) {
        return null;
    }
}

function planById(id) {
    return plans.find(item => item.id === id) || plans[0];
}

function activePlan(user) {
    if (!user) return plans[0];
    const subscription = user.subscription || {};
    const expired = subscription.expiresAt && new Date(subscription.expiresAt) <= new Date();
    if (user.plan === 'free' || subscription.status === 'active' && !expired) return planById(user.plan);
    return plans[0];
}

function usageKey(req, user) {
    if (user?.email) return `user:${String(user.email).toLowerCase()}`;
    const raw = String(req.ip || req.socket?.remoteAddress || 'anonymous');
    return `anon:${crypto.createHash('sha256').update(raw).digest('hex').slice(0, 18)}`;
}

async function consume(req, type) {
    const user = await userFromRequest(req);
    const plan = activePlan(user);
    const store = loadUsage();
    const key = usageKey(req, user);
    const today = new Date().toISOString().slice(0, 10);
    const month = today.slice(0, 7);
    const usage = store[key] || { day: today, month, ai: 0, ocr: 0 };
    if (usage.day !== today) {
        usage.day = today;
        usage.ai = 0;
    }
    if (usage.month !== month) {
        usage.month = month;
        usage.ocr = 0;
    }

    const counter = type === 'ocr' ? 'ocr' : 'ai';
    const limit = type === 'ocr' ? plan.limits.ocrPerMonth : plan.limits.aiPerDay;
    if (usage[counter] >= limit) {
        return {
            ok: false,
            status: 429,
            error: type === 'ocr'
                ? `이번 달 사진 분석 ${limit}회를 모두 사용했습니다. 요금제를 업그레이드해 주세요.`
                : `오늘 AI 요청 ${limit}회를 모두 사용했습니다. 내일 다시 사용하거나 요금제를 업그레이드해 주세요.`,
            plan,
            usage
        };
    }

    usage[counter] += 1;
    usage.updatedAt = new Date().toISOString();
    store[key] = usage;
    saveUsage(store);
    return { ok: true, user, plan, usage, remaining: Math.max(0, limit - usage[counter]) };
}

async function planStatus(req) {
    const user = await userFromRequest(req);
    return { user, plan: activePlan(user) };
}

module.exports = { activePlan, consume, planById, plans, planStatus, userFromRequest };
