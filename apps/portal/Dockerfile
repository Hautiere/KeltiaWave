FROM nginx:1.27-alpine

COPY apps/portal/index.html /usr/share/nginx/html/index.html
COPY apps/portal/about.html /usr/share/nginx/html/about.html
COPY apps/portal/feedback.html /usr/share/nginx/html/feedback.html
COPY apps/portal/portal-pages.css /usr/share/nginx/html/portal-pages.css
COPY apps/portal/assets /usr/share/nginx/html/assets
COPY deploy/nginx-portal.conf /etc/nginx/conf.d/default.conf
