require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });

const fs = require('fs');
const path = require('path');
const mongoose = require('mongoose');

async function main() {
    const outputDir = process.argv[2];
    if (!outputDir) throw new Error('Backup output directory is required.');
    fs.mkdirSync(outputDir, { recursive: true });

    const uri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/kita';
    await mongoose.connect(uri);
    const db = mongoose.connection.db;
    const collections = await db.listCollections().toArray();
    const manifest = {
        createdAt: new Date().toISOString(),
        uri: uri.replace(/\/\/.*@/, '//***@'),
        collections: []
    };

    for (const item of collections) {
        const docs = await db.collection(item.name).find({}).toArray();
        const fileName = `${item.name}.json`;
        fs.writeFileSync(path.join(outputDir, fileName), JSON.stringify(docs, null, 2), 'utf8');
        manifest.collections.push({ name: item.name, count: docs.length, file: fileName });
    }

    fs.writeFileSync(path.join(outputDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
    await mongoose.disconnect();
}

main().catch(async err => {
    console.error(err.message);
    try { await mongoose.disconnect(); } catch (_) {}
    process.exit(1);
});

