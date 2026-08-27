FROM node:20-alpine AS build

WORKDIR /app
COPY apps/corpus/package*.json ./
RUN npm ci

COPY apps/corpus/ .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
