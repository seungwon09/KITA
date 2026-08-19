const express = require('express');
const multer = require('multer');
const { checkStudyAiHealth, requestMultipart, requestStudyAi, solveWithStudyAi } = require('../services/studyAiClient');
const { askExternalAi, externalAiStatus, solveWithExternalAi } = require('../services/externalAiClient');
const { addFailure, answerMatches } = require('../services/qualityStore');
const { consume } = require('../services/plans');
const auth = require('../middleware/auth');
const { aiImageFileFilter } = require('../middleware/security');

const router = express.Router();
const upload = multer({
    storage: multer.memoryStorage(),
    fileFilter: aiImageFileFilter,
    limits: { fileSize: 10 * 1024 * 1024, files: 1 }
});
const LOCAL_LLM_URL = process.env.LOCAL_LLM_URL || 'http://127.0.0.1:11434/api/generate';
const LOCAL_LLM_MODEL = process.env.LOCAL_LLM_MODEL || 'qwen2.5:3b';
const clean = (value, max = 8000) => String(value || '').trim().slice(0, max);
const subject = req => ['math', 'science', 'mixed', 'auto'].includes(req.body?.subject) ? req.body.subject : 'auto';
const fmt = value => Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)));

function limit(type) {
    return async (req, res, next) => {
        const access = await consume(req, type);
        if (!access.ok) return res.status(access.status).json(access);
        req.kitaAccess = access; next();
    };
}
async function localLlm(prompt) {
    const response = await fetch(LOCAL_LLM_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: LOCAL_LLM_MODEL, prompt, stream: false, options: { temperature: 0.2, top_p: 0.85, num_predict: 520 } }), signal: AbortSignal.timeout(42000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '로컬 AI가 응답하지 않았습니다.');
    return clean(data.response, 12000);
}
function verifiedChat(message) {
    if (/로켓|rocket|치올콥스키|tsiolkovsky/i.test(message)) return ['로켓 방정식은 보통 치올콥스키 로켓 방정식을 뜻합니다.','','\\[\\Delta v = v_e \\ln\\left(\\frac{m_0}{m_f}\\right)\\]','','- \\(\\Delta v\\): 로켓이 얻을 수 있는 속도 변화량','- \\(v_e\\): 배기 속도','- \\(m_0\\): 연료를 포함한 초기 질량','- \\(m_f\\): 연료를 사용한 뒤의 질량','','핵심은 질량비가 클수록 더 큰 속도 변화량을 얻는다는 점입니다. 실제 궤도 계산에는 중력, 공기 저항, 추력 방향을 함께 고려합니다.'].join('\n');
    if (/광합성/.test(message)) return ['광합성은 식물이 빛에너지를 이용해 포도당을 만들고 산소를 내보내는 과정입니다.','','\\[6CO_2 + 6H_2O \\rightarrow C_6H_{12}O_6 + 6O_2\\]','','시험에서는 장소는 엽록체, 필요한 것은 빛·물·이산화탄소, 생성물은 포도당·산소로 기억하면 됩니다.'].join('\n');
    if (/뉴턴.*법칙|작용.*반작용/.test(message)) return ['뉴턴의 운동 법칙은 물체의 움직임과 힘의 관계를 설명합니다.','','1. 관성: 알짜힘이 0이면 운동 상태가 유지됩니다.','2. 가속도: \\(F=ma\\). 힘이 클수록 가속도가 커집니다.','3. 작용·반작용: 두 물체가 주고받는 힘은 크기가 같고 방향이 반대입니다.'].join('\n');
    if (/DNA|유전자|염색체/i.test(message)) return ['DNA는 생물의 유전 정보를 저장하는 분자입니다.','','- DNA: 유전 정보를 담는 긴 분자','- 유전자: DNA 중 특정 기능에 필요한 정보 구간','- 염색체: DNA가 단백질과 함께 정리된 구조','','즉, 염색체 안에 DNA가 있고 DNA의 일부 구간이 유전자입니다.'].join('\n');
    if (/수행평가|보고서|발표|탐구/.test(message)) return ['수행평가는 주제를 좁게 잡고, 교과 개념과 실제 사례를 연결하면 좋습니다.','','추천 구성','1. 주제 선택 이유','2. 핵심 개념 2~3개','3. 사례 또는 간단한 실험','4. 표·그래프로 근거 제시','5. 해석과 결론','','원하는 과목과 학년을 알려 주면 주제와 목차를 더 구체적으로 만들 수 있습니다.'].join('\n');
    return null;
}
function fallbackChat(message) {
    return [`질문을 이렇게 정리해 볼 수 있습니다: ${message}`,'','정확한 답을 만들려면 조건과 구하려는 값을 나누어 보세요. 문제 사진이나 더 구체적인 조건을 보내면 풀이형 답변으로 바꿔 드릴게요.'].join('\n');
}
function graphAnalysis(text) {
    const compact = clean(text).replace(/\s+/g, '').replace(/²/g, '^2');
    let match = compact.match(/\(x([+-]\d+(?:\.\d+)?)\)\^2\+\(y([+-]\d+(?:\.\d+)?)\)\^2=(\d+(?:\.\d+)?)(\^2)?/);
    if (match) {
        const x = -Number(match[1]), y = -Number(match[2]), r = match[4] ? Number(match[3]) : Math.sqrt(Number(match[3]));
        return { ok: true, graphType: '원의 방정식', confidence: 0.92, conclusion: `중심은 (${fmt(x)}, ${fmt(y)}), 반지름은 ${fmt(r)}입니다.`, keyFeatures: [`중심: (${fmt(x)}, ${fmt(y)})`, `반지름: ${fmt(r)}`], solutionSteps: ['(x-a)^2+(y-b)^2=r^2 꼴과 비교합니다.', '괄호 안 부호를 반대로 읽어 중심을 구합니다.'], warnings: ['중심 좌표의 부호를 반대로 읽는 실수에 주의하세요.'] };
    }
    match = compact.match(/(?:y=)?([+-]?(?:\d+(?:\.\d+)?)?)x\^2([+-]\d+(?:\.\d+)?)x?([+-]\d+(?:\.\d+)?)?/);
    if (match) {
        const a = Number(match[1] === '' || match[1] === '+' ? 1 : match[1] === '-' ? -1 : match[1]), b = Number(match[2] || 0), c = Number(match[3] || 0), vx = -b / (2 * a), vy = a * vx * vx + b * vx + c;
        return { ok: true, graphType: '이차함수 그래프', confidence: 0.92, conclusion: `꼭짓점은 (${fmt(vx)}, ${fmt(vy)})이고 축의 방정식은 x=${fmt(vx)}입니다.`, keyFeatures: [`꼭짓점: (${fmt(vx)}, ${fmt(vy)})`, `축: x=${fmt(vx)}`, a > 0 ? `최솟값: ${fmt(vy)}` : `최댓값: ${fmt(vy)}`], solutionSteps: [`x=-b/(2a)=${fmt(vx)}`, `x=${fmt(vx)}를 식에 대입하면 y=${fmt(vy)}`], warnings: ['최솟값과 그때의 x값을 혼동하지 마세요.'] };
    }
    match = compact.match(/(?:y=)?([+-]?(?:\d+(?:\.\d+)?)?)x([+-]\d+(?:\.\d+)?)?/);
    if (match) {
        const a = Number(match[1] === '' || match[1] === '+' ? 1 : match[1] === '-' ? -1 : match[1]), b = Number(match[2] || 0);
        return { ok: true, graphType: '일차함수 그래프', confidence: 0.9, conclusion: `기울기는 ${fmt(a)}, y절편은 ${fmt(b)}입니다.`, keyFeatures: [`기울기: ${fmt(a)}`, `y절편: ${fmt(b)}`], solutionSteps: ['y=ax+b 꼴에서 a는 기울기, b는 y절편입니다.'], warnings: ['기울기와 y절편을 바꾸어 읽지 마세요.'] };
    }
    return { ok: true, graphType: '그래프 분석', confidence: 0.55, conclusion: '식, 좌표, 축 이름을 더 선명하게 입력하면 핵심 지점을 분석할 수 있습니다.', keyFeatures: ['축 이름', '단위', '절편', '기울기 또는 꼭짓점'], solutionSteps: ['축과 단위를 확인합니다.', '문제가 묻는 값과 연결되는 지점을 찾습니다.'], warnings: ['사진 그래프는 숫자를 한 번 확인해 주세요.'] };
}
function geometryAnalysis(text) {
    const raw = clean(text);
    const nums = [...raw.matchAll(/\d+(?:\.\d+)?/g)].map(item => Number(item[0]));
    if (/원|circle/i.test(raw) && nums.length) { const r = nums[0]; return { ok: true, shape: '원', confidence: 0.88, conclusion: `반지름이 ${fmt(r)}인 원의 넓이는 ${fmt(Math.PI * r * r)}, 둘레는 ${fmt(2 * Math.PI * r)}입니다.`, formulas: ['넓이 = πr^2', '둘레 = 2πr'], steps: [`r=${fmt(r)}를 공식에 대입합니다.`], mistakes: ['반지름과 지름을 혼동하지 마세요.'] }; }
    if (/사다리꼴|trapezoid/i.test(raw) && nums.length >= 3) { const [a, b, h] = nums; return { ok: true, shape: '사다리꼴', confidence: 0.86, conclusion: `넓이는 ${fmt((a + b) * h / 2)}입니다.`, formulas: ['넓이 = (윗변 + 아랫변) × 높이 ÷ 2'], steps: [`(${a}+${b})×${h}÷2=${fmt((a + b) * h / 2)}`], mistakes: ['마지막에 2로 나누는 것을 잊지 마세요.'] }; }
    if (/삼각형|triangle/i.test(raw) && nums.length >= 2) { const [a, h] = nums; return { ok: true, shape: '삼각형', confidence: 0.86, conclusion: `넓이는 ${fmt(a * h / 2)}입니다.`, formulas: ['넓이 = 밑변 × 높이 ÷ 2'], steps: [`${a}×${h}÷2=${fmt(a * h / 2)}`], mistakes: ['높이가 아닌 변의 길이를 높이로 쓰지 마세요.'] }; }
    if (/직사각형|rectangle/i.test(raw) && nums.length >= 2) { const [a, b] = nums; return { ok: true, shape: '직사각형', confidence: 0.86, conclusion: `넓이는 ${fmt(a * b)}, 둘레는 ${fmt(2 * (a + b))}입니다.`, formulas: ['넓이 = 가로 × 세로', '둘레 = 2 × (가로 + 세로)'], steps: [`${a}×${b}=${fmt(a * b)}`], mistakes: ['넓이와 둘레를 혼동하지 마세요.'] }; }
    if (/직각|피타고라스|빗변/i.test(raw) && nums.length >= 2) { const [a, b] = nums; return { ok: true, shape: '직각삼각형', confidence: 0.84, conclusion: `빗변은 ${fmt(Math.sqrt(a * a + b * b))}입니다.`, formulas: ['a^2+b^2=c^2'], steps: [`√(${a}^2+${b}^2)=${fmt(Math.sqrt(a * a + b * b))}`], mistakes: ['가장 긴 변이 빗변입니다.'] }; }
    return { ok: true, shape: '도형', confidence: 0.55, conclusion: '도형 종류와 길이를 더 적어 주면 넓이, 둘레, 각도를 계산할 수 있습니다.', formulas: ['삼각형: 밑변×높이÷2', '원: πr^2, 2πr', '직각삼각형: a^2+b^2=c^2'], steps: ['도형 이름을 확인합니다.', '주어진 길이와 구할 값을 나눕니다.'], mistakes: ['단위와 높이를 확인하세요.'] };
}

router.get('/health', async (req, res) => { const studyAi = await checkStudyAiHealth(); res.status(studyAi.ok ? 200 : 503).json({ ok: studyAi.ok, studyAi }); });
router.get('/status', async (req, res) => { const studyAi = await checkStudyAiHealth(); res.json({ ok: true, node: 'kita-web', localModel: LOCAL_LLM_MODEL, externalAi: externalAiStatus(), studyAi, featureCount: 30 }); });

router.use(auth);

async function chat(req, res) {
    const message = clean(req.body?.message || req.body?.question || req.body?.problem_text, 5000);
    if (!message) return res.status(400).json({ ok: false, error: '질문을 입력해 주세요.' });
    let apiWarning = null;
    if (externalAiStatus().enabled) {
        try {
            return res.json(await askExternalAi({
                message,
                subject: subject(req),
                history: req.body?.history || []
            }));
        } catch (err) {
            apiWarning = err.message;
            console.warn(`External AI chat fallback: ${err.message}`);
        }
    }
    const verified = verifiedChat(message);
    if (verified) return res.json({ ok: true, provider: 'kita-verified', reply: verified, apiWarning });
    if (apiWarning) {
        try {
            return res.json({
                ok: true,
                provider: 'local-llm',
                reply: await localLlm(`Answer in Korean as KITA, a study assistant. Be concise and accurate.\nStudent question: ${message}\nKITA answer:`),
                apiWarning
            });
        } catch (err) {
            return res.json({ ok: true, provider: 'kita-fallback', reply: fallbackChat(message), warning: err.message, apiWarning });
        }
    }
    try { res.json({ ok: true, provider: 'local-llm', reply: await localLlm(`너는 중고등학생을 돕는 KITA 공부 AI다. 한국어로 결론부터 짧고 정확하게 답하고, 모르면 모른다고 말한다.\n학생 질문: ${message}\nKITA 답변:`) }); }
    catch (err) { res.json({ ok: true, provider: 'kita-fallback', reply: fallbackChat(message), warning: err.message, apiWarning }); }
}
router.post('/chat', limit('ai'), chat);
router.post('/ask', limit('ai'), chat);
router.post('/graph', limit('ai'), (req, res) => res.json(graphAnalysis(req.body?.graph_text || req.body?.question)));
router.post('/geometry', limit('ai'), (req, res) => res.json(geometryAnalysis(req.body?.geometry_text || req.body?.question)));
router.post('/ocr', limit('ocr'), upload.single('image'), async (req, res) => {
    if (!req.file) return res.status(400).json({ ok: false, error: '이미지 파일이 없습니다.' });
    const form = new FormData(); form.append('image', new Blob([req.file.buffer], { type: req.file.mimetype }), req.file.originalname || 'problem.png');
    try { res.json(await requestMultipart('/ocr', form)); } catch (err) { res.status(503).json({ ok: false, error: err.message }); }
});
router.post('/graph-image', limit('ocr'), upload.single('image'), async (req, res) => {
    if (!req.file) return res.status(400).json({ ok: false, error: '이미지 파일이 없습니다.' });
    try {
        const form = new FormData(); form.append('image', new Blob([req.file.buffer], { type: req.file.mimetype }), req.file.originalname || 'graph.png');
        const ocr = await requestMultipart('/ocr', form), combined = [req.body?.graph_text, ocr.normalized_text || ocr.extracted_text || ocr.text].filter(Boolean).join('\n');
        const graph = graphAnalysis(combined), geometry = geometryAnalysis(combined);
        res.json({ ok: true, type: 'image_analysis', ocr, graph, geometry, conclusion: graph.confidence >= geometry.confidence ? graph.conclusion : geometry.conclusion, warnings: ['사진 속 숫자와 기호는 한 번 확인해 주세요.'] });
    } catch (err) { res.status(503).json({ ok: false, error: err.message }); }
});
router.post('/solve', limit('ai'), async (req, res) => {
    try {
        const question = clean(req.body?.question || req.body?.problem_text, 6000);
        if (!question) return res.status(400).json({ ok: false, error: '문제를 입력해 주세요.' });
        let result = null;
        let apiWarning = null;
        if (externalAiStatus().enabled) {
            try {
                result = await solveWithExternalAi({
                    question,
                    subject: subject(req),
                    elapsedSeconds: Number(req.body?.solveTime || req.body?.elapsed_seconds),
                    studentLevel: clean(req.body?.student_level || 'intermediate', 80)
                });
            } catch (err) {
                apiWarning = err.message;
                console.warn(`External AI solve fallback: ${err.message}`);
            }
        }
        if (!result) {
            result = await solveWithStudyAi({ question, subject: subject(req), userId: clean(req.body?.user_id || 'kita-user', 80), elapsedSeconds: Number(req.body?.solveTime || req.body?.elapsed_seconds) });
            if (apiWarning) result.apiWarning = apiWarning;
        }
        const expected = clean(req.body?.expected_answer || req.body?.expectedAnswer, 500);
        if (expected && !answerMatches(expected, result.verifiedAnswer || '')) addFailure({ subject: subject(req), question, expectedAnswer: expected, actualAnswer: result.verifiedAnswer || '', actualSolution: result.solution || '', category: result.verifiedAnswer ? 'answer_mismatch' : 'no_verified_answer', source: 'solve_with_answer_key' });
        if (!req.kitaAccess.plan.limits.eliteSolution) { result.eliteSolution = ''; result.eliteLocked = true; }
        result.access = { planId: req.kitaAccess.plan.id, planName: req.kitaAccess.plan.name, remainingToday: req.kitaAccess.remaining };
        res.status(result.ok ? 200 : 503).json(result);
    } catch (err) { res.status(500).json({ ok: false, error: 'AI 풀이 중 오류가 발생했습니다.', detail: err.message }); }
});
router.post('/recognize', limit('ai'), async (req, res) => { try { res.json(await requestStudyAi('/app-ai/problem/recognize', { method: 'POST', body: { user_id: clean(req.body?.user_id || 'kita-user'), problem_text: req.body?.problem_text || req.body?.question || '', subject: subject(req), source: 'kita-web' } })); } catch (err) { res.status(503).json({ ok: false, error: err.message }); } });
router.post('/quality', limit('ai'), async (req, res) => { try { res.json(await requestStudyAi('/app-ai/quality/check', { method: 'POST', body: req.body || {} })); } catch (err) { res.status(503).json({ ok: false, error: err.message }); } });

module.exports = router;
