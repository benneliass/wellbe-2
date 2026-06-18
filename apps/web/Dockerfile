# syntax=docker/dockerfile:1
# Build context is the monorepo root (see infra/k8s/deploy.sh / Tiltfile).
# Next.js standalone output is used so the runtime image carries only the
# traced subset of node_modules, not the whole workspace install.

FROM node:22-alpine AS base
WORKDIR /app

# ---------------------------------------------------------------------------
# deps — install the full workspace from the lockfile. Copying only the
# manifests first keeps this layer cached across source-only changes.
# ---------------------------------------------------------------------------
FROM base AS deps
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/tsconfig/package.json packages/tsconfig/package.json
COPY packages/eslint-config/package.json packages/eslint-config/package.json
RUN npm ci

# ---------------------------------------------------------------------------
# builder — compile the Next.js app into .next/standalone. Based on `deps` so
# the full install (including non-hoisted nested node_modules such as
# packages/ui/node_modules/lucide-react) is preserved; source is layered on top
# via merge-COPY and never clobbers the installed dependency trees.
# ---------------------------------------------------------------------------
FROM deps AS builder
ENV NEXT_TELEMETRY_DISABLED=1
# Dev workspace identity + API base. NEXT_PUBLIC_* values are inlined into the
# client bundle at build time, so they must be present here (a runtime env on the
# Deployment would not reach the browser bundle). With no dev identity passed the
# build produces the calm sign-in state — these args are how the local kind chart
# opts into a pre-populated Dev workspace (see infra/k8s/deploy.sh + values.yaml).
ARG NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID=""
ARG NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID=""
ARG NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE=""
ARG NEXT_PUBLIC_WELLBE_API_URL=""
ENV NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID=$NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID
ENV NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID=$NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID
ENV NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE=$NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE
ENV NEXT_PUBLIC_WELLBE_API_URL=$NEXT_PUBLIC_WELLBE_API_URL
COPY apps/web apps/web
COPY packages packages
RUN npm run build --workspace=apps/web

# ---------------------------------------------------------------------------
# runner — minimal runtime image serving the standalone server.
# ---------------------------------------------------------------------------
FROM base AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs \
  && adduser -u 1001 -S nextjs -G nodejs

# Standalone output preserves the monorepo layout: server.js lives under
# apps/web/, with the traced node_modules at the image root.
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
