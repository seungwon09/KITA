const AI_API_PROVIDER = process.env.AI_API_PROVIDER || 'openai-compatible';
const AI_API_KEY = process.env.AI_API_KEY || process.env.OPENAI_API_KEY || '';
const AI_API_BASE_URL = (process.env.AI_API_BASE_URL || 'https://api.openai.com/v1').replace(/\/$/, '');
const AI_API_MODEL = process.env.AI_API_MODEL || process.env.OPENAI_MODEL || 'gpt-4.1-mini';
const AI_API_TIMEOUT_MS = Number(process.env.AI_API_TIMEOUT_MS || 45000);

function externalAiStatus() {
    return {
        enabled: Boolean(AI_API_KEY),
        provider: AI_API_PROVIDER,
        model: AI_API_MODEL,
        baseUrl: AI_API_BASE_URL.replace(/\/$/, '')
    };
}

function clean(value, max = 12000) {
    return String(value || '').trim().slice(0, max);
}

function normalizeSubject(subject) {
    if (['math', 'science', 'mixed', 'auto'].includes(subject)) return subject;
    return 'auto';
}

function normalizeMessages(history = []) {
    if (!Array.isArray(history)) return [];
    return history
        .slice(-8)
        .map(item => ({
            role: item?.role === 'assistant' ? 'assistant' : 'user',
            content: clean(item?.content, 3000)
        }))
        .filter(item => item.content);
}

async function chatCompletion(messages, options = {}) {
    if (!AI_API_KEY) {
        const err = new Error('AI_API_KEY is not configured.');
        err.code = 'AI_API_NOT_CONFIGURED';
        throw err;
    }

    const payload = {
        model: options.model || AI_API_MODEL,
        messages,
        temperature: options.temperature ?? 0.2,
        top_p: options.topP ?? 0.9,
        max_tokens: options.maxTokens || 1400
    };
    if (options.json) {
        payload.response_format = { type: 'json_object' };
    }

    const response = await fetch(`${AI_API_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${AI_API_KEY}`
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(options.timeoutMs || AI_API_TIMEOUT_MS)
    });

    const raw = await response.text();
    let data = null;
    try {
        data = raw ? JSON.parse(raw) : null;
    } catch (err) {
        data = { raw };
    }

    if (!response.ok) {
        const message = data?.error?.message || data?.message || data?.raw || response.statusText;
        const err = new Error(`External AI ${response.status}: ${message}`);
        err.code = 'AI_API_REQUEST_FAILED';
        throw err;
    }

    const content = data?.choices?.[0]?.message?.content || data?.choices?.[0]?.text || '';
    if (!content.trim()) {
        const err = new Error('External AI returned an empty response.');
        err.code = 'AI_API_EMPTY_RESPONSE';
        throw err;
    }

    return {
        content: clean(content, 20000),
        raw: data
    };
}

async function askExternalAi({ message, subject = 'auto', history = [] }) {
    const question = clean(message, 6000);
    const safeSubject = normalizeSubject(subject);
    const messages = [
        {
            role: 'system',
            content: [
                'You are KITA, a Korean study assistant for middle/high-school students.',
                'Answer in Korean. Be direct, accurate, and useful for studying.',
                'Keep the answer compact unless the student asks for detail.',
                'Use this order when solving: 정답, 핵심 풀이, 왜 그런지, 조심할 실수.',
                'Use readable Markdown and LaTeX for math. Do not show broken raw code-like formulas.',
                'For exponents, write LaTeX like x^2 or \\(x^2\\), not d2/dt2 or r3.',
                'For physics units, keep units clear: m/s, m/s^2, N, J, W.',
                'Do not change the topic. In Korean, "5줄" means five lines, not five kinds or five states.',
                'If the question is not a study problem, answer normally but keep it age-appropriate.',
                'If you are unsure, say what is uncertain and give the safest next step.'
            ].join(' ')
        },
        ...normalizeMessages(history),
        {
            role: 'user',
            content: `Subject: ${safeSubject}\nQuestion:\n${question}`
        }
    ];

    const result = await chatCompletion(messages, { maxTokens: 1200, temperature: 0.25 });
    return {
        ok: true,
        provider: 'external-api',
        apiProvider: AI_API_PROVIDER,
        model: AI_API_MODEL,
        reply: result.content
    };
}

function extractJson(text) {
    const source = clean(text, 30000);
    const fenced = source.match(/```(?:json)?\s*([\s\S]*?)```/i);
    const candidate = fenced ? fenced[1] : source;
    const start = candidate.indexOf('{');
    const end = candidate.lastIndexOf('}');
    if (start === -1 || end === -1 || end <= start) throw new Error('JSON object not found in AI response.');
    return JSON.parse(candidate.slice(start, end + 1));
}

function arrayOfStrings(value) {
    if (!Array.isArray(value)) return [];
    return value.map(item => clean(item, 1000)).filter(Boolean).slice(0, 8);
}

async function solveWithExternalAi({ question, subject = 'auto', elapsedSeconds = 0, studentLevel = 'intermediate' }) {
    const problemText = clean(question, 7000);
    const safeSubject = normalizeSubject(subject);
    const messages = [
        {
            role: 'system',
            content: [
                'You are KITA, a Korean AI solver for math and science.',
                'Solve accurately before writing. Prefer exam-usable, short methods.',
                'Keep basic_solution readable, not overly long. fast_solution must be short enough for exam use.',
                'elite_solution should focus on the fastest realistic strategy and calculation reduction.',
                'All JSON string values must be written in Korean, except fixed enum values like math/science.',
                'verified_answer must contain only the exact value requested by the problem.',
                'If the problem asks for 최솟값 or 최댓값, verified_answer must be the minimum/maximum value only, not the vertex coordinate.',
                'Use readable LaTeX for expressions such as x^2, fractions, vectors, roots, derivatives, and units.',
                'Never write broken formula text like d2/dt2, r3, or v02. Use d^2/dt^2, r^3, v_0^2.',
                'Return only one valid JSON object. No Markdown fence.',
                'If information is missing, still return JSON and put warnings in quality_warnings.'
            ].join(' ')
        },
        {
            role: 'user',
            content: [
                `subject=${safeSubject}`,
                `student_level=${clean(studentLevel, 80)}`,
                `elapsed_seconds=${Number.isFinite(elapsedSeconds) ? elapsedSeconds : 0}`,
                '문제:',
                problemText,
                '',
                'JSON schema:',
                JSON.stringify({
                    analysis: {
                        subject: 'math|science|mixed',
                        unit: 'string',
                        problem_type: 'string',
                        difficulty: '하|중|상|최상',
                        intent: 'string',
                        is_killer: false
                    },
                    verified_answer: 'string',
                    basic_solution: 'string',
                    fast_solution: 'string',
                    elite_solution: 'string',
                    concept: 'string',
                    wrong_answer_reasons: ['string'],
                    similar_problem: 'string',
                    tutor_hint: 'string',
                    recommended_next_action: 'string',
                    traps: ['string'],
                    recommended_drills: ['string'],
                    time_target_seconds: 30,
                    confidence: 0.8,
                    quality_warnings: ['string']
                })
            ].join('\n')
        }
    ];

    const result = await chatCompletion(messages, { maxTokens: 1800, temperature: 0.12, json: true });
    const parsed = extractJson(result.content);
    const analysis = parsed.analysis || {};

    return {
        ok: true,
        provider: 'external-api',
        apiProvider: AI_API_PROVIDER,
        model: AI_API_MODEL,
        verifiedAnswer: clean(parsed.verified_answer || parsed.verifiedAnswer || '', 1000),
        solution: clean(parsed.basic_solution || parsed.solution || '', 8000),
        shortcut: clean(parsed.fast_solution || parsed.shortcut || '', 5000),
        concept: clean(parsed.concept || '', 4000),
        basicSolution: clean(parsed.basic_solution || parsed.solution || '', 8000),
        fastSolution: clean(parsed.fast_solution || parsed.shortcut || '', 5000),
        eliteSolution: clean(parsed.elite_solution || parsed.fast_solution || parsed.basic_solution || '', 8000),
        similarProblem: clean(parsed.similar_problem || '', 3000),
        tutorHint: clean(parsed.tutor_hint || '', 2000),
        recommendedNextAction: clean(parsed.recommended_next_action || '', 2000),
        traps: arrayOfStrings(parsed.traps || parsed.wrong_answer_reasons),
        recommendedDrills: arrayOfStrings(parsed.recommended_drills),
        timeTargetSeconds: Number(parsed.time_target_seconds) || null,
        confidence: Number(parsed.confidence) || null,
        analysis: {
            detected_subject: clean(analysis.subject || safeSubject, 80),
            detected_unit: clean(analysis.unit || '', 120),
            problem_type: clean(analysis.problem_type || '', 120),
            difficulty: clean(analysis.difficulty || '', 80),
            intent: clean(analysis.intent || '', 500),
            is_killer: Boolean(analysis.is_killer)
        },
        warnings: arrayOfStrings(parsed.quality_warnings)
    };
}

module.exports = {
    askExternalAi,
    externalAiStatus,
    solveWithExternalAi
};
