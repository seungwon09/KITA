FROM node:22-bookworm-slim

WORKDIR /app

ENV NODE_ENV=production

COPY package*.json ./
RUN npm ci --omit=dev

COPY src ./src
COPY public ./public

RUN mkdir -p data uploads \
    && chown -R node:node /app

USER node

EXPOSE 3000

CMD ["node", "src/server.js"]
