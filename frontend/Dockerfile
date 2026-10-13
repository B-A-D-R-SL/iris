# AI contribution: 50% or more AI-generated
FROM node:24-alpine

WORKDIR /app
RUN npm install --global pnpm@10.34.6
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .

EXPOSE 5173
