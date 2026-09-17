FROM node:20-alpine AS builder
# 註：Next.js 16要求 node >=20.9.0；node:20-alpine 標籤追蹤該系列最新版，符合需求
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# 資安：node:alpine映像檔內建非root的node使用者，切換過去執行降低容器逃逸風險
RUN chown -R node:node /app
USER node

EXPOSE 3000
CMD ["npm", "start"]
