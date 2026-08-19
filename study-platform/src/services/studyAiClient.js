const STUDY_AI_BASE_URL = (process.env.STUDY_AI_BASE_URL || 'http://127.0.0.1:8002').replace(/\/$/, '');

function compactText(value) {
    return String(value || '').trim();
}

function normalizeSubject(subject) {
    if (subject === 'math' || subject === 'science') return subject;
    return 'auto';
}

function numericCoefficient(value, fallback = 1) {
    if (value === '' || value === '+') return fallback;
    if (value === '-') return -fallback;
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

function formatNumber(value) {
    if (!Number.isFinite(value)) return '';
    if (Math.abs(value - Math.round(value)) < 1e-9) return String(Math.round(value));
    return String(Number(value.toFixed(4)));
}

async function requestJson(path, options = {}) {
    const timeoutMs = options.timeoutMs || 45000;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(`${STUDY_AI_BASE_URL}${path}`, {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                ...(options.headers || {})
            },
            body: options.body ? JSON.stringify(options.body) : undefined,
            signal: controller.signal
        });

        const text = await response.text();
        let data = null;
        try {
            data = text ? JSON.parse(text) : null;
        } catch (err) {
            data = { raw: text };
        }

        if (!response.ok) {
            const detail = data?.detail || data?.message || data?.raw || response.statusText;
            throw new Error(`Study AI ${response.status}: ${detail}`);
        }
        return data;
    } finally {
        clearTimeout(timer);
    }
}

async function requestStudyAi(path, options = {}) {
    return requestJson(path, options);
}

async function requestMultipart(path, formData, options = {}) {
    const timeoutMs = options.timeoutMs || 60000;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(`${STUDY_AI_BASE_URL}${path}`, {
            method: options.method || 'POST',
            body: formData,
            signal: controller.signal
        });

        const text = await response.text();
        let data = null;
        try {
            data = text ? JSON.parse(text) : null;
        } catch (err) {
            data = { raw: text };
        }

        if (!response.ok) {
            const detail = data?.detail || data?.message || data?.raw || response.statusText;
            throw new Error(`Study AI ${response.status}: ${detail}`);
        }
        return data;
    } finally {
        clearTimeout(timer);
    }
}

async function checkStudyAiHealth() {
    try {
        const health = await requestJson('/health', { timeoutMs: 5000 });
        return { ok: true, baseUrl: STUDY_AI_BASE_URL, health };
    } catch (err) {
        return { ok: false, baseUrl: STUDY_AI_BASE_URL, error: err.message };
    }
}

function inferQuadraticExtreme(problemText) {
    const text = compactText(problemText)
        .replace(/[−–—]/g, '-')
        .replace(/²/g, '^2')
        .replace(/\s+/g, '');

    if (!/x\^2/.test(text) || !/(최솟값|최소값|최댓값|최대값)/.test(text)) return null;

    const match = text.match(/(?:y=)?([+-]?(?:\d+(?:\.\d+)?)?)x\^2([+-](?:\d+(?:\.\d+)?)?)x?([+-]\d+(?:\.\d+)?)?/);
    if (!match) return null;

    const a = numericCoefficient(match[1], 1);
    const b = numericCoefficient(match[2], 1);
    const c = Number(match[3] || 0);
    if (!Number.isFinite(a) || !Number.isFinite(b) || !Number.isFinite(c) || a === 0) return null;

    const vertexX = -b / (2 * a);
    const vertexY = a * vertexX * vertexX + b * vertexX + c;
    const wantsMin = /(최솟값|최소값)/.test(text);
    const wantsMax = /(최댓값|최대값)/.test(text);
    const validExtreme = (wantsMin && a > 0) || (wantsMax && a < 0) || (!wantsMin && !wantsMax);
    if (!validExtreme) return null;

    return {
        answer: formatNumber(vertexY),
        x: formatNumber(vertexX),
        basic: [
            `이차함수의 꼭짓점 x좌표는 -b/(2a)=${formatNumber(vertexX)}입니다.`,
            `x=${formatNumber(vertexX)}를 원래 식에 대입하면 y=${formatNumber(vertexY)}입니다.`,
            a > 0 ? `그래프가 위로 열리므로 최솟값은 ${formatNumber(vertexY)}입니다.` : `그래프가 아래로 열리므로 최댓값은 ${formatNumber(vertexY)}입니다.`
        ].join('\n'),
        fast: `꼭짓점만 보면 됩니다. x=-b/(2a)=${formatNumber(vertexX)}, y=${formatNumber(vertexY)}이므로 답은 ${formatNumber(vertexY)}입니다.`
    };
}

function localFallbackSolve(problemText, subject = 'auto', error = null) {
    const inferred = inferQuadraticExtreme(problemText);
    if (inferred) {
        return {
            ok: true,
            provider: 'kita-local-fallback',
            baseUrl: STUDY_AI_BASE_URL,
            verifiedAnswer: inferred.answer,
            solution: inferred.basic,
            shortcut: inferred.fast,
            concept: '이차함수의 최댓값/최솟값은 꼭짓점에서 확인합니다.',
            basicSolution: inferred.basic,
            fastSolution: inferred.fast,
            eliteSolution: inferred.fast,
            similarProblem: 'y=x^2-6x+5의 최솟값을 구하시오.',
            tutorHint: '완전제곱식으로 바꾸거나 x=-b/(2a)를 사용하세요.',
            recommendedNextAction: '비슷한 이차함수 최솟값 문제를 3개 더 풀어보세요.',
            traps: ['-b/(2a) 부호 실수', '최솟값과 그때의 x값 혼동'],
            recommendedDrills: ['꼭짓점 구하기', '완전제곱식 변형', '최대/최소 판별'],
            timeTargetSeconds: 25,
            confidence: 0.9,
            analysis: { detected_subject: subject, problem_type: '이차함수 최적화', detected_unit: '이차함수' },
            warnings: error ? [error.message] : []
        };
    }

    return {
        ok: false,
        provider: 'kita-local-fallback',
        baseUrl: STUDY_AI_BASE_URL,
        solution: 'Study AI 서버와 연결하지 못했습니다. 문제 식을 더 구체적으로 입력하면 기본 규칙으로도 풀이를 시도할 수 있습니다.',
        shortcut: '서버를 다시 켠 뒤 재시도해 주세요.',
        concept: error?.message || '',
        warnings: ['study_ai_unreachable']
    };
}

async function solveWithStudyAi({ question, subject, userId, elapsedSeconds }) {
    const problemText = compactText(question);
    const normalizedSubject = normalizeSubject(subject);
    if (!problemText) {
        return {
            ok: false,
            provider: 'study-ai-local',
            solution: '문제를 먼저 입력해 주세요.',
            shortcut: '',
            concept: '',
            warnings: ['empty_question']
        };
    }

    let elite = null;
    let solve = null;

    try {
        elite = await requestJson('/app-ai/elite/solution', {
            method: 'POST',
            timeoutMs: 16000,
            body: {
                user_id: userId || 'kita-user',
                problem_text: problemText,
                subject: normalizedSubject,
                student_level: 'advanced',
                elapsed_seconds: Number.isFinite(elapsedSeconds) ? elapsedSeconds : null,
                mode: 'exam',
                include_drills: true
            }
        });
    } catch (err) {
        elite = null;
    }

    try {
        const detectedSubject = elite?.recognition?.detected_subject || normalizedSubject || 'math';
        solve = await requestJson('/solve', {
            method: 'POST',
            timeoutMs: 6000,
            body: {
                user_id: userId || 'kita-user',
                problem_text: problemText,
                subject: detectedSubject === 'science' ? 'science' : 'math',
                elapsed_seconds: Number.isFinite(elapsedSeconds) ? elapsedSeconds : null,
                mode: 'compare'
            }
        });
    } catch (err) {
        solve = null;
    }

    if (!elite && !solve) {
        return localFallbackSolve(problemText, normalizedSubject, new Error('Study AI 응답 없음'));
    }

    const inferred = inferQuadraticExtreme(problemText);
    const analysis = elite?.recognition || solve?.analysis || {};
    const selectedPattern = Array.isArray(elite?.selected_patterns) ? elite.selected_patterns[0] : null;
    const verifiedAnswer = elite?.verified_answer || solve?.verified_answer || inferred?.answer || null;
    const basicSolution = solve?.basic_solution || inferred?.basic || elite?.top_student_solution || '풀이를 생성했습니다.';
    const fastSolution = solve?.fast_solution || elite?.exam_shortcut || inferred?.fast || '';
    const eliteSolution = elite?.top_student_solution || fastSolution || basicSolution;
    const concept = [
        analysis.detected_unit ? `단원: ${analysis.detected_unit}` : null,
        analysis.problem_type ? `유형: ${analysis.problem_type}` : null,
        selectedPattern?.shortcut ? `상위권 패턴: ${selectedPattern.shortcut}` : null,
        elite?.calculation_reduction ? `계산 줄이기: ${elite.calculation_reduction}` : null
    ].filter(Boolean).join('\n');

    return {
        ok: true,
        provider: 'study-ai-local',
        baseUrl: STUDY_AI_BASE_URL,
        verifiedAnswer,
        solution: basicSolution,
        shortcut: fastSolution,
        concept,
        basicSolution,
        fastSolution,
        eliteSolution,
        similarProblem: solve?.similar_problem || '',
        tutorHint: solve?.tutor_hint || '',
        recommendedNextAction: elite?.next_action || solve?.recommended_next_action || '',
        traps: elite?.traps || [],
        recommendedDrills: elite?.recommended_drills || [],
        timeTargetSeconds: elite?.time_target_seconds || null,
        confidence: elite?.confidence || analysis.confidence || null,
        dataReadinessPercent: elite?.data_readiness_percent || null,
        analysis,
        raw: { elite, solve }
    };
}

module.exports = {
    STUDY_AI_BASE_URL,
    checkStudyAiHealth,
    requestMultipart,
    requestStudyAi,
    solveWithStudyAi
};
