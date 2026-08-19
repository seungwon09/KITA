const express = require('express');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const crypto = require('crypto');

const { solveWithStudyAi } = require('../services/studyAiClient');
const { parseUploadedMaterial } = require('../services/materialParser');
const { UPLOAD_DIR, addBenchmarkCases, addFailure, answerMatches, ensureDataDirs, id, loadStore, metrics, saveStore } = require('../services/qualityStore');
const { auditSecurityEvent, materialFileFilter, secureEqual } = require('../middleware/security');

const router = express.Router();

function requireAdmin(req, res, next) {
    if (!process.env.ADMIN_PIN) return res.status(503).json({ ok: false, error: 'ADMIN_PIN_NOT_CONFIGURED' });
    if (!secureEqual(req.headers['x-admin-pin'], process.env.ADMIN_PIN)) {
        auditSecurityEvent(req, 'admin_pin_rejected');
        return res.status(401).json({ ok: false, error: 'ADMIN_AUTH_REQUIRED' });
    }
    next();
}

function safeFileName(name) {
    const ext = path.extname(name || '').slice(0, 16);
    const base = path.basename(name || 'upload', ext).replace(/[^\w.-]+/g, '_').slice(0, 80) || 'upload';
    return `${Date.now()}_${crypto.randomUUID()}_${base}${ext}`;
}

const upload = multer({
    storage: multer.diskStorage({
        destination(req, file, cb) { ensureDataDirs(); cb(null, UPLOAD_DIR); },
        filename(req, file, cb) { cb(null, safeFileName(file.originalname)); }
    }),
    fileFilter: materialFileFilter,
    limits: { fileSize: 80 * 1024 * 1024, files: 1 }
});

function publicMaterial(item) {
    return { ...item, localPath: undefined, searchText: undefined };
}

function releaseStatus(req) {
    const rootDir = path.resolve(__dirname, '../../..');
    const publicBaseUrl = process.env.PUBLIC_BASE_URL || `${req.protocol}://${req.get('host')}`;
    const hasTossKeys = Boolean(process.env.TOSS_CLIENT_KEY && process.env.TOSS_SECRET_KEY);
    const devPayments = process.env.ALLOW_DEV_PAYMENTS === 'true' && process.env.NODE_ENV !== 'production';
    return [
        {
            label: 'Git 저장소',
            ready: fs.existsSync(path.join(rootDir, '.git')),
            detail: '코드 되돌리기와 백업 기준점'
        },
        {
            label: 'AI API',
            ready: Boolean(process.env.AI_API_KEY || process.env.OPENAI_API_KEY),
            detail: process.env.AI_API_MODEL || '모델 설정 대기'
        },
        {
            label: '카카오 로그인',
            ready: Boolean(process.env.KAKAO_REST_API_KEY),
            detail: process.env.KAKAO_REST_API_KEY ? '개발자 키 연결됨' : 'REST API 키 입력 필요'
        },
        {
            label: '결제',
            ready: hasTossKeys || devPayments,
            detail: hasTossKeys ? '토스 키 연결됨' : devPayments ? '개발모드 테스트 가능' : '토스 키 또는 개발모드 필요'
        },
        {
            label: '배포 주소',
            ready: /^https:\/\//.test(publicBaseUrl),
            detail: publicBaseUrl
        }
    ];
}

function parseCsvLine(line) {
    const values = [];
    let value = '';
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
        const char = line[index];
        if (char === '"' && line[index + 1] === '"') { value += '"'; index += 1; }
        else if (char === '"') quoted = !quoted;
        else if (char === ',' && !quoted) { values.push(value.trim()); value = ''; }
        else value += char;
    }
    values.push(value.trim());
    return values;
}

function parseDataset(content, ext) {
    if (ext === '.json') {
        const parsed = JSON.parse(content);
        return Array.isArray(parsed) ? parsed : parsed.cases || parsed.items || [];
    }
    if (ext === '.csv') {
        const lines = content.split(/\r?\n/).filter(line => line.trim());
        if (!lines.length) return [];
        const headers = parseCsvLine(lines[0]);
        return lines.slice(1).map(line => Object.fromEntries(headers.map((header, index) => [header, parseCsvLine(line)[index] || ''])));
    }
    return content.split(/\r?\n/).filter(line => line.trim()).map(line => {
        const [question, expectedAnswer, subject = '', unit = ''] = line.split('|').map(value => value.trim());
        return { question, expectedAnswer, subject, unit };
    });
}

async function normalizeMaterial(body, file, overrides = {}) {
    const parsed = await parseUploadedMaterial(file);
    return {
        id: id(),
        type: body.type || 'problem_book',
        subject: body.subject || 'mixed',
        title: body.title || file.originalname,
        grade: body.grade || '',
        source: body.source || '',
        memo: body.memo || '',
        originalName: file.originalname,
        fileName: file.filename,
        localPath: file.path,
        mimeType: file.mimetype,
        size: file.size,
        parseStatus: parsed.parseStatus,
        textPreview: parsed.textPreview,
        indexedCharacters: parsed.indexedCharacters || 0,
        pages: parsed.pages || 0,
        parser: parsed.parser || 'none',
        parseNote: parsed.parseNote || '',
        searchText: [body.title, body.subject, body.grade, body.source, body.memo, file.originalname, parsed.searchText].filter(Boolean).join('\n').toLowerCase(),
        aiUse: 'library_search',
        uploadedAt: new Date().toISOString(),
        ...overrides
    };
}

router.get('/status', requireAdmin, (req, res) => res.json({ ok: true, ...metrics(loadStore()), adminProtection: 'ADMIN_PIN' }));
router.get('/dashboard', requireAdmin, (req, res) => {
    const store = loadStore();
    res.json({ ok: true, metrics: metrics(store), releaseStatus: releaseStatus(req), latestRun: store.benchmarkRuns[0] || null, recentFailures: store.failureCases.filter(item => item.status === 'open').slice(0, 30), recentCases: store.benchmarkCases.slice(-20).reverse() });
});
router.get('/library', requireAdmin, (req, res) => {
    const store = loadStore();
    res.json({ ok: true, materials: store.materials.map(publicMaterial), solutionPatterns: store.solutionPatterns, integrations: store.integrations || {} });
});
router.get('/search', requireAdmin, (req, res) => {
    const q = String(req.query.q || '').trim().toLowerCase();
    const store = loadStore();
    res.json({ ok: true, query: q, materials: q ? store.materials.filter(item => String(item.searchText || '').includes(q)).slice(0, 20).map(publicMaterial) : [], solutionPatterns: q ? store.solutionPatterns.filter(item => JSON.stringify(item).toLowerCase().includes(q)).slice(0, 20) : [] });
});

router.post('/materials', requireAdmin, upload.single('file'), async (req, res) => {
    if (!req.file) return res.status(400).json({ ok: false, error: '업로드할 파일이 없습니다.' });
    const store = loadStore();
    const material = await normalizeMaterial(req.body || {}, req.file);
    store.materials.unshift(material);
    saveStore(store);
    res.json({ ok: true, material: publicMaterial(material) });
});
router.post('/materials/:id/reparse', requireAdmin, async (req, res) => {
    const store = loadStore();
    const material = store.materials.find(item => item.id === req.params.id);
    if (!material?.localPath || !fs.existsSync(material.localPath)) return res.status(404).json({ ok: false, error: '다시 분석할 자료를 찾지 못했습니다.' });
    const parsed = await parseUploadedMaterial({ path: material.localPath, originalname: material.originalName, filename: material.fileName, mimetype: material.mimeType });
    Object.assign(material, parsed, { reparsedAt: new Date().toISOString(), searchText: [material.title, material.subject, material.originalName, parsed.searchText].filter(Boolean).join('\n').toLowerCase() });
    saveStore(store);
    res.json({ ok: true, material: publicMaterial(material) });
});
router.delete('/materials/:id', requireAdmin, (req, res) => {
    const store = loadStore();
    const target = store.materials.find(item => item.id === req.params.id);
    store.materials = store.materials.filter(item => item.id !== req.params.id);
    if (target?.localPath) {
        const resolved = path.resolve(target.localPath);
        const uploadRoot = `${path.resolve(UPLOAD_DIR)}${path.sep}`;
        if (resolved.startsWith(uploadRoot) && fs.existsSync(resolved)) fs.unlinkSync(resolved);
    }
    saveStore(store);
    res.json({ ok: true });
});

router.post('/benchmark/import', requireAdmin, upload.single('file'), async (req, res) => {
    if (!req.file) return res.status(400).json({ ok: false, error: 'CSV, JSON 또는 TXT 파일을 선택해 주세요.' });
    try {
        const ext = path.extname(req.file.originalname || '').toLowerCase();
        if (!['.csv', '.json', '.txt'].includes(ext)) return res.status(400).json({ ok: false, error: '자동 채점 데이터는 CSV, JSON, TXT 형식만 지원합니다.' });
        const rows = parseDataset(fs.readFileSync(req.file.path, 'utf8'), ext);
        const added = addBenchmarkCases(rows, { subject: req.body.subject || 'math', unit: req.body.unit || '', source: req.file.originalname });
        const store = loadStore();
        store.materials.unshift(await normalizeMaterial({ ...req.body, type: 'benchmark_dataset', title: req.body.title || req.file.originalname }, req.file, { aiUse: 'auto_benchmark', importedCases: added.length, parseStatus: 'benchmark_indexed' }));
        saveStore(store);
        res.json({ ok: true, imported: added.length, skipped: Math.max(0, rows.length - added.length), cases: added.slice(0, 20) });
    } catch (err) {
        res.status(400).json({ ok: false, error: `검증 데이터 분석 실패: ${err.message}` });
    }
});

router.post('/benchmark/cases', requireAdmin, (req, res) => {
    const added = addBenchmarkCases(Array.isArray(req.body?.items) ? req.body.items : [req.body || {}], { source: 'admin_manual' });
    if (!added.length) return res.status(400).json({ ok: false, error: '문제와 정답을 모두 입력해 주세요.' });
    res.json({ ok: true, added: added.length, cases: added });
});
router.post('/benchmark/seed', requireAdmin, (req, res) => {
    const store = loadStore();
    if (store.benchmarkCases.some(item => item.source === 'kita_starter')) return res.json({ ok: true, added: 0, message: '기본 검증 문제가 이미 등록되어 있습니다.' });
    const added = addBenchmarkCases([
        { subject: 'math', unit: '이차함수', question: '이차함수 y=x^2-4x+1의 최솟값을 구하시오.', expectedAnswer: '-3' },
        { subject: 'math', unit: '이차방정식', question: '방정식 x^2-5x+6=0을 풀어 보시오.', expectedAnswer: 'x=2 또는 x=3' },
        { subject: 'math', unit: '도형', question: '밑변 8, 높이 5인 삼각형의 넓이를 구하시오.', expectedAnswer: '20' },
        { subject: 'math', unit: '방정식', question: '방정식 3x+2=11을 풀어 보시오.', expectedAnswer: 'x=3' },
        { subject: 'math', unit: '비율', question: '200의 15%를 구하시오.', expectedAnswer: '30' },
        { subject: 'science', unit: '물리/힘', question: '질량 2kg, 가속도 3m/s^2일 때 힘을 구하시오.', expectedAnswer: '6N' },
        { subject: 'science', unit: '물리/전기', question: '전류 2A, 저항 5Ω일 때 전압과 전력을 각각 구하시오.', expectedAnswer: '10V, 20W' },
        { subject: 'science', unit: '물리/파동', question: '파장 3m, 진동수 4Hz인 파동의 속력을 구하시오.', expectedAnswer: '12m/s' },
        { subject: 'science', unit: '물리/에너지', question: '질량 2kg, 속력 6m/s인 물체의 운동 에너지를 구하시오.', expectedAnswer: '36J' },
        { subject: 'science', unit: '물리/전기', question: '전압 12V, 전류 3A일 때 전력을 구하시오.', expectedAnswer: '36W' }
    ], { source: 'kita_starter' });
    res.json({ ok: true, added: added.length, message: '기본 검증 문제를 추가했습니다.' });
});
router.get('/benchmark/cases', requireAdmin, (req, res) => res.json({ ok: true, cases: loadStore().benchmarkCases.slice().reverse() }));
router.delete('/benchmark/cases/:id', requireAdmin, (req, res) => {
    const store = loadStore();
    store.benchmarkCases = store.benchmarkCases.filter(item => item.id !== req.params.id);
    saveStore(store);
    res.json({ ok: true });
});
router.post('/benchmark/run', requireAdmin, async (req, res) => {
    const store = loadStore();
    const cases = store.benchmarkCases.slice(-Math.max(1, Math.min(Number(req.body?.limit) || 100, 300)));
    if (!cases.length) return res.status(400).json({ ok: false, error: '먼저 검증 문제를 등록해 주세요.' });
    const results = [];
    for (const item of cases) {
        try {
            const ai = await solveWithStudyAi({ question: item.question, subject: item.subject, userId: 'admin-benchmark', elapsedSeconds: null });
            const actualAnswer = ai.verifiedAnswer || '';
            const correct = Boolean(ai.ok) && answerMatches(item.expectedAnswer, actualAnswer);
            results.push({ caseId: item.id, subject: item.subject, question: item.question, expectedAnswer: item.expectedAnswer, actualAnswer, correct, provider: ai.provider });
            if (!correct) addFailure({ benchmarkCaseId: item.id, subject: item.subject, unit: item.unit, question: item.question, expectedAnswer: item.expectedAnswer, actualAnswer, actualSolution: ai.solution, category: actualAnswer ? 'answer_mismatch' : 'no_verified_answer', source: 'auto_benchmark' });
            if (correct) {
                const updated = loadStore();
                let changed = false;
                updated.failureCases.forEach(failure => {
                    if (failure.benchmarkCaseId === item.id && failure.status === 'open') {
                        Object.assign(failure, { status: 'auto_resolved', resolvedAt: new Date().toISOString(), note: '재검증에서 정답이 확인되어 자동 해결되었습니다.' });
                        changed = true;
                    }
                });
                if (changed) saveStore(updated);
            }
        } catch (err) {
            results.push({ caseId: item.id, subject: item.subject, question: item.question, expectedAnswer: item.expectedAnswer, actualAnswer: '', correct: false, error: err.message });
            addFailure({ benchmarkCaseId: item.id, subject: item.subject, unit: item.unit, question: item.question, expectedAnswer: item.expectedAnswer, category: 'solver_error', source: 'auto_benchmark', note: err.message });
        }
    }
    const passed = results.filter(item => item.correct).length;
    const run = { id: id(), total: results.length, passed, failed: results.length - passed, accuracy: Number(((passed / results.length) * 100).toFixed(1)), results, createdAt: new Date().toISOString() };
    const fresh = loadStore();
    fresh.benchmarkRuns.unshift(run);
    fresh.benchmarkRuns = fresh.benchmarkRuns.slice(0, 30);
    saveStore(fresh);
    res.json({ ok: true, run, metrics: metrics(fresh) });
});

router.get('/failures', requireAdmin, (req, res) => {
    const store = loadStore();
    const status = String(req.query.status || 'open');
    res.json({ ok: true, failures: status === 'all' ? store.failureCases : store.failureCases.filter(item => item.status === status) });
});
router.patch('/failures/:id', requireAdmin, (req, res) => {
    const store = loadStore();
    const failure = store.failureCases.find(item => item.id === req.params.id);
    if (!failure) return res.status(404).json({ ok: false, error: '개선 항목을 찾지 못했습니다.' });
    Object.assign(failure, { status: req.body?.status || 'resolved', note: req.body?.note ?? failure.note, resolvedAt: new Date().toISOString() });
    saveStore(store);
    res.json({ ok: true, failure });
});
router.post('/failures/:id/promote', requireAdmin, (req, res) => {
    const store = loadStore();
    const failure = store.failureCases.find(item => item.id === req.params.id);
    if (!failure) return res.status(404).json({ ok: false, error: '개선 항목을 찾지 못했습니다.' });
    const pattern = {
        id: id(),
        subject: failure.subject,
        unit: failure.unit,
        problemType: '오답 보정',
        problemText: failure.question,
        answer: failure.expectedAnswer,
        basicSolution: req.body?.correctedSolution || failure.correctedSolution || '',
        fastSolution: req.body?.fastSolution || '',
        eliteSolution: req.body?.eliteSolution || '',
        tags: ['quality_fix', failure.category],
        createdAt: new Date().toISOString()
    };
    store.solutionPatterns.unshift(pattern);
    Object.assign(failure, { status: 'promoted', resolvedAt: new Date().toISOString() });
    saveStore(store);
    res.json({ ok: true, pattern, failure });
});
router.post('/solution-patterns', requireAdmin, (req, res) => {
    const store = loadStore();
    const pattern = { id: id(), ...req.body, createdAt: new Date().toISOString() };
    store.solutionPatterns.unshift(pattern);
    saveStore(store);
    res.json({ ok: true, pattern });
});
router.delete('/solution-patterns/:id', requireAdmin, (req, res) => {
    const store = loadStore();
    store.solutionPatterns = store.solutionPatterns.filter(item => item.id !== req.params.id);
    saveStore(store);
    res.json({ ok: true });
});

module.exports = router;
