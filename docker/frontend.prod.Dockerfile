# Dockerfile for React frontend - Production with Distroless
# Multi-stage build for minimal attack surface

# Stage 1: Builder
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY . .

# Build arguments for environment
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


# Stage 2: Runtime with Distroless (static files served by nginx)
# Note: For static files, we use nginx distroless
FROM nginxinc/nginx-unprivileged:alpine AS nginx-stage

# Copy build output
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx config
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

# User is already non-root in nginx-unprivileged


# Alternative: Pure distroless with custom server
# Uncomment below if you want a Node-based static server instead of nginx
# FROM gcr.io/distroless/nodejs18-debian12
# WORKDIR /app
# COPY --from=builder /app/build ./build
# COPY --from=builder /app/node_modules ./node_modules
# COPY docker/serve.js ./serve.js
# EXPOSE 3000
# CMD ["serve.js"]
