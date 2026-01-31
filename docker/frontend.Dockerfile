# Dockerfile for React frontend - Development
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source (will be overridden by volume mount in dev)
COPY . .

# Expose port
EXPOSE 3000

# Start React development server (not the Node.js backend)
CMD ["npm", "run", "frontend"]
