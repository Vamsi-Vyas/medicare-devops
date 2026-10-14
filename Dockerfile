FROM nginxinc/nginx-unprivileged:alpine

COPY app/index.html /usr/share/nginx/html/index.html

USER 101

EXPOSE 8080
