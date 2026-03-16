FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Polyfill CustomEvent for Node.js (needed by @xyflow/react during build)
RUN echo "if(!globalThis.CustomEvent){globalThis.CustomEvent=class extends Event{constructor(e,t={}){super(e,t);this.detail=t.detail}}}" > /tmp/polyfill.js
RUN node -r /tmp/polyfill.js ./node_modules/.bin/vite build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3001
CMD ["nginx", "-g", "daemon off;"]
