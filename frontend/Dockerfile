# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy manifests first for layer caching.
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

# Copy source and build.
COPY . .

# VITE_API_URL is baked in at build time. When running behind nginx on the
# same origin the default "/api" proxy works for local dev, but for a
# cross-origin Render backend you need to pass the real URL here:
#   docker build --build-arg VITE_API_URL=https://your-render-app.onrender.com
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove the default nginx welcome page.
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets.
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config: serve the SPA and proxy /api to the backend.
# The BACKEND_URL env var is substituted at container start via envsubst.
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80

# envsubst rewrites the template with runtime env vars before nginx starts.
CMD ["/bin/sh", "-c", \
  "envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
