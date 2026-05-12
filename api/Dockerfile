FROM node:20-alpine

WORKDIR /app

COPY api/package*.json ./
RUN npm install

COPY api/src ./src
COPY api/shared ./shared

CMD ["node", "src/server.js"]