const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DATA_DIR = path.join(__dirname, '../../data');
const UPLOAD_DIR = path.join(DATA_DIR, 'uploads');
const STORE_PATH = path.join(DATA_DIR, 'admin_library.json');

function emptyStore() {
    return {
        materials: [],
        solutionPatterns: [],
        benchmarkCases: [],
        benchmarkRuns: [],
        failureCases: [],
        feedback: [],
        integrations: {
            kakao: { enabled: false },
            payment: { provider: 'manual', enabled: false }
        },
        createdAt: new Date().toISOString()
    };
}

function ensureDataDirs() {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
    if (!fs.existsSync(STORE_PATH)) saveStore(emptyStore());
}

function loadStore() {
    ensureDataDirs();
    try {
        return { ...emptyStore(), ...JSON.parse(fs.readFileSync(STORE_PATH, 'utf8')) };
    } catch (err) {
        return emptyStore();
    }
}

function saveStore(store) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    store.updatedAt = new Date().toISOString();
    fs.writeFileSync(STORE_PATH, JSON.stringify(store, null, 2), 'utf8');
}

function id() {
    return crypto.randomUUID();
}

function normalizeAnswer(value) {
    return String(value || '')
        .toLowerCase()
        .replace(/[−–—]/g, '-')
        .replace(/²/g, '^2')
        .replace(/³/g, '^3')
        .replace(/π/g, 'pi')
        .replace(/입니다|정답|답은|답/g, '')
        .replace(/또는|혹은|or/gi, '|')
        .replace(/[,\s]/g, '')
        .replace(/\.0+(?=[a-z가-힣|]|$)/g, '');
}

function answerMatches(expected, actual) {
    const expectedParts = normalizeAnswer(expected).split('|').filter(Boolean).sort();
    const actualParts = normalizeAnswer(actual).split('|').filter(Boolean).sort();
    if (!expectedParts.length || !actualParts.length) return false;
    if (expectedParts.join('|') === actualParts.join('|')) return true;
    const expectedCompact = expectedParts.join('|');
    const actualCompact = actualParts.join('|');
    return expectedCompact.includes(actualCompact) || actualCompact.includes(expectedCompact);
}

function addBenchmarkCases(items, defaults = {}) {
    const store = loadStore();
    const added = [];
    for (const raw of items) {
        const question = String(raw.question || raw.problem || raw.problemText || '').trim();
        const expectedAnswer = String(raw.expectedAnswer || raw.answer || raw.expected_answer || '').trim();
        if (!question || !expectedAnswer) continue;
        const item = {
            id: id(),
            subject: raw.subject || defaults.subject || 'math',
            unit: raw.unit || defaults.unit || '',
            question,
            expectedAnswer,
            source: raw.source || defaults.source || 'admin',
            tags: Array.isArray(raw.tags)
                ? raw.tags
                : String(raw.tags || '').split(',').map(tag => tag.trim()).filter(Boolean),
            createdAt: new Date().toISOString()
        };
        store.benchmarkCases.push(item);
        added.push(item);
    }
    saveStore(store);
    return added;
}

function addFailure(raw) {
    const store = loadStore();
    const fingerprint = [
        raw.benchmarkCaseId || '',
        normalizeAnswer(raw.expectedAnswer),
        normalizeAnswer(raw.actualAnswer),
        String(raw.question || '').trim()
    ].join('::');
    const existing = store.failureCases.find(item => item.fingerprint === fingerprint && item.status === 'open');
    if (existing) {
        existing.occurrences = (existing.occurrences || 1) + 1;
        existing.updatedAt = new Date().toISOString();
        saveStore(store);
        return existing;
    }
    const failure = {
        id: id(),
        benchmarkCaseId: raw.benchmarkCaseId || null,
        subject: raw.subject || 'auto',
        unit: raw.unit || '',
        question: String(raw.question || '').trim(),
        expectedAnswer: String(raw.expectedAnswer || '').trim(),
        actualAnswer: String(raw.actualAnswer || '').trim(),
        actualSolution: String(raw.actualSolution || '').trim().slice(0, 8000),
        correctedSolution: String(raw.correctedSolution || '').trim().slice(0, 8000),
        category: raw.category || 'answer_mismatch',
        source: raw.source || 'benchmark',
        note: String(raw.note || '').trim().slice(0, 2000),
        status: 'open',
        occurrences: 1,
        fingerprint,
        createdAt: new Date().toISOString()
    };
    store.failureCases.unshift(failure);
    saveStore(store);
    return failure;
}

function metrics(store = loadStore()) {
    const latest = store.benchmarkRuns[0] || null;
    const openFailures = store.failureCases.filter(item => item.status === 'open');
    return {
        materials: store.materials.length,
        solutionPatterns: store.solutionPatterns.length,
        benchmarkCases: store.benchmarkCases.length,
        benchmarkRuns: store.benchmarkRuns.length,
        openFailures: openFailures.length,
        latestAccuracy: latest?.accuracy ?? null,
        latestRunAt: latest?.createdAt || null
    };
}

module.exports = {
    DATA_DIR,
    UPLOAD_DIR,
    STORE_PATH,
    addBenchmarkCases,
    addFailure,
    answerMatches,
    ensureDataDirs,
    id,
    loadStore,
    metrics,
    normalizeAnswer,
    saveStore
};
