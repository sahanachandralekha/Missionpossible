# Multi-stage production build Dockerfile for ScamCheck Frontend
FROM node:20-alpine as builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginx:alpine as runner

COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx configuration for SPA routing fallback to index.html
RUN echo $'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html index.htm;\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
