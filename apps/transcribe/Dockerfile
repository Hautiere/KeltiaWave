FROM node:20-alpine AS build
WORKDIR /app
COPY apps/transcribe/package*.json ./
RUN npm ci
COPY apps/transcribe/ .
COPY apps/shared/ /shared/
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist/transcribe-frontend/browser /usr/share/nginx/html
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf
