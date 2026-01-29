FROM node:18-alpine

WORKDIR /app

# Копирование package файлов
COPY package*.json ./

# Установка зависимостей
RUN npm install

# Копирование исходного кода
COPY . .

# Переменные окружения
ARG REACT_APP_API_URL
ARG REACT_APP_WS_URL
ARG REACT_APP_YANDEX_MAPS_API_KEY

ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_WS_URL=$REACT_APP_WS_URL
ENV REACT_APP_YANDEX_MAPS_API_KEY=$REACT_APP_YANDEX_MAPS_API_KEY

# Сборка приложения
RUN npm run build

# Production сервер
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
