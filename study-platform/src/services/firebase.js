const { applicationDefault, cert, getApps, initializeApp } = require('firebase-admin/app');
const { getAuth } = require('firebase-admin/auth');

let firebaseApp = null;
let firebaseInitError = '';

function value(name) {
    return String(process.env[name] || '').trim();
}

function normalizePrivateKey(raw) {
    return String(raw || '').replace(/\\n/g, '\n');
}

function serviceAccountFromEnv() {
    if (value('FIREBASE_SERVICE_ACCOUNT_JSON')) {
        return JSON.parse(value('FIREBASE_SERVICE_ACCOUNT_JSON'));
    }
    if (value('FIREBASE_PROJECT_ID') && value('FIREBASE_CLIENT_EMAIL') && value('FIREBASE_PRIVATE_KEY')) {
        return {
            projectId: value('FIREBASE_PROJECT_ID'),
            clientEmail: value('FIREBASE_CLIENT_EMAIL'),
            privateKey: normalizePrivateKey(value('FIREBASE_PRIVATE_KEY'))
        };
    }
    return null;
}

function getFirebaseAdmin() {
    if (firebaseApp) return firebaseApp;
    try {
        const serviceAccount = serviceAccountFromEnv();
        if (serviceAccount) {
            firebaseApp = initializeApp({
                credential: cert(serviceAccount),
                projectId: serviceAccount.projectId || value('FIREBASE_PROJECT_ID')
            });
        } else if (value('GOOGLE_APPLICATION_CREDENTIALS')) {
            firebaseApp = initializeApp({
                credential: applicationDefault(),
                projectId: value('FIREBASE_PROJECT_ID') || undefined
            });
        } else if (getApps().length) {
            firebaseApp = getApps()[0];
        }
        firebaseInitError = '';
        return firebaseApp;
    } catch (err) {
        firebaseInitError = err.message;
        return null;
    }
}

function firebaseAdminStatus() {
    const configured = Boolean(
        value('FIREBASE_SERVICE_ACCOUNT_JSON')
        || value('GOOGLE_APPLICATION_CREDENTIALS')
        || value('FIREBASE_PROJECT_ID') && value('FIREBASE_CLIENT_EMAIL') && value('FIREBASE_PRIVATE_KEY')
    );
    if (configured) getFirebaseAdmin();
    return {
        configured,
        ready: Boolean(firebaseApp),
        projectId: value('FIREBASE_PROJECT_ID') || '',
        error: configured && !firebaseApp ? firebaseInitError : ''
    };
}

function firebaseClientConfig() {
    const config = {
        apiKey: value('FIREBASE_WEB_API_KEY'),
        authDomain: value('FIREBASE_AUTH_DOMAIN'),
        projectId: value('FIREBASE_PROJECT_ID'),
        appId: value('FIREBASE_APP_ID'),
        messagingSenderId: value('FIREBASE_MESSAGING_SENDER_ID'),
        storageBucket: value('FIREBASE_STORAGE_BUCKET'),
        measurementId: value('FIREBASE_MEASUREMENT_ID')
    };
    return {
        configured: Boolean(config.apiKey && config.authDomain && config.projectId && config.appId),
        config
    };
}

async function verifyFirebaseIdToken(idToken) {
    const app = getFirebaseAdmin();
    if (!app) {
        const err = new Error(firebaseInitError || 'Firebase Admin is not configured.');
        err.code = 'FIREBASE_NOT_CONFIGURED';
        throw err;
    }
    return getAuth(app).verifyIdToken(String(idToken || ''), true);
}

module.exports = {
    firebaseAdminStatus,
    firebaseClientConfig,
    verifyFirebaseIdToken
};
