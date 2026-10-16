# ShopSmart AI - Frontend Dockerfile
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Backend URL baked into the bundle (Vite reads VITE_* at build time)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Security headers; the CSP lets the app call the backend at VITE_API_URL's origin.
ARG VITE_API_URL
COPY security-headers.conf /etc/nginx/security-headers.conf
RUN api_origin=$(printf '%s' "$VITE_API_URL" | sed -E 's#^([a-zA-Z]+://[^/]+).*#\1#') && \
    sed -i "s#__API_ORIGIN__#${api_origin}#" /etc/nginx/security-headers.conf

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
