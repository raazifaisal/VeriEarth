# VeriEarth web (Next.js standalone) for Cloud Run.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# The API URL is baked in at build time (NEXT_PUBLIC_*).
ARG NEXT_PUBLIC_VERI_API
ENV NEXT_PUBLIC_VERI_API=$NEXT_PUBLIC_VERI_API NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=8080 HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
CMD ["node", "server.js"]
