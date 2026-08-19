const express = require('express');

const { addFailure, loadStore, metrics } = require('../services/qualityStore');

const router = express.Router();

router.get('/status', (req, res) => {
    const current = metrics(loadStore());
    res.json({
        ok: true,
        benchmarkCases: current.benchmarkCases,
        benchmarkRuns: current.benchmarkRuns,
        latestAccuracy: current.latestAccuracy,
        message: 'KITA는 검증 문제와 사용자 신고를 바탕으로 풀이 품질을 개선합니다.'
    });
});

router.post('/report', (req, res) => {
    const body = req.body || {};
    if (!String(body.question || '').trim()) return res.status(400).json({ ok: false, error: '문제를 입력해 주세요.' });
    const failure = addFailure({
        subject: body.subject || 'auto',
        unit: body.unit || '',
        question: body.question,
        expectedAnswer: body.correctAnswer || body.expectedAnswer || '',
        actualAnswer: body.aiAnswer || body.actualAnswer || '',
        actualSolution: body.aiSolution || '',
        correctedSolution: body.correctedSolution || '',
        category: body.category || 'user_report',
        source: 'user_report',
        note: body.note || ''
    });
    res.json({ ok: true, reportId: failure.id, message: '신고가 저장되었습니다. 관리자 개선 목록에 반영합니다.' });
});

module.exports = router;
