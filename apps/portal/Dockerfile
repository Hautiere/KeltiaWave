FROM nginx:1.27-alpine

COPY apps/portal/index.html /usr/share/nginx/html/index.html
COPY apps/portal/assets /usr/share/nginx/html/assets
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf
