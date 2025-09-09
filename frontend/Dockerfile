FROM node:20-alpine AS deps
WORKDIR /app
# Root workspace manifests
COPY package.json package-lock.json ./
# Workspace package manifests needed for a clean install
COPY packages/api-client/package.json packages/api-client/package.json
COPY apps/web/package.json apps/web/package.json
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Build workspace packages first, then Next standalone output
RUN npm run build -w packages/api-client && npm run build -w apps/web

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# Copy only what Next needs to run standalone
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
EXPOSE 3000
CMD ["node","apps/web/server.js"]
