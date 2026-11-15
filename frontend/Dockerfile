# AI contribution: 50% or more AI-generated
FROM node:24-alpine

WORKDIR /app
RUN npm install --global pnpm@10.34.6 --ignore-scripts \
    && chown node:node /app /home/node

ENV HOME=/home/node
USER node

COPY --chown=node:node package.json pnpm-lock.yaml ./
# The locked Vite toolchain gets Rolldown and Lightning CSS binaries from optional
# packages. Keep those packages installed while disabling lifecycle scripts.
RUN pnpm install --frozen-lockfile --ignore-scripts

COPY --chown=node:node index.html vite.config.ts tsconfig.json tsconfig.app.json \
    tsconfig.node.json eslint.config.js .prettierrc.json .prettierignore ./
COPY --chown=node:node src/ ./src/
COPY --chown=node:node public/ ./public/
COPY --chown=node:node scripts/ ./scripts/

EXPOSE 5173
