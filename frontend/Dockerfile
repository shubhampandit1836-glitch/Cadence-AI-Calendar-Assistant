FROM node:20-slim AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_DESCOPE_PROJECT_ID
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_DESCOPE_PROJECT_ID=${NEXT_PUBLIC_DESCOPE_PROJECT_ID}

COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]