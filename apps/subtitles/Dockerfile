FROM node:20-alpine AS build
WORKDIR /app
COPY apps/subtitles/package*.json ./
RUN npm ci
COPY apps/subtitles/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist/subtitles-frontend/browser /usr/share/nginx/html
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf
