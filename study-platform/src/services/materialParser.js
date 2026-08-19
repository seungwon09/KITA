const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

const MAX_INDEXED_TEXT = 240000;
const MAX_PREVIEW_TEXT = 1800;

function compactText(value, limit = MAX_INDEXED_TEXT) {
    return String(value || '')
        .replace(/\u0000/g, '')
        .replace(/[ \t]+\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
        .slice(0, limit);
}

function textResult(parseStatus, text, extra = {}) {
    const cleaned = compactText(text);
    return {
        parseStatus,
        searchText: cleaned.toLowerCase(),
        textPreview: cleaned.slice(0, MAX_PREVIEW_TEXT),
        indexedCharacters: cleaned.length,
        ...extra
    };
}

async function parsePdf(file) {
    const result = await pdf(fs.readFileSync(file.path), {
        max: 0,
        version: 'default'
    });
    const text = compactText(result.text);
    if (text.length < 80) {
        return textResult('pdf_needs_ocr', text, {
            pages: Number(result.numpages || 0),
            parser: 'pdf-parse',
            parseNote: '텍스트가 거의 없는 스캔 PDF입니다. 페이지 OCR 처리가 필요합니다.'
        });
    }
    return textResult('pdf_indexed', text, {
        pages: Number(result.numpages || 0),
        parser: 'pdf-parse',
        parseNote: 'PDF 텍스트를 자동 추출하여 검색 인덱스를 만들었습니다.'
    });
}

async function parseUploadedMaterial(file) {
    const ext = path.extname(file.originalname || file.filename || '').toLowerCase();
    const textLike = file.mimetype?.startsWith('text/') || ['.txt', '.md', '.csv', '.json'].includes(ext);

    if (ext === '.pdf' || file.mimetype === 'application/pdf') {
        try {
            return await parsePdf(file);
        } catch (err) {
            return textResult('pdf_parse_failed', '', {
                parser: 'pdf-parse',
                parseNote: `PDF 자동 분석 실패: ${err.message}`
            });
        }
    }

    if (textLike) {
        return textResult('text_indexed', fs.readFileSync(file.path, 'utf8'), {
            parser: 'plain-text',
            parseNote: '텍스트 자료를 검색 인덱스에 등록했습니다.'
        });
    }

    if (file.mimetype?.startsWith('image/')) {
        return textResult('image_needs_ocr', '', {
            parser: 'pending-ocr',
            parseNote: '이미지 자료입니다. 문제 사진 OCR에서 분석할 수 있습니다.'
        });
    }

    return textResult('stored_needs_parser', '', {
        parser: 'none',
        parseNote: '파일을 보관했습니다. 이 형식의 자동 분석기는 아직 연결되지 않았습니다.'
    });
}

module.exports = { parseUploadedMaterial };
