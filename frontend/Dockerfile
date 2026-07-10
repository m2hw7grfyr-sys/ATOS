FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json frontend/pnpm-lock.yaml* frontend/pnpm-workspace.yaml* /app/
RUN corepack enable && pnpm install

COPY frontend /app

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
