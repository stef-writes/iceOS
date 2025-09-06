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
# Build workspace packages first, then the web app
RUN npm run build -w packages/api-client && npm run build -w apps/web

FROM node:20-alpine AS runner
# Keep workspace node_modules at /app/node_modules
WORKDIR /app/apps/web
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# Bring built app and deps
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/apps/web/.next ./.next
COPY --from=builder /app/apps/web/package.json ./package.json
EXPOSE 3000
CMD ["npm","run","start","--","-p","3000","-H","0.0.0.0"]
